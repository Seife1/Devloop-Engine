"""Unit tests for LearnLoop dashboard command and collision handling."""

from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

from learnloop.cli import cmd_dashboard
from learnloop.daemon import stop_daemon


def test_cmd_dashboard_when_daemon_already_running(capsys: pytest.CaptureFixture[str]) -> None:
    with patch("learnloop.daemon.is_daemon_running", return_value=True), patch("webbrowser.open") as mock_open:
        code = cmd_dashboard(port=8765, use_gui=False, open_browser=True)
        assert code == 0
        mock_open.assert_called_once_with("http://127.0.0.1:8765/")
        captured = capsys.readouterr()
        assert "LearnLoop dashboard is active at http://127.0.0.1:8765/" in captured.out


def test_cmd_dashboard_recovers_from_socket_collision_with_daemon(capsys: pytest.CaptureFixture[str]) -> None:
    # First call to is_daemon_running returns False (simulating race condition before uvicorn),
    # then uvicorn fails with errno 10048, then second call to is_daemon_running returns True.
    daemon_checks = iter([False, True])
    with patch("learnloop.daemon.is_daemon_running", side_effect=lambda **kw: next(daemon_checks)), \
         patch("uvicorn.run", side_effect=OSError(10048, "Address already in use")), \
         patch("webbrowser.open") as mock_open:
        code = cmd_dashboard(port=8765, use_gui=False, open_browser=True)
        assert code == 0
        mock_open.assert_called_once_with("http://127.0.0.1:8765/")
        captured = capsys.readouterr()
        assert "LearnLoop dashboard is active at http://127.0.0.1:8765/" in captured.out


def test_cmd_dashboard_reports_foreign_port_collision(capsys: pytest.CaptureFixture[str]) -> None:
    with patch("learnloop.daemon.is_daemon_running", return_value=False), \
         patch("uvicorn.run", side_effect=OSError(10048, "Address already in use")):
        code = cmd_dashboard(port=8765, use_gui=False, open_browser=False)
        assert code == 1
        captured = capsys.readouterr()
        assert "Port 8765 is in use by another application" in captured.err


def test_stop_daemon_removes_pid_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pid_file = tmp_path / "daemon.pid"
    pid_file.write_text("99999", encoding="utf-8")
    monkeypatch.setattr("learnloop.daemon.get_pid_path", lambda: pid_file)
    monkeypatch.setattr("learnloop.daemon.is_pid_alive", lambda pid: False)

    stopped = stop_daemon()
    assert stopped is False
    assert not pid_file.exists()

