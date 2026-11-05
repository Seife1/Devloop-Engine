"""Unit tests for LearnLoop clean uninstallation."""

import json
from pathlib import Path
import pytest

from learnloop.integrator import LearnLoopIntegrator
from learnloop.cli import cmd_uninstall, HOOK_MARKER


def test_uninstall_from_json_preserves_other_servers(tmp_path: Path) -> None:
    config_file = tmp_path / "settings.json"
    initial_data = {
        "mcpServers": {
            "github": {"command": "npx", "args": ["-y", "@modelcontextprotocol/server-github"]},
            "learnloop": {"command": "learnloop", "args": ["serve"]},
            "sqlite": {"command": "uvx", "args": ["mcp-server-sqlite"]},
        },
        "editor.tabSize": 2,
    }
    config_file.write_text(json.dumps(initial_data, indent=2), encoding="utf-8")

    result = LearnLoopIntegrator._uninstall_from_json(config_file)
    assert result is True

    updated_data = json.loads(config_file.read_text(encoding="utf-8"))
    assert "learnloop" not in updated_data["mcpServers"]
    assert "github" in updated_data["mcpServers"]
    assert "sqlite" in updated_data["mcpServers"]
    assert updated_data["editor.tabSize"] == 2


def test_uninstall_from_json_non_existent(tmp_path: Path) -> None:
    non_existent = tmp_path / "does_not_exist.json"
    assert LearnLoopIntegrator._uninstall_from_json(non_existent) is False


def test_strip_rule_file_preserves_user_content(tmp_path: Path) -> None:
    rules_file = tmp_path / "AGENTS.md"
    content = (
        "# User Project Rules\n\n"
        "Always use Python 3.12.\n\n"
        "## LearnLoop (learning companion)\n\n"
        "1. Active Coding (track_intent)\n"
        "2. Spaced Repetition (manage_reviews)\n"
    )
    rules_file.write_text(content, encoding="utf-8")

    result = LearnLoopIntegrator._strip_rule_file(rules_file)
    assert result is True
    assert rules_file.exists()
    remaining = rules_file.read_text(encoding="utf-8")
    assert "Always use Python 3.12" in remaining
    assert "## LearnLoop (learning companion)" not in remaining


def test_cmd_uninstall_removes_learnloop_hook(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Setup mock git repo
    git_dir = tmp_path / ".git" / "hooks"
    git_dir.mkdir(parents=True)
    hook_file = git_dir / "post-commit"
    hook_file.write_text(f"#!/bin/sh\n{HOOK_MARKER}\nlearnloop record-commit\n", encoding="utf-8")

    exit_code = cmd_uninstall(repo=tmp_path, yes=True)
    assert exit_code == 0
    assert not hook_file.exists()


def test_cmd_uninstall_preserves_custom_hook(tmp_path: Path) -> None:
    git_dir = tmp_path / ".git" / "hooks"
    git_dir.mkdir(parents=True)
    hook_file = git_dir / "post-commit"
    custom_content = "#!/bin/sh\n# custom team hook\necho 'running lint'\n"
    hook_file.write_text(custom_content, encoding="utf-8")

    exit_code = cmd_uninstall(repo=tmp_path, yes=True)
    assert exit_code == 0
    assert hook_file.exists()
    assert hook_file.read_text(encoding="utf-8") == custom_content
