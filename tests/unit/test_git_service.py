"""Unit tests for Git Integration Service.

Tests requirements 5.1-5.9, 6.1-6.5 for hook generation and installation.
"""

from __future__ import annotations

import json
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from learnloop.services.git_service import HOOK_MARKER, GitIntegrationService


class TestHookGeneration:
    """Test hook script generation."""

    def test_generate_hook_script_default_python(self):
        """Test hook generation uses sys.executable by default."""
        hook_script = GitIntegrationService.generate_hook_script()
        
        # Should contain hook marker
        assert HOOK_MARKER in hook_script
        
        # Should contain python path with forward slashes
        expected_python = sys.executable.replace("\\", "/")
        assert expected_python in hook_script
        
        # Should contain record-commit command
        assert "record-commit" in hook_script
        
        # Should exit with 0
        assert "exit 0" in hook_script

    def test_generate_hook_script_custom_python(self):
        """Test hook generation with custom python path."""
        custom_path = "/usr/bin/python3"
        hook_script = GitIntegrationService.generate_hook_script(custom_path)
        
        assert custom_path in hook_script
        assert HOOK_MARKER in hook_script

    def test_hook_script_has_shebang(self):
        """Test hook script starts with proper shebang."""
        hook_script = GitIntegrationService.generate_hook_script()
        
        assert hook_script.startswith("#!/bin/sh\n")

    def test_hook_script_is_non_blocking(self):
        """Test hook script runs in background and never fails commit."""
        hook_script = GitIntegrationService.generate_hook_script()
        
        # Should run in background with ()
        assert "( " in hook_script
        
        # Should redirect output
        assert ">/dev/null 2>&1 &" in hook_script
        
        # Should always exit 0
        assert hook_script.strip().endswith("exit 0")

    def test_hook_script_uses_git_rev_parse(self):
        """Test hook script dynamically detects repo root."""
        hook_script = GitIntegrationService.generate_hook_script()
        
        # Should use git rev-parse to find repo root
        assert "git rev-parse --show-toplevel" in hook_script


class TestHookInstallation:
    """Test hook installation logic."""

    def test_install_hook_not_git_repo(self, tmp_path: Path):
        """Test hook installation fails gracefully on non-git directory."""
        result = GitIntegrationService.install_hook(tmp_path)
        
        assert result["success"] is False
        assert result["action"] == "skipped"
        assert "not a git repository" in result["message"].lower()
        assert result["hook_path"] is None

    def test_install_hook_creates_new(self, tmp_path: Path):
        """Test creating new hook in fresh git repository.
        
        Requirement 5.2: Create new hook if none exists
        Requirement 5.6: Set executable permissions
        """
        # Initialize git repo
        git_dir = tmp_path / ".git"
        hooks_dir = git_dir / "hooks"
        hooks_dir.mkdir(parents=True)
        
        result = GitIntegrationService.install_hook(tmp_path)
        
        assert result["success"] is True
        assert result["action"] == "created"
        assert "installed new" in result["message"].lower()
        
        # Check hook file exists
        hook_path = Path(result["hook_path"])
        assert hook_path.exists()
        assert hook_path.name == "post-commit"
        
        # Check hook content
        content = hook_path.read_text(encoding="utf-8")
        assert HOOK_MARKER in content
        assert "record-commit" in content
        
        # Check executable permissions (skip on Windows where chmod doesn't work the same)
        import platform
        if platform.system() != "Windows":
            mode = hook_path.stat().st_mode
            assert mode & stat.S_IXUSR  # User executable

    def test_install_hook_updates_existing_learnloop_hook(self, tmp_path: Path):
        """Test updating existing LearnLoop hook.
        
        Requirement 5.4: Update existing LearnLoop hooks in-place
        """
        # Initialize git repo with existing LearnLoop hook
        git_dir = tmp_path / ".git"
        hooks_dir = git_dir / "hooks"
        hooks_dir.mkdir(parents=True)
        
        hook_path = hooks_dir / "post-commit"
        old_hook = f"#!/bin/sh\n{HOOK_MARKER}\necho 'old version'\nexit 0\n"
        hook_path.write_text(old_hook, encoding="utf-8")
        
        result = GitIntegrationService.install_hook(tmp_path)
        
        assert result["success"] is True
        assert result["action"] == "updated"
        assert "updated existing" in result["message"].lower()
        
        # Check hook was updated
        new_content = hook_path.read_text(encoding="utf-8")
        assert HOOK_MARKER in new_content
        assert "record-commit" in new_content
        assert "old version" not in new_content

    def test_install_hook_appends_to_foreign_hook(self, tmp_path: Path):
        """Test appending to existing non-LearnLoop hook.
        
        Requirement 5.3: Append to existing hooks without markers
        Requirement 5.5: Mark hook code with learnloop-hook comments
        """
        # Initialize git repo with foreign hook
        git_dir = tmp_path / ".git"
        hooks_dir = git_dir / "hooks"
        hooks_dir.mkdir(parents=True)
        
        hook_path = hooks_dir / "post-commit"
        foreign_hook = "#!/bin/sh\necho 'custom hook'\n"
        hook_path.write_text(foreign_hook, encoding="utf-8")
        
        result = GitIntegrationService.install_hook(tmp_path)
        
        assert result["success"] is True
        assert result["action"] == "appended"
        assert "appended" in result["message"].lower()
        
        # Check both hooks are present
        content = hook_path.read_text(encoding="utf-8")
        assert "custom hook" in content  # Original hook preserved
        assert HOOK_MARKER in content  # LearnLoop hook added
        assert "record-commit" in content

    def test_install_hook_skips_suspicious_hook(self, tmp_path: Path):
        """Test skipping hook that mentions learnloop without marker.
        
        Prevents corrupting manually modified hooks.
        """
        # Initialize git repo with suspicious hook
        git_dir = tmp_path / ".git"
        hooks_dir = git_dir / "hooks"
        hooks_dir.mkdir(parents=True)
        
        hook_path = hooks_dir / "post-commit"
        suspicious_hook = "#!/bin/sh\necho 'learnloop modified'\n"
        hook_path.write_text(suspicious_hook, encoding="utf-8")
        
        result = GitIntegrationService.install_hook(tmp_path)
        
        assert result["success"] is False
        assert result["action"] == "skipped"
        assert "manual intervention" in result["message"].lower()
        
        # Hook should be unchanged
        content = hook_path.read_text(encoding="utf-8")
        assert content == suspicious_hook

    def test_install_hook_creates_hooks_directory(self, tmp_path: Path):
        """Test hook installation creates hooks directory if missing."""
        # Initialize git repo without hooks directory
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        
        result = GitIntegrationService.install_hook(tmp_path)
        
        assert result["success"] is True
        assert (git_dir / "hooks").is_dir()
        assert (git_dir / "hooks" / "post-commit").exists()


class TestCommitRecording:
    """Test commit recording functionality."""

    def test_record_commit_success(self, tmp_path: Path):
        """Test successful commit recording.
        
        Requirements:
        - 6.1: Extract commit SHA, message, timestamp, and file list
        - 6.2: Write JSON to .learn/queue/
        - 6.3: Use commit SHA as filename for idempotency
        """
        # Initialize git repo with commit
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True)
        
        # Create and commit a file
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        subprocess.run(["git", "add", "test.txt"], cwd=tmp_path, check=True)
        subprocess.run(["git", "commit", "-m", "Test commit"], cwd=tmp_path, check=True)
        
        # Record the commit
        result = GitIntegrationService.record_commit(tmp_path)
        
        assert result["success"] is True
        assert "sha" in result
        assert len(result["sha"]) == 40  # Git SHA length
        assert "queue_file" in result
        assert result["files_count"] == 1
        
        # Check queue file was created
        queue_file = Path(result["queue_file"])
        assert queue_file.exists()
        assert queue_file.parent.name == "queue"
        assert queue_file.name == f"{result['sha']}.json"
        
        # Check queue file content
        queue_data = json.loads(queue_file.read_text(encoding="utf-8"))
        assert queue_data["sha"] == result["sha"]
        assert "test commit" in queue_data["message"].lower()
        assert "test.txt" in queue_data["files"]
        assert "committed_at" in queue_data

    def test_record_commit_handles_error_gracefully(self, tmp_path: Path):
        """Test commit recording never fails the commit.
        
        Requirement 5.9: Return exit code 0 even on error
        """
        # Try to record commit in non-git directory
        result = GitIntegrationService.record_commit(tmp_path)
        
        # Should return failure but not raise exception
        assert result["success"] is False
        assert "error" in result

    def test_record_commit_idempotency(self, tmp_path: Path):
        """Test recording same commit twice uses same filename.
        
        Requirement 6.3: Use commit SHA as filename for idempotency
        """
        # Initialize git repo with commit
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True)
        
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        subprocess.run(["git", "add", "test.txt"], cwd=tmp_path, check=True)
        subprocess.run(["git", "commit", "-m", "Test commit"], cwd=tmp_path, check=True)
        
        # Record commit twice
        result1 = GitIntegrationService.record_commit(tmp_path)
        result2 = GitIntegrationService.record_commit(tmp_path)
        
        # Should create same file
        assert result1["sha"] == result2["sha"]
        assert result1["queue_file"] == result2["queue_file"]


class TestGitRepositoryDetection:
    """Test git repository detection."""

    def test_check_git_repository_valid(self, tmp_path: Path):
        """Test detecting valid git repository."""
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        
        git_root = GitIntegrationService.check_git_repository(tmp_path)
        
        assert git_root is not None
        assert git_root == tmp_path

    def test_check_git_repository_not_git(self, tmp_path: Path):
        """Test detecting non-git directory."""
        git_root = GitIntegrationService.check_git_repository(tmp_path)
        
        assert git_root is None

    def test_check_git_repository_subdirectory(self, tmp_path: Path):
        """Test detecting git repository from subdirectory."""
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
        
        # Create subdirectory
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        
        git_root = GitIntegrationService.check_git_repository(subdir)
        
        assert git_root is not None
        assert git_root == tmp_path


class TestLearnLoopHookDetection:
    """Test LearnLoop hook detection."""

    def test_has_learnloop_hook_not_installed(self, tmp_path: Path):
        """Test detecting absence of LearnLoop hook."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        
        assert not GitIntegrationService.has_learnloop_hook(tmp_path)

    def test_has_learnloop_hook_installed(self, tmp_path: Path):
        """Test detecting presence of LearnLoop hook."""
        # Initialize git repo
        git_dir = tmp_path / ".git"
        hooks_dir = git_dir / "hooks"
        hooks_dir.mkdir(parents=True)
        
        # Install hook
        GitIntegrationService.install_hook(tmp_path)
        
        assert GitIntegrationService.has_learnloop_hook(tmp_path)

    def test_has_learnloop_hook_foreign_hook(self, tmp_path: Path):
        """Test detecting hook without LearnLoop marker."""
        git_dir = tmp_path / ".git"
        hooks_dir = git_dir / "hooks"
        hooks_dir.mkdir(parents=True)
        
        hook_path = hooks_dir / "post-commit"
        hook_path.write_text("#!/bin/sh\necho 'foreign hook'\n", encoding="utf-8")
        
        assert not GitIntegrationService.has_learnloop_hook(tmp_path)
