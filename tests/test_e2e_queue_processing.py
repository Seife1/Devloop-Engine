"""End-to-end test for queue processing flow (Task 8.3).

This test verifies the complete workflow:
1. Write commit to queue via git hook simulation
2. Ingest queue to create commit and queue_entry records
3. Verify queue_entry is created with processed=0
4. Verify commit record is created properly

Requirements: 7.1, 24.7
"""

import json
import sqlite3
from pathlib import Path

import pytest

from learnloop.capture.queue import ingest, write_queue_entry
from learnloop.config import Settings


@pytest.fixture
def test_setup(tmp_path: Path):
    """Set up test database and repository."""
    # Create test repo
    repo = tmp_path / "test_repo"
    repo.mkdir()
    
    # Create database
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    
    # Create schema
    conn.execute("""
        CREATE TABLE projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            repo_path TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    
    conn.execute("""
        CREATE TABLE commits (
            sha TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(id),
            message TEXT NOT NULL,
            files TEXT NOT NULL,
            committed_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'new',
            origin TEXT DEFAULT 'hook',
            kind TEXT DEFAULT 'commit'
        )
    """)
    
    conn.execute("""
        CREATE TABLE queue_entries (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(id),
            commit_sha TEXT NOT NULL REFERENCES commits(sha) ON DELETE CASCADE,
            processed INTEGER NOT NULL DEFAULT 0,
            processed_at TEXT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE (commit_sha)
        )
    """)
    
    # Insert test project
    conn.execute(
        "INSERT INTO projects (id, name, repo_path, created_at) VALUES (?, ?, ?, ?)",
        ("test-proj", "Test Project", str(repo), "2024-01-01T00:00:00Z"),
    )
    conn.commit()
    
    settings = Settings(
        db_path=str(db_path),
        max_queue_files=100,
        max_queue_file_bytes=1024 * 1024,
        abandon_days=14,
    )
    
    return {
        "conn": conn,
        "repo": repo,
        "settings": settings,
        "project_id": "test-proj",
    }


def test_end_to_end_queue_processing(test_setup):
    """Test the complete queue processing workflow.
    
    This simulates:
    1. Git hook writing commit metadata to queue
    2. MCP server ingesting the queue
    3. Verifying both commit and queue_entry are created
    
    Requirements: 7.1, 24.7
    """
    conn = test_setup["conn"]
    repo = test_setup["repo"]
    settings = test_setup["settings"]
    project_id = test_setup["project_id"]
    
    # Step 1: Simulate git hook writing to queue
    commit_sha = "e2e_test_sha_123abc"
    commit_message = "Implement feature X"
    commit_files = ["src/feature_x.py", "tests/test_feature_x.py", "docs/feature_x.md"]
    committed_at = "2024-01-20T15:45:30Z"
    
    write_queue_entry(
        repo,
        commit_sha,
        commit_message,
        commit_files,
        committed_at,
        origin="hook",
    )
    
    # Verify queue file was created
    queue_dir = repo / ".learn" / "queue"
    queue_file = queue_dir / f"{commit_sha}.json"
    assert queue_file.exists()
    
    # Verify queue file content
    queue_data = json.loads(queue_file.read_text())
    assert queue_data["sha"] == commit_sha
    assert queue_data["message"] == commit_message
    assert queue_data["origin"] == "hook"
    
    # Step 2: Ingest the queue (simulates MCP server processing)
    stats = ingest(conn, settings, project_id, repo)
    
    # Verify ingestion statistics
    assert stats["ingested"] == 1
    assert stats["duplicates"] == 0
    assert stats["rejected"] == 0
    
    # Verify queue file was deleted after successful ingestion
    assert not queue_file.exists()
    
    # Step 3: Verify commit record was created
    commit = conn.execute(
        "SELECT * FROM commits WHERE sha = ?", (commit_sha,)
    ).fetchone()
    
    assert commit is not None
    assert commit["project_id"] == project_id
    assert commit["message"] == commit_message
    assert commit["origin"] == "hook"
    assert commit["status"] == "new"
    assert commit["kind"] == "commit"
    
    commit_files_db = json.loads(commit["files"])
    assert commit_files_db == commit_files
    
    # Step 4: Verify queue_entry record was created (Requirement 7.1)
    queue_entry = conn.execute(
        "SELECT * FROM queue_entries WHERE commit_sha = ?", (commit_sha,)
    ).fetchone()
    
    assert queue_entry is not None
    assert queue_entry["project_id"] == project_id
    assert queue_entry["commit_sha"] == commit_sha
    assert queue_entry["processed"] == 0  # Initially unprocessed
    assert queue_entry["processed_at"] is None  # Not processed yet
    assert queue_entry["created_at"] is not None
    
    # Step 5: Verify the relationship between commit and queue_entry
    assert queue_entry["commit_sha"] == commit["sha"]


def test_multiple_commits_in_queue(test_setup):
    """Test processing multiple commits from the queue in one batch.
    
    Requirements: 7.1
    """
    conn = test_setup["conn"]
    repo = test_setup["repo"]
    settings = test_setup["settings"]
    project_id = test_setup["project_id"]
    
    # Write multiple commits to queue
    commits = [
        ("sha1", "Commit 1", ["file1.py"], "2024-01-20T10:00:00Z"),
        ("sha2", "Commit 2", ["file2.py"], "2024-01-20T10:05:00Z"),
        ("sha3", "Commit 3", ["file3.py"], "2024-01-20T10:10:00Z"),
    ]
    
    for sha, message, files, timestamp in commits:
        write_queue_entry(repo, sha, message, files, timestamp)
    
    # Ingest all at once
    stats = ingest(conn, settings, project_id, repo)
    
    assert stats["ingested"] == 3
    assert stats["duplicates"] == 0
    assert stats["rejected"] == 0
    
    # Verify all commits and queue_entries were created
    for sha, _, _, _ in commits:
        commit = conn.execute("SELECT * FROM commits WHERE sha = ?", (sha,)).fetchone()
        assert commit is not None
        
        queue_entry = conn.execute(
            "SELECT * FROM queue_entries WHERE commit_sha = ?", (sha,)
        ).fetchone()
        assert queue_entry is not None
        assert queue_entry["processed"] == 0


def test_error_handling_preserves_good_commits(test_setup):
    """Test that one bad queue file doesn't prevent processing good ones.
    
    Requirements: 24.7
    """
    conn = test_setup["conn"]
    repo = test_setup["repo"]
    settings = test_setup["settings"]
    project_id = test_setup["project_id"]
    
    queue_dir = repo / ".learn" / "queue"
    queue_dir.mkdir(parents=True, exist_ok=True)
    
    # Write one good commit
    write_queue_entry(repo, "good_sha", "Good commit", ["good.py"], "2024-01-20T10:00:00Z")
    
    # Write one malformed file
    bad_file = queue_dir / "bad_sha.json"
    bad_file.write_text("{malformed json", encoding="utf-8")
    
    # Write another good commit
    write_queue_entry(repo, "good_sha2", "Another good", ["good2.py"], "2024-01-20T10:05:00Z")
    
    # Ingest should process good files and quarantine bad one
    stats = ingest(conn, settings, project_id, repo)
    
    assert stats["ingested"] == 2  # Two good commits
    assert stats["rejected"] == 1  # One bad file
    
    # Verify good commits were processed
    assert conn.execute("SELECT * FROM commits WHERE sha = 'good_sha'").fetchone() is not None
    assert conn.execute("SELECT * FROM commits WHERE sha = 'good_sha2'").fetchone() is not None
    
    # Verify bad file was quarantined
    assert not bad_file.exists()
    assert (queue_dir / "bad_sha.failed").exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
