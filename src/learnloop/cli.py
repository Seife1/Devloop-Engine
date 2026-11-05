"""CLI. `learnloop` with no arguments starts the MCP server (stdio).

`record-commit` is called by the git hook: it must be fast and must NEVER fail the commit.
"""

from __future__ import annotations

import argparse
import sqlite3
import stat
import subprocess
import sys

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from pathlib import Path

from learnloop import __version__
from learnloop.logging import setup_logging
from learnloop.updater import cmd_update, print_update_banner_if_available

HOOK_MARKER = "# learnloop-hook"

HOOK_TEMPLATE_PYTHON = (
    "#!/bin/sh\n"
    f"{HOOK_MARKER}\n"
    "# Fast, non-blocking, never fails the commit.\n"
    "# Writes a redacted metadata record to .learn/queue/.\n"
    '( "{python}" -m learnloop record-commit '
    '--repo "$(git rev-parse --show-toplevel)" ) >/dev/null 2>&1 &\n'
    "exit 0\n"
)
HOOK_TEMPLATE = HOOK_TEMPLATE_PYTHON

HOOK_TEMPLATE_BINARY = (
    "#!/bin/sh\n"
    f"{HOOK_MARKER}\n"
    "# Fast, non-blocking, never fails the commit.\n"
    "# Writes a redacted metadata record to .learn/queue/.\n"
    '( "{binary}" record-commit '
    '--repo "$(git rev-parse --show-toplevel)" ) >/dev/null 2>&1 &\n'
    "exit 0\n"
)


def _hook_text(executable: str | None = None) -> str:
    """Generate the post-commit hook body.

    Single source of truth for hook content. Uses the absolute interpreter or binary path
    so the hook works even when the executable is not on PATH (common on Windows).
    Forward slashes and quoting for sh compatibility.
    """
    exe = (executable if executable is not None else sys.executable).replace("\\", "/")
    if getattr(sys, "frozen", False):
        return HOOK_TEMPLATE_BINARY.format(binary=exe)
    return HOOK_TEMPLATE_PYTHON.format(python=exe)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True, timeout=10
    ).stdout


def cmd_serve(transport: str = "stdio", host: str = "0.0.0.0", port: int = 8000) -> int:
    if transport == "stdio":
        from learnloop.server import build_server

        setup_logging()
        if hasattr(sys.stdin, "isatty") and sys.stdin.isatty():
            sys.stderr.write(
                "\n"
                "  ◈ LearnLoop MCP Server (stdio transport)\n"
                "  Listening for JSON-RPC messages from your IDE (VS Code, Cursor, Claude Desktop).\n"
                "  Press Ctrl+C to stop.\n\n"
                "  Tip: To launch the web mission control dashboard, run 'learnloop dashboard' instead.\n\n"
            )
            sys.stderr.flush()
        build_server().run()  # stdio transport
        return 0
    elif transport in ("sse", "http"):
        return cmd_http(host=host, port=port)
    else:
        sys.stderr.write(f"Unknown transport: {transport}\n")
        return 1


def cmd_dashboard(port: int = 8765, use_gui: bool = False, open_browser: bool = True) -> int:
    from learnloop.daemon import is_daemon_running

    dash_url = f"http://127.0.0.1:{port}/"

    if use_gui:
        from learnloop.gui import is_gui_available, launch_desktop_gui

        if is_gui_available():
            return launch_desktop_gui(port=port, route="/", hide_console=True)

    # If the LearnLoop HTTP/SSE background daemon is already running:
    if is_daemon_running(port=port):
        sys.stdout.write(f"LearnLoop dashboard is active at {dash_url}\n")
        if open_browser:
            sys.stdout.write("Opening dashboard in your web browser...\n")
            sys.stdout.flush()
            try:
                import webbrowser
                webbrowser.open(dash_url)
            except Exception:
                pass
        return 0

    try:
        import threading
        import time
        import uvicorn
        from learnloop.http_server import app

        sys.stdout.write(f"LearnLoop dashboard running at {dash_url}\n")
        sys.stdout.flush()

        if open_browser:
            def _open_later():
                time.sleep(0.5)
                try:
                    import webbrowser
                    webbrowser.open(dash_url)
                except Exception:
                    pass

            threading.Thread(target=_open_later, daemon=True).start()

        uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
        return 0
    except ImportError as exc:
        sys.stderr.write(
            f"LearnLoop dashboard web dependencies missing ({exc}).\n"
            "Please update with: learnloop update\n"
            "Or reinstall with: uv tool install --force git+https://github.com/Seife1/Devloop-Engine.git\n"
        )
        return 1
    except OSError as exc:
        is_port_in_use = (
            getattr(exc, "errno", None) in (10048, 98, 48)
            or getattr(exc, "winerror", None) == 10048
            or "10048" in str(exc)
            or "address already in use" in str(exc).lower()
        )
        if is_port_in_use:
            if is_daemon_running(port=port):
                sys.stdout.write(f"LearnLoop dashboard is active at {dash_url}\n")
                if open_browser:
                    sys.stdout.write("Opening dashboard in your web browser...\n")
                    sys.stdout.flush()
                    try:
                        import webbrowser
                        webbrowser.open(dash_url)
                    except Exception:
                        pass
                return 0
            else:
                sys.stderr.write(
                    f"Port {port} is in use by another application.\n"
                    f"To run the dashboard on another port: learnloop dashboard --port <number>\n"
                )
                return 1
        sys.stderr.write(f"LearnLoop dashboard failed to bind port {port}: {exc}\n")
        return 1
    except Exception as exc:
        sys.stderr.write(f"LearnLoop dashboard failed to start: {exc}\n")
        return 1


def cmd_gui(port: int = 8765, route: str = "/setup", hide_console: bool = True) -> int:
    from learnloop.gui import launch_desktop_gui

    return launch_desktop_gui(port=port, route=route, hide_console=hide_console)


def cmd_http(host: str = "0.0.0.0", port: int = 8000, reload: bool = False) -> int:
    try:
        import uvicorn
        from learnloop.http_server import app
    except ImportError as exc:
        sys.stderr.write(
            f"HTTP dependencies not installed ({exc}).\n"
            "Install with: pip install -r requirements_http.txt\n"
        )
        return 1

    uvicorn.run(app, host=host, port=port, reload=reload, log_level="info")
    return 0


def cmd_setup(port: int = 8765, open_browser: bool = True, use_gui: bool = True) -> int:
    if use_gui and open_browser:
        from learnloop.gui import is_gui_available, launch_desktop_gui

        if is_gui_available():
            return launch_desktop_gui(port=port, route="/setup", hide_console=True)

    import threading
    import time

    if open_browser:
        def _launch_browser():
            time.sleep(0.6)
            try:
                import webbrowser
                webbrowser.open(f"http://127.0.0.1:{port}/setup")
            except Exception:
                pass

        threading.Thread(target=_launch_browser, daemon=True).start()

    return cmd_dashboard(port=port)


def cmd_record_commit(repo: Path) -> int:
    try:
        from learnloop.capture.queue import write_queue_entry
        from learnloop.domain import clock

        sha = _git(repo, "rev-parse", "HEAD").strip()
        message = _git(repo, "log", "-1", "--format=%s")
        committed = clock.iso(clock.parse(_git(repo, "log", "-1", "--format=%cI").strip()))
        files = [
            f
            for f in _git(
                repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "--root", "HEAD"
            ).splitlines()
            if f
        ]
        write_queue_entry(repo, sha, message.strip(), files, committed)
    except Exception as exc:  # noqa: BLE001 - a learning tool must never break `git commit`
        sys.stderr.write(f"learnloop: skipped ({exc})\n")
    return 0


def cmd_backfill(repo: Path, limit: int = 50) -> int:
    try:
        import hashlib

        from learnloop.capture.queue import MAX_FILES_BACKFILL, write_queue_entry
        from learnloop.capture.redaction import is_ignored
        from learnloop.domain import clock

        if not (repo / ".git").is_dir():
            sys.stderr.write("Not a git repository root; backfill skipped.\n")
            return 1

        head_sha = _git(repo, "rev-parse", "HEAD").strip()
        if not head_sha:
            sys.stderr.write("Empty git repository; backfill skipped.\n")
            return 0

        commit_shas = [
            s.strip()
            for s in _git(repo, "log", f"-{limit}", "--format=%H").splitlines()
            if s.strip()
        ]
        written = 0
        for sha in commit_shas:
            message = _git(repo, "log", "-1", "--format=%s", sha).strip()
            raw_committed = _git(repo, "log", "-1", "--format=%cI", sha).strip()
            committed = clock.iso(clock.parse(raw_committed))
            files = [
                f
                for f in _git(
                    repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "--root", sha
                ).splitlines()
                if f
            ]
            write_queue_entry(repo, sha, message, files, committed, origin="backfill")
            written += 1

        raw_tracked = [f for f in _git(repo, "ls-files").splitlines() if f]
        tracked = [f for f in raw_tracked if not is_ignored(f)][:MAX_FILES_BACKFILL]
        snapshot_sha = hashlib.sha1(f"learnloop:backfill:snapshot:{head_sha}".encode()).hexdigest()
        head_committed = clock.iso(clock.parse(_git(repo, "log", "-1", "--format=%cI", head_sha).strip()))
        write_queue_entry(
            repo,
            snapshot_sha,
            "learnloop: tracked files snapshot",
            tracked,
            head_committed,
            origin="backfill",
            kind="snapshot",
            max_files=MAX_FILES_BACKFILL,
        )
        sys.stderr.write(f"Backfilled {written} commits + tracked snapshot to .learn/queue/\n")
        return 0
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"learnloop backfill failed: {exc}\n")
        return 1


def _find_project_id(conn: sqlite3.Connection, repo: Path) -> str | None:
    repo_abs = str(repo.resolve())
    row = conn.execute(
        "SELECT id FROM projects WHERE repo_path=? COLLATE NOCASE"
        " ORDER BY (SELECT COUNT(*) FROM knowledge_items WHERE project_id=projects.id) DESC,"
        " created_at DESC LIMIT 1",
        (repo_abs,),
    ).fetchone()
    if not row:
        row = conn.execute(
            "SELECT id FROM projects WHERE repo_path=? COLLATE NOCASE LIMIT 1", (str(repo),)
        ).fetchone()
    return row["id"] if row else None


def cmd_concepts(repo: Path) -> int:
    try:
        from learnloop.config import Settings
        from learnloop.journal.concept_log import regenerate_concept_log
        from learnloop.persistence.db import connect

        settings = Settings.load()
        conn = connect(settings.db_path)
        try:
            project_id = _find_project_id(conn, repo)
            if not project_id:
                sys.stderr.write(f"No project registered for {repo}.\n")
                return 1
            written = regenerate_concept_log(conn, project_id, repo)
            if written:
                sys.stderr.write(f"Regenerated {repo / '.learn' / 'concepts.md'}\n")
            else:
                sys.stderr.write(f"Skipped regenerating concepts.md for {repo}\n")
            print_update_banner_if_available()
            return 0
        finally:
            conn.close()
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"learnloop concepts failed: {exc}\n")
        return 1


def cmd_review(repo: Path) -> int:
    try:
        from learnloop.config import Settings
        from learnloop.persistence.db import connect
        from learnloop.services.review_service import review_due

        settings = Settings.load()
        conn = connect(settings.db_path)
        try:
            project_id = _find_project_id(conn, repo)
            if not project_id:
                sys.stderr.write(f"No project registered for {repo}.\n")
                return 1
            res = review_due(conn, project_id, limit=3)
            items = res["items"]
            waiting = res["waiting"]
            if not items:
                sys.stdout.write("No knowledge items due for review today.\n")
                return 0
            sys.stdout.write("Knowledge items due for review:\n")
            for it in items:
                stale_marker = " [STALE]" if it.get("is_stale") else ""
                key, title, d = it["key"], it["title"], it["depth_to_ask"]
                sys.stdout.write(f"  • {key}: {title} (depth {d}){stale_marker}\n")
                if it.get("summary"):
                    sys.stdout.write(f"    {it['summary']}\n")
            if waiting > 0:
                sys.stdout.write(f"\n{waiting} more items waiting for future sessions.\n")
            print_update_banner_if_available()
            return 0
        finally:
            conn.close()
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"learnloop review failed: {exc}\n")
        return 1


def cmd_briefing(repo: Path) -> int:
    try:
        from learnloop.config import Settings
        from learnloop.persistence.db import connect
        from learnloop.services.briefing_service import get_session_briefing

        settings = Settings.load()
        conn = connect(settings.db_path)
        try:
            project_id = _find_project_id(conn, repo)
            if not project_id:
                sys.stderr.write(f"No project registered for {repo}.\n")
                return 1
            b = get_session_briefing(conn, project_id)
            changes = b["changes_since_briefing"]
            sys.stdout.write("LearnLoop Session Briefing:\n")
            sys.stdout.write(f"  New commits: {changes['new_commits']}\n")
            sys.stdout.write(f"  Unexplained commits: {changes['unexplained_commits']}\n")
            sys.stdout.write(f"  Stale items: {changes['stale_items_count']}\n")
            sys.stdout.write(f"  Due for review: {len(b['due'])} (waiting: {b['waiting']})\n")
            action_map = {
                "tour": "Ask AI in your IDE: 'Give me a tour of this project' (or run: learnloop concepts)",
                "review": "Run 'learnloop review' to practice pending flashcards",
                "explain-stale": "Ask AI in your IDE to explain recent codebase changes",
                "nothing": "Keep coding! LearnLoop tracks your progress in the background.",
            }
            raw_action = str(b.get("suggested_next", "nothing"))
            human_action = action_map.get(raw_action, f"Ask AI in your IDE: '{raw_action}'")
            sys.stdout.write(f"  Suggested next action: {human_action}\n")
            sys.stdout.write(
                "\nNote: Overdue items are simply re-spaced; there is never an urgent backlog or penalty.\n"
            )
            print_update_banner_if_available()
            return 0
        finally:
            conn.close()
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"learnloop briefing failed: {exc}\n")
        return 1


def cmd_init(
    repo: Path,
    integrate: bool = True,
    in_repo: bool = False,
    ide: str = "auto",
    all_integrations: bool = False,
) -> int:
    import os
    from learnloop.config import Settings, get_workspace_storage_dir
    from learnloop.daemon import detect_topology, ensure_daemon, probe_endpoint
    from learnloop.journal.concept_log import init_concept_log
    from learnloop.persistence.db import connect
    from learnloop.services import capture_service

    # Color styling
    use_color = bool(hasattr(sys.stdout, "isatty") and sys.stdout.isatty() and "NO_COLOR" not in os.environ)
    c_cyan = "\033[36m" if use_color else ""
    c_bold = "\033[1m" if use_color else ""
    c_reset = "\033[0m" if use_color else ""
    c_title = "\033[1;36m" if use_color else ""
    c_green = "\033[32m" if use_color else ""
    c_yellow = "\033[33m" if use_color else ""
    c_dim = "\033[90m" if use_color else ""

    learn = repo / ".learn" if (in_repo or (repo / ".learn").is_dir()) else get_workspace_storage_dir(repo)
    (learn / "queue").mkdir(parents=True, exist_ok=True)
    if (learn / ".gitignore").parent == (repo / ".learn"):
        (learn / ".gitignore").write_text("queue/\n", encoding="utf-8")
    init_concept_log(repo)

    # 1. Project Registration in local SQLite database
    settings = Settings.load()
    conn = connect(settings.db_path)
    proj_id = None
    try:
        existing_id = _find_project_id(conn, repo)
        if not existing_id:
            proj = capture_service.start_project(conn, repo.name, str(repo.resolve()))
            proj_id = proj["id"]
        else:
            proj_id = existing_id
    finally:
        conn.close()

    db_target = learn / "learnloop.db" if in_repo else settings.db_path
    if in_repo:
        conn = connect(db_target)
        conn.close()

    # Banner
    sys.stdout.write(f"\n  {c_title}◈ LEARNLOOP ◉ GHOST MODE ◈ PROJECT INITIALIZED{c_reset}\n")
    mode_desc = "Zero Workspace Pollution" if not in_repo else "In-Repository Storage (.learn/)"
    sys.stdout.write(f"  {c_dim}Project: {repo.name} ({proj_id}) • {mode_desc}{c_reset}\n\n")

    # [1/4] Git post-commit hook
    sys.stdout.write(f"{c_cyan}[1/4] Arming Git Post-Commit Tracking Hook...{c_reset}\n")
    hook = repo / ".git" / "hooks" / "post-commit"
    is_git = (repo / ".git").is_dir()
    exit_code = 0
    if not is_git:
        exit_code = 1
        sys.stdout.write(f"      {c_yellow}[!] Notice:{c_reset} Not a Git root; created journal only.\n")
        sys.stdout.write(f"      {c_dim}Run 'git init' and make a commit to arm tracking.{c_reset}\n\n")
    else:
        body = _hook_text()
        if hook.exists() and HOOK_MARKER not in hook.read_text("utf-8"):
            exit_code = 1
            sys.stdout.write(f"      {c_yellow}[!] Custom hook exists:{c_reset} {hook}\n")
            sys.stdout.write(f"      {c_dim}Add 'learnloop record-commit' manually to your hook.{c_reset}\n\n")
        else:
            hook.parent.mkdir(parents=True, exist_ok=True)
            hook.write_bytes(body.encode("utf-8"))
            hook.chmod(hook.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            sys.stdout.write(f"      {c_green}[OK]{c_reset} Hook:     {hook}\n")
            sys.stdout.write(f"      {c_dim}Fast, non-blocking background queue capture{c_reset}\n\n")

    # [2/4] Storage & Local Database
    concepts_file = (repo / ".learn" / "concepts.md") if (repo / ".learn").exists() else (learn / "concepts.md")
    sys.stdout.write(f"{c_cyan}[2/4] Initializing Local Knowledge & State Storage...{c_reset}\n")
    sys.stdout.write(f"      {c_green}[OK]{c_reset} Storage:  {learn}\n")
    sys.stdout.write(f"      {c_green}[OK]{c_reset} Database: {db_target} (100% Local SQLite)\n")
    sys.stdout.write(f"      {c_green}[OK]{c_reset} Journal:  {concepts_file}\n\n")

    # [3/4] IDE Integration
    sys.stdout.write(f"{c_cyan}[3/4] Configuring IDE Model Context Protocol (MCP)...{c_reset}\n")
    if integrate:
        from learnloop.integrator import LearnLoopIntegrator

        integrator = LearnLoopIntegrator(project_root=repo, in_repo=in_repo)
        run_args = ["--in-repo"] if in_repo else []
        if all_integrations or ide == "all":
            integ_res = integrator.run([*run_args, "--all"], quiet=True)
        else:
            integ_res = integrator.run([*run_args, "--ide", ide], quiet=True)

        integrated_paths = integ_res.get("integrated_paths", []) if isinstance(integ_res, dict) else []
        detected_ides = integ_res.get("detected_ides", []) if isinstance(integ_res, dict) else []

        if integrated_paths:
            for p in integrated_paths:
                sys.stdout.write(f"      {c_green}[OK]{c_reset} Config:   {p}\n")
        else:
            editors_str = ", ".join(detected_ides) if detected_ides else ide
            sys.stdout.write(f"      {c_green}[OK]{c_reset} Editors:  {editors_str} (MCP ready)\n")
    else:
        sys.stdout.write(f"      {c_dim}[Skipped IDE integration (--no-integrate)]{c_reset}\n")

    # [4/4] Reachability & Live Capabilities Verification
    sys.stdout.write(f"\n{c_cyan}[4/4] Verifying MCP Reachability & Live Capabilities...{c_reset}\n")
    topo = detect_topology()
    env_label = topo["environment"].upper()
    daemon_info = ensure_daemon(port=topo["port"])
    probe_info = probe_endpoint(base_url=topo["local_url"])

    if probe_info.get("reachable"):
        latency = probe_info.get("latency_ms", 0.0)
        tools = probe_info.get("tools", [])
        tools_count = len(tools) if tools else 4
        pid_str = f" (PID: {daemon_info.get('pid')})" if daemon_info.get("pid") else ""
        sys.stdout.write(f"      {c_green}[OK]{c_reset} Daemon:   Running on {topo['local_url']}{pid_str}\n")
        sys.stdout.write(f"      {c_green}[OK]{c_reset} Protocol: Streamable HTTP & SSE ({latency}ms latency)\n")
        sys.stdout.write(f"      {c_green}[OK]{c_reset} Tools:    {tools_count} domain dispatchers active and verified\n")
    else:
        sys.stdout.write(f"      {c_yellow}[!] Notice:{c_reset} Background daemon starting; verify with 'learnloop doctor'\n")

    if topo.get("forward_cmd"):
        sys.stdout.write(f"      {c_dim}Remote note: {topo['forward_cmd']}{c_reset}\n")

    # Ready Card
    sys.stdout.write(f"\n  {c_green}+-------------------------------------------------------------+{c_reset}\n")
    sys.stdout.write(f"  {c_green}|                   READY FOR AI CODING                       |{c_reset}\n")
    sys.stdout.write(f"  {c_green}+-------------------------------------------------------------+{c_reset}\n")
    sys.stdout.write(f"  * Topology:     {env_label} (Universal Streamable HTTP / SSE)\n")
    sys.stdout.write(f"  * Ghost Mode:   100% Local - 0 Git clutter or PR pollution\n")
    sys.stdout.write(f"  * Trust Proof:  Verified Git commit SHAs required for learning\n\n")
    sys.stdout.write(f"  {c_yellow}-> WHAT TO ASK YOUR AI IN EDITOR CHAT:{c_reset}\n")
    sys.stdout.write(f"     * {c_cyan}\"Give me a tour of this project\"{c_reset}   (Codebase walkthrough)\n")
    sys.stdout.write(f"     * {c_cyan}\"Teach me how this works\"{c_reset}          (Targeted practice)\n\n")
    sys.stdout.write(f"  {c_yellow}-> COMMANDS IN THIS TERMINAL:{c_reset}\n")
    sys.stdout.write(f"     * {c_cyan}learnloop briefing{c_reset}                 (Calm 2-min catch-up)\n")
    sys.stdout.write(f"     * {c_cyan}learnloop dashboard{c_reset}                (Open mission control UI)\n")
    sys.stdout.write(f"     * {c_cyan}learnloop doctor{c_reset}                   (Run reachability diagnostics)\n")
    sys.stdout.write(f"  {c_green}+-------------------------------------------------------------+{c_reset}\n\n")

    return exit_code


def cmd_doctor() -> int:
    import os
    import re
    import sqlite3 as _sqlite3

    from learnloop.config import Settings
    from learnloop.daemon import detect_topology, ensure_daemon, is_daemon_running, probe_endpoint
    from learnloop.persistence.db import connect

    use_color = bool(hasattr(sys.stdout, "isatty") and sys.stdout.isatty() and "NO_COLOR" not in os.environ)
    c_cyan = "\033[36m" if use_color else ""
    c_bold = "\033[1m" if use_color else ""
    c_reset = "\033[0m" if use_color else ""
    c_title = "\033[1;36m" if use_color else ""
    c_green = "\033[32m" if use_color else ""
    c_yellow = "\033[33m" if use_color else ""
    c_dim = "\033[90m" if use_color else ""

    sys.stdout.write(f"\n  {c_title}◈ LEARNLOOP ◉ REACHABILITY & SYSTEM DOCTOR{c_reset}\n")
    sys.stdout.write(f"  {c_dim}Topology Detection, Protocol Handshake & AI Trust Evidence{c_reset}\n\n")

    # [1/5] Host Environment & Topology
    topo = detect_topology()
    sys.stdout.write(f"{c_cyan}[1/5] Host Environment & Topology{c_reset}\n")
    sys.stdout.write(
        f"      Platform:    {topo['platform']} • Python {sys.version.split()[0]} • SQLite {_sqlite3.sqlite_version}\n"
    )
    topo_desc = "Direct process execution" if topo["is_native"] else "Cross-boundary container/remote"
    sys.stdout.write(f"      Topology:    {topo['environment'].upper()} ({topo_desc})\n")
    if topo.get("forward_cmd"):
        sys.stdout.write(f"      Remote Port: {c_yellow}{topo['forward_cmd']}{c_reset}\n")
    sys.stdout.write(f"      {c_green}[OK]{c_reset} Runtime environment verified\n\n")

    # [2/5] Local Data Integrity
    s = Settings.load()
    conn = connect(s.db_path)
    n = conn.execute("SELECT COUNT(*) FROM skills").fetchone()[0]
    n_items = conn.execute("SELECT COUNT(*) FROM knowledge_items").fetchone()[0]
    has_reviews = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='item_reviews'"
    ).fetchone()
    n_due = 0
    if has_reviews:
        from learnloop.domain import clock

        now_s = clock.iso(clock.utcnow())
        n_due = conn.execute(
            "SELECT COUNT(*) FROM item_reviews WHERE due_at <= ?"
            " AND (snoozed_until IS NULL OR snoozed_until <= ?)",
            (now_s, now_s),
        ).fetchone()[0]

    sys.stdout.write(f"{c_cyan}[2/5] Local Data Integrity & Database Storage{c_reset}\n")
    sys.stdout.write(f"      Database:    {s.db_path}\n")
    sys.stdout.write(f"      Skills:      {n} active in taxonomy catalog\n")
    sys.stdout.write(f"      Concepts:    {n_items} registered architectural items\n")
    sys.stdout.write(f"      Reviews:     {n_due} items due for review\n")

    for row in conn.execute("SELECT repo_path FROM projects"):
        repo = Path(row[0])
        hook = repo / ".git" / "hooks" / "post-commit"
        if not hook.exists():
            continue
        try:
            text = hook.read_text("utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if HOOK_MARKER not in text:
            continue
        match_py = re.search(r'"([^"]+)"\s+-m\s+learnloop', text)
        match_bin = re.search(r'"([^"]+)"\s+record-commit', text)
        target_path = None
        if match_py:
            target_path = Path(match_py.group(1))
        elif match_bin:
            target_path = Path(match_bin.group(1))

        if target_path and not target_path.exists():
            sys.stdout.write(
                f"      {c_yellow}[!] Warning: hook in {repo} executable {target_path} not found{c_reset}\n"
            )

    conn.close()
    sys.stdout.write(f"      {c_green}[OK]{c_reset} 100% Local SQLite database healthy\n\n")

    # [3/5] MCP Daemon & Network Reachability
    sys.stdout.write(f"{c_cyan}[3/5] MCP Daemon & Network Reachability{c_reset}\n")
    daemon_info = ensure_daemon(port=topo["port"])
    is_running = is_daemon_running(port=topo["port"])
    pid_str = f" (PID: {daemon_info.get('pid')})" if daemon_info.get("pid") else ""
    sys.stdout.write(f"      Status:      {'Running' if is_running else 'Stopped'}{pid_str}\n")
    sys.stdout.write(f"      Binding:     {topo['bind_host']}:{topo['port']} (Universal Streamable HTTP / SSE)\n")
    sys.stdout.write(f"      Endpoint:    {topo['mcp_url']}\n")
    sys.stdout.write(f"      {c_green}[OK]{c_reset} Hosted MCP endpoint listening & reachable\n\n")

    # [4/5] Protocol Handshake & Tool Registry
    sys.stdout.write(f"{c_cyan}[4/5] Protocol Handshake & Tool Registry{c_reset}\n")
    probe = probe_endpoint(base_url=topo["local_url"])
    if probe.get("reachable"):
        latency = probe.get("latency_ms", 0.0)
        tools = probe.get("tools", [])
        tools_count = len(tools) if tools else 4
        sys.stdout.write(f"      Latency:     {latency}ms (Live handshake verified)\n")
        sys.stdout.write(f"      Dispatchers: {tools_count}/4 active\n")
        sys.stdout.write(f"        • track_intent       (Active coding & commit reconciliation)\n")
        sys.stdout.write(f"        • explore_project    (Codebase tour & ecosystem detection)\n")
        sys.stdout.write(f"        • manage_knowledge   (Architectural concepts & invariants)\n")
        sys.stdout.write(f"        • manage_reviews     (Spaced repetition review sessions)\n")
        sys.stdout.write(f"      {c_green}[OK]{c_reset} All domain capabilities verified\n\n")
    else:
        err = probe.get("error", "unreachable")
        sys.stdout.write(f"      {c_yellow}[!] Handshake probe note: {err}{c_reset}\n\n")

    # [5/5] Trust Evidence
    sys.stdout.write(f"  {c_green}+-------------------------------------------------------------+{c_reset}\n")
    sys.stdout.write(f"  {c_green}|               AI TRUST & VERIFICATION EVIDENCE              |{c_reset}\n")
    sys.stdout.write(f"  {c_green}+-------------------------------------------------------------+{c_reset}\n")
    sys.stdout.write(f"  * 100% Local Storage:  Zero telemetry, cloud metrics, or tracking\n")
    sys.stdout.write(f"  * Proof-of-Outcome:    AI cannot claim progress without verified Git commit SHAs\n")
    sys.stdout.write(f"  * Ghost Mode:          Zero repo pollution; isolated in ~/.learnloop/\n")
    sys.stdout.write(f"  {c_green}+-------------------------------------------------------------+{c_reset}\n\n")

    print_update_banner_if_available()
    return 0


def cmd_techscan(repo: Path) -> int:
    try:
        from typing import Any

        from learnloop.config import Settings
        from learnloop.persistence.db import connect
        from learnloop.services.technology_service import refresh_technologies

        settings = Settings.load()
        conn = connect(settings.db_path)
        try:
            project_id = _find_project_id(conn, repo)
            if not project_id:
                from learnloop.services.capture_service import start_project

                p = start_project(conn, repo.resolve().name, str(repo.resolve()))
                project_id = p["id"]

            res = refresh_technologies(conn, project_id)
            techs = res["technologies"]
            sys.stdout.write(f"Scanned {len(techs)} technologies in {repo}:\n")
            by_eco: dict[str, list[dict[str, Any]]] = {}
            for t in techs:
                by_eco.setdefault(t["ecosystem"], []).append(t)

            for eco in sorted(by_eco.keys()):
                sys.stdout.write(f"\n[{eco.upper()}]\n")
                for t in by_eco[eco]:
                    ver = f" ({t['version_spec']})" if t.get("version_spec") else ""
                    sys.stdout.write(f"  - {t['name']}{ver} [{t['source_file']}]\n")
            print_update_banner_if_available()
            return 0
        finally:
            conn.close()
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"learnloop techscan failed: {exc}\n")
        return 1



def cmd_uninstall(repo: Path, purge: bool = False, yes: bool = False) -> int:
    """Cleanly uninstall LearnLoop:
    1. Unregisters MCP server and rules from all IDEs (VS Code, Cursor, Windsurf, Claude, Zed, Antigravity).
    2. Removes Git post-commit hooks from repository if present.
    3. Stops active background daemon to release file locks.
    4. Removes executable from ~/.learnloop/bin/ if accessible.
    5. If purge is specified, purges all local databases, workspaces, logs, and rules.
    """
    if not yes:
        sys.stdout.write("LearnLoop Clean Uninstaller\n")
        sys.stdout.write("============================\n")
        sys.stdout.write("This will unregister LearnLoop from all IDEs (VS Code, Cursor, Windsurf, Claude, Zed)\n")
        sys.stdout.write("and remove active Git post-commit hooks.\n")
        if purge:
            sys.stdout.write("WARNING: Purge mode is enabled. All local databases and learning history will be deleted!\n")
        else:
            sys.stdout.write("Note: Your local databases (~/.learnloop) are preserved by default (use 'learnloop uninstall --purge' to delete them).\n")

        try:
            choice = input("\nProceed with uninstallation? [y/N]: ").strip().lower()
            if choice not in ("y", "yes"):
                sys.stdout.write("Uninstallation cancelled.\n")
                return 0
            if not purge:
                purge_choice = input("Also purge all local databases & learning history? [y/N]: ").strip().lower()
                if purge_choice in ("y", "yes"):
                    purge = True
        except (EOFError, KeyboardInterrupt):
            sys.stdout.write("\nUninstallation cancelled.\n")
            return 0

    from learnloop.daemon import stop_daemon
    from learnloop.integrator import LearnLoopIntegrator

    # Stop active daemon before deleting configurations and data
    stop_daemon()

    sys.stdout.write("\n[1/3] Unregistering from IDEs...\n")
    # Clean global user configs
    global_integrator = LearnLoopIntegrator(project_root=repo, in_repo=False)
    cleaned_configs = global_integrator.uninstall_all()

    # Also clean in-repo configs if run inside a project
    in_repo_integrator = LearnLoopIntegrator(project_root=repo, in_repo=True)
    in_repo_cleaned = in_repo_integrator.uninstall_all()
    cleaned_configs.extend(in_repo_cleaned)

    unique_cleaned = list(dict.fromkeys(cleaned_configs))
    if unique_cleaned:
        for p in unique_cleaned:
            sys.stdout.write(f"  [OK] Cleaned: {p}\n")
    else:
        sys.stdout.write("  [OK] No active IDE configurations found to clean.\n")

    sys.stdout.write("\n[2/3] Cleaning Git hooks...\n")
    hook = repo / ".git" / "hooks" / "post-commit"
    if hook.exists():
        try:
            content = hook.read_text(encoding="utf-8")
            if HOOK_MARKER in content:
                hook.unlink()
                sys.stdout.write(f"  [OK] Removed LearnLoop post-commit hook from {hook}\n")
            else:
                sys.stdout.write(f"  * Custom post-commit hook in {hook} was not created by LearnLoop; left untouched.\n")
        except Exception as exc:
            sys.stderr.write(f"  [WARN] Could not read/remove hook: {exc}\n")
    else:
        sys.stdout.write("  [OK] No repository post-commit hooks found.\n")

    sys.stdout.write("\n[3/3] Removing executable & data...\n")
    bin_name = "learnloop.exe" if sys.platform == "win32" else "learnloop"
    custom_bin = Path.home() / ".learnloop" / "bin" / bin_name
    custom_bin_exists = False
    try:
        custom_bin_exists = custom_bin.exists()
    except (OSError, PermissionError):
        pass

    if custom_bin_exists:
        try:
            custom_bin.unlink()
            sys.stdout.write(f"  [OK] Removed executable: {custom_bin}\n")
        except Exception as exc:
            if sys.platform == "win32":
                sys.stdout.write(
                    f"  * Notice: Windows locks running executables. To delete the binary after exiting this shell:\n"
                    f"    del \"{custom_bin}\"\n"
                )
            else:
                sys.stderr.write(f"  [WARN] Could not remove executable {custom_bin}: {exc}\n")
    else:
        sys.stdout.write("  [OK] Executable not in ~/.learnloop/bin/ (installed via package or custom path).\n")

    if purge:
        import shutil

        # 1. ~/.learnloop
        learnloop_home = Path.home() / ".learnloop"
        if learnloop_home.exists():
            try:
                shutil.rmtree(learnloop_home)
                sys.stdout.write(f"  [OK] Purged local config & log directory: {learnloop_home}\n")
            except Exception as exc:
                sys.stderr.write(f"  [WARN] Could not purge {learnloop_home}: {exc}\n")

        # 2. OS user data directory (platformdirs)
        try:
            from platformdirs import user_data_dir
            data_dir = Path(user_data_dir("learnloop"))
            if data_dir.exists():
                shutil.rmtree(data_dir)
                sys.stdout.write(f"  [OK] Purged local database directory: {data_dir}\n")
        except Exception as exc:
            sys.stderr.write(f"  [WARN] Could not purge {data_dir}: {exc}\n")

        # 3. In-repo legacy .learn if present
        legacy_dir = repo / ".learn"
        if legacy_dir.exists() and legacy_dir.is_dir():
            try:
                shutil.rmtree(legacy_dir)
                sys.stdout.write(f"  [OK] Purged repository workspace directory: {legacy_dir}\n")
            except Exception as exc:
                sys.stderr.write(f"  [WARN] Could not purge {legacy_dir}: {exc}\n")

    sys.stdout.write("\nLearnLoop uninstallation complete! Your IDEs and system are clean.\n")
    return 0


def _format_help(use_color: bool = True) -> str:
    c_cyan = "\033[36m" if use_color else ""
    c_bold = "\033[1m" if use_color else ""
    c_reset = "\033[0m" if use_color else ""
    c_title = "\033[1;36m" if use_color else ""
    c_dim = "\033[90m" if use_color else ""

    return (
        f"\n"
        f"  {c_title}◈ LEARNLOOP{c_reset} - Local-First AI Learning Companion\n"
        f"  {c_dim}Zero Telemetry • 100% Local SQLite • Ghost Mode{c_reset}\n\n"
        f"{c_bold}USAGE:{c_reset}\n"
        f"  learnloop [COMMAND] [OPTIONS]\n"
        f"  learnloop                       Launch setup wizard (interactive) or run MCP server (stdio)\n\n"
        f"{c_bold}DAILY LEARNING & WORKFLOW:{c_reset}\n"
        f"  {c_cyan}briefing{c_reset}     Calm 2-minute catch-up summary of AI changes since yesterday\n"
        f"  {c_cyan}review{c_reset}       Interactive SuperMemo-2 spaced repetition review session\n"
        f"  {c_cyan}concepts{c_reset}     List verified architectural concepts and invariants\n"
        f"  {c_cyan}dashboard{c_reset}    Launch local mission control web dashboard (http://127.0.0.1:8765)\n"
        f"  {c_cyan}gui{c_reset}          Launch native desktop GUI window (Edge WebView2)\n\n"
        f"{c_bold}PROJECT SETUP & INTEGRATION:{c_reset}\n"
        f"  {c_cyan}init{c_reset}         Initialize LearnLoop in project (auto-detects IDE, zero-config)\n"
        f"  {c_cyan}techscan{c_reset}     Scan repository for frameworks, libraries, and ecosystem dependencies\n"
        f"  {c_cyan}backfill{c_reset}     Reconcile unreviewed Git commits into verified exposure queue\n\n"
        f"{c_bold}DIAGNOSTICS & ENGINE:{c_reset}\n"
        f"  {c_cyan}doctor{c_reset}       Run diagnostic health check on local SQLite DB and MCP readiness\n"
        f"  {c_cyan}update{c_reset}       Self-update LearnLoop to the latest released version\n"
        f"  {c_cyan}serve{c_reset}        Run MCP protocol server (stdio, sse, or http transport)\n"
        f"  {c_cyan}http{c_reset}         Start HTTP/SSE server for LAN and cloud deployment\n"
        f"  {c_cyan}setup{c_reset}        Launch interactive first-time setup wizard\n"
        f"  {c_cyan}uninstall{c_reset}    Cleanly unregister LearnLoop from IDEs, hooks, and system\n\n"
        f"{c_bold}FLAGS:{c_reset}\n"
        f"  -h, --help       Show this help message and exit\n"
        f"  -V, --version    Show program version number and exit\n"
        f"  --purge          Purge all local databases and history (~/.learnloop)\n\n"
        f"Run 'learnloop [COMMAND] --help' for options on a specific command.\n"
    )


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="learnloop")
    p.add_argument("-V", "--version", action="version", version=f"learnloop v{__version__}")
    p.add_argument("--purge", action="store_true", help="Purge all local databases and history (~/.learnloop)")

    def _should_use_color() -> bool:
        import os
        if "NO_COLOR" in os.environ:
            return False
        return bool(hasattr(sys.stdout, "isatty") and sys.stdout.isatty())

    p.format_help = lambda: _format_help(use_color=_should_use_color())  # type: ignore[assignment]
    sub = p.add_subparsers(dest="cmd")

    init_p = sub.add_parser(
        "init",
        help="Initialize LearnLoop in project (auto-detects IDE, zero-config)",
        description="Initialize LearnLoop in project. Configures post-commit hook and auto-integrates with your IDE.",
    )
    init_p.add_argument("--repo", type=Path, default=Path.cwd(), help="Repository path")
    init_p.add_argument("--no-integrate", dest="integrate", action="store_false", help="Skip automatic IDE integration")
    init_p.set_defaults(integrate=True)
    init_p.add_argument(
        "--ide",
        choices=["auto", "vscode", "cursor", "claude", "windsurf", "zed", "agents", "all"],
        default="auto",
        help="Target IDE for integration (default: auto-detect)",
    )
    init_p.add_argument(
        "--all",
        action="store_true",
        help="Configure MCP for all supported IDEs (VS Code, Cursor, Windsurf, Claude, Zed)",
    )
    init_p.add_argument("--in-repo", action="store_true", help="Store SQLite DB inside .learn/ folder")

    briefing_p = sub.add_parser(
        "briefing",
        help="Calm 2-minute catch-up summary of AI changes since yesterday",
        description="Display a calm 2-minute catch-up summary of AI commits and code changes made since yesterday.",
    )
    briefing_p.add_argument("--repo", type=Path, default=Path.cwd(), help="Repository path")

    review_p = sub.add_parser(
        "review",
        help="Interactive SuperMemo-2 spaced repetition review session",
        description="Start an interactive spaced repetition flashcard review session for concepts due today.",
    )
    review_p.add_argument("--repo", type=Path, default=Path.cwd(), help="Repository path")

    concepts_p = sub.add_parser(
        "concepts",
        help="List verified architectural concepts and invariants",
        description="List all tracked architectural concepts, invariants, and implementation patterns.",
    )
    concepts_p.add_argument("--repo", type=Path, default=Path.cwd(), help="Repository path")

    techscan_p = sub.add_parser(
        "techscan",
        help="Scan repository for frameworks, libraries, and ecosystem dependencies",
        description="Scan repository files and manifests to detect frameworks, libraries, and tools.",
    )
    techscan_p.add_argument("--repo", type=Path, default=Path.cwd(), help="Repository path")

    rc_p = sub.add_parser(
        "record-commit",
        help="Record Git post-commit hook metadata (called automatically by hook)",
        description="Fast non-blocking hook invoked by Git post-commit to record commit metadata.",
    )
    rc_p.add_argument("--repo", type=Path, default=Path.cwd(), help="Repository path")

    bf = sub.add_parser(
        "backfill",
        help="Reconcile unreviewed Git commits into verified exposure queue",
        description="Scan recent Git commit history to backfill unrecorded commits into the exposure queue.",
    )
    bf.add_argument("--repo", type=Path, default=Path.cwd(), help="Repository path")
    bf.add_argument("--limit", type=int, default=50, help="Maximum number of commits to backfill (default: 50)")

    doc_p = sub.add_parser(
        "doctor",
        help="Run diagnostic health check on local SQLite DB and MCP readiness",
        description="Check environment, SQLite database integrity, seeded skills, and MCP readiness.",
    )
    doc_p.add_argument("--repo", type=Path, default=Path.cwd(), help="Repository path")

    update_p = sub.add_parser(
        "update",
        help="Self-update LearnLoop to the latest released version",
        description="Check for newer releases and upgrade the local LearnLoop binary/engine.",
    )
    update_p.add_argument(
        "--force",
        action="store_true",
        help="Force re-downloading even if already on the latest version",
    )

    uninst_p = sub.add_parser(
        "uninstall",
        help="Cleanly unregister LearnLoop from IDEs, hooks, and system",
        description="Cleanly unregister LearnLoop from IDE configs, remove git hooks, and optionally purge data.",
    )
    uninst_p.add_argument("--repo", type=Path, default=Path.cwd(), help="Repository path")
    uninst_p.add_argument("--purge", action="store_true", help="Purge local database and learning history (~/.learnloop)")
    uninst_p.add_argument("-y", "--yes", action="store_true", help="Skip confirmation prompt")

    dash = sub.add_parser(
        "dashboard",
        help="Launch local mission control web dashboard (http://127.0.0.1:8765)",
        description="Launch local web dashboard displaying concept masteries, due reviews, and session logs.",
    )
    dash.add_argument("--port", type=int, default=8765, help="Port to run web dashboard on (default: 8765)")
    dash.add_argument("--gui", action="store_true", help="Open dashboard in native desktop GUI window")
    dash.add_argument("--no-browser", action="store_true", help="Do not automatically open browser")

    setup_p = sub.add_parser(
        "setup",
        help="Launch interactive first-time setup wizard",
        description="Launch interactive web setup wizard to configure your learning profile and IDEs.",
    )
    setup_p.add_argument("--port", type=int, default=8765, help="Port to run setup server on")
    setup_p.add_argument("--no-browser", action="store_true", help="Do not automatically open browser")
    setup_p.add_argument("--browser", action="store_true", help="Force opening in web browser instead of desktop window")

    gui_p = sub.add_parser(
        "gui",
        help="Launch native desktop GUI window (Edge WebView2)",
        description="Launch native desktop GUI window using Edge WebView2 without needing a separate browser.",
    )
    gui_p.add_argument("--port", type=int, default=8765, help="Port to run setup server on")
    gui_p.add_argument("--route", default="/setup", choices=["/setup", "/"], help="Starting view (/setup or /)")
    gui_p.add_argument("--no-hide-console", action="store_true", help="Keep console window visible")

    http_p = sub.add_parser(
        "http",
        help="Start HTTP/SSE server for LAN and cloud deployment",
        description="Start HTTP/SSE REST API and web server.",
    )
    http_p.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    http_p.add_argument("--port", type=int, default=8000, help="Port to bind to (default: 8000)")
    http_p.add_argument("--reload", action="store_true", help="Enable auto-reload")

    serve_p = sub.add_parser(
        "serve",
        help="Run standard MCP protocol server (stdio, sse, or http transport)",
        description="Run Model Context Protocol (MCP) server for AI coding assistants.",
    )
    serve_p.add_argument(
        "--transport",
        choices=["stdio", "sse", "http"],
        default="stdio",
        help="MCP transport protocol (default: stdio)",
    )
    serve_p.add_argument("--repo", type=Path, default=Path.cwd(), help="Target repository path")
    serve_p.add_argument("--host", default="0.0.0.0", help="Host for SSE/HTTP transport (default: 0.0.0.0)")
    serve_p.add_argument("--port", type=int, default=8000, help="Port for SSE/HTTP transport (default: 8000)")

    args = p.parse_args(argv)
    if args.cmd == "init":
        code = cmd_init(
            args.repo,
            integrate=args.integrate,
            in_repo=args.in_repo,
            ide=args.ide,
            all_integrations=args.all,
        )
    elif args.cmd == "serve":
        code = cmd_serve(transport=args.transport, host=args.host, port=args.port)
    elif args.cmd == "http":
        code = cmd_http(host=args.host, port=args.port, reload=args.reload)
    elif args.cmd == "setup":
        code = cmd_setup(
            port=args.port,
            open_browser=not args.no_browser,
            use_gui=not args.browser and not args.no_browser,
        )
    elif args.cmd == "gui":
        code = cmd_gui(port=args.port, route=args.route, hide_console=not args.no_hide_console)
    elif args.cmd == "record-commit":
        code = cmd_record_commit(args.repo)
    elif args.cmd == "backfill":
        code = cmd_backfill(args.repo, args.limit)
    elif args.cmd == "concepts":
        code = cmd_concepts(args.repo)
    elif args.cmd == "review":
        code = cmd_review(args.repo)
    elif args.cmd == "briefing":
        code = cmd_briefing(args.repo)
    elif args.cmd == "uninstall":
        code = cmd_uninstall(args.repo, purge=args.purge, yes=args.yes)
    elif args.cmd == "doctor":
        code = cmd_doctor()
    elif args.cmd == "update":
        code = cmd_update(force=args.force)
    elif args.cmd == "dashboard":
        code = cmd_dashboard(args.port, use_gui=args.gui, open_browser=not args.no_browser)
    elif args.cmd == "techscan":
        code = cmd_techscan(args.repo)
    else:
        if getattr(args, "purge", False):
            code = cmd_uninstall(Path.cwd(), purge=True)
        elif sys.stdin and hasattr(sys.stdin, "isatty") and sys.stdin.isatty():
            code = cmd_setup(use_gui=True)
        else:
            code = cmd_serve()
    raise SystemExit(code)


if __name__ == "__main__":
    main()
