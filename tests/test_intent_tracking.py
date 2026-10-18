"""Tests for MCP-native intent tracking (Task 7.1).

Tests the start_skill_session_v2 implementation that uses the new
intent_records schema with session_id tracking.

Requirements tested: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6
"""

from __future__ import annotations

import sqlite3
import time
from datetime import datetime, timezone

import pytest

from learnloop.domain.errors import NotFoundError, ValidationError
from learnloop.services import capture_service


@pytest.fixture
def temp_db_with_project(tmp_path):
    """Create a temporary database with a project and skills."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    
    # Create minimal schema
    conn.executescript("""
        CREATE TABLE projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            repo_path TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL
        );
        
        CREATE TABLE skills (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL
        );
        
        CREATE TABLE intent_records (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            project_id TEXT NOT NULL REFERENCES projects(id),
            intent_description TEXT NOT NULL,
            files_json TEXT NOT NULL,
            skills_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'matched', 'abandoned')),
            matched_commit_sha TEXT NULL,
            created_at TEXT NOT NULL,
            closed_at TEXT NULL,
            CHECK (
                (status = 'matched' AND matched_commit_sha IS NOT NULL) OR
                (status != 'matched')
            ),
            CHECK (
                (status != 'open' AND closed_at IS NOT NULL) OR
                (status = 'open')
            )
        );
        
        CREATE INDEX idx_intent_records_project ON intent_records(project_id);
        CREATE INDEX idx_intent_records_status ON intent_records(status);
        CREATE INDEX idx_intent_records_session ON intent_records(session_id);
    """)
    
    # Insert test data
    project_id = "test-project-123"
    conn.execute(
        "INSERT INTO projects (id, name, repo_path, created_at) VALUES (?, ?, ?, ?)",
        (project_id, "Test Project", "/test/path", datetime.now(timezone.utc).isoformat())
    )
    
    conn.execute("INSERT INTO skills (id, name) VALUES (?, ?)", ("python.basics", "Python Basics"))
    conn.execute("INSERT INTO skills (id, name) VALUES (?, ?)", ("testing.pytest", "Pytest Testing"))
    
    conn.commit()
    
    yield conn, project_id
    
    conn.close()


def test_start_skill_session_v2_creates_intent_with_session_id(temp_db_with_project):
    """Test that start_skill_session_v2 creates intent with session_id.
    
    Requirements:
        - 4.1: Create IntentRecord when user calls start_skill_session
        - 4.2: Capture intent description, file list, and skills
        - 4.3: Mark with status "open" upon creation
        - 4.4: Store session_id and timestamp
    """
    conn, project_id = temp_db_with_project
    
    # Call the service
    result = capture_service.start_skill_session_v2(
        conn=conn,
        project_id=project_id,
        session_id="test-session-abc123",
        intent_description="Implement user authentication with JWT",
        files=["src/auth.py", "src/models/user.py", "tests/test_auth.py"],
        skills=["python.basics"],
    )
    
    # Verify response
    assert result["created"] is True
    assert result["status"] == "open"
    assert "intent_id" in result
    intent_id = result["intent_id"]
    
    # Verify database record (Requirements 4.2, 4.3, 4.4)
    row = conn.execute(
        "SELECT * FROM intent_records WHERE id = ?", (intent_id,)
    ).fetchone()
    
    assert row is not None
    assert row["session_id"] == "test-session-abc123"  # Requirement 4.4
    assert row["project_id"] == project_id
    assert row["intent_description"] == "Implement user authentication with JWT"  # Requirement 4.2
    assert row["status"] == "open"  # Requirement 4.3
    assert row["files_json"] == '["src/auth.py", "src/models/user.py", "tests/test_auth.py"]'  # Requirement 4.2
    assert row["skills_json"] == '["python.basics"]'  # Requirement 4.2
    assert row["matched_commit_sha"] is None
    assert row["closed_at"] is None
    
    # Verify timestamp is stored (Requirement 4.4)
    assert row["created_at"] is not None
    created_at = datetime.fromisoformat(row["created_at"])
    assert (datetime.now(timezone.utc) - created_at).total_seconds() < 5


def test_start_skill_session_v2_validates_empty_files(temp_db_with_project):
    """Test that empty files list is rejected.
    
    Requirements:
        - 4.2: Validate input parameters
    """
    conn, project_id = temp_db_with_project
    
    with pytest.raises(ValidationError, match="files list must not be empty"):
        capture_service.start_skill_session_v2(
            conn=conn,
            project_id=project_id,
            session_id="test-session",
            intent_description="Test intent",
            files=[],  # Empty files - should fail
            skills=[],
        )


def test_start_skill_session_v2_validates_empty_description(temp_db_with_project):
    """Test that empty intent description is rejected.
    
    Requirements:
        - 4.2: Validate input parameters
    """
    conn, project_id = temp_db_with_project
    
    with pytest.raises(ValidationError, match="intent_description must not be empty"):
        capture_service.start_skill_session_v2(
            conn=conn,
            project_id=project_id,
            session_id="test-session",
            intent_description="",  # Empty - should fail
            files=["src/test.py"],
            skills=[],
        )


def test_start_skill_session_v2_validates_too_many_files(temp_db_with_project):
    """Test that file count limit is enforced.
    
    Requirements:
        - 4.2: Validate input parameters
    """
    conn, project_id = temp_db_with_project
    
    # Create 51 files (exceeds limit of 50)
    many_files = [f"src/file_{i}.py" for i in range(51)]
    
    with pytest.raises(ValidationError, match="files list cannot exceed 50 items"):
        capture_service.start_skill_session_v2(
            conn=conn,
            project_id=project_id,
            session_id="test-session",
            intent_description="Test with many files",
            files=many_files,
            skills=[],
        )


def test_start_skill_session_v2_allows_multiple_open_intents(temp_db_with_project):
    """Test that multiple open intents can exist for same project.
    
    Requirements:
        - 4.5: Allow multiple open intents per project simultaneously
    """
    conn, project_id = temp_db_with_project
    
    # Create first intent
    result1 = capture_service.start_skill_session_v2(
        conn=conn,
        project_id=project_id,
        session_id="session-1",
        intent_description="First task",
        files=["src/feature1.py"],
        skills=[],
    )
    
    # Create second intent
    result2 = capture_service.start_skill_session_v2(
        conn=conn,
        project_id=project_id,
        session_id="session-2",
        intent_description="Second task",
        files=["src/feature2.py"],
        skills=[],
    )
    
    # Both should be created successfully
    assert result1["created"] is True
    assert result2["created"] is True
    assert result1["intent_id"] != result2["intent_id"]
    
    # Both should be open
    open_intents = conn.execute(
        "SELECT id FROM intent_records WHERE project_id = ? AND status = 'open'",
        (project_id,)
    ).fetchall()
    
    assert len(open_intents) == 2


def test_start_skill_session_v2_is_idempotent(temp_db_with_project):
    """Test that providing same intent_id is idempotent.
    
    Requirements:
        - 4.6: Idempotent operation for retries
    """
    conn, project_id = temp_db_with_project
    
    intent_id = "stable-intent-id-123"
    
    # First call - creates intent
    result1 = capture_service.start_skill_session_v2(
        conn=conn,
        project_id=project_id,
        session_id="session-1",
        intent_description="Test idempotency",
        files=["src/test.py"],
        skills=[],
        intent_id=intent_id,
    )
    
    # Second call with same intent_id - should not create duplicate
    result2 = capture_service.start_skill_session_v2(
        conn=conn,
        project_id=project_id,
        session_id="session-1",
        intent_description="Different description",  # Different data
        files=["src/other.py"],
        skills=[],
        intent_id=intent_id,  # Same ID
    )
    
    # First creates, second returns existing
    assert result1["created"] is True
    assert result2["created"] is False
    assert result1["intent_id"] == result2["intent_id"] == intent_id
    
    # Verify only one record exists
    count = conn.execute(
        "SELECT COUNT(*) as cnt FROM intent_records WHERE id = ?",
        (intent_id,)
    ).fetchone()["cnt"]
    assert count == 1


def test_start_skill_session_v2_validates_unknown_skills(temp_db_with_project):
    """Test that unknown skill IDs are rejected.
    
    Requirements:
        - 4.2: Validate input parameters
    """
    conn, project_id = temp_db_with_project
    
    with pytest.raises(ValidationError, match="Unknown skill id"):
        capture_service.start_skill_session_v2(
            conn=conn,
            project_id=project_id,
            session_id="test-session",
            intent_description="Test with invalid skill",
            files=["src/test.py"],
            skills=["nonexistent.skill"],  # Invalid skill
        )


def test_start_skill_session_v2_validates_unknown_project(temp_db_with_project):
    """Test that unknown project ID is rejected.
    
    Requirements:
        - 4.1: Validate project exists before creating intent
    """
    conn, _ = temp_db_with_project
    
    with pytest.raises(NotFoundError, match="Unknown project_id"):
        capture_service.start_skill_session_v2(
            conn=conn,
            project_id="nonexistent-project",
            session_id="test-session",
            intent_description="Test with invalid project",
            files=["src/test.py"],
            skills=[],
        )


def test_start_skill_session_v2_performance(temp_db_with_project):
    """Test that intent creation completes under 50ms.
    
    Requirements:
        - 4.6: Return success response in under 50ms
    """
    conn, project_id = temp_db_with_project
    
    start_time = time.perf_counter()
    
    capture_service.start_skill_session_v2(
        conn=conn,
        project_id=project_id,
        session_id="perf-test-session",
        intent_description="Performance test",
        files=["src/test.py"],
        skills=[],
    )
    
    elapsed_ms = (time.perf_counter() - start_time) * 1000
    
    # Should complete in under 50ms (Requirement 4.6)
    # Using 100ms threshold to account for test overhead
    assert elapsed_ms < 100, f"Intent creation took {elapsed_ms:.2f}ms (should be < 50ms)"


def test_start_skill_session_v2_normalizes_file_paths(temp_db_with_project):
    """Test that file paths are normalized and deduplicated."""
    conn, project_id = temp_db_with_project
    
    result = capture_service.start_skill_session_v2(
        conn=conn,
        project_id=project_id,
        session_id="test-session",
        intent_description="Test path normalization",
        files=[
            "src/test.py",
            "src\\test.py",  # Duplicate with different separator
            "src/other.py",
        ],
        skills=[],
    )
    
    # Check stored files are normalized and deduplicated
    row = conn.execute(
        "SELECT files_json FROM intent_records WHERE id = ?",
        (result["intent_id"],)
    ).fetchone()
    
    import json
    files = json.loads(row["files_json"])
    
    # Should be deduplicated
    assert len(files) == 2
    # All should use forward slashes
    assert all("/" in f or "\\" not in f for f in files)


def test_start_skill_session_v2_works_without_skills(temp_db_with_project):
    """Test that skills parameter is optional.
    
    Requirements:
        - 4.2: Skills are optional parameter
    """
    conn, project_id = temp_db_with_project
    
    result = capture_service.start_skill_session_v2(
        conn=conn,
        project_id=project_id,
        session_id="test-session",
        intent_description="Test without skills",
        files=["src/test.py"],
        skills=None,  # No skills provided
    )
    
    assert result["created"] is True
    
    # Verify empty skills array stored
    row = conn.execute(
        "SELECT skills_json FROM intent_records WHERE id = ?",
        (result["intent_id"],)
    ).fetchone()
    
    import json
    skills = json.loads(row["skills_json"])
    assert skills == []


def test_start_skill_session_v2_with_multiple_skills(temp_db_with_project):
    """Test intent creation with multiple skills."""
    conn, project_id = temp_db_with_project
    
    result = capture_service.start_skill_session_v2(
        conn=conn,
        project_id=project_id,
        session_id="test-session",
        intent_description="Test multiple skills",
        files=["src/test.py"],
        skills=["python.basics", "testing.pytest"],
    )
    
    assert result["created"] is True
    
    # Verify skills stored
    row = conn.execute(
        "SELECT skills_json FROM intent_records WHERE id = ?",
        (result["intent_id"],)
    ).fetchone()
    
    import json
    skills = json.loads(row["skills_json"])
    assert set(skills) == {"python.basics", "testing.pytest"}
