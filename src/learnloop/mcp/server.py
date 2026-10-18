"""LearnLoop MCP Server implementation.

This module implements the Model Context Protocol server for LearnLoop with automatic
project detection, context initialization, and progressive feature unlocking.

Requirements:
- 1.1: Automatic project detection and initialization
- 1.2-1.5: Auto-bootstrap for new projects
- 1.6-1.9: Context detection and loading
- 2.1-2.5: Zero-friction welcome experience
- 25.1: Project initialization within 500ms
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import UUID

from learnloop.domain.project_context import ProjectContext, Technology
from learnloop.mcp.config import MCPServerConfig
from learnloop.persistence.async_db import AsyncDatabase
from learnloop.capture.techscan import scan_technologies, DetectedTechnology

log = logging.getLogger(__name__)


class LearnLoopMCPServer:
    """MCP server with automatic project detection and progressive enhancement.
    
    This class manages the Model Context Protocol server lifecycle including:
    - Automatic workspace context detection
    - Auto-bootstrap for new projects
    - Progressive feature unlocking based on readiness level
    - Tool routing and response formatting
    
    Requirements:
    - 1.1: Auto-detect project existence
    - 1.9: Return project context to AI assistant
    - 25.1: Initialize in under 500ms
    """
    
    def __init__(self, config: MCPServerConfig, db: AsyncDatabase):
        """Initialize MCP server with configuration and database.
        
        Args:
            config: Server configuration settings
            db: Async database connection
        """
        self.config = config
        self.db = db
        self._initialized = False
        self._current_project: Optional[ProjectContext] = None
    
    async def initialize(self, workspace_path: Path) -> dict:
        """Initialize server with automatic project detection.
        
        This method:
        1. Detects or bootstraps project context
        2. Generates appropriate welcome/briefing message
        3. Registers MCP capabilities
        
        Requirements:
        - 1.1: Detect whether LearnLoop project exists
        - 1.9: Complete initialization and return context
        - 25.1: Complete in under 500ms
        
        Args:
            workspace_path: Absolute path to workspace directory
        
        Returns:
            Dictionary with initialization result and messages
        
        Raises:
            ValueError: If workspace_path is invalid
        """
        start_time = datetime.now(timezone.utc)
        
        if not workspace_path.exists():
            raise ValueError(f"Workspace path does not exist: {workspace_path}")
        
        if not workspace_path.is_dir():
            raise ValueError(f"Workspace path is not a directory: {workspace_path}")
        
        # Ensure database is initialized
        await self.db.initialize()
        
        # Detect or bootstrap project context
        self._current_project = await self.detect_context(workspace_path)
        
        # Generate appropriate message
        if self._current_project.is_new:
            message = self._generate_welcome_message(self._current_project)
            message_type = "welcome"
        else:
            message = self._generate_briefing_message(self._current_project)
            message_type = "briefing"
        
        self._initialized = True
        
        # Calculate initialization time
        elapsed_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        
        log.info(f"Initialized LearnLoop for project {self._current_project.name} in {elapsed_ms:.1f}ms")
        
        return {
            "success": True,
            "project_id": str(self._current_project.id),
            "project_name": self._current_project.name,
            "is_new": self._current_project.is_new,
            "readiness_level": self._current_project.readiness_level,
            "message_type": message_type,
            "message": message,
            "initialization_time_ms": elapsed_ms,
        }
    
    async def detect_context(self, workspace_path: Path) -> ProjectContext:
        """Auto-detect project context or bootstrap new project.
        
        This method implements the context detection algorithm:
        1. Check for existing project in database
        2. If found, load and update last accessed timestamp
        3. If not found, create new project with auto-detected metadata
        
        Requirements:
        - 1.1: Detect whether project exists
        - 1.6: Load existing project context
        - 1.7: Detect project technologies
        - 1.8: Calculate initial readiness level
        
        Args:
            workspace_path: Absolute path to workspace directory
        
        Returns:
            ProjectContext (existing or newly created)
        """
        # Step 1: Check for existing project
        existing_project = await self.db.get_project_by_path(workspace_path)
        
        if existing_project:
            log.info(f"Loaded existing project: {existing_project.name}")
            
            # Update last accessed timestamp
            await self.db.update_project_last_accessed(existing_project.id)
            
            return existing_project
        
        # Step 2: Auto-bootstrap new project
        log.info(f"Bootstrapping new project in {workspace_path}")
        
        # Detect git repository root
        git_root = self._detect_git_root(workspace_path)
        
        # Extract project name from path or git
        project_name = self._extract_project_name(workspace_path, git_root)
        
        # Detect technologies
        technologies = await self._detect_technologies(workspace_path)
        
        # Create project record in database
        project = await self.db.create_project(
            name=project_name,
            repo_path=workspace_path,
            git_root=git_root,
            technologies=technologies,
        )
        
        # Initialize .learn/ directory structure
        await self._bootstrap_learn_directory(workspace_path)
        
        # Install git hook if git repository detected
        if git_root:
            await self._install_git_hook(git_root, workspace_path)
        
        log.info(f"Created new project {project.id}: {project_name}")
        
        return project
    
    def _detect_git_root(self, workspace_path: Path) -> Optional[Path]:
        """Detect git repository root from workspace path.
        
        Walks up the directory tree looking for .git directory.
        
        Args:
            workspace_path: Starting directory
        
        Returns:
            Path to git root if found, None otherwise
        """
        current = workspace_path.resolve()
        
        # Walk up the directory tree
        for _ in range(10):  # Limit depth to prevent infinite loops
            git_dir = current / ".git"
            if git_dir.exists() and git_dir.is_dir():
                return current
            
            parent = current.parent
            if parent == current:  # Reached filesystem root
                break
            current = parent
        
        return None
    
    def _extract_project_name(self, workspace_path: Path, git_root: Optional[Path]) -> str:
        """Extract project name from path or git configuration.
        
        Priority:
        1. Git repository directory name
        2. Workspace directory name
        
        Args:
            workspace_path: Workspace directory
            git_root: Git repository root (if detected)
        
        Returns:
            Project name string
        """
        if git_root:
            return git_root.name
        
        return workspace_path.name
    
    async def _detect_technologies(self, workspace_path: Path) -> list[Technology]:
        """Detect project technologies by scanning configuration files.
        
        Uses techscan module to detect:
        - Python dependencies (requirements.txt, pyproject.toml)
        - Node.js dependencies (package.json)
        - Go dependencies (go.mod)
        - Rust dependencies (Cargo.toml)
        - Docker images (Dockerfile, docker-compose.yml)
        
        Requirements:
        - 19.1-19.7: Technology detection from config files
        
        Args:
            workspace_path: Directory to scan
        
        Returns:
            List of detected Technology objects
        """
        # Run technology scan (CPU-bound operation)
        detected: list[DetectedTechnology] = await asyncio.to_thread(
            scan_technologies, workspace_path
        )
        
        # Convert to Technology domain objects
        technologies = []
        for tech in detected:
            technologies.append(Technology(
                name=tech["name"],
                version=tech["version_spec"],
                category=tech["ecosystem"],
            ))
        
        log.info(f"Detected {len(technologies)} technologies in {workspace_path}")
        
        return technologies
    
    async def _bootstrap_learn_directory(self, workspace_path: Path) -> None:
        """Initialize .learn/ directory structure for new project.
        
        Creates:
        - .learn/ directory
        - .learn/queue/ directory for commit queue entries
        - .learn/.gitignore to exclude queue files
        - .learn/concepts.md with template
        
        Requirements:
        - 1.3: Initialize .learn/ directory structure
        - 1.4: Create .learn/queue/ directory
        - 5.2: Write .learn/.gitignore file
        - 5.3: Initialize concepts.md with template
        
        Args:
            workspace_path: Project workspace directory
        """
        learn_dir = workspace_path / ".learn"
        
        # Create directories
        learn_dir.mkdir(exist_ok=True)
        (learn_dir / "queue").mkdir(exist_ok=True)
        
        # Create .gitignore
        gitignore_path = learn_dir / ".gitignore"
        gitignore_content = """# LearnLoop queue entries (processed after reconciliation)
queue/
*.log
"""
        await asyncio.to_thread(gitignore_path.write_text, gitignore_content, encoding="utf-8")
        
        # Initialize concepts.md
        concepts_path = learn_dir / "concepts.md"
        if not concepts_path.exists():
            concepts_content = """# Learning Concepts

This file tracks concepts and skills you're learning in this project.
LearnLoop automatically maintains this file as you document your learning.

## How to Use

1. **Declare Intent**: Start a learning session with `start_skill_session`
2. **Write Code**: Implement your feature and commit with git
3. **Explain Back**: Answer prompts about what you learned
4. **Review**: Complete spaced repetition reviews to cement knowledge

---

"""
            await asyncio.to_thread(concepts_path.write_text, concepts_content, encoding="utf-8")
        
        log.info(f"Initialized .learn/ directory structure in {workspace_path}")
    
    async def _install_git_hook(self, git_root: Path, workspace_path: Path) -> None:
        """Install post-commit git hook for automatic tracking.
        
        Requirements:
        - 1.5: Install git hook if repository detected
        - 5.1-5.6: Non-invasive hook installation
        
        Args:
            git_root: Git repository root
            workspace_path: Project workspace path
        """
        from learnloop.services.git_service import GitIntegrationService
        
        try:
            result = GitIntegrationService.install_hook(git_root)
            
            if result["success"]:
                log.info(f"Git hook {result['action']}: {result['message']}")
            else:
                log.warning(f"Git hook installation skipped: {result['message']}")
                log.info("LearnLoop will continue without automatic commit tracking")
                log.info("You can manually track commits using the ingest_queue tool")
                
        except Exception as e:
            # Log error but don't fail - continue without hooks
            log.error(f"Failed to install git hook: {e}")
            log.info("LearnLoop will continue without automatic commit tracking")
            log.info("You can manually track commits using the ingest_queue tool")
    
    def _generate_hook_script(self, python_executable: str, workspace_path: Path, marker: str) -> str:
        """Generate the post-commit hook script content.
        
        Requirements:
        - 5.7: Record commit metadata to .learn/queue/ directory
        - 5.8: Complete in under 50 milliseconds
        - 5.9: Return exit code 0 even on errors
        - 6.1-6.5: Extract commit metadata and write to queue
        
        Args:
            python_executable: Path to Python executable
            workspace_path: Project workspace path
            marker: Unique marker comment for LearnLoop section
            
        Returns:
            Hook script content as string
        """
        # Use the template from integrations/hooks/post-commit but make it work with the MCP server
        script = f'''#!/bin/sh
{marker}
# Fast, non-blocking, never fails the commit.
# Writes commit metadata to .learn/queue/ for later processing.
( "{python_executable}" -m learnloop record-commit --repo "$(git rev-parse --show-toplevel)" ) >/dev/null 2>&1 &
exit 0
'''
        return script
    
    def _replace_hook_section(self, existing_content: str, new_hook_content: str, marker: str) -> str:
        """Replace the LearnLoop section in an existing hook file while preserving other content.
        
        Requirements:
        - 5.4: Update existing LearnLoop hooks in-place
        - 5.5: Use marker comments to identify LearnLoop section
        
        The LearnLoop section starts with the marker line and ends at:
        - The next shebang (#!/...), or
        - Another section marker/comment, or
        - An 'exit 0' line (the exit 0 is part of LearnLoop, content after is preserved)
        
        Args:
            existing_content: Current hook file content
            new_hook_content: New LearnLoop hook content (includes marker)
            marker: Unique marker comment identifying LearnLoop section
        
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
            
            if marker in line and not in_learnloop_section:
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
    
    def _generate_welcome_message(self, project: ProjectContext) -> str:
        """Generate welcome message for new users.
        
        Requirements:
        - 2.1: Generate welcome message explaining core concepts
        - 2.2: Message under 100 words
        - 2.3: Explain no manual actions required
        - 2.4: Offer optional quick start actions
        - 2.5: Allow declining quick start
        
        Args:
            project: Newly created project context
        
        Returns:
            Welcome message string
        """
        tech_list = ", ".join([t.name for t in project.technologies[:5]]) if project.technologies else "your stack"
        
        message = f"""# 🎓 Welcome to LearnLoop!

I've automatically set up learning tracking for **{project.name}** (detected: {tech_list}).

**Core Concept**: Learning through *doing* (exposure) + *explaining* (mastery).

**How it works**:
1. Declare what you're learning before coding
2. I track your commits automatically
3. I'll ask you to explain what you learned
4. Spaced reviews help you remember

No setup needed—you're ready to start! Just begin coding and I'll guide you."""
        
        return message
    
    def _generate_briefing_message(self, project: ProjectContext) -> str:
        """Generate session briefing for returning users.
        
        Requirements:
        - 13.1-13.8: Session briefing with project state
        
        Args:
            project: Existing project context
        
        Returns:
            Briefing message string
        """
        # TODO: Implement full session briefing in task 16.1
        # For now, generate a simple welcome back message
        
        days_elapsed = (datetime.now(timezone.utc) - project.last_accessed).days
        
        if days_elapsed == 0:
            time_phrase = "today"
        elif days_elapsed == 1:
            time_phrase = "yesterday"
        else:
            time_phrase = f"{days_elapsed} days ago"
        
        message = f"""# 📚 Welcome back to {project.name}!

Last session: {time_phrase}

**Project Stats**:
- Commits tracked: {project.total_commits}
- Commits explained: {project.explained_commits}
- Knowledge items: {project.knowledge_items_count}
- Readiness level: {project.readiness_level}/4

Ready to continue learning?"""
        
        return message
    
    @property
    def current_project(self) -> Optional[ProjectContext]:
        """Get current project context."""
        return self._current_project
    
    @property
    def is_initialized(self) -> bool:
        """Check if server is initialized."""
        return self._initialized
