from __future__ import annotations

import http.client
import json
import sqlite3
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from learnloop.dashboard.server import DashboardHandler, DashboardServer
from learnloop.persistence.db import migrate


@pytest.fixture
def wizard_env(tmp_path: Path):
    db_path = tmp_path / "wizard_test.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    migrate(conn, db_path)
    conn.close()

    server = DashboardServer(("127.0.0.1", 0), DashboardHandler)
    port = server.server_address[1]
    DashboardHandler.server_port = port
    DashboardHandler.db_path = db_path

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    yield {
        "port": port,
        "db_path": db_path,
        "tmp_path": tmp_path,
        "server": server,
    }

    try:
        server.shutdown()
        server.server_close()
    except Exception:
        pass


def _req(
    port: int,
    method: str,
    path: str,
    headers: dict[str, str] | None = None,
    body: str | None = None,
) -> tuple[int, dict[str, str], str]:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    default_headers = {"Host": f"127.0.0.1:{port}"}
    if headers:
        default_headers.update(headers)
    conn.request(method, path, body=body, headers=default_headers)
    resp = conn.getresponse()
    status = resp.status
    resp_headers = {k: v for k, v in resp.getheaders()}
    resp_body = resp.read().decode("utf-8")
    conn.close()
    return status, resp_headers, resp_body


def test_get_setup_page_renders_wizard(wizard_env):
    port = wizard_env["port"]
    status, headers, body = _req(port, "GET", "/setup")

    assert status == 200
    assert "LearnLoop Setup Wizard" in body
    assert "100% Local-First" in body
    assert "Zero Data Sharing" in body
    assert "Cursor" in body
    assert "VS Code" in body
    assert "Windsurf" in body
    assert "Claude Desktop &amp; Code" in body or "Claude" in body
    assert "Global Developer Library" in body
    assert "In-Project Storage" in body
    assert "Auto-track commits with Git post-commit hook" in body
    assert "Complete Setup &amp; Open Dashboard" in body
    assert "form-action 'self'" in headers.get("Content-Security-Policy", "")


def test_post_api_setup_json(wizard_env):
    port = wizard_env["port"]
    tmp_path = wizard_env["tmp_path"]
    target_repo = tmp_path / "test_repo"
    target_repo.mkdir()

    payload = json.dumps({
        "ides": ["cursor", "vscode", "agents"],
        "storage": "in_repo",
        "install_hook": True,
        "repo_path": str(target_repo),
    })

    status, headers, body = _req(
        port,
        "POST",
        "/api/setup",
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        body=payload,
    )

    assert status == 200
    data = json.loads(body)
    assert data["status"] == "ok"
    assert data["redirect"] == "/"
    assert "cursor" in data["configured_ides"]
    assert "vscode" in data["configured_ides"]
    assert "agents" in data["configured_ides"]

    # Check files created
    assert (target_repo / ".cursorrules").exists()
    assert (target_repo / ".cursor" / "mcp.json").exists()
    assert (target_repo / ".vscode" / "settings.json").exists()
    assert (target_repo / "AGENTS.md").exists()
    assert (target_repo / "GEMINI.md").exists()
    assert (target_repo / ".learn" / "learnloop.db").exists()


def test_post_api_setup_form(wizard_env):
    port = wizard_env["port"]
    tmp_path = wizard_env["tmp_path"]
    target_repo = tmp_path / "form_repo"
    target_repo.mkdir()

    form_body = (
        f"ides=cursor&ides=agents&storage=global&install_hook=true&repo_path={target_repo}"
    )

    status, headers, body = _req(
        port,
        "POST",
        "/api/setup",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        body=form_body,
    )

    assert status == 200
    assert "Setup Complete!" in body
    assert "CURSOR, AGENTS" in body
    assert (target_repo / ".cursorrules").exists()
    assert (target_repo / "AGENTS.md").exists()


def test_post_api_shutdown_json(wizard_env):
    port = wizard_env["port"]

    status, headers, body = _req(
        port,
        "POST",
        "/api/shutdown",
        headers={"Accept": "application/json"},
    )

    assert status == 200
    data = json.loads(body)
    assert data["status"] == "shutting_down"


def test_cli_smart_launch_detection():
    from learnloop.cli import main

    # 1. When sys.stdin.isatty() is False, it calls cmd_serve()
    with patch("sys.stdin.isatty", return_value=False), \
         patch("learnloop.cli.cmd_serve", return_value=0) as mock_serve, \
         pytest.raises(SystemExit) as exc_info:
        main([])
    assert exc_info.value.code == 0
    mock_serve.assert_called_once()

    # 2. When sys.stdin.isatty() is True, it calls cmd_setup()
    with patch("sys.stdin.isatty", return_value=True), \
         patch("learnloop.cli.cmd_setup", return_value=0) as mock_setup, \
         pytest.raises(SystemExit) as exc_info:
        main([])
    assert exc_info.value.code == 0
    mock_setup.assert_called_once()

    # 3. Explicit 'setup' subcommand
    with patch("learnloop.cli.cmd_setup", return_value=0) as mock_setup, \
         pytest.raises(SystemExit) as exc_info:
        main(["setup", "--no-browser", "--port", "9999"])
    assert exc_info.value.code == 0
    mock_setup.assert_called_once_with(port=9999, open_browser=False, use_gui=False)

    # 4. Explicit 'gui' subcommand
    with patch("learnloop.cli.cmd_gui", return_value=0) as mock_gui, \
         pytest.raises(SystemExit) as exc_info:
        main(["gui", "--port", "8888", "--route", "/"])
    assert exc_info.value.code == 0
    mock_gui.assert_called_once_with(port=8888, route="/", hide_console=True)


def test_gui_helpers():
    from learnloop.gui import is_gui_available, hide_console_window, show_console_window, get_webview2_cache_dir

    assert isinstance(is_gui_available(), bool)
    assert isinstance(hide_console_window(), bool)
    assert isinstance(show_console_window(), bool)
    cache_dir = get_webview2_cache_dir()
    assert cache_dir.exists()
    assert "webview2_cache" in str(cache_dir)
