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


def test_cmd_uninstall_interactive_prompt_with_purge(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    inputs = iter(["y", "y"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    monkeypatch.setattr("learnloop.daemon.stop_daemon", lambda: True)

    fake_home = tmp_path / "home"
    fake_learnloop = fake_home / ".learnloop"
    fake_learnloop.mkdir(parents=True)
    (fake_learnloop / "data.txt").write_text("dummy", encoding="utf-8")
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    exit_code = cmd_uninstall(repo=tmp_path, purge=False, yes=False)
    assert exit_code == 0
    assert not fake_learnloop.exists()


def test_cmd_uninstall_interactive_prompt_without_purge(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    inputs = iter(["y", "n"])
    monkeypatch.setattr("builtins.input", lambda _: next(inputs))
    monkeypatch.setattr("learnloop.daemon.stop_daemon", lambda: True)

    fake_home = tmp_path / "home"
    fake_learnloop = fake_home / ".learnloop"
    fake_learnloop.mkdir(parents=True)
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    exit_code = cmd_uninstall(repo=tmp_path, purge=False, yes=False)
    assert exit_code == 0
    assert fake_learnloop.exists()


def test_main_root_purge_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    from learnloop.cli import main
    called = []
    monkeypatch.setattr("learnloop.cli.cmd_uninstall", lambda repo, purge=False, yes=False: called.append((purge, yes)) or 0)

    with pytest.raises(SystemExit) as exc_info:
        main(["--purge"])
    assert exc_info.value.code == 0
    assert called == [(True, False)]


def test_uninstall_vscode_preserves_custom_copilot_locations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    settings_file = fake_home / "settings.json"
    copilot_dir = fake_home / ".copilot" / "instructions"
    copilot_dir.mkdir(parents=True)
    copilot_inst = copilot_dir / "learnloop.instructions.md"
    copilot_inst.write_text("---\napplyTo: '**'\n---\n## LearnLoop", encoding="utf-8")

    initial_settings = {
        "mcpServers": {
            "learnloop": {"command": "learnloop", "args": ["serve"]},
            "sqlite": {"command": "uvx", "args": ["mcp-server-sqlite"]},
        },
        "chat.instructionsFilesLocations": {
            str(fake_home / ".copilot" / "instructions"): True,
            "~/.copilot/instructions": True,
            "~/.learnloop/rules": True,
            ".github/instructions": True,
            "C:\\MyCustomRules": True,
        },
    }
    settings_file.write_text(json.dumps(initial_settings, indent=2), encoding="utf-8")

    integrator = LearnLoopIntegrator(project_root=tmp_path)
    monkeypatch.setattr(integrator, "_get_vscode_user_settings_paths", lambda: [settings_file])

    cleaned = integrator.uninstall_ide("vscode")
    assert settings_file in cleaned
    assert copilot_inst in cleaned
    assert not copilot_inst.exists()

    updated = json.loads(settings_file.read_text(encoding="utf-8"))
    assert "learnloop" not in updated["mcpServers"]
    assert "sqlite" in updated["mcpServers"]

    locs = updated["chat.instructionsFilesLocations"]
    assert str(fake_home / ".copilot" / "instructions") not in locs
    assert "~/.copilot/instructions" not in locs
    assert "~/.learnloop/rules" not in locs
    assert locs[".github/instructions"] is True
    assert locs["C:\\MyCustomRules"] is True
