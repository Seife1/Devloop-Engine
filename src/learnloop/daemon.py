"""LearnLoop Daemon Lifecycle, Topology Detection & Reachability Prober.

Provides automatic background daemon management, cross-environment topology
detection (Native, WSL2, DevContainers, Remote SSH), and live MCP protocol
health probes.
"""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_PORT = 8765
DEFAULT_HOST = "0.0.0.0"


def get_learnloop_home() -> Path:
    """Return user's ~/.learnloop directory."""
    p = Path.home() / ".learnloop"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_pid_path() -> Path:
    """Return path to the active daemon PID file."""
    return get_learnloop_home() / "daemon.pid"


def get_daemon_log_path() -> Path:
    """Return path to the daemon output log file."""
    log_dir = get_learnloop_home() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "daemon.log"


def detect_topology() -> dict[str, Any]:
    """Detect the host-guest execution environment and network topology."""
    sys_name = platform.system()
    is_wsl = False
    is_container = False
    is_ssh = bool(os.environ.get("SSH_CONNECTION") or os.environ.get("SSH_CLIENT") or os.environ.get("SSH_TTY"))

    if sys_name == "Linux":
        # Check WSL
        try:
            if Path("/proc/version").exists():
                proc_ver = Path("/proc/version").read_text(encoding="utf-8").lower()
                if "microsoft" in proc_ver or "wsl" in proc_ver:
                    is_wsl = True
        except Exception:
            pass

        if "WSL_DISTRO_NAME" in os.environ or "WSL_INTEROP" in os.environ:
            is_wsl = True

        # Check Docker / DevContainer
        if Path("/.dockerenv").exists() or os.environ.get("DEVCONTAINER") == "true" or "REMOTE_CONTAINERS" in os.environ:
            is_container = True

    env_type = "native"
    if is_wsl:
        env_type = "wsl"
    elif is_container:
        env_type = "devcontainer"
    elif is_ssh:
        env_type = "ssh"

    forward_cmd = None
    if is_ssh:
        forward_cmd = f"ssh -L {DEFAULT_PORT}:localhost:{DEFAULT_PORT} <user>@<remote-host>"
    elif is_container:
        forward_cmd = f"Forward container port {DEFAULT_PORT} -> host {DEFAULT_PORT}"

    return {
        "platform": sys_name,
        "environment": env_type,
        "is_wsl": is_wsl,
        "is_container": is_container,
        "is_ssh": is_ssh,
        "is_native": (env_type == "native"),
        "bind_host": DEFAULT_HOST,
        "port": DEFAULT_PORT,
        "local_url": f"http://127.0.0.1:{DEFAULT_PORT}",
        "mcp_url": f"http://127.0.0.1:{DEFAULT_PORT}/mcp",
        "sse_url": f"http://127.0.0.1:{DEFAULT_PORT}/sse",
        "forward_cmd": forward_cmd,
    }


def is_pid_alive(pid: int) -> bool:
    """Check whether a process with the given PID is running."""
    if pid <= 0:
        return False
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            SYNCHRONIZE = 0x00100000
            process = kernel32.OpenProcess(SYNCHRONIZE, False, pid)
            if process != 0:
                kernel32.CloseHandle(process)
                return True
            return False
        except Exception:
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


def is_daemon_running(port: int = DEFAULT_PORT, host: str = "127.0.0.1", timeout: float = 0.6) -> bool:
    """Probe the health endpoint to see if the HTTP/SSE daemon is responding."""
    url = f"http://{host}:{port}/health"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "LearnLoop-Doctor/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def get_current_pid() -> int | None:
    """Read PID from ~/.learnloop/daemon.pid if valid and alive."""
    pid_file = get_pid_path()
    if not pid_file.exists():
        return None
    try:
        pid = int(pid_file.read_text(encoding="utf-8").strip())
        if is_pid_alive(pid):
            return pid
    except Exception:
        pass
    return None


def stop_daemon() -> bool:
    """Stop the running LearnLoop background daemon process if active."""
    pid = get_current_pid()
    pid_file = get_pid_path()
    stopped = False

    if pid and is_pid_alive(pid):
        try:
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/F", "/PID", str(pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
            else:
                import signal
                os.kill(pid, signal.SIGTERM)
                time.sleep(0.2)
                if is_pid_alive(pid):
                    os.kill(pid, signal.SIGKILL)
            stopped = True
        except Exception:
            pass

    if pid_file.exists():
        try:
            pid_file.unlink()
        except Exception:
            pass

    return stopped


def ensure_daemon(
    port: int = DEFAULT_PORT,
    host: str = DEFAULT_HOST,
    wait_timeout: float = 3.5,
) -> dict[str, Any]:
    """Ensure the LearnLoop streamable HTTP/SSE daemon is running, spawning it if needed."""
    if is_daemon_running(port=port):
        return {
            "status": "running",
            "already_running": True,
            "port": port,
            "pid": get_current_pid(),
            "url": f"http://127.0.0.1:{port}",
        }

    # Prepare command to launch daemon in background
    cmd = [
        sys.executable,
        "-m",
        "learnloop.http_server",
        "--host",
        host,
        "--port",
        str(port),
    ]

    kwargs: dict[str, Any] = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }

    if sys.platform == "win32":
        DETACHED_PROCESS = 0x00000008
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        kwargs["creationflags"] = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True

    proc = None
    try:
        proc = subprocess.Popen(cmd, **kwargs)
        pid = proc.pid
        get_pid_path().write_text(str(pid), encoding="utf-8")
    except PermissionError:
        # Fallback if running inside a restricted job object
        try:
            kwargs.pop("creationflags", None)
            proc = subprocess.Popen(cmd, **kwargs)
            pid = proc.pid
            get_pid_path().write_text(str(pid), encoding="utf-8")
        except Exception as exc:
            return {
                "status": "error",
                "already_running": False,
                "error": f"Failed to spawn daemon: {exc}",
                "port": port,
                "pid": None,
            }
    except Exception as exc:
        return {
            "status": "error",
            "already_running": False,
            "error": f"Failed to spawn daemon: {exc}",
            "port": port,
            "pid": None,
        }

    # Wait for daemon to become ready
    deadline = time.time() + wait_timeout
    ready = False
    while time.time() < deadline:
        if is_daemon_running(port=port):
            ready = True
            break
        time.sleep(0.15)

    log_file = get_daemon_log_path()
    return {
        "status": "started" if ready else "timeout",
        "already_running": False,
        "port": port,
        "pid": pid,
        "ready": ready,
        "url": f"http://127.0.0.1:{port}",
        "log_path": str(log_file),
    }


def probe_endpoint(base_url: str = f"http://127.0.0.1:{DEFAULT_PORT}", timeout: float = 1.5) -> dict[str, Any]:
    """Perform a live handshake against the LearnLoop hosted endpoint and verify tool registration."""
    health_url = f"{base_url.rstrip('/')}/health"
    tools_url = f"{base_url.rstrip('/')}/mcp/v1/tools"

    t0 = time.perf_counter()
    try:
        req = urllib.request.Request(health_url, headers={"User-Agent": "LearnLoop-Doctor/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            latency_ms = round((time.perf_counter() - t0) * 1000, 1)

        # Check database health
        db_val = data.get("database")
        db_healthy = False
        if isinstance(db_val, dict):
            db_healthy = db_val.get("status") == "healthy"
        elif db_val:
            try:
                db_healthy = Path(str(db_val)).exists()
            except Exception:
                db_healthy = True

        # Query tools
        tools: list[str] = []
        try:
            req_tools = urllib.request.Request(tools_url, headers={"User-Agent": "LearnLoop-Doctor/1.0"})
            with urllib.request.urlopen(req_tools, timeout=timeout) as t_resp:
                tools_data = json.loads(t_resp.read().decode("utf-8"))
                raw_tools = []
                if isinstance(tools_data, dict):
                    if "result" in tools_data and isinstance(tools_data["result"], dict):
                        raw_tools = tools_data["result"].get("tools", [])
                    elif "tools" in tools_data:
                        raw_tools = tools_data.get("tools", [])
                elif isinstance(tools_data, list):
                    raw_tools = tools_data
                
                if isinstance(raw_tools, list):
                    tools = [t.get("name", "") for t in raw_tools if isinstance(t, dict) and t.get("name")]
        except Exception:
            pass

        return {
            "reachable": True,
            "latency_ms": latency_ms,
            "status": data.get("status", "healthy"),
            "db_healthy": db_healthy,
            "tools": tools,
            "error": None,
        }
    except Exception as exc:
        return {
            "reachable": False,
            "latency_ms": None,
            "status": "unreachable",
            "db_healthy": False,
            "tools": [],
            "error": str(exc),
        }
