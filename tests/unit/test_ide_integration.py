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


def test_cmd_init_in_vscode_terminal_only_configures_vscode(tmp_path: Path):
    (tmp_path / ".git").mkdir()

    env = clean_ide_env({"TERM_PROGRAM": "vscode", "VSCODE_PID": "12345"})
    with patch.dict(os.environ, env, clear=True):
        rc = cmd_init(tmp_path)
        assert rc == 0

        # VS Code configs must exist
        assert (tmp_path / ".vscode" / "settings.json").is_file()
        assert (tmp_path / ".vscode" / "mcp.json").is_file()
        vsc_settings = json.loads((tmp_path / ".vscode" / "settings.json").read_text("utf-8"))
        assert "learnloop" in vsc_settings.get("mcpServers", {})

        # OTHER IDE configs must NOT be dumped
        assert not (tmp_path / ".cursorrules").exists()
        assert not (tmp_path / ".cursor").exists()
        assert not (tmp_path / "CLAUDE.md").exists()
        assert not (tmp_path / ".windsurfrules").exists()
        assert not (tmp_path / ".windsurf").exists()
        assert not (tmp_path / ".zed").exists()
        assert not (tmp_path / "AGENTS.md").exists()
        assert not (tmp_path / "GEMINI.md").exists()

        # Terminal scripts must NOT be created on default init
        assert not (tmp_path / ".learn" / "tools.sh").exists()
        assert not (tmp_path / ".learn" / "tools.bat").exists()
        assert not (tmp_path / ".learn" / "environment.sh").exists()
        assert not (tmp_path / ".learn" / "LearnLoop.ps1").exists()


def test_cmd_init_explicit_ide(tmp_path: Path):
    (tmp_path / ".git").mkdir()

    env = clean_ide_env({"TERM_PROGRAM": "vscode"})
    with patch.dict(os.environ, env, clear=True):
        # Even if in vscode terminal, explicit --ide cursor should only configure cursor
        rc = cmd_init(tmp_path, ide="cursor")
        assert rc == 0

        assert (tmp_path / ".cursorrules").is_file()
        assert (tmp_path / ".cursor" / "mcp.json").is_file()
        assert not (tmp_path / ".vscode").exists()
        assert not (tmp_path / ".windsurfrules").exists()


def test_cmd_init_all_flag_configures_everything(tmp_path: Path):
    (tmp_path / ".git").mkdir()

    env = clean_ide_env({"TERM_PROGRAM": "vscode"})
    with patch.dict(os.environ, env, clear=True):
        rc = cmd_init(tmp_path, all_integrations=True)
        assert rc == 0

        # All IDE configs exist
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
        assert not (tmp_path / ".learn").exists()
