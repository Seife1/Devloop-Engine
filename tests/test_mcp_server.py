"""Unit tests for LearnLoop MCP server initialization and context detection.

Tests cover:
- Project detection and auto-bootstrap
- Technology detection
- Welcome message generation
- Git root detection
- .learn/ directory initialization
"""

import asyncio
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import pytest

from learnloop.domain.project_context import ProjectContext, Technology
from learnloop.mcp.config import MCPServerConfig
from learnloop.mcp.server import LearnLoopMCPServer
from learnloop.persistence.async_db import AsyncDatabase


@pytest.fixture
async def temp_workspace():
    """Create temporary workspace directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir) / "test_project"
        workspace.mkdir()
        yield workspace


@pytest.fixture
async def temp_db():
    """Create temporary database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = AsyncDatabase(db_path)
        await db.initialize()
        yield db


@pytest.fixture
def config():
    """Create test configuration."""
    return MCPServerConfig.default()


@pytest.fixture
async def server(config, temp_db):
    """Create MCP server instance."""
    return LearnLoopMCPServer(config, temp_db)


@pytest.mark.asyncio
class TestServerInitialization:
    """Test server initialization and context detection."""
    
    async def test_initialize_new_project(self, server, temp_workspace):
        """Test initialization of a new project."""
        result = await server.initialize(temp_workspace)
        
        assert result["success"] is True
        assert result["is_new"] is True
        assert result["message_type"] == "welcome"
        assert result["readiness_level"] == 1
        assert UUID(result["project_id"])  # Valid UUID
        assert result["initialization_time_ms"] < 500  # Performance requirement
        
        # Verify project is stored
        assert server.current_project is not None
        assert server.current_project.name == temp_workspace.name
        assert server.is_initialized
    
    async def test_initialize_existing_project(self, server, temp_workspace, temp_db):
        """Test initialization loads existing project."""
        # Create project first
        await server.initialize(temp_workspace)
        first_project_id = server.current_project.id
        
        # Create new server instance
        server2 = LearnLoopMCPServer(server.config, temp_db)
        
        # Initialize again - should load existing
        result = await server2.initialize(temp_workspace)
        
        assert result["success"] is True
        assert result["is_new"] is False
        assert result["message_type"] == "briefing"
        assert UUID(result["project_id"]) == first_project_id
    
    async def test_initialize_invalid_workspace(self, server):
        """Test initialization with invalid workspace path."""
        with pytest.raises(ValueError, match="does not exist"):
            await server.initialize(Path("/nonexistent/path"))
    
    async def test_initialize_file_not_directory(self, server):
        """Test initialization with file path instead of directory."""
        with tempfile.NamedTemporaryFile() as tmpfile:
            with pytest.raises(ValueError, match="not a directory"):
                await server.initialize(Path(tmpfile.name))


@pytest.mark.asyncio
class TestContextDetection:
    """Test project context detection algorithm."""
    
    async def test_detect_context_creates_new_project(self, server, temp_workspace):
        """Test context detection creates new project when none exists."""
        project = await server.detect_context(temp_workspace)
        
        assert isinstance(project, ProjectContext)
        assert project.name == temp_workspace.name
        assert project.repo_path == temp_workspace
        assert project.readiness_level == 1
        assert project.is_new is True
        assert project.total_commits == 0
        assert project.explained_commits == 0
    
    async def test_detect_context_loads_existing(self, server, temp_workspace):
        """Test context detection loads existing project."""
        # Create project first
        project1 = await server.detect_context(temp_workspace)
        
        # Detect again - should load same project
        project2 = await server.detect_context(temp_workspace)
        
        assert project2.id == project1.id
        assert project2.is_new is False
    
    async def test_detect_context_updates_last_accessed(self, server, temp_workspace, temp_db):
        """Test context detection updates last accessed timestamp."""
        # Create project
        await server.detect_context(temp_workspace)
        
        # Wait a moment
        await asyncio.sleep(0.1)
        
        # Load project again
        project = await temp_db.get_project_by_path(temp_workspace)
        original_accessed = project.last_accessed
        
        # Detect context again
        await server.detect_context(temp_workspace)
        
        # Check timestamp updated
        updated_project = await temp_db.get_project_by_path(temp_workspace)
        assert updated_project.last_accessed > original_accessed


@pytest.mark.asyncio
class TestGitDetection:
    """Test git repository detection."""
    
    async def test_detect_git_root_finds_repo(self, server, temp_workspace):
        """Test detection of git repository root."""
        # Create .git directory
        git_dir = temp_workspace / ".git"
        git_dir.mkdir()
        
        git_root = server._detect_git_root(temp_workspace)
        
        # Use resolve() to handle Windows path normalization
        assert git_root.resolve() == temp_workspace.resolve()
    
    async def test_detect_git_root_walks_up_tree(self, server, temp_workspace):
        """Test git detection walks up directory tree."""
        # Create .git at parent level
        git_dir = temp_workspace.parent / ".git"
        git_dir.mkdir(exist_ok=True)
        
        try:
            git_root = server._detect_git_root(temp_workspace)
            # Use resolve() to handle Windows path normalization
            assert git_root.resolve() == temp_workspace.parent.resolve()
        finally:
            # Clean up
            git_dir.rmdir()
    
    async def test_detect_git_root_none_when_not_found(self, server, temp_workspace):
        """Test git detection returns None when no repo found."""
        git_root = server._detect_git_root(temp_workspace)
        assert git_root is None


@pytest.mark.asyncio
class TestTechnologyDetection:
    """Test technology detection from configuration files."""
    
    async def test_detect_technologies_python(self, server, temp_workspace):
        """Test detection of Python dependencies."""
        # Create requirements.txt
        req_file = temp_workspace / "requirements.txt"
        req_file.write_text("requests==2.28.0\nflask>=2.0.0\n")
        
        technologies = await server._detect_technologies(temp_workspace)
        
        tech_names = [t.name for t in technologies]
        assert "requests" in tech_names
        assert "flask" in tech_names
        
        # Check categories
        for tech in technologies:
            assert tech.category == "python"
    
    async def test_detect_technologies_nodejs(self, server, temp_workspace):
        """Test detection of Node.js dependencies."""
        # Create package.json
        package_json = temp_workspace / "package.json"
        package_json.write_text("""{
  "dependencies": {
    "express": "^4.18.0",
    "react": "^18.0.0"
  }
}""")
        
        technologies = await server._detect_technologies(temp_workspace)
        
        tech_names = [t.name for t in technologies]
        assert "express" in tech_names
        assert "react" in tech_names
        
        # Check categories
        for tech in technologies:
            assert tech.category == "npm"
    
    async def test_detect_technologies_empty_project(self, server, temp_workspace):
        """Test technology detection on empty project."""
        technologies = await server._detect_technologies(temp_workspace)
        
        assert technologies == []


@pytest.mark.asyncio
class TestLearnDirectoryBootstrap:
    """Test .learn/ directory structure initialization."""
    
    async def test_bootstrap_creates_directories(self, server, temp_workspace):
        """Test bootstrap creates .learn/ and queue/ directories."""
        await server._bootstrap_learn_directory(temp_workspace)
        
        learn_dir = temp_workspace / ".learn"
        assert learn_dir.exists()
        assert learn_dir.is_dir()
        
        queue_dir = learn_dir / "queue"
        assert queue_dir.exists()
        assert queue_dir.is_dir()
    
    async def test_bootstrap_creates_gitignore(self, server, temp_workspace):
        """Test bootstrap creates .gitignore file."""
        await server._bootstrap_learn_directory(temp_workspace)
        
        gitignore = temp_workspace / ".learn" / ".gitignore"
        assert gitignore.exists()
        
        content = gitignore.read_text()
        assert "queue/" in content
    
    async def test_bootstrap_creates_concepts_file(self, server, temp_workspace):
        """Test bootstrap creates concepts.md file."""
        await server._bootstrap_learn_directory(temp_workspace)
        
        concepts = temp_workspace / ".learn" / "concepts.md"
        assert concepts.exists()
        
        content = concepts.read_text()
        assert "Learning Concepts" in content
        assert "start_skill_session" in content
    
    async def test_bootstrap_preserves_existing_concepts(self, server, temp_workspace):
        """Test bootstrap doesn't overwrite existing concepts.md."""
        learn_dir = temp_workspace / ".learn"
        learn_dir.mkdir()
        
        concepts = learn_dir / "concepts.md"
        original_content = "# My Custom Content\n\nDon't overwrite me!"
        concepts.write_text(original_content)
        
        await server._bootstrap_learn_directory(temp_workspace)
        
        # Should preserve original content
        assert concepts.read_text() == original_content
    
    async def test_bootstrap_idempotent(self, server, temp_workspace):
        """Test bootstrap can be called multiple times safely."""
        await server._bootstrap_learn_directory(temp_workspace)
        await server._bootstrap_learn_directory(temp_workspace)
        
        # Should still work without errors
        assert (temp_workspace / ".learn").exists()
        assert (temp_workspace / ".learn" / "queue").exists()


@pytest.mark.asyncio
class TestWelcomeMessages:
    """Test welcome and briefing message generation."""
    
    async def test_welcome_message_for_new_project(self, server, temp_workspace):
        """Test welcome message generation for new users."""
        project = ProjectContext.create_new(
            name="test-project",
            repo_path=temp_workspace,
            technologies=[Technology(name="python", category="language")]
        )
        
        message = server._generate_welcome_message(project)
        
        assert "Welcome to LearnLoop" in message
        assert "test-project" in message
        assert "python" in message
        assert len(message.split()) < 120  # Roughly 100 words requirement
        assert "exposure" in message.lower() or "explain" in message.lower()
    
    async def test_briefing_message_for_existing_project(self, server, temp_workspace, temp_db):
        """Test briefing message for returning users."""
        # Create project with some history
        project = await temp_db.create_project(
            name="test-project",
            repo_path=temp_workspace,
        )
        
        # Update metrics
        await temp_db.update_project_metrics(
            project.id,
            total_commits=10,
            explained_commits=5,
            knowledge_items_count=3
        )
        
        # Reload project
        project = await temp_db.get_project_by_id(project.id)
        
        message = server._generate_briefing_message(project)
        
        assert "Welcome back" in message
        assert "test-project" in message
        assert "10" in message  # total commits
        assert "5" in message   # explained commits
        assert "3" in message   # knowledge items
    
    async def test_briefing_shows_time_elapsed(self, server, temp_workspace):
        """Test briefing message shows time since last session."""
        # Create project with old last_accessed
        from datetime import timedelta
        
        old_time = datetime.now(timezone.utc) - timedelta(days=3)
        
        project = ProjectContext(
            id=UUID("12345678-1234-1234-1234-123456789abc"),
            name="test-project",
            repo_path=temp_workspace,
            last_accessed=old_time,
        )
        
        message = server._generate_briefing_message(project)
        
        assert "3 days ago" in message


@pytest.mark.asyncio
class TestProjectNaming:
    """Test project name extraction logic."""
    
    async def test_extract_name_from_workspace(self, server, temp_workspace):
        """Test name extraction from workspace directory."""
        name = server._extract_project_name(temp_workspace, None)
        assert name == temp_workspace.name
    
    async def test_extract_name_prefers_git_root(self, server, temp_workspace):
        """Test name extraction prefers git root over workspace."""
        git_root = temp_workspace.parent / "my-git-repo"
        
        name = server._extract_project_name(temp_workspace, git_root)
        assert name == "my-git-repo"
