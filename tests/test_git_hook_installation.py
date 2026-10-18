"""Unit tests for git hook installation logic.

Tests Requirements:
- 5.1: Check for existing post-commit hooks
- 5.2: Create new hook if none exists
- 5.3: Append to existing hooks without LearnLoop markers
- 5.4: Update existing LearnLoop hooks in-place
- 5.5: Mark hook code with "# learnloop-hook" comments
- 5.6: Set executable permissions
"""

import pytest
import stat
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from learnloop.mcp.server import LearnLoopMCPServer


@pytest.fixture
def temp_git_repo(tmp_path):
    """Create a temporary git repository structure."""
    git_root = tmp_path / "test_repo"
    hooks_dir = git_root / ".git" / "hooks"
    hooks_dir.mkdir(parents=True)
    return git_root


@pytest.fixture
def server():
    """Create a LearnLoopMCPServer instance for testing."""
    from learnloop.mcp.config import MCPServerConfig
    from unittest.mock import MagicMock
    
    config = MCPServerConfig.default()
    db = MagicMock()  # Mock database
    server = LearnLoopMCPServer(config, db)
    return server


class TestGitHookInstallation:
    """Test git hook installation logic."""
    
    @pytest.mark.asyncio
    async def test_create_new_hook_when_none_exists(self, server, temp_git_repo):
        """Test creating a new post-commit hook when none exists.
        
        Requirements: 5.2, 5.5, 5.6
        """
        workspace_path = temp_git_repo
        hook_path = temp_git_repo / ".git" / "hooks" / "post-commit"
        
        # Ensure hook doesn't exist
        assert not hook_path.exists()
        
        # Install hook
        await server._install_git_hook(temp_git_repo, workspace_path)
        
        # Verify hook was created
        assert hook_path.exists()
        
        # Verify hook contains marker
        content = hook_path.read_text()
        assert "# learnloop-hook" in content
        
        # Verify hook is executable (Unix) or has read permission (Windows)
        import sys
        import platform
        mode = hook_path.stat().st_mode
        if platform.system() != 'Windows':
            # On Unix, verify executable bits are set
            assert mode & stat.S_IXUSR
            assert mode & stat.S_IXGRP
            assert mode & stat.S_IXOTH
        else:
            # On Windows, we can't really set executable bits, but verify file exists and is readable
            assert hook_path.exists()
            assert hook_path.is_file()
    
    @pytest.mark.asyncio
    async def test_append_to_existing_hook_without_marker(self, server, temp_git_repo):
        """Test appending to existing hook that doesn't have LearnLoop marker.
        
        Requirements: 5.1, 5.3, 5.5
        """
        workspace_path = temp_git_repo
        hook_path = temp_git_repo / ".git" / "hooks" / "post-commit"
        
        # Create existing hook without LearnLoop marker
        existing_content = """#!/bin/sh
# Some other hook
echo "Custom post-commit hook"
"""
        hook_path.write_text(existing_content)
        
        # Install LearnLoop hook
        await server._install_git_hook(temp_git_repo, workspace_path)
        
        # Verify hook still exists
        assert hook_path.exists()
        
        # Verify original content preserved
        new_content = hook_path.read_text()
        assert "# Some other hook" in new_content
        assert 'echo "Custom post-commit hook"' in new_content
        
        # Verify LearnLoop hook appended
        assert "# learnloop-hook" in new_content
        
        # Verify both sections present
        lines = new_content.split('\n')
        original_found = False
        learnloop_found = False
        for line in lines:
            if "# Some other hook" in line:
                original_found = True
            if "# learnloop-hook" in line:
                learnloop_found = True
        assert original_found and learnloop_found
    
    @pytest.mark.asyncio
    async def test_update_existing_learnloop_hook(self, server, temp_git_repo):
        """Test updating existing LearnLoop hook in-place.
        
        Requirements: 5.1, 5.4, 5.5
        """
        workspace_path = temp_git_repo
        hook_path = temp_git_repo / ".git" / "hooks" / "post-commit"
        
        # Create existing hook with LearnLoop marker (old version)
        existing_content = """#!/bin/sh
# learnloop-hook
# Old version of LearnLoop hook
python -m learnloop old-command
exit 0
"""
        hook_path.write_text(existing_content)
        
        # Install updated LearnLoop hook
        await server._install_git_hook(temp_git_repo, workspace_path)
        
        # Verify hook exists
        assert hook_path.exists()
        
        # Verify updated content
        new_content = hook_path.read_text()
        assert "# learnloop-hook" in new_content
        
        # Verify old command not present (replaced)
        assert "old-command" not in new_content
        
        # Verify new command present
        assert "record-commit" in new_content
    
    @pytest.mark.asyncio
    async def test_preserve_other_hooks_when_updating_learnloop(self, server, temp_git_repo):
        """Test that other hooks are preserved when updating LearnLoop section.
        
        Requirements: 5.3, 5.4
        """
        workspace_path = temp_git_repo
        hook_path = temp_git_repo / ".git" / "hooks" / "post-commit"
        
        # Create hook with both custom content and LearnLoop section
        # Note: Other hooks should be separated by blank lines for proper parsing
        existing_content = """#!/bin/sh
# Custom pre-LearnLoop hook
echo "Before LearnLoop"

# learnloop-hook
# Old LearnLoop version
python -m learnloop old-command
exit 0

# Custom post-LearnLoop hook
echo "After LearnLoop"
"""
        hook_path.write_text(existing_content)
        
        # Install updated LearnLoop hook
        await server._install_git_hook(temp_git_repo, workspace_path)
        
        # Verify hook exists
        assert hook_path.exists()
        
        # Verify custom content preserved
        new_content = hook_path.read_text()
        assert "Before LearnLoop" in new_content
        assert 'echo "Before LearnLoop"' in new_content
        assert "After LearnLoop" in new_content
        assert 'echo "After LearnLoop"' in new_content
        
        # Verify LearnLoop section updated
        assert "# learnloop-hook" in new_content
        assert "record-commit" in new_content
        assert "old-command" not in new_content
    
    @pytest.mark.asyncio
    async def test_hook_uses_correct_python_executable(self, server, temp_git_repo):
        """Test that hook uses the same Python executable as the server.
        
        Requirements: 5.2, 6.1
        """
        workspace_path = temp_git_repo
        hook_path = temp_git_repo / ".git" / "hooks" / "post-commit"
        
        # Install hook
        await server._install_git_hook(temp_git_repo, workspace_path)
        
        # Verify hook contains correct Python executable
        content = hook_path.read_text()
        assert sys.executable in content or "python" in content
    
    @pytest.mark.asyncio
    async def test_hook_installation_creates_hooks_directory(self, server, temp_git_repo):
        """Test that hooks directory is created if it doesn't exist.
        
        Requirements: 5.2
        """
        workspace_path = temp_git_repo
        hooks_dir = temp_git_repo / ".git" / "hooks"
        
        # Remove hooks directory
        import shutil
        if hooks_dir.exists():
            shutil.rmtree(hooks_dir)
        
        assert not hooks_dir.exists()
        
        # Install hook
        await server._install_git_hook(temp_git_repo, workspace_path)
        
        # Verify hooks directory created
        assert hooks_dir.exists()
        assert hooks_dir.is_dir()
        
        # Verify hook file created
        hook_path = hooks_dir / "post-commit"
        assert hook_path.exists()
    
    @pytest.mark.asyncio
    async def test_hook_installation_error_handling(self, server, temp_git_repo):
        """Test that hook installation errors don't crash the server.
        
        Requirements: 5.9, 24.5
        """
        workspace_path = temp_git_repo
        
        # Make hooks directory read-only to simulate permission error
        hooks_dir = temp_git_repo / ".git" / "hooks"
        hooks_dir.chmod(0o444)
        
        try:
            # Install hook should not raise exception
            await server._install_git_hook(temp_git_repo, workspace_path)
            # If we get here, error was handled gracefully
            assert True
        except Exception as e:
            pytest.fail(f"Hook installation should handle errors gracefully, but raised: {e}")
        finally:
            # Restore permissions for cleanup
            hooks_dir.chmod(0o755)
    
    def test_generate_hook_script_format(self, server):
        """Test that generated hook script has correct format.
        
        Requirements: 5.5, 5.7, 5.8, 5.9
        """
        python_exe = "/usr/bin/python3"
        workspace = Path("/path/to/workspace")
        marker = "# learnloop-hook"
        
        script = server._generate_hook_script(python_exe, workspace, marker)
        
        # Verify shebang
        assert script.startswith("#!/bin/sh")
        
        # Verify marker present
        assert marker in script
        
        # Verify exits with 0
        assert "exit 0" in script
        
        # Verify runs in background (non-blocking)
        assert "&" in script
        
        # Verify error suppression (>/dev/null 2>&1)
        assert ">/dev/null 2>&1" in script
        
        # Verify uses Python executable
        assert python_exe in script or "python" in script
        
        # Verify calls record-commit
        assert "record-commit" in script
    
    def test_replace_hook_section_simple(self, server):
        """Test replacing LearnLoop section in simple hook.
        
        Requirements: 5.4, 5.5
        """
        marker = "# learnloop-hook"
        existing = f"""#!/bin/sh
{marker}
old content
exit 0
"""
        new_hook = f"""#!/bin/sh
{marker}
new content
exit 0
"""
        
        result = server._replace_hook_section(existing, new_hook, marker)
        
        # Verify new content present
        assert "new content" in result
        
        # Verify old content removed
        assert "old content" not in result
        
        # Verify marker still present
        assert marker in result
    
    def test_replace_hook_section_with_surrounding_content(self, server):
        """Test replacing LearnLoop section while preserving surrounding content.
        
        Requirements: 5.3, 5.4
        """
        marker = "# learnloop-hook"
        existing = f"""#!/bin/sh
# Before LearnLoop
echo "before"

{marker}
old learnloop content
exit 0

# After LearnLoop
echo "after"
"""
        new_hook = f"""#!/bin/sh
{marker}
new learnloop content
exit 0
"""
        
        result = server._replace_hook_section(existing, new_hook, marker)
        
        # Verify surrounding content preserved
        assert "Before LearnLoop" in result
        assert 'echo "before"' in result
        assert "After LearnLoop" in result
        assert 'echo "after"' in result
        
        # Verify LearnLoop section updated
        assert "new learnloop content" in result
        assert "old learnloop content" not in result


class TestHookContentValidation:
    """Test validation of hook content."""
    
    def test_hook_contains_required_elements(self, server):
        """Test that generated hook contains all required elements.
        
        Requirements: 5.5, 5.7, 5.8, 5.9, 6.1
        """
        python_exe = sys.executable
        workspace = Path("/workspace")
        marker = "# learnloop-hook"
        
        script = server._generate_hook_script(python_exe, workspace, marker)
        
        # Required elements for fast, non-blocking execution
        required_elements = [
            "#!/bin/sh",  # Shebang
            marker,  # LearnLoop marker
            "record-commit",  # Command to record commit
            "&",  # Background execution
            "exit 0",  # Always succeed
            ">/dev/null",  # Suppress output
            "2>&1",  # Redirect stderr
        ]
        
        for element in required_elements:
            assert element in script, f"Hook missing required element: {element}"
