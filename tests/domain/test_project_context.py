"""Unit tests for ProjectContext model.

Tests validation rules and serialization for the ProjectContext dataclass.

Requirements tested:
- 1.1: Project detection and context loading
- 1.6: Load existing project context
- 23.1: Enforce readiness_level between 1 and 4
- 23.2: Enforce explained_commits <= total_commits
"""

import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4
from src.learnloop.domain.project_context import ProjectContext, Technology


class TestTechnology:
    """Tests for Technology dataclass."""
    
    def test_create_technology_with_minimal_fields(self):
        """Test creating Technology with only required fields."""
        tech = Technology(name="Python")
        assert tech.name == "Python"
        assert tech.version is None
        assert tech.category is None
    
    def test_create_technology_with_all_fields(self):
        """Test creating Technology with all fields."""
        tech = Technology(name="Django", version="4.2.0", category="framework")
        assert tech.name == "Django"
        assert tech.version == "4.2.0"
        assert tech.category == "framework"
    
    def test_empty_name_raises_error(self):
        """Test that empty technology name raises ValueError."""
        with pytest.raises(ValueError, match="Technology name cannot be empty"):
            Technology(name="")
    
    def test_whitespace_only_name_raises_error(self):
        """Test that whitespace-only name raises ValueError."""
        with pytest.raises(ValueError, match="Technology name cannot be empty"):
            Technology(name="   ")


class TestProjectContextValidation:
    """Tests for ProjectContext validation rules."""
    
    @pytest.fixture
    def valid_repo_path(self, tmp_path):
        """Create a valid temporary directory path."""
        return tmp_path
    
    @pytest.fixture
    def valid_git_root(self, tmp_path):
        """Create a valid git root directory."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        return tmp_path
    
    def test_create_valid_project_context(self, valid_repo_path):
        """Test creating ProjectContext with valid data."""
        ctx = ProjectContext(
            id=uuid4(),
            name="Test Project",
            repo_path=valid_repo_path,
            readiness_level=2,
        )
        
        assert ctx.name == "Test Project"
        assert ctx.repo_path == valid_repo_path
        assert ctx.readiness_level == 2
        assert ctx.total_commits == 0
        assert ctx.explained_commits == 0
    
    def test_readiness_level_must_be_between_1_and_4(self, valid_repo_path):
        """Test that readiness_level is validated to be in range 1-4 (Requirement 23.1)."""
        # Valid levels
        for level in [1, 2, 3, 4]:
            ctx = ProjectContext(
                id=uuid4(),
                name="Test",
                repo_path=valid_repo_path,
                readiness_level=level,
            )
            assert ctx.readiness_level == level
        
        # Invalid levels
        for level in [0, 5, -1, 10]:
            with pytest.raises(ValueError, match="readiness_level must be between 1 and 4"):
                ProjectContext(
                    id=uuid4(),
                    name="Test",
                    repo_path=valid_repo_path,
                    readiness_level=level,
                )
    
    def test_readiness_level_must_be_integer(self, valid_repo_path):
        """Test that readiness_level must be an integer."""
        with pytest.raises(ValueError, match="readiness_level must be an integer"):
            ProjectContext(
                id=uuid4(),
                name="Test",
                repo_path=valid_repo_path,
                readiness_level=2.5,
            )
    
    def test_repo_path_must_be_absolute(self, tmp_path):
        """Test that repo_path must be absolute (Requirement 1.1)."""
        with pytest.raises(ValueError, match="repo_path must be absolute"):
            ProjectContext(
                id=uuid4(),
                name="Test",
                repo_path=Path("relative/path"),
            )
    
    def test_repo_path_must_exist(self, tmp_path):
        """Test that repo_path must exist (Requirement 1.1)."""
        non_existent = tmp_path / "does_not_exist"
        with pytest.raises(ValueError, match="repo_path must exist"):
            ProjectContext(
                id=uuid4(),
                name="Test",
                repo_path=non_existent,
            )
    
    def test_repo_path_must_be_directory(self, tmp_path):
        """Test that repo_path must be a directory."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("test")
        
        with pytest.raises(ValueError, match="repo_path must be a directory"):
            ProjectContext(
                id=uuid4(),
                name="Test",
                repo_path=file_path,
            )
    
    def test_repo_path_converts_string_to_path(self, valid_repo_path):
        """Test that repo_path string is converted to Path."""
        ctx = ProjectContext(
            id=uuid4(),
            name="Test",
            repo_path=str(valid_repo_path),
        )
        assert isinstance(ctx.repo_path, Path)
        assert ctx.repo_path == valid_repo_path
    
    def test_git_root_must_be_absolute_if_provided(self, valid_repo_path):
        """Test that git_root must be absolute when provided."""
        with pytest.raises(ValueError, match="git_root must be absolute"):
            ProjectContext(
                id=uuid4(),
                name="Test",
                repo_path=valid_repo_path,
                git_root=Path("relative/path"),
            )
    
    def test_last_accessed_cannot_be_future(self, valid_repo_path):
        """Test that last_accessed cannot be in the future."""
        future_time = datetime.now(timezone.utc) + timedelta(days=1)
        
        with pytest.raises(ValueError, match="last_accessed cannot be in the future"):
            ProjectContext(
                id=uuid4(),
                name="Test",
                repo_path=valid_repo_path,
                last_accessed=future_time,
            )
    
    def test_explained_commits_must_not_exceed_total_commits(self, valid_repo_path):
        """Test explained_commits <= total_commits constraint (Requirement 23.2)."""
        # Valid: explained <= total
        ctx = ProjectContext(
            id=uuid4(),
            name="Test",
            repo_path=valid_repo_path,
            total_commits=10,
            explained_commits=5,
        )
        assert ctx.explained_commits == 5
        assert ctx.total_commits == 10
        
        # Invalid: explained > total
        with pytest.raises(ValueError, match="explained_commits .* cannot exceed total_commits"):
            ProjectContext(
                id=uuid4(),
                name="Test",
                repo_path=valid_repo_path,
                total_commits=5,
                explained_commits=10,
            )
    
    def test_commits_must_be_non_negative(self, valid_repo_path):
        """Test that commit counts must be non-negative."""
        with pytest.raises(ValueError, match="total_commits must be non-negative"):
            ProjectContext(
                id=uuid4(),
                name="Test",
                repo_path=valid_repo_path,
                total_commits=-1,
            )
        
        with pytest.raises(ValueError, match="explained_commits must be non-negative"):
            ProjectContext(
                id=uuid4(),
                name="Test",
                repo_path=valid_repo_path,
                explained_commits=-1,
            )
    
    def test_knowledge_items_count_must_be_non_negative(self, valid_repo_path):
        """Test that knowledge_items_count must be non-negative."""
        with pytest.raises(ValueError, match="knowledge_items_count must be non-negative"):
            ProjectContext(
                id=uuid4(),
                name="Test",
                repo_path=valid_repo_path,
                knowledge_items_count=-1,
            )
    
    def test_project_name_cannot_be_empty(self, valid_repo_path):
        """Test that project name cannot be empty."""
        with pytest.raises(ValueError, match="Project name cannot be empty"):
            ProjectContext(
                id=uuid4(),
                name="",
                repo_path=valid_repo_path,
            )
    
    def test_project_name_cannot_be_whitespace(self, valid_repo_path):
        """Test that project name cannot be only whitespace."""
        with pytest.raises(ValueError, match="Project name cannot be empty"):
            ProjectContext(
                id=uuid4(),
                name="   ",
                repo_path=valid_repo_path,
            )


class TestProjectContextCreation:
    """Tests for ProjectContext creation methods."""
    
    def test_create_new_project_context(self, tmp_path):
        """Test creating a new project with create_new factory method."""
        ctx = ProjectContext.create_new(
            name="New Project",
            repo_path=tmp_path,
        )
        
        assert ctx.name == "New Project"
        assert ctx.repo_path == tmp_path
        assert ctx.is_new is True
        assert ctx.readiness_level == 1
        assert ctx.total_commits == 0
        assert ctx.explained_commits == 0
        assert ctx.knowledge_items_count == 0
        assert isinstance(ctx.id, UUID)
    
    def test_create_new_with_technologies(self, tmp_path):
        """Test creating new project with technologies."""
        techs = [
            Technology(name="Python", version="3.11", category="language"),
            Technology(name="pytest", version="7.4", category="tool"),
        ]
        
        ctx = ProjectContext.create_new(
            name="Test",
            repo_path=tmp_path,
            technologies=techs,
        )
        
        assert len(ctx.technologies) == 2
        assert ctx.technologies[0].name == "Python"
        assert ctx.technologies[1].name == "pytest"
    
    def test_create_new_with_git_root(self, tmp_path):
        """Test creating new project with git root."""
        git_root = tmp_path / "git"
        git_root.mkdir()
        
        ctx = ProjectContext.create_new(
            name="Test",
            repo_path=tmp_path,
            git_root=git_root,
        )
        
        assert ctx.git_root == git_root


class TestProjectContextSerialization:
    """Tests for ProjectContext serialization and deserialization."""
    
    def test_to_dict_with_minimal_data(self, tmp_path):
        """Test serializing ProjectContext with minimal data."""
        ctx = ProjectContext.create_new(
            name="Test",
            repo_path=tmp_path,
        )
        
        data = ctx.to_dict()
        
        assert data["name"] == "Test"
        assert data["repo_path"] == str(tmp_path)
        assert data["readiness_level"] == 1
        assert data["is_new"] is True
        assert data["total_commits"] == 0
        assert data["explained_commits"] == 0
        assert data["knowledge_items_count"] == 0
        assert data["technologies"] == []
        assert data["git_root"] is None
        assert "id" in data
        assert "last_accessed" in data
    
    def test_to_dict_with_full_data(self, tmp_path):
        """Test serializing ProjectContext with all fields."""
        git_root = tmp_path / "git"
        git_root.mkdir()
        
        techs = [Technology(name="Python", version="3.11")]
        
        ctx = ProjectContext(
            id=uuid4(),
            name="Full Test",
            repo_path=tmp_path,
            technologies=techs,
            readiness_level=3,
            is_new=False,
            git_root=git_root,
            total_commits=50,
            explained_commits=25,
            knowledge_items_count=10,
        )
        
        data = ctx.to_dict()
        
        assert data["name"] == "Full Test"
        assert data["readiness_level"] == 3
        assert data["is_new"] is False
        assert data["git_root"] == str(git_root)
        assert data["total_commits"] == 50
        assert data["explained_commits"] == 25
        assert data["knowledge_items_count"] == 10
        assert len(data["technologies"]) == 1
        assert data["technologies"][0]["name"] == "Python"
    
    def test_from_dict_with_minimal_data(self, tmp_path):
        """Test deserializing ProjectContext with minimal data."""
        project_id = str(uuid4())
        data = {
            "id": project_id,
            "name": "Test",
            "repo_path": str(tmp_path),
            "readiness_level": 1,
            "last_accessed": datetime.now(timezone.utc).isoformat(),
        }
        
        ctx = ProjectContext.from_dict(data)
        
        assert str(ctx.id) == project_id
        assert ctx.name == "Test"
        assert ctx.repo_path == tmp_path
        assert ctx.readiness_level == 1
        assert ctx.is_new is False
        assert ctx.total_commits == 0
        assert ctx.explained_commits == 0
    
    def test_from_dict_with_full_data(self, tmp_path):
        """Test deserializing ProjectContext with all fields."""
        git_root = tmp_path / "git"
        git_root.mkdir()
        
        project_id = str(uuid4())
        data = {
            "id": project_id,
            "name": "Full Test",
            "repo_path": str(tmp_path),
            "technologies": [
                {"name": "Python", "version": "3.11", "category": "language"},
                {"name": "Django", "version": "4.2", "category": "framework"},
            ],
            "readiness_level": 3,
            "is_new": True,
            "last_accessed": datetime.now(timezone.utc).isoformat(),
            "git_root": str(git_root),
            "total_commits": 100,
            "explained_commits": 50,
            "knowledge_items_count": 20,
        }
        
        ctx = ProjectContext.from_dict(data)
        
        assert str(ctx.id) == project_id
        assert ctx.name == "Full Test"
        assert ctx.readiness_level == 3
        assert ctx.is_new is True
        assert ctx.git_root == git_root
        assert ctx.total_commits == 100
        assert ctx.explained_commits == 50
        assert ctx.knowledge_items_count == 20
        assert len(ctx.technologies) == 2
        assert ctx.technologies[0].name == "Python"
        assert ctx.technologies[1].name == "Django"
    
    def test_serialization_round_trip(self, tmp_path):
        """Test that serialization and deserialization are inverse operations."""
        git_root = tmp_path / "git"
        git_root.mkdir()
        
        original = ProjectContext(
            id=uuid4(),
            name="Round Trip Test",
            repo_path=tmp_path,
            technologies=[Technology(name="Python", version="3.11")],
            readiness_level=2,
            is_new=True,
            git_root=git_root,
            total_commits=10,
            explained_commits=5,
            knowledge_items_count=3,
        )
        
        data = original.to_dict()
        restored = ProjectContext.from_dict(data)
        
        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.repo_path == original.repo_path
        assert restored.readiness_level == original.readiness_level
        assert restored.is_new == original.is_new
        assert restored.git_root == original.git_root
        assert restored.total_commits == original.total_commits
        assert restored.explained_commits == original.explained_commits
        assert restored.knowledge_items_count == original.knowledge_items_count
        assert len(restored.technologies) == len(original.technologies)


class TestProjectContextMethods:
    """Tests for ProjectContext instance methods."""
    
    def test_update_metrics_with_valid_values(self, tmp_path):
        """Test updating metrics with valid values."""
        ctx = ProjectContext.create_new(name="Test", repo_path=tmp_path)
        
        ctx.update_metrics(
            total_commits=20,
            explained_commits=10,
            knowledge_items_count=5,
        )
        
        assert ctx.total_commits == 20
        assert ctx.explained_commits == 10
        assert ctx.knowledge_items_count == 5
    
    def test_update_metrics_partial_update(self, tmp_path):
        """Test updating only some metrics."""
        ctx = ProjectContext.create_new(name="Test", repo_path=tmp_path)
        ctx.update_metrics(total_commits=10)
        
        ctx.update_metrics(explained_commits=5)
        
        assert ctx.total_commits == 10
        assert ctx.explained_commits == 5
    
    def test_update_metrics_validates_constraint(self, tmp_path):
        """Test that update_metrics enforces explained <= total constraint (Requirement 23.2)."""
        ctx = ProjectContext.create_new(name="Test", repo_path=tmp_path)
        ctx.update_metrics(total_commits=10)
        
        with pytest.raises(ValueError, match="explained_commits .* cannot exceed total_commits"):
            ctx.update_metrics(explained_commits=15)
        
        # Verify original values unchanged after failed update
        assert ctx.total_commits == 10
        assert ctx.explained_commits == 0
    
    def test_update_metrics_validates_non_negative(self, tmp_path):
        """Test that update_metrics enforces non-negative values."""
        ctx = ProjectContext.create_new(name="Test", repo_path=tmp_path)
        
        with pytest.raises(ValueError, match="total_commits must be non-negative"):
            ctx.update_metrics(total_commits=-1)
        
        with pytest.raises(ValueError, match="explained_commits must be non-negative"):
            ctx.update_metrics(explained_commits=-1)
        
        with pytest.raises(ValueError, match="knowledge_items_count must be non-negative"):
            ctx.update_metrics(knowledge_items_count=-1)
    
    def test_update_metrics_rollback_on_error(self, tmp_path):
        """Test that failed update_metrics doesn't change state."""
        ctx = ProjectContext.create_new(name="Test", repo_path=tmp_path)
        ctx.update_metrics(total_commits=10, explained_commits=5)
        
        # Try to set explained > total (should fail)
        try:
            ctx.update_metrics(total_commits=3)
        except ValueError:
            pass
        
        # Verify state unchanged
        assert ctx.total_commits == 10
        assert ctx.explained_commits == 5
    
    def test_update_readiness_level_with_valid_value(self, tmp_path):
        """Test updating readiness level with valid value (Requirement 23.1)."""
        ctx = ProjectContext.create_new(name="Test", repo_path=tmp_path)
        
        for level in [1, 2, 3, 4]:
            ctx.update_readiness_level(level)
            assert ctx.readiness_level == level
    
    def test_update_readiness_level_with_invalid_value(self, tmp_path):
        """Test updating readiness level with invalid value."""
        ctx = ProjectContext.create_new(name="Test", repo_path=tmp_path)
        
        with pytest.raises(ValueError, match="readiness_level must be between 1 and 4"):
            ctx.update_readiness_level(0)
        
        with pytest.raises(ValueError, match="readiness_level must be between 1 and 4"):
            ctx.update_readiness_level(5)
        
        # Original value unchanged
        assert ctx.readiness_level == 1
    
    def test_update_readiness_level_must_be_integer(self, tmp_path):
        """Test that readiness level must be integer."""
        ctx = ProjectContext.create_new(name="Test", repo_path=tmp_path)
        
        with pytest.raises(ValueError, match="readiness_level must be an integer"):
            ctx.update_readiness_level(2.5)
    
    def test_mark_accessed_updates_timestamp(self, tmp_path):
        """Test mark_accessed updates last_accessed timestamp."""
        ctx = ProjectContext.create_new(name="Test", repo_path=tmp_path)
        original_time = ctx.last_accessed
        
        # Wait a small amount to ensure time difference
        import time
        time.sleep(0.01)
        
        ctx.mark_accessed()
        
        assert ctx.last_accessed > original_time
