"""Integration tests for MCP server end-to-end workflows.

Tests the complete initialization workflow from workspace detection through
project bootstrap and message generation.
"""

import tempfile
from pathlib import Path

import pytest

from learnloop.mcp.config import MCPServerConfig
from learnloop.mcp.server import LearnLoopMCPServer
from learnloop.persistence.async_db import AsyncDatabase


@pytest.mark.asyncio
class TestMCPServerIntegration:
    """Integration tests for complete MCP server workflows."""
    
    async def test_complete_new_project_workflow(self):
        """Test complete initialization workflow for a new project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup
            workspace = Path(tmpdir) / "my-new-project"
            workspace.mkdir()
            
            # Create sample project files
            (workspace / "requirements.txt").write_text("requests==2.28.0\nflask==2.3.0\n")
            (workspace / "README.md").write_text("# My Project\n")
            
            # Create git repository
            git_dir = workspace / ".git"
            git_dir.mkdir()
            
            # Initialize database
            db_path = Path(tmpdir) / "test.db"
            db = AsyncDatabase(db_path)
            await db.initialize()
            
            # Initialize server
            config = MCPServerConfig.default()
            server = LearnLoopMCPServer(config, db)
            
            # Execute initialization
            result = await server.initialize(workspace)
            
            # Verify result structure
            assert result["success"] is True
            assert result["is_new"] is True
            assert result["message_type"] == "welcome"
            assert result["project_name"] == "my-new-project"
            assert result["readiness_level"] == 1
            
            # Verify message content
            message = result["message"]
            assert "Welcome to LearnLoop" in message
            assert "my-new-project" in message
            assert "requests" in message or "flask" in message  # Detected tech
            
            # Verify .learn/ directory structure created
            learn_dir = workspace / ".learn"
            assert learn_dir.exists()
            assert (learn_dir / "queue").exists()
            assert (learn_dir / ".gitignore").exists()
            assert (learn_dir / "concepts.md").exists()
            
            # Verify gitignore content
            gitignore_content = (learn_dir / ".gitignore").read_text()
            assert "queue/" in gitignore_content
            
            # Verify concepts.md content
            concepts_content = (learn_dir / "concepts.md").read_text()
            assert "Learning Concepts" in concepts_content
            
            # Verify project in database
            project = await db.get_project_by_path(workspace)
            assert project is not None
            assert project.name == "my-new-project"
            assert project.repo_path == workspace
            assert project.readiness_level == 1
            assert len(project.technologies) >= 2  # requests and flask
            
            # Verify technologies stored
            tech_names = [t.name for t in project.technologies]
            assert "requests" in tech_names
            assert "flask" in tech_names
    
    async def test_returning_user_workflow(self):
        """Test workflow for a user returning to an existing project."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup
            workspace = Path(tmpdir) / "existing-project"
            workspace.mkdir()
            
            db_path = Path(tmpdir) / "test.db"
            db = AsyncDatabase(db_path)
            await db.initialize()
            
            # First initialization (new project)
            config = MCPServerConfig.default()
            server1 = LearnLoopMCPServer(config, db)
            result1 = await server1.initialize(workspace)
            
            assert result1["is_new"] is True
            assert result1["message_type"] == "welcome"
            
            project_id = result1["project_id"]
            
            # Simulate some activity
            await db.update_project_metrics(
                project_id,
                total_commits=15,
                explained_commits=8,
                knowledge_items_count=5
            )
            
            # Second initialization (returning user)
            server2 = LearnLoopMCPServer(config, db)
            result2 = await server2.initialize(workspace)
            
            # Verify returning user experience
            assert result2["success"] is True
            assert result2["is_new"] is False
            assert result2["message_type"] == "briefing"
            assert result2["project_id"] == project_id
            
            # Verify briefing message
            message = result2["message"]
            assert "Welcome back" in message
            assert "existing-project" in message
            assert "15" in message  # total commits
            assert "8" in message   # explained commits
            assert "5" in message   # knowledge items
    
    async def test_multiple_projects_isolation(self):
        """Test that multiple projects are properly isolated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup two projects
            project1_path = Path(tmpdir) / "project-one"
            project2_path = Path(tmpdir) / "project-two"
            project1_path.mkdir()
            project2_path.mkdir()
            
            db_path = Path(tmpdir) / "test.db"
            db = AsyncDatabase(db_path)
            await db.initialize()
            
            config = MCPServerConfig.default()
            
            # Initialize first project
            server1 = LearnLoopMCPServer(config, db)
            result1 = await server1.initialize(project1_path)
            
            assert result1["project_name"] == "project-one"
            project1_id = result1["project_id"]
            
            # Initialize second project
            server2 = LearnLoopMCPServer(config, db)
            result2 = await server2.initialize(project2_path)
            
            assert result2["project_name"] == "project-two"
            project2_id = result2["project_id"]
            
            # Verify projects are different
            assert project1_id != project2_id
            
            # Verify both projects exist in database
            proj1 = await db.get_project_by_path(project1_path)
            proj2 = await db.get_project_by_path(project2_path)
            
            assert proj1.name == "project-one"
            assert proj2.name == "project-two"
            assert proj1.id != proj2.id
    
    async def test_performance_requirement(self):
        """Test that initialization completes within 500ms."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir) / "perf-test"
            workspace.mkdir()
            
            # Add multiple dependency files to stress test
            (workspace / "requirements.txt").write_text("\n".join([
                f"package{i}==1.0.0" for i in range(50)
            ]))
            (workspace / "package.json").write_text("""{
  "dependencies": {
    "pkg1": "1.0.0",
    "pkg2": "2.0.0"
  }
}""")
            
            db_path = Path(tmpdir) / "test.db"
            db = AsyncDatabase(db_path)
            await db.initialize()
            
            config = MCPServerConfig.default()
            server = LearnLoopMCPServer(config, db)
            
            # Execute and measure
            result = await server.initialize(workspace)
            
            # Verify performance requirement (Requirement 25.1)
            assert result["initialization_time_ms"] < 500, \
                f"Initialization took {result['initialization_time_ms']}ms, expected < 500ms"
    
    async def test_git_root_detection_with_nested_workspace(self):
        """Test git root detection when workspace is nested in git repo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create git repo at root
            repo_root = Path(tmpdir) / "my-repo"
            repo_root.mkdir()
            (repo_root / ".git").mkdir()
            
            # Create nested workspace
            workspace = repo_root / "subdir" / "workspace"
            workspace.mkdir(parents=True)
            
            db_path = Path(tmpdir) / "test.db"
            db = AsyncDatabase(db_path)
            await db.initialize()
            
            config = MCPServerConfig.default()
            server = LearnLoopMCPServer(config, db)
            
            # Initialize
            result = await server.initialize(workspace)
            
            # Should use git repo name, not nested workspace name
            assert result["project_name"] == "my-repo"
            
            # Verify project context has correct git_root
            project = server.current_project
            assert project.git_root.resolve() == repo_root.resolve()
            assert project.repo_path.resolve() == workspace.resolve()
