from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


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
