"""Integration test for Task 8.3: Commit Queue Processing

This test demonstrates the complete workflow of the ingest_queue MCP tool:
1. Queue entries are written by git hooks to .learn/queue/
2. ingest_queue tool reads and parses JSON files
3. Commit metadata is stored in the database (commits table)
4. Files are processed with error handling (malformed JSON quarantined)
5. After reconciliation, processed files are deleted

Requirements validated:
- 7.1: Load unprocessed queue entries
- 24.7: Error handling for malformed JSON (skip and log)
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from learnloop.capture import queue
from learnloop.config import Settings
from learnloop.persistence.db import connect
from learnloop.services import capture_service


@pytest.fixture
def test_env(tmp_path: Path):
    """Set up test environment with database and git repo."""
    db_path = tmp_path / "test.db"
    repo_path = tmp_path / "repo"
    repo_path.mkdir()
    
    conn = connect(db_path)
    settings = Settings(db_path=db_path)
    
    # Create test project
    project = capture_service.start_project(
        conn, 
        name="test-project",
        repo_path=str(repo_path)
    )
    
    return {
        "conn": conn,
        "settings": settings,
        "project_id": project["id"],
        "repo_path": repo_path,
        "queue_dir": queue.queue_dir(repo_path),
    }


def test_ingest_queue_reads_json_files_from_queue_directory(test_env):
    """Verify ingest_queue reads JSON files from .learn/queue/ directory."""
    conn = test_env["conn"]
    settings = test_env["settings"]
    project_id = test_env["project_id"]
    repo_path = test_env["repo_path"]
    queue_dir = test_env["queue_dir"]
    
    # Create queue directory
    queue_dir.mkdir(parents=True, exist_ok=True)
    
    # Write a queue entry
    commit_time = datetime(2024, 1, 15, 10, 0, tzinfo=UTC).isoformat()
    queue.write_queue_entry(
        repo=repo_path,
        sha="abc123def456",
        message="Add new feature",
        files=["src/feature.py", "tests/test_feature.py"],
        committed_at=commit_time
    )
    
    # Verify queue file exists
    queue_files = list(queue_dir.glob("*.json"))
    assert len(queue_files) == 1
    assert queue_files[0].name == "abc123def456.json"
    
    # Ingest the queue
    stats = queue.ingest(conn, settings, project_id, repo_path)
    
    # Verify ingestion stats
    assert stats["ingested"] == 1
    assert stats["duplicates"] == 0
    assert stats["rejected"] == 0
    
    # Verify commit record created in database
    commit_row = conn.execute(
        "SELECT * FROM commits WHERE sha='abc123def456'"
    ).fetchone()
    
    assert commit_row is not None
    assert commit_row["project_id"] == project_id
    assert commit_row["message"] == "Add new feature"
    assert json.loads(commit_row["files"]) == ["src/feature.py", "tests/test_feature.py"]
    
    # Verify queue file was deleted after successful processing
    remaining_files = list(queue_dir.glob("*.json"))
    assert len(remaining_files) == 0


def test_ingest_queue_handles_malformed_json_with_error_recovery(test_env):
    """Verify Requirement 24.7: Malformed JSON is quarantined and logged."""
    conn = test_env["conn"]
    settings = test_env["settings"]
    project_id = test_env["project_id"]
    repo_path = test_env["repo_path"]
    queue_dir = test_env["queue_dir"]
    
    # Create queue directory
    queue_dir.mkdir(parents=True, exist_ok=True)
    
    # Write a valid queue entry
    commit_time = datetime(2024, 1, 15, 10, 0, tzinfo=UTC).isoformat()
    queue.write_queue_entry(
        repo=repo_path,
        sha="valid123",
        message="Valid commit",
        files=["src/valid.py"],
        committed_at=commit_time
    )
    
    # Write a malformed JSON file
    bad_file = queue_dir / "bad456.json"
    bad_file.write_text("{this is not valid json", encoding="utf-8")
    
    # Write another valid entry
    queue.write_queue_entry(
        repo=repo_path,
        sha="valid789",
        message="Another valid commit",
        files=["src/another.py"],
        committed_at=commit_time
    )
    
    # Ingest the queue
    stats = queue.ingest(conn, settings, project_id, repo_path)
    
    # Verify stats: 2 valid ingested, 1 rejected
    assert stats["ingested"] == 2
    assert stats["rejected"] == 1
    
    # Verify valid commits are in database
    valid_commits = conn.execute(
        "SELECT sha FROM commits WHERE sha IN ('valid123', 'valid789')"
    ).fetchall()
    assert len(valid_commits) == 2
    
    # Verify bad commit is NOT in database
    bad_commit = conn.execute(
        "SELECT * FROM commits WHERE sha='bad456'"
    ).fetchone()
    assert bad_commit is None
    
    # Verify malformed file was quarantined (renamed to .failed)
    failed_files = list(queue_dir.glob("*.failed"))
    assert len(failed_files) == 1
    assert failed_files[0].name == "bad456.failed"
    
    # Verify no .json files remain
    json_files = list(queue_dir.glob("*.json"))
    assert len(json_files) == 0


def test_ingest_queue_is_idempotent_duplicates_are_skipped(test_env):
    """Verify duplicate commits are detected and skipped (idempotency)."""
    conn = test_env["conn"]
    settings = test_env["settings"]
    project_id = test_env["project_id"]
    repo_path = test_env["repo_path"]
    
    commit_time = datetime(2024, 1, 15, 10, 0, tzinfo=UTC).isoformat()
    
    # First ingestion
    queue.write_queue_entry(
        repo=repo_path,
        sha="duplicate123",
        message="Original message",
        files=["src/file.py"],
        committed_at=commit_time
    )
    
    stats1 = queue.ingest(conn, settings, project_id, repo_path)
    assert stats1["ingested"] == 1
    assert stats1["duplicates"] == 0
    
    # Second ingestion with same SHA (simulates duplicate processing)
    queue.write_queue_entry(
        repo=repo_path,
        sha="duplicate123",
        message="Different message (should be ignored)",
        files=["src/different.py"],
        committed_at=commit_time
    )
    
    stats2 = queue.ingest(conn, settings, project_id, repo_path)
    assert stats2["ingested"] == 0
    assert stats2["duplicates"] == 1
    
    # Verify only one commit record exists with original data
    commits = conn.execute(
        "SELECT * FROM commits WHERE sha='duplicate123'"
    ).fetchall()
    assert len(commits) == 1
    assert commits[0]["message"] == "Original message"


def test_ingest_queue_processes_and_deletes_files_atomically(test_env):
    """Verify files are deleted only after successful processing."""
    conn = test_env["conn"]
    settings = test_env["settings"]
    project_id = test_env["project_id"]
    repo_path = test_env["repo_path"]
    queue_dir = test_env["queue_dir"]
    
    queue_dir.mkdir(parents=True, exist_ok=True)
    
    commit_time = datetime(2024, 1, 15, 10, 0, tzinfo=UTC).isoformat()
    
    # Write multiple queue entries
    for i in range(5):
        queue.write_queue_entry(
            repo=repo_path,
            sha=f"commit{i:03d}",
            message=f"Commit message {i}",
            files=[f"src/file{i}.py"],
            committed_at=commit_time
        )
    
    # Verify all files exist before ingestion
    queue_files_before = list(queue_dir.glob("*.json"))
    assert len(queue_files_before) == 5
    
    # Ingest the queue
    stats = queue.ingest(conn, settings, project_id, repo_path)
    assert stats["ingested"] == 5
    
    # Verify all commits are in database
    commit_count = conn.execute(
        "SELECT COUNT(*) FROM commits WHERE project_id=?",
        (project_id,)
    ).fetchone()[0]
    assert commit_count == 5
    
    # Verify all queue files were deleted
    queue_files_after = list(queue_dir.glob("*.json"))
    assert len(queue_files_after) == 0


def test_ingest_queue_respects_max_queue_files_limit(test_env):
    """Verify Settings.max_queue_files limit is respected."""
    conn = test_env["conn"]
    repo_path = test_env["repo_path"]
    project_id = test_env["project_id"]
    queue_dir = test_env["queue_dir"]
    
    # Create settings with low limit
    settings = Settings(db_path=test_env["settings"].db_path, max_queue_files=3)
    
    queue_dir.mkdir(parents=True, exist_ok=True)
    
    commit_time = datetime(2024, 1, 15, 10, 0, tzinfo=UTC).isoformat()
    
    # Write 10 queue entries
    for i in range(10):
        queue.write_queue_entry(
            repo=repo_path,
            sha=f"sha{i:03d}",
            message=f"Message {i}",
            files=[f"file{i}.py"],
            committed_at=commit_time
        )
    
    # Ingest with limit of 3
    stats = queue.ingest(conn, settings, project_id, repo_path)
    
    # Only 3 should be processed (the limit)
    assert stats["ingested"] == 3
    
    # 7 files should remain in queue
    remaining = list(queue_dir.glob("*.json"))
    assert len(remaining) == 7


def test_ingest_queue_redacts_sensitive_information(test_env):
    """Verify sensitive information is redacted from commit messages."""
    conn = test_env["conn"]
    settings = test_env["settings"]
    project_id = test_env["project_id"]
    repo_path = test_env["repo_path"]
    
    commit_time = datetime(2024, 1, 15, 10, 0, tzinfo=UTC).isoformat()
    
    # Write queue entry with recognizable secrets (AWS key pattern)
    queue.write_queue_entry(
        repo=repo_path,
        sha="secret123",
        message="Add AWS credentials AKIAIOSFODNN7EXAMPLE to config",
        files=["config.py"],
        committed_at=commit_time
    )
    
    # Ingest the queue
    stats = queue.ingest(conn, settings, project_id, repo_path)
    assert stats["ingested"] == 1
    
    # Verify AWS key was redacted
    commit_row = conn.execute(
        "SELECT message FROM commits WHERE sha='secret123'"
    ).fetchone()
    
    # The redaction should have removed or masked the AWS key
    message = commit_row["message"]
    assert "AKIAIOSFODNN7EXAMPLE" not in message
    assert "[REDACTED]" in message


def test_ingest_queue_filters_ignored_files(test_env):
    """Verify files matching .gitignore patterns are filtered out."""
    conn = test_env["conn"]
    settings = test_env["settings"]
    project_id = test_env["project_id"]
    repo_path = test_env["repo_path"]
    
    commit_time = datetime(2024, 1, 15, 10, 0, tzinfo=UTC).isoformat()
    
    # Write queue entry with both tracked and ignored files
    queue.write_queue_entry(
        repo=repo_path,
        sha="filtered123",
        message="Commit with ignored files",
        files=[
            "src/main.py",          # Should be kept
            ".env",                  # Should be filtered
            "node_modules/pkg.js",   # Should be filtered
            "tests/test.py",         # Should be kept
        ],
        committed_at=commit_time
    )
    
    # Ingest the queue
    stats = queue.ingest(conn, settings, project_id, repo_path)
    assert stats["ingested"] == 1
    
    # Verify only non-ignored files are stored
    commit_row = conn.execute(
        "SELECT files FROM commits WHERE sha='filtered123'"
    ).fetchone()
    
    stored_files = json.loads(commit_row["files"])
    assert "src/main.py" in stored_files
    assert "tests/test.py" in stored_files
    assert ".env" not in stored_files
    assert "node_modules/pkg.js" not in stored_files
