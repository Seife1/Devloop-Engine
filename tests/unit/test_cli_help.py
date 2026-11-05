import pytest
from unittest.mock import patch
from learnloop.cli import main, _format_help


def test_format_help_contains_all_categories_and_commands():
    help_text = _format_help(use_color=False)
    assert "DAILY LEARNING & WORKFLOW:" in help_text
    assert "PROJECT SETUP & INTEGRATION:" in help_text
    assert "DIAGNOSTICS & ENGINE:" in help_text

    expected_commands = [
        "briefing",
        "review",
        "concepts",
        "dashboard",
        "gui",
        "init",
        "techscan",
        "backfill",
        "doctor",
        "serve",
        "http",
        "setup",
        "uninstall",
        "update",
    ]
    for cmd in expected_commands:
        assert cmd in help_text
    assert "integrate" not in help_text


def test_cli_version_flag_exits_cleanly(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "learnloop v" in captured.out


def test_cli_help_flag_exits_cleanly(capsys):
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert "DAILY LEARNING & WORKFLOW:" in captured.out
    assert "briefing" in captured.out
    assert "init" in captured.out
    assert "doctor" in captured.out

