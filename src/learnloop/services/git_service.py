"""Git Integration Service for LearnLoop.

Manages git hook installation, commit recording, and queue processing.
Implements requirements 5.1-5.9, 6.1-6.5, 7.1-7.10, 36.1-36.6.
"""

from __future__ import annotations

import json
import logging
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

from learnloop.capture.queue import write_queue_entry
from learnloop.domain import clock

log = logging.getLogger(__name__)

# Hook marker for detecting LearnLoop hooks
HOOK_MARKER = "# learnloop-hook"

# Post-commit hook template
# Requirements:
# - 5.7: Hook records commit metadata (SHA, message, timestamp, files)
# - 5.8: Hook completes in under 50ms
# - 5.9: Hook returns exit code 0 even on error
# - 6.1: Extract commit SHA, message, timestamp, and file list
# - 6.2: Write JSON to .learn/queue/ directory
# - 6.3: Use commit SHA as filename for idempotency
# - 6.4: Include project path in queue file
# - 6.5: Complete file write in under 30ms
HOOK_TEMPLATE = (
    "#!/bin/sh\n"
    f"{HOOK_MARKER}\n"
    "# Fast, non-blocking, never fails the commit.\n"
    "# Writes a redacted metadata record to .learn/queue/.\n"
    '( "{python}" -m learnloop record-commit '
    '--repo "$(git rev-parse --show-toplevel)" ) >/dev/null 2>&1 &\n'
    "exit 0\n"
)


class GitIntegrationService:
    """Service for managing git hooks and commit tracking.
    
    Implements:
    - Requirement 5.1-5.6: Non-invasive hook installation
    - Requirement 5.7-5.9: Fast, reliable commit recording
    - Requirement 6.1-6.5: Queue entry creation
    """

    @staticmethod
    def generate_hook_script(python_path: str | None = None) -> str:
        """Generate the post-commit hook script.
        
        Requirements:
        - 6.1: Extract commit metadata (SHA, message, timestamp, files)
        - 6.2: Write JSON to .learn/queue/ directory
        - 6.3: Use commit SHA as filename for idempotency
        - 5.9: Add error handling with exit code 0 guarantee
        - 5.8: Optimize for <50ms execution time
        
        Args:
            python_path: Path to Python interpreter. If None, uses sys.executable.
        
        Returns:
            Hook script content as string
        """
        # Use absolute interpreter path for reliability across different shells
        # Convert backslashes to forward slashes for sh compatibility
        py = (python_path if python_path is not None else sys.executable).replace("\\", "/")
        return HOOK_TEMPLATE.format(python=py)

    @staticmethod
    def _replace_learnloop_section(existing_content: str, new_hook_content: str) -> str:
        """Replace the LearnLoop section in an existing hook file while preserving other content.
        
        The LearnLoop section starts with the HOOK_MARKER line and ends at:
        - The next shebang (#!/...), or
        - Another section marker/comment, or
        - An 'exit 0' line (the exit 0 is part of LearnLoop, content after is preserved)
        
        Args:
            existing_content: Current hook file content
            new_hook_content: New LearnLoop hook content (includes marker)
        
        Returns:
            Updated hook content with LearnLoop section replaced
        """
        lines = existing_content.split('\n')
        result_lines = []
        in_learnloop_section = False
        learnloop_inserted = False
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            if HOOK_MARKER in line and not in_learnloop_section:
                # Start of LearnLoop section - replace it with new content
                in_learnloop_section = True
                if not learnloop_inserted:
                    result_lines.append(new_hook_content.rstrip())
                    learnloop_inserted = True
                
            elif in_learnloop_section:
                # We're inside the LearnLoop section, skip until we find the end
                # End markers: 
                # 1. Next shebang
                # 2. Exit 0 line (marks end of LearnLoop section)
                # 3. Significant comment that's not about learnloop
                if line.strip().startswith('#!'):
                    # Found next shebang - end of our section
                    in_learnloop_section = False
                    result_lines.append(line)
                elif line.strip() == 'exit 0':
                    # Exit 0 is the last line of LearnLoop section
                    # End the section here, content after will be preserved
                    in_learnloop_section = False
                    # Don't add this line - it's already in new_hook_content
                elif line.strip().startswith('#') and 'learnloop' not in line.lower() and len(line.strip()) > 5:
                    # Significant comment that's not about learnloop
                    in_learnloop_section = False
                    result_lines.append(line)
                # Otherwise skip this line (it's part of old LearnLoop section)
                
            else:
                # Outside LearnLoop section - keep the line
                result_lines.append(line)
            
            i += 1
        
        return '\n'.join(result_lines)

    @staticmethod
    def install_hook(git_root: Path, python_path: str | None = None) -> dict[str, Any]:
        """Install or update post-commit hook.
        
        Requirements:
        - 5.1: Check for existing post-commit hooks
        - 5.2: Create new hook if none exists
        - 5.3: Append LearnLoop hook code to existing hooks without markers
        - 5.4: Update existing LearnLoop hooks to latest version
        - 5.5: Mark hook code with learnloop-hook comments
        - 5.6: Set executable permissions
        
        Args:
            git_root: Path to git repository root
            python_path: Path to Python interpreter. If None, uses sys.executable.
        
        Returns:
            Dict with status information:
            - success: bool
            - action: "created" | "updated" | "appended" | "skipped"
            - message: str
            - hook_path: str
        """
        # Check if git directory exists
        git_dir = git_root / ".git"
        if not git_dir.is_dir():
            return {
                "success": False,
                "action": "skipped",
                "message": "Not a git repository",
                "hook_path": None,
            }

        # Ensure hooks directory exists
        hooks_dir = git_dir / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)

        hook_path = hooks_dir / "post-commit"
        hook_content = GitIntegrationService.generate_hook_script(python_path)

        # Requirement 5.1: Check for existing post-commit hooks
        if not hook_path.exists():
            # Requirement 5.2: Create new hook file
            hook_path.write_text(hook_content, encoding="utf-8")
            # Requirement 5.6: Set executable permissions
            hook_path.chmod(hook_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            log.info(f"Created new post-commit hook at {hook_path}")
            return {
                "success": True,
                "action": "created",
                "message": "Installed new post-commit hook",
                "hook_path": str(hook_path),
            }

        # Read existing hook
        existing_content = hook_path.read_text(encoding="utf-8")

        # Requirement 5.4: Update existing LearnLoop hooks in-place
        if HOOK_MARKER in existing_content:
            # Replace LearnLoop section while preserving other content
            updated_content = GitIntegrationService._replace_learnloop_section(existing_content, hook_content)
            hook_path.write_text(updated_content, encoding="utf-8")
            # Requirement 5.6: Ensure executable permissions
            hook_path.chmod(hook_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            log.info(f"Updated existing LearnLoop hook at {hook_path}")
            return {
                "success": True,
                "action": "updated",
                "message": "Updated existing LearnLoop hook",
                "hook_path": str(hook_path),
            }

        # Requirement 5.3: Append LearnLoop hook code to existing hooks without markers
        # Don't append if the hook already contains references to learnloop
        if "learnloop" in existing_content.lower():
            log.warning(f"Hook at {hook_path} contains learnloop reference but no marker. Skipping.")
            return {
                "success": False,
                "action": "skipped",
                "message": "Hook contains learnloop but no marker - manual intervention needed",
                "hook_path": str(hook_path),
            }

        # Append our hook to existing hook
        combined_content = existing_content.rstrip() + "\n\n" + hook_content
        hook_path.write_text(combined_content, encoding="utf-8")
        # Requirement 5.6: Ensure executable permissions
        hook_path.chmod(hook_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        log.info(f"Appended LearnLoop hook to existing hook at {hook_path}")
        return {
            "success": True,
            "action": "appended",
            "message": "Appended LearnLoop hook to existing post-commit hook",
            "hook_path": str(hook_path),
        }

    @staticmethod
    def record_commit(repo_path: Path) -> dict[str, Any]:
        """Record commit metadata to queue.
        
        Called by the post-commit hook to capture commit information.
        Must be fast (<50ms) and never fail.
        
        Requirements:
        - 6.1: Extract commit SHA, message, timestamp, and file list
        - 6.2: Write commit metadata as JSON to .learn/queue/
        - 6.3: Use commit SHA as filename for idempotency
        - 6.4: Include project path to support multi-project tracking
        - 6.5: Complete file write in under 30 milliseconds
        - 5.8: Complete in under 50 milliseconds total
        - 5.9: Return exit code 0 even on error
        
        Args:
            repo_path: Path to git repository root
        
        Returns:
            Dict with status information (for testing/debugging)
        """
        try:
            # Extract commit metadata using git commands
            # Use subprocess for fast, direct git access
            
            # Get commit SHA
            sha_result = subprocess.run(
                ["git", "-C", str(repo_path), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
            sha = sha_result.stdout.strip()

            # Get commit message (first line only for speed)
            msg_result = subprocess.run(
                ["git", "-C", str(repo_path), "log", "-1", "--format=%s"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
            message = msg_result.stdout.strip()

            # Get commit timestamp in ISO format
            time_result = subprocess.run(
                ["git", "-C", str(repo_path), "log", "-1", "--format=%cI"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
            committed_at = clock.iso(clock.parse(time_result.stdout.strip()))

            # Get list of files changed in this commit
            files_result = subprocess.run(
                ["git", "-C", str(repo_path), "diff-tree", "--no-commit-id", "--name-only", "-r", "--root", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
            files = [f for f in files_result.stdout.splitlines() if f.strip()]

            # Write to queue using existing function
            # This handles redaction, idempotency, and atomic writes
            queue_file = write_queue_entry(repo_path, sha, message, files, committed_at)

            return {
                "success": True,
                "sha": sha,
                "queue_file": str(queue_file),
                "files_count": len(files),
            }

        except Exception as exc:
            # Requirement 5.9: Never fail the commit
            # Log error but return success
            log.error(f"Error recording commit in {repo_path}: {exc}")
            return {
                "success": False,
                "error": str(exc),
            }

    @staticmethod
    def check_git_repository(path: Path) -> Path | None:
        """Check if path is within a git repository and return the root.
        
        Args:
            path: Path to check
        
        Returns:
            Git repository root path, or None if not in a git repository
        """
        try:
            result = subprocess.run(
                ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                check=True,
                timeout=5,
            )
            return Path(result.stdout.strip())
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            return None

    @staticmethod
    def has_learnloop_hook(git_root: Path) -> bool:
        """Check if LearnLoop hook is installed.
        
        Args:
            git_root: Path to git repository root
        
        Returns:
            True if LearnLoop hook is installed
        """
        hook_path = git_root / ".git" / "hooks" / "post-commit"
        if not hook_path.exists():
            return False
        
        content = hook_path.read_text(encoding="utf-8")
        return HOOK_MARKER in content
