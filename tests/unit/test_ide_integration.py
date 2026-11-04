import json
import os
from pathlib import Path
from unittest.mock import patch

from learnloop.cli import cmd_init
from learnloop.integrator import LearnLoopIntegrator

IDE_VARS = [
    "TERM_PROGRAM",
    "VSCODE_PID",
    "VSCODE_CWD",
    "VSCODE_GIT_IPC_HANDLE",
    "CURSOR_TRACE_ID",
    "CURSOR_VERSION",
    "WINDSURF_VERSION",
    "ANTIGRAVITY_AGENT",
    "CLAUDE_CODE",
    "CLAUDE_PROJECT_DIR",
    "ZED_TERM",
]


def clean_ide_env(extra=None):
    env = dict(os.environ)
    for v in IDE_VARS:
        env.pop(v, None)
    if extra:
        env.update(extra)
    return env


def test_detect_active_ide_vscode(tmp_path: Path):
    env = clean_ide_env({"TERM_PROGRAM": "vscode", "VSCODE_CWD": "C:\\fake\\path"})
    with patch.dict(os.environ, env, clear=True):
        integrator = LearnLoopIntegrator(project_root=tmp_path)
        assert integrator.detect_active_ide() == "vscode"
        assert integrator.detect_ide() == ["vscode"]


def test_detect_active_ide_cursor(tmp_path: Path):
    env = clean_ide_env({"TERM_PROGRAM": "vscode", "CURSOR_TRACE_ID": "cursor-abc-123"})
    with patch.dict(os.environ, env, clear=True):
        integrator = LearnLoopIntegrator(project_root=tmp_path)
        assert integrator.detect_active_ide() == "cursor"
        assert integrator.detect_ide() == ["cursor"]


def test_detect_active_ide_windsurf(tmp_path: Path):
    env = clean_ide_env({"TERM_PROGRAM": "vscode", "WINDSURF_VERSION": "1.0.0"})
    with patch.dict(os.environ, env, clear=True):
        integrator = LearnLoopIntegrator(project_root=tmp_path)
        assert integrator.detect_active_ide() == "windsurf"
        assert integrator.detect_ide() == ["windsurf"]


def test_detect_active_ide_claude_code(tmp_path: Path):
    env = clean_ide_env({"CLAUDE_CODE": "1"})
    with patch.dict(os.environ, env, clear=True):
        integrator = LearnLoopIntegrator(project_root=tmp_path)
        assert integrator.detect_active_ide() == "claude"
        assert integrator.detect_ide() == ["claude"]


def test_detect_active_ide_zed(tmp_path: Path):
    env = clean_ide_env({"TERM_PROGRAM": "zed"})
    with patch.dict(os.environ, env, clear=True):
        integrator = LearnLoopIntegrator(project_root=tmp_path)
        assert integrator.detect_active_ide() == "zed"
        assert integrator.detect_ide() == ["zed"]


def test_detect_active_ide_antigravity(tmp_path: Path):
    env = clean_ide_env({"ANTIGRAVITY_AGENT": "1"})
    with patch.dict(os.environ, env, clear=True):
        integrator = LearnLoopIntegrator(project_root=tmp_path)
        assert integrator.detect_active_ide() == "agents"
        assert integrator.detect_ide() == ["agents"]


def test_detect_active_ide_project_marker_fallback(tmp_path: Path):
    env = clean_ide_env()
    with patch.dict(os.environ, env, clear=True):
        # Empty env, no markers -> defaults to agents
        integrator = LearnLoopIntegrator(project_root=tmp_path)
        assert integrator.detect_ide() == ["agents"]

        # If .cursorrules exists -> detects cursor
        (tmp_path / ".cursorrules").write_text("# cursor rules", encoding="utf-8")
        assert integrator.detect_ide() == ["cursor"]


def test_cmd_init_ghost_mode_default_does_not_pollute_workspace(tmp_path: Path):
    (tmp_path / ".git").mkdir()

    fake_home = tmp_path / "fake_home"
    fake_home.mkdir()
    fake_user_settings = fake_home / ".config" / "Code" / "User" / "settings.json"

    env = clean_ide_env({"TERM_PROGRAM": "vscode", "VSCODE_PID": "12345"})
    with patch.dict(os.environ, env, clear=True), \
         patch.object(LearnLoopIntegrator, "_get_vscode_user_settings_paths", return_value=[fake_user_settings]), \
         patch.object(LearnLoopIntegrator, "_get_vscode_cline_mcp_paths", return_value=[]):
        rc = cmd_init(tmp_path)
        assert rc == 0

        # Zero workspace pollution: In-repo editor configs must NOT exist
        assert not (tmp_path / ".vscode").exists()
        assert not (tmp_path / ".cursorrules").exists()
        assert not (tmp_path / ".cursor").exists()
        assert not (tmp_path / "CLAUDE.md").exists()
        assert not (tmp_path / ".windsurfrules").exists()
        assert not (tmp_path / ".windsurf").exists()
        assert not (tmp_path / ".zed").exists()
        assert not (tmp_path / "AGENTS.md").exists()
        assert not (tmp_path / "GEMINI.md").exists()
        assert not (tmp_path / ".learn").exists()

        # Ghost Mode: Global user settings must receive MCP configuration
        assert fake_user_settings.is_file()
        user_cfg = json.loads(fake_user_settings.read_text("utf-8"))
        assert "learnloop" in user_cfg.get("mcpServers", {})
        assert user_cfg["mcpServers"]["learnloop"]["args"] == ["serve"]


def test_cmd_init_in_repo_creates_local_vscode_config(tmp_path: Path):
    (tmp_path / ".git").mkdir()

    env = clean_ide_env({"TERM_PROGRAM": "vscode", "VSCODE_PID": "12345"})
    with patch.dict(os.environ, env, clear=True):
        rc = cmd_init(tmp_path, in_repo=True)
        assert rc == 0

        # VS Code in-repo configs must exist when in_repo=True
        assert (tmp_path / ".vscode" / "settings.json").is_file()
        assert (tmp_path / ".vscode" / "mcp.json").is_file()
        vsc_settings = json.loads((tmp_path / ".vscode" / "settings.json").read_text("utf-8"))
        assert "learnloop" in vsc_settings.get("mcpServers", {})
        assert vsc_settings["mcpServers"]["learnloop"]["args"] == ["serve"]

        # OTHER IDE configs must NOT be dumped
        assert not (tmp_path / ".cursorrules").exists()
        assert not (tmp_path / ".cursor").exists()
        assert not (tmp_path / "CLAUDE.md").exists()
        assert not (tmp_path / ".windsurfrules").exists()
        assert not (tmp_path / ".windsurf").exists()
        assert not (tmp_path / ".zed").exists()
        assert not (tmp_path / "AGENTS.md").exists()
        assert not (tmp_path / "GEMINI.md").exists()


def test_cmd_init_explicit_ide(tmp_path: Path):
    (tmp_path / ".git").mkdir()

    env = clean_ide_env({"TERM_PROGRAM": "vscode"})
    with patch.dict(os.environ, env, clear=True):
        # Even if in vscode terminal, explicit --ide cursor --in-repo should only configure in-repo cursor
        rc = cmd_init(tmp_path, ide="cursor", in_repo=True)
        assert rc == 0

        assert (tmp_path / ".cursorrules").is_file()
        assert (tmp_path / ".cursor" / "mcp.json").is_file()
        assert not (tmp_path / ".vscode").exists()
        assert not (tmp_path / ".windsurfrules").exists()


def test_cmd_init_all_flag_configures_everything_in_repo(tmp_path: Path):
    (tmp_path / ".git").mkdir()

    env = clean_ide_env({"TERM_PROGRAM": "vscode"})
    with patch.dict(os.environ, env, clear=True):
        rc = cmd_init(tmp_path, all_integrations=True, in_repo=True)
        assert rc == 0

        # All in-repo IDE configs exist
        assert (tmp_path / ".vscode" / "settings.json").is_file()
        assert (tmp_path / ".cursorrules").is_file()
        assert (tmp_path / "CLAUDE.md").is_file()
        assert (tmp_path / ".windsurfrules").is_file()
        assert (tmp_path / ".zed" / "settings.json").is_file()
        assert (tmp_path / "AGENTS.md").is_file()
        assert (tmp_path / "GEMINI.md").is_file()

        # Terminal integration wrappers exist in isolated user storage (Ghost Mode)
        from learnloop.config import get_workspace_storage_dir

        storage_dir = get_workspace_storage_dir(tmp_path)
        assert (storage_dir / "tools.sh").is_file()
        assert (storage_dir / "tools.bat").is_file()
        assert (storage_dir / "environment.sh").is_file()
        assert (storage_dir / "LearnLoop.ps1").is_file()
        assert (tmp_path / ".learn").exists()


def test_ghost_mode_across_all_ides_leaves_zero_repo_files(tmp_path: Path):
    """Test that all supported IDE integrations in default Ghost Mode write to global configs, never polluting repo."""
    (tmp_path / ".git").mkdir()

    fake_home = tmp_path / "global_user_home"
    fake_home.mkdir()

    fake_vsc_settings = fake_home / ".config" / "Code" / "User" / "settings.json"
    fake_cursor_mcp = fake_home / ".cursor" / "mcp.json"
    fake_windsurf_mcp = fake_home / ".codeium" / "windsurf" / "mcp_config.json"
    fake_claude_cfg = fake_home / ".config" / "Claude" / "claude_desktop_config.json"
    fake_zed_cfg = fake_home / ".config" / "zed" / "settings.json"

    with patch("pathlib.Path.home", return_value=fake_home), \
         patch.object(LearnLoopIntegrator, "_get_vscode_user_settings_paths", return_value=[fake_vsc_settings]), \
         patch.object(LearnLoopIntegrator, "_get_vscode_cline_mcp_paths", return_value=[]), \
         patch.object(LearnLoopIntegrator, "_get_cursor_global_config_path", return_value=fake_cursor_mcp), \
         patch.object(LearnLoopIntegrator, "_get_windsurf_global_config_path", return_value=fake_windsurf_mcp), \
         patch.object(LearnLoopIntegrator, "_get_claude_desktop_config_path", return_value=fake_claude_cfg), \
         patch.object(LearnLoopIntegrator, "_get_zed_global_config_path", return_value=fake_zed_cfg):

        integrator = LearnLoopIntegrator(project_root=tmp_path, in_repo=False)
        for ide in ("vscode", "cursor", "windsurf", "claude", "zed", "agents"):
            success = integrator.integrate_ide(ide)
            assert success is True

        # Verify repo is completely untouched (Ghost Mode guarantee)
        repo_files = list(tmp_path.iterdir())
        # Only .git and our test fixture fake_home exist in tmp_path
        expected_names = {".git", "global_user_home"}
        actual_names = {p.name for p in repo_files}
        assert actual_names == expected_names, f"Pollution detected: {actual_names - expected_names}"

        # Verify global files received configurations
        assert fake_vsc_settings.is_file()
        assert fake_cursor_mcp.is_file()
        assert fake_windsurf_mcp.is_file()
        assert fake_claude_cfg.is_file()
        assert fake_zed_cfg.is_file()
        assert (fake_home / ".learnloop" / "rules" / "AGENTS.md").is_file()

