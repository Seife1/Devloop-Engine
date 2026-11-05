import io
import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

from learnloop.daemon import (
    DEFAULT_PORT,
    detect_topology,
    get_learnloop_home,
    get_pid_path,
    is_daemon_running,
    is_pid_alive,
    probe_endpoint,
)


def test_get_learnloop_home():
    home = get_learnloop_home()
    assert home.exists()
    assert home.name == ".learnloop"


def test_get_pid_path():
    p = get_pid_path()
    assert p.name == "daemon.pid"


def test_detect_topology_native():
    with patch.dict(os.environ, {}, clear=True), patch("platform.system", return_value="Darwin"):
        topo = detect_topology()
        assert topo["platform"] == "Darwin"
        assert topo["environment"] == "native"
        assert topo["is_native"] is True
        assert topo["is_wsl"] is False
        assert topo["is_container"] is False
        assert topo["is_ssh"] is False
        assert topo["port"] == DEFAULT_PORT
        assert topo["mcp_url"] == f"http://127.0.0.1:{DEFAULT_PORT}/mcp"
        assert topo["sse_url"] == f"http://127.0.0.1:{DEFAULT_PORT}/sse"
        assert topo["forward_cmd"] is None


def test_detect_topology_wsl():
    with patch.dict(os.environ, {"WSL_DISTRO_NAME": "Ubuntu"}, clear=True), patch("platform.system", return_value="Linux"):
        topo = detect_topology()
        assert topo["environment"] == "wsl"
        assert topo["is_wsl"] is True
        assert topo["is_native"] is False


def test_detect_topology_container():
    with patch.dict(os.environ, {"DEVCONTAINER": "true"}, clear=True), patch("platform.system", return_value="Linux"):
        topo = detect_topology()
        assert topo["environment"] == "devcontainer"
        assert topo["is_container"] is True
        assert topo["is_native"] is False
        assert "Forward container port" in str(topo["forward_cmd"])


def test_detect_topology_ssh():
    with patch.dict(os.environ, {"SSH_CONNECTION": "192.168.1.10 50000 192.168.1.20 22"}, clear=True):
        topo = detect_topology()
        assert topo["environment"] == "ssh"
        assert topo["is_ssh"] is True
        assert topo["is_native"] is False
        assert "ssh -L" in str(topo["forward_cmd"])


def test_is_pid_alive_invalid():
    assert is_pid_alive(-1) is False
    assert is_pid_alive(0) is False


def test_is_daemon_running_mock():
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        assert is_daemon_running(port=8765) is True

    with patch("urllib.request.urlopen", side_effect=Exception("Connection refused")):
        assert is_daemon_running(port=8765) is False


def test_probe_endpoint_success():
    health_payload = json.dumps({
        "status": "healthy",
        "database": {"status": "healthy"},
        "tools_available": 4
    }).encode("utf-8")

    tools_payload = json.dumps({
        "jsonrpc": "2.0",
        "result": {
            "tools": [
                {"name": "track_intent"},
                {"name": "manage_reviews"},
                {"name": "manage_knowledge"},
                {"name": "explore_project"},
            ]
        }
    }).encode("utf-8")

    def mock_urlopen(req, timeout=1.0):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        mock = MagicMock()
        mock.__enter__.return_value = mock
        if "/health" in url:
            mock.read.return_value = health_payload
        elif "/mcp/v1/tools" in url:
            mock.read.return_value = tools_payload
        return mock

    with patch("urllib.request.urlopen", side_effect=mock_urlopen):
        res = probe_endpoint("http://127.0.0.1:8765")
        assert res["reachable"] is True
        assert res["status"] == "healthy"
        assert res["db_healthy"] is True
        assert "track_intent" in res["tools"]
        assert "explore_project" in res["tools"]
        assert len(res["tools"]) == 4


def test_probe_endpoint_failure():
    with patch("urllib.request.urlopen", side_effect=Exception("Timeout")):
        res = probe_endpoint("http://127.0.0.1:8765")
        assert res["reachable"] is False
        assert res["status"] == "unreachable"
        assert res["tools"] == []
        assert "Timeout" in res["error"]

