"""Unit tests for async database operations.

Tests CRUD operations for all models with transaction support and error handling.

Requirements:
- 1.6: Load existing project context
- 27.2: Efficient database operations
- 24.1-24.3: Error handling with retry logic
"""

import asyncio
import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from learnloop.domain.errors import ValidationError
from learnloop.domain.models import DepthBand, IntentStatus
from learnloop.domain.project_context import Technology
from learnloop.persistence.async_db import AsyncDatabase


@pytest.fixture
async def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = AsyncDatabase(db_path, pool_size=3)
        await db.initialize()
        yield db


@pytest.fixture
def sample_project_data():
    """Sample project data for testing."""
    return {
        "name": "Test Project",
        "repo_path": Path.cwd(),  # Use current directory as test path
        "git_root": None,
        "technologies": [
            Technology(name="Python", version="3.11", category="language"),
            Technology(name="pytest", version="7.4", category="tool"),
        ],
    }


async def create_commit_record(temp_db, project_id: str, commit_sha: str):
    """Helper to create a commit record for testing."""
    async with temp_db._get_connection() as conn:
        await conn.execute(
            """
            INSERT INTO commits (sha, project_id, message, files, committed_at, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (commit_sha, project_id, "Test commit", json.dumps(["file.py"]), datetime.now(timezone.utc).isoformat(), "new")
        )
        await conn.commit()


# ============================================================================
# ProjectContext Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_project(temp_db, sample_project_data):
    """Test creating a new project."""
    project = await temp_db.create_project(**sample_project_data)
    
    assert project.name == sample_project_data["name"]
    assert project.repo_path == sample_project_data["repo_path"]
    assert project.readiness_level == 1
    assert project.total_commits == 0
    assert project.explained_commits == 0
    assert len(project.technologies) == 2


@pytest.mark.asyncio
async def test_get_project_by_path(temp_db, sample_project_data):
    """Test retrieving project by repository path."""
    # Create project
    created = await temp_db.create_project(**sample_project_data)
    
    # Retrieve by path
    retrieved = await temp_db.get_project_by_path(sample_project_data["repo_path"])
    
    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.name == created.name
    assert len(retrieved.technologies) == 2


@pytest.mark.asyncio
async def test_get_project_by_path_not_found(temp_db):
    """Test retrieving non-existent project returns None."""
    result = await temp_db.get_project_by_path(Path("/nonexistent/path"))
    assert result is None


@pytest.mark.asyncio
async def test_get_project_by_id(temp_db, sample_project_data):
    """Test retrieving project by ID."""
    created = await temp_db.create_project(**sample_project_data)
    
    retrieved = await temp_db.get_project_by_id(created.id)
    
    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.name == created.name


@pytest.mark.asyncio
async def test_update_project_metrics(temp_db, sample_project_data):
    """Test updating project metrics."""
    project = await temp_db.create_project(**sample_project_data)
    
    # Update metrics
    await temp_db.update_project_metrics(
        project.id,
        total_commits=10,
        explained_commits=5,
        knowledge_items_count=3,
    )
    
    # Verify update
    updated = await temp_db.get_project_by_id(project.id)
    assert updated.total_commits == 10
    assert updated.explained_commits == 5
    assert updated.knowledge_items_count == 3


@pytest.mark.asyncio
async def test_update_project_readiness_level(temp_db, sample_project_data):
    """Test updating project readiness level."""
    project = await temp_db.create_project(**sample_project_data)
    
    # Update level
    await temp_db.update_project_readiness_level(project.id, 3)
    
    # Verify update
    updated = await temp_db.get_project_by_id(project.id)
    assert updated.readiness_level == 3


@pytest.mark.asyncio
async def test_update_project_readiness_level_invalid(temp_db, sample_project_data):
    """Test updating with invalid readiness level raises error."""
    project = await temp_db.create_project(**sample_project_data)
    
    with pytest.raises(ValueError, match="must be between 1 and 4"):
        await temp_db.update_project_readiness_level(project.id, 5)


@pytest.mark.asyncio
async def test_update_project_last_accessed(temp_db, sample_project_data):
    """Test updating last accessed timestamp."""
    project = await temp_db.create_project(**sample_project_data)
    original_time = project.last_accessed
    
    # Wait a bit
    await asyncio.sleep(0.1)
    
    # Update timestamp
    await temp_db.update_project_last_accessed(project.id)
    
    # Verify update
    updated = await temp_db.get_project_by_id(project.id)
    assert updated.last_accessed > original_time


# ============================================================================
# IntentRecord Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_intent(temp_db, sample_project_data):
    """Test creating an intent record."""
    project = await temp_db.create_project(**sample_project_data)
    
    intent = await temp_db.create_intent(
        session_id="session-123",
        project_id=project.id,
        intent_description="Learn async/await patterns",
        files=["src/async_example.py"],
        skills=["python.async", "concurrency"],
    )
    
    assert intent.session_id == "session-123"
    assert intent.project_id == str(project.id)
    assert intent.status == IntentStatus.OPEN
    assert len(intent.files) == 1
    assert len(intent.skills) == 2


@pytest.mark.asyncio
async def test_get_open_intents(temp_db, sample_project_data):
    """Test retrieving open intents for a project (Requirement 7.2).
    
    Requirements validated:
    - 7.2: Load all open Intent_Records for the project
    - Filter by project_id
    - Return intents ordered by created_at
    """
    project = await temp_db.create_project(**sample_project_data)
    
    # Create multiple intents with small delays to ensure different timestamps
    intent1 = await temp_db.create_intent(
        session_id="session-1",
        project_id=project.id,
        intent_description="Intent 1",
        files=["file1.py"],
        skills=["skill1"],
    )
    
    await asyncio.sleep(0.01)  # Ensure different timestamps
    
    intent2 = await temp_db.create_intent(
        session_id="session-2",
        project_id=project.id,
        intent_description="Intent 2",
        files=["file2.py"],
        skills=["skill2"],
    )
    
    await asyncio.sleep(0.01)
    
    intent3 = await temp_db.create_intent(
        session_id="session-3",
        project_id=project.id,
        intent_description="Intent 3",
        files=["file3.py"],
        skills=["skill3"],
    )
    
    # Retrieve open intents
    open_intents = await temp_db.get_open_intents(project.id)
    
    # Verify all intents are returned
    assert len(open_intents) == 3
    
    # Verify all are OPEN status
    assert all(i.status == IntentStatus.OPEN for i in open_intents)
    
    # Verify filtering by project_id - all should belong to this project
    assert all(i.project_id == str(project.id) for i in open_intents)
    
    # Verify ordering by created_at DESC (most recent first)
    # Intent 3 should be first, then intent2, then intent1
    assert open_intents[0].id == intent3.id
    assert open_intents[1].id == intent2.id
    assert open_intents[2].id == intent1.id
    
    # Verify timestamps are in descending order
    for i in range(len(open_intents) - 1):
        assert open_intents[i].created_at >= open_intents[i + 1].created_at


@pytest.mark.asyncio
async def test_get_open_intents_excludes_closed(temp_db, sample_project_data):
    """Test that closed intents are not returned in open intents query."""
    project = await temp_db.create_project(**sample_project_data)
    
    # Create open intent
    open_intent = await temp_db.create_intent(
        session_id="session-1",
        project_id=project.id,
        intent_description="Open Intent",
        files=["file1.py"],
        skills=["skill1"],
    )
    
    # Create intent that will be closed
    closed_intent = await temp_db.create_intent(
        session_id="session-2",
        project_id=project.id,
        intent_description="To be closed",
        files=["file2.py"],
        skills=["skill2"],
    )
    
    # Close the second intent
    await temp_db.close_intent(closed_intent.id, IntentStatus.ABANDONED)
    
    # Retrieve open intents - should only get the open one
    open_intents = await temp_db.get_open_intents(project.id)
    
    assert len(open_intents) == 1
    assert open_intents[0].id == open_intent.id
    assert open_intents[0].status == IntentStatus.OPEN


@pytest.mark.asyncio
async def test_get_open_intents_filters_by_project(temp_db, sample_project_data):
    """Test that open intents are filtered by project_id."""
    import tempfile
    
    # Create two projects
    project1 = await temp_db.create_project(**sample_project_data)
    
    # Create second project with different path
    with tempfile.TemporaryDirectory() as tmpdir:
        project2_data = {
            "name": "Another Project",
            "repo_path": Path(tmpdir),
            "git_root": None,
            "technologies": sample_project_data["technologies"],
        }
        project2 = await temp_db.create_project(**project2_data)
        
        # Create intents in different projects
        intent1 = await temp_db.create_intent(
            session_id="session-1",
            project_id=project1.id,
            intent_description="Project 1 Intent",
            files=["file1.py"],
            skills=["skill1"],
        )
        
        intent2 = await temp_db.create_intent(
            session_id="session-2",
            project_id=project2.id,
            intent_description="Project 2 Intent",
            files=["file2.py"],
            skills=["skill2"],
        )
        
        # Get intents for project 1 - should only return intent1
        project1_intents = await temp_db.get_open_intents(project1.id)
        assert len(project1_intents) == 1
        assert project1_intents[0].id == intent1.id
        assert project1_intents[0].project_id == str(project1.id)
        
        # Get intents for project 2 - should only return intent2
        project2_intents = await temp_db.get_open_intents(project2.id)
        assert len(project2_intents) == 1
        assert project2_intents[0].id == intent2.id
        assert project2_intents[0].project_id == str(project2.id)


@pytest.mark.asyncio
async def test_close_intent_matched(temp_db, sample_project_data):
    """Test closing an intent with MATCHED status."""
    project = await temp_db.create_project(**sample_project_data)
    
    intent = await temp_db.create_intent(
        session_id="session-1",
        project_id=project.id,
        intent_description="Test intent",
        files=["file.py"],
        skills=["skill"],
    )
    
    # Create a commit record first (required by foreign key)
    commit_sha = "a" * 40
    async with temp_db._get_connection() as conn:
        await conn.execute(
            """
            INSERT INTO commits (sha, project_id, message, files, committed_at, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (commit_sha, str(project.id), "Test commit", json.dumps(["file.py"]), datetime.now(timezone.utc).isoformat(), "new")
        )
        await conn.commit()
    
    # Close as matched
    await temp_db.close_intent(intent.id, IntentStatus.MATCHED, commit_sha)
    
    # Verify it's no longer in open intents
    open_intents = await temp_db.get_open_intents(project.id)
    assert len(open_intents) == 0


@pytest.mark.asyncio
async def test_close_intent_matched_requires_commit_sha(temp_db, sample_project_data):
    """Test closing with MATCHED status requires commit SHA."""
    project = await temp_db.create_project(**sample_project_data)
    
    intent = await temp_db.create_intent(
        session_id="session-1",
        project_id=project.id,
        intent_description="Test intent",
        files=["file.py"],
        skills=["skill"],
    )
    
    with pytest.raises(ValidationError, match="matched_commit_sha required"):
        await temp_db.close_intent(intent.id, IntentStatus.MATCHED, None)


@pytest.mark.asyncio
async def test_close_intent_abandoned(temp_db, sample_project_data):
    """Test closing an intent with ABANDONED status."""
    project = await temp_db.create_project(**sample_project_data)
    
    intent = await temp_db.create_intent(
        session_id="session-1",
        project_id=project.id,
        intent_description="Test intent",
        files=["file.py"],
        skills=["skill"],
    )
    
    # Close as abandoned
    await temp_db.close_intent(intent.id, IntentStatus.ABANDONED)
    
    # Verify it's no longer in open intents
    open_intents = await temp_db.get_open_intents(project.id)
    assert len(open_intents) == 0


# ============================================================================
# ExposureRecord Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_exposure(temp_db, sample_project_data):
    """Test creating an exposure record."""
    project = await temp_db.create_project(**sample_project_data)
    
    intent = await temp_db.create_intent(
        session_id="session-1",
        project_id=project.id,
        intent_description="Test intent",
        files=["file.py"],
        skills=["skill1"],
    )
    
    # Create a commit record first (required by foreign key)
    commit_sha = "a" * 40
    async with temp_db._get_connection() as conn:
        await conn.execute(
            """
            INSERT INTO commits (sha, project_id, message, files, committed_at, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (commit_sha, str(project.id), "Test commit", json.dumps(["file.py"]), datetime.now(timezone.utc).isoformat(), "new")
        )
        await conn.commit()
    
    exposure = await temp_db.create_exposure(
        project_id=project.id,
        intent_id=intent.id,
        commit_sha=commit_sha,
        skills=["skill1"],
        files=["file.py"],
    )
    
    assert exposure.project_id == str(project.id)
    assert exposure.intent_id == intent.id
    assert exposure.commit_sha == commit_sha
    assert not exposure.explanation_recorded


@pytest.mark.asyncio
async def test_create_exposure_invalid_commit_sha(temp_db, sample_project_data):
    """Test creating exposure with invalid commit SHA raises error."""
    project = await temp_db.create_project(**sample_project_data)
    
    intent = await temp_db.create_intent(
        session_id="session-1",
        project_id=project.id,
        intent_description="Test intent",
        files=["file.py"],
        skills=["skill1"],
    )
    
    with pytest.raises(ValidationError, match="must be 40 hex characters"):
        await temp_db.create_exposure(
            project_id=project.id,
            intent_id=intent.id,
            commit_sha="invalid",  # Not 40 hex chars
            skills=["skill1"],
            files=["file.py"],
        )


@pytest.mark.asyncio
async def test_update_exposure_explanation(temp_db, sample_project_data):
    """Test updating exposure with explanation data."""
    project = await temp_db.create_project(**sample_project_data)
    
    intent = await temp_db.create_intent(
        session_id="session-1",
        project_id=project.id,
        intent_description="Test intent",
        files=["file.py"],
        skills=["skill1"],
    )
    
    commit_sha = "a" * 40
    async with temp_db._get_connection() as conn:
        await conn.execute(
            """
            INSERT INTO commits (sha, project_id, message, files, committed_at, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (commit_sha, str(project.id), "Test commit", json.dumps(["file.py"]), datetime.now(timezone.utc).isoformat(), "new")
        )
        await conn.commit()
    
    exposure = await temp_db.create_exposure(
        project_id=project.id,
        intent_id=intent.id,
        commit_sha=commit_sha,
        skills=["skill1"],
        files=["file.py"],
    )
    
    # Update with explanation
    await temp_db.update_exposure_explanation(exposure.id, 0.75)
    
    # Verify not in unexplained list anymore
    unexplained = await temp_db.get_exposures_without_explanation(project.id)
    assert len(unexplained) == 0


@pytest.mark.asyncio
async def test_update_exposure_explanation_invalid_depth(temp_db, sample_project_data):
    """Test updating with invalid depth raises error."""
    project = await temp_db.create_project(**sample_project_data)
    
    intent = await temp_db.create_intent(
        session_id="session-1",
        project_id=project.id,
        intent_description="Test intent",
        files=["file.py"],
        skills=["skill1"],
    )
    
    commit_sha = "a" * 40
    async with temp_db._get_connection() as conn:
        await conn.execute(
            """
            INSERT INTO commits (sha, project_id, message, files, committed_at, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (commit_sha, str(project.id), "Test commit", json.dumps(["file.py"]), datetime.now(timezone.utc).isoformat(), "new")
        )
        await conn.commit()
    
    exposure = await temp_db.create_exposure(
        project_id=project.id,
        intent_id=intent.id,
        commit_sha=commit_sha,
        skills=["skill1"],
        files=["file.py"],
    )
    
    with pytest.raises(ValidationError, match="must be 0.0-1.0"):
        await temp_db.update_exposure_explanation(exposure.id, 1.5)


@pytest.mark.asyncio
async def test_get_exposures_without_explanation(temp_db, sample_project_data):
    """Test retrieving exposures without explanations."""
    project = await temp_db.create_project(**sample_project_data)
    
    intent = await temp_db.create_intent(
        session_id="session-1",
        project_id=project.id,
        intent_description="Test intent",
        files=["file.py"],
        skills=["skill1"],
    )
    
    commit_sha = "a" * 40
    async with temp_db._get_connection() as conn:
        await conn.execute(
            """
            INSERT INTO commits (sha, project_id, message, files, committed_at, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (commit_sha, str(project.id), "Test commit", json.dumps(["file.py"]), datetime.now(timezone.utc).isoformat(), "new")
        )
        await conn.commit()
    
    # Create exposure without explanation
    await temp_db.create_exposure(
        project_id=project.id,
        intent_id=intent.id,
        commit_sha=commit_sha,
        skills=["skill1"],
        files=["file.py"],
    )
    
    # Retrieve unexplained exposures
    unexplained = await temp_db.get_exposures_without_explanation(project.id)
    
    assert len(unexplained) == 1
    assert not unexplained[0].explanation_recorded


# ============================================================================
# KnowledgeItem Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_knowledge_item(temp_db, sample_project_data):
    """Test creating a knowledge item."""
    project = await temp_db.create_project(**sample_project_data)
    
    item = await temp_db.create_knowledge_item(
        project_id=project.id,
        key="async-patterns",
        title="Async/Await Patterns",
        summary="Understanding async programming in Python",
        tracked_files=["src/async_example.py"],
        depth_band=DepthBand.INTERMEDIATE,
        self_rating=3.5,
    )
    
    assert item.key == "async-patterns"
    assert item.title == "Async/Await Patterns"
    assert item.depth_band == DepthBand.INTERMEDIATE
    assert item.self_rating == 3.5


@pytest.mark.asyncio
async def test_create_knowledge_item_duplicate_key(temp_db, sample_project_data):
    """Test creating knowledge item with duplicate key raises error."""
    project = await temp_db.create_project(**sample_project_data)
    
    # Create first item
    await temp_db.create_knowledge_item(
        project_id=project.id,
        key="test-key",
        title="Test Item",
        summary="Test summary",
        tracked_files=["file.py"],
        depth_band=DepthBand.BASIC,
    )
    
    # Try to create duplicate
    with pytest.raises(ValidationError, match="already exists"):
        await temp_db.create_knowledge_item(
            project_id=project.id,
            key="test-key",  # Same key
            title="Another Item",
            summary="Another summary",
            tracked_files=["file2.py"],
            depth_band=DepthBand.BASIC,
        )


@pytest.mark.asyncio
async def test_get_knowledge_item_by_key(temp_db, sample_project_data):
    """Test retrieving knowledge item by key."""
    project = await temp_db.create_project(**sample_project_data)
    
    created = await temp_db.create_knowledge_item(
        project_id=project.id,
        key="test-key",
        title="Test Item",
        summary="Test summary",
        tracked_files=["file.py"],
        depth_band=DepthBand.BASIC,
    )
    
    retrieved = await temp_db.get_knowledge_item_by_key(project.id, "test-key")
    
    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.key == "test-key"


@pytest.mark.asyncio
async def test_list_knowledge_items(temp_db, sample_project_data):
    """Test listing all knowledge items for a project."""
    project = await temp_db.create_project(**sample_project_data)
    
    # Create multiple items
    await temp_db.create_knowledge_item(
        project_id=project.id,
        key="item1",
        title="Item 1",
        summary="Summary 1",
        tracked_files=["file1.py"],
        depth_band=DepthBand.BASIC,
    )
    
    await temp_db.create_knowledge_item(
        project_id=project.id,
        key="item2",
        title="Item 2",
        summary="Summary 2",
        tracked_files=["file2.py"],
        depth_band=DepthBand.ADVANCED,
    )
    
    items = await temp_db.list_knowledge_items(project.id)
    
    assert len(items) == 2


@pytest.mark.asyncio
async def test_update_knowledge_item_staleness(temp_db, sample_project_data):
    """Test updating knowledge item staleness."""
    project = await temp_db.create_project(**sample_project_data)
    
    item = await temp_db.create_knowledge_item(
        project_id=project.id,
        key="test-key",
        title="Test Item",
        summary="Test summary",
        tracked_files=["file.py"],
        depth_band=DepthBand.BASIC,
    )
    
    # Mark as stale
    stale_time = datetime.now(timezone.utc)
    await temp_db.update_knowledge_item_staleness(item.id, True, stale_time)
    
    # Verify update
    updated = await temp_db.get_knowledge_item_by_key(project.id, "test-key")
    assert updated.is_stale
    assert updated.stale_since is not None


# ============================================================================
# ReviewSchedule Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_review_schedule(temp_db, sample_project_data):
    """Test creating initial review schedule."""
    project = await temp_db.create_project(**sample_project_data)
    
    item = await temp_db.create_knowledge_item(
        project_id=project.id,
        key="test-key",
        title="Test Item",
        summary="Test summary",
        tracked_files=["file.py"],
        depth_band=DepthBand.BASIC,
    )
    
    schedule = await temp_db.create_review_schedule(item.id)
    
    assert schedule.item_id == item.id
    assert schedule.interval == 1
    assert schedule.easiness == 2.5
    assert schedule.repetitions == 0


@pytest.mark.asyncio
async def test_get_review_schedule(temp_db, sample_project_data):
    """Test retrieving review schedule."""
    project = await temp_db.create_project(**sample_project_data)
    
    item = await temp_db.create_knowledge_item(
        project_id=project.id,
        key="test-key",
        title="Test Item",
        summary="Test summary",
        tracked_files=["file.py"],
        depth_band=DepthBand.BASIC,
    )
    
    created = await temp_db.create_review_schedule(item.id)
    retrieved = await temp_db.get_review_schedule(item.id)
    
    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.item_id == item.id


@pytest.mark.asyncio
async def test_update_review_schedule(temp_db, sample_project_data):
    """Test updating review schedule after review."""
    project = await temp_db.create_project(**sample_project_data)
    
    item = await temp_db.create_knowledge_item(
        project_id=project.id,
        key="test-key",
        title="Test Item",
        summary="Test summary",
        tracked_files=["file.py"],
        depth_band=DepthBand.BASIC,
    )
    
    schedule = await temp_db.create_review_schedule(item.id)
    
    # Update schedule
    schedule.interval = 3
    schedule.repetitions = 1
    schedule.last_reviewed_at = datetime.now(timezone.utc)
    schedule.due_at = datetime.now(timezone.utc) + timedelta(days=3)
    
    await temp_db.update_review_schedule(schedule)
    
    # Verify update
    updated = await temp_db.get_review_schedule(item.id)
    assert updated.interval == 3
    assert updated.repetitions == 1
    assert updated.last_reviewed_at is not None


@pytest.mark.asyncio
async def test_get_due_reviews(temp_db, sample_project_data):
    """Test retrieving due reviews."""
    project = await temp_db.create_project(**sample_project_data)
    
    # Create item with overdue review
    item = await temp_db.create_knowledge_item(
        project_id=project.id,
        key="test-key",
        title="Test Item",
        summary="Test summary",
        tracked_files=["file.py"],
        depth_band=DepthBand.BASIC,
    )
    
    schedule = await temp_db.create_review_schedule(item.id)
    
    # Make it overdue
    schedule.due_at = datetime.now(timezone.utc) - timedelta(days=1)
    await temp_db.update_review_schedule(schedule)
    
    # Retrieve due reviews
    due = await temp_db.get_due_reviews(project.id)
    
    assert len(due) == 1
    assert due[0][0].id == item.id
    assert due[0][1].id == schedule.id


@pytest.mark.asyncio
async def test_get_due_reviews_excludes_snoozed(temp_db, sample_project_data):
    """Test that snoozed reviews are excluded from due reviews."""
    project = await temp_db.create_project(**sample_project_data)
    
    item = await temp_db.create_knowledge_item(
        project_id=project.id,
        key="test-key",
        title="Test Item",
        summary="Test summary",
        tracked_files=["file.py"],
        depth_band=DepthBand.BASIC,
    )
    
    schedule = await temp_db.create_review_schedule(item.id)
    
    # Make it overdue but snoozed
    schedule.due_at = datetime.now(timezone.utc) - timedelta(days=1)
    await temp_db.update_review_schedule(schedule)
    await temp_db.snooze_review(schedule.id, 2)
    
    # Should not appear in due reviews
    due = await temp_db.get_due_reviews(project.id)
    assert len(due) == 0


@pytest.mark.asyncio
async def test_snooze_review(temp_db, sample_project_data):
    """Test snoozing a review."""
    project = await temp_db.create_project(**sample_project_data)
    
    item = await temp_db.create_knowledge_item(
        project_id=project.id,
        key="test-key",
        title="Test Item",
        summary="Test summary",
        tracked_files=["file.py"],
        depth_band=DepthBand.BASIC,
    )
    
    schedule = await temp_db.create_review_schedule(item.id)
    
    # Snooze for 3 days
    await temp_db.snooze_review(schedule.id, 3)
    
    # Verify snooze
    updated = await temp_db.get_review_schedule(item.id)
    assert updated.snoozed_until is not None
    assert updated.snoozed_until > datetime.now(timezone.utc)


# ============================================================================
# Transaction Tests
# ============================================================================


@pytest.mark.asyncio
async def test_transaction_commit(temp_db, sample_project_data):
    """Test transaction commits on success."""
    project = await temp_db.create_project(**sample_project_data)
    
    async with temp_db.transaction() as conn:
        await conn.execute(
            "UPDATE projects SET total_commits = ? WHERE id = ?",
            (10, str(project.id))
        )
    
    # Verify commit
    updated = await temp_db.get_project_by_id(project.id)
    assert updated.total_commits == 10


@pytest.mark.asyncio
async def test_transaction_rollback(temp_db, sample_project_data):
    """Test transaction rolls back on exception."""
    project = await temp_db.create_project(**sample_project_data)
    
    try:
        async with temp_db.transaction() as conn:
            await conn.execute(
                "UPDATE projects SET total_commits = ? WHERE id = ?",
                (10, str(project.id))
            )
            raise ValueError("Test error")
    except ValueError:
        pass
    
    # Verify rollback - value should still be 0
    updated = await temp_db.get_project_by_id(project.id)
    assert updated.total_commits == 0
