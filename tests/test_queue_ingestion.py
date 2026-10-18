"""Tests for commit queue ingestion (Task 8.3).

Requirements: 7.1, 24.7

Tests verify that:
- JSON files are read from .learn/queue/
- Commit metadata is parsed with error handling
- Commit records are created in database
- Queue_Entry records are created for reconciliation tracking
- Queue files are deleted after successful processing
- Malformed files are quarantined with .failed extension
"""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pytest

from learnloop.capture.queue import ingest, write_queue_entry
from learnloop.config import Settings


@pytest.fixture
def test_db() -> sqlite3.Connection:
    """Create an in-memory test database with schema."""
    conn = sqlite3.Connection(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    
    # Create projects table
    conn.execute("""
        CREATE TABLE projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            repo_path TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    
    # Create commits table
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
    
    # Create queue_entries table
    conn.execute("""
        CREATE TABLE queue_entries (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(id),
            commit_sha TEXT NOT NULL REFERENCES commits(sha),
            processed INTEGER NOT NULL DEFAULT 0,
            processed_at TEXT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE (commit_sha)
        )
    """)
    
    # Insert test project
    conn.execute(
        "INSERT INTO projects (id, name, repo_path, created_at) VALUES (?, ?, ?, ?)",
        ("test-proj", "Test Project", "/test/repo", "2024-01-01T00:00:00Z"),
    )
    
    conn.commit()
    return conn


@pytest.fixture
def test_repo(tmp_path: Path) -> Path:
    """Create a temporary repository with .learn/queue/ directory."""
    repo = tmp_path / "test_repo"
    repo.mkdir()
    queue_dir = repo / ".learn" / "queue"
    queue_dir.mkdir(parents=True)
    return repo


@pytest.fixture
def settings() -> Settings:
    """Create test settings."""
    return Settings(
        db_path=":memory:",
        max_queue_files=100,
        max_queue_file_bytes=1024 * 1024,  # 1MB
        abandon_days=14,
    )


class TestQueueIngestion:
    """Test queue.ingest() creates Queue_Entry records properly."""
    
    def test_ingest_creates_commit_and_queue_entry(self, test_db, test_repo, settings):
        """Test that ingesting a queue file creates both commit and queue_entry records.
        
        Requirements: 7.1
        """
        # Create a queue file
        sha = "abc123def456"
        message = "Add feature"
        files = ["src/feature.py", "tests/test_feature.py"]
        committed_at = "2024-01-15T10:30:00Z"
        
        write_queue_entry(
            test_repo,
            sha,
            message,
            files,
            committed_at,
            origin="hook",
        )
        
        # Ingest the queue
        stats = ingest(test_db, settings, "test-proj", test_repo)
        
        # Verify statistics
        assert stats["ingested"] == 1
        assert stats["duplicates"] == 0
        assert stats["rejected"] == 0
        
        # Verify commit was created
        commit = test_db.execute(
            "SELECT * FROM commits WHERE sha = ?", (sha,)
        ).fetchone()
        assert commit is not None
        assert commit["project_id"] == "test-proj"
        assert commit["message"] == message
        assert json.loads(commit["files"]) == files
        # Note: clock.iso() normalizes the timestamp format slightly
        assert committed_at.replace("Z", "+00:00") in commit["committed_at"] or committed_at in commit["committed_at"]
        assert commit["origin"] == "hook"
        
        # Verify queue_entry was created (Requirement 7.1)
        queue_entry = test_db.execute(
            "SELECT * FROM queue_entries WHERE commit_sha = ?", (sha,)
        ).fetchone()
        assert queue_entry is not None
        assert queue_entry["project_id"] == "test-proj"
        assert queue_entry["commit_sha"] == sha
        assert queue_entry["processed"] == 0
        assert queue_entry["processed_at"] is None
        
        # Verify queue file was deleted
        queue_dir = test_repo / ".learn" / "queue"
        assert not (queue_dir / f"{sha}.json").exists()
    
    def test_ingest_handles_duplicate_commits(self, test_db, test_repo, settings):
        """Test that re-ingesting the same commit doesn't create duplicates.
        
        Requirements: 7.1, 31.1
        """
        sha = "duplicate123"
        
        # Write same commit twice
        write_queue_entry(test_repo, sha, "First", ["a.py"], "2024-01-15T10:00:00Z")
        
        # Ingest first time
        stats1 = ingest(test_db, settings, "test-proj", test_repo)
        assert stats1["ingested"] == 1
        
        # Write again
        write_queue_entry(test_repo, sha, "Second", ["b.py"], "2024-01-15T10:01:00Z")
        
        # Ingest second time
        stats2 = ingest(test_db, settings, "test-proj", test_repo)
        assert stats2["duplicates"] == 1
        assert stats2["ingested"] == 0
        
        # Verify only one commit exists
        commits = test_db.execute(
            "SELECT COUNT(*) as count FROM commits WHERE sha = ?", (sha,)
        ).fetchone()
        assert commits["count"] == 1
        
        # Verify only one queue_entry exists
        queue_entries = test_db.execute(
            "SELECT COUNT(*) as count FROM queue_entries WHERE commit_sha = ?", (sha,)
        ).fetchone()
        assert queue_entries["count"] == 1
    
    def test_ingest_handles_malformed_json(self, test_db, test_repo, settings):
        """Test that malformed JSON files are quarantined, not crash.
        
        Requirements: 24.7
        """
        queue_dir = test_repo / ".learn" / "queue"
        bad_file = queue_dir / "badsha123.json"
        bad_file.write_text("{invalid json", encoding="utf-8")
        
        # Ingest should not crash
        stats = ingest(test_db, settings, "test-proj", test_repo)
        
        assert stats["rejected"] == 1
        assert stats["ingested"] == 0
        
        # Verify file was quarantined
        assert not bad_file.exists()
        assert (queue_dir / "badsha123.failed").exists()
    
    def test_ingest_handles_missing_fields(self, test_db, test_repo, settings):
        """Test that files with missing required fields are quarantined.
        
        Requirements: 24.7
        """
        queue_dir = test_repo / ".learn" / "queue"
        incomplete_file = queue_dir / "incomplete123.json"
        incomplete_file.write_text(
            json.dumps({"sha": "incomplete123"}),  # Missing required fields
            encoding="utf-8",
        )
        
        # Ingest should not crash
        stats = ingest(test_db, settings, "test-proj", test_repo)
        
        assert stats["rejected"] == 1
        
        # Verify file was quarantined
        assert not incomplete_file.exists()
        assert (queue_dir / "incomplete123.failed").exists()
    
    def test_ingest_processes_multiple_commits(self, test_db, test_repo, settings):
        """Test that multiple queue files are processed in order."""
        # Create multiple queue files
        commits_data = [
            ("sha1", "Commit 1", ["a.py"], "2024-01-15T10:00:00Z"),
            ("sha2", "Commit 2", ["b.py"], "2024-01-15T10:01:00Z"),
            ("sha3", "Commit 3", ["c.py"], "2024-01-15T10:02:00Z"),
        ]
        
        for sha, message, files, committed_at in commits_data:
            write_queue_entry(test_repo, sha, message, files, committed_at)
        
        # Ingest all
        stats = ingest(test_db, settings, "test-proj", test_repo)
        
        assert stats["ingested"] == 3
        assert stats["duplicates"] == 0
        assert stats["rejected"] == 0
        
        # Verify all commits and queue_entries were created
        for sha, _, _, _ in commits_data:
            commit = test_db.execute(
                "SELECT * FROM commits WHERE sha = ?", (sha,)
            ).fetchone()
            assert commit is not None
            
            queue_entry = test_db.execute(
                "SELECT * FROM queue_entries WHERE commit_sha = ?", (sha,)
            ).fetchone()
            assert queue_entry is not None
            assert queue_entry["processed"] == 0
    
    def test_ingest_respects_file_size_limit(self, test_db, test_repo, settings):
        """Test that oversized queue files are rejected.
        
        Requirements: 24.7
        """
        # Create settings with small file size limit
        small_settings = Settings(
            db_path=":memory:",
            max_queue_files=100,
            max_queue_file_bytes=100,  # 100 bytes limit
            abandon_days=14,
        )
        
        # Create a large queue file
        queue_dir = test_repo / ".learn" / "queue"
        large_file = queue_dir / "large123.json"
        large_data = {
            "sha": "large123",
            "message": "x" * 500,  # Exceeds 100 byte limit
            "files": ["a.py"],
            "committed_at": "2024-01-15T10:00:00Z",
        }
        large_file.write_text(json.dumps(large_data), encoding="utf-8")
        
        # Ingest should reject the file
        stats = ingest(test_db, small_settings, "test-proj", test_repo)
        
        assert stats["rejected"] == 1
        assert stats["ingested"] == 0
        
        # Verify file was quarantined
        assert not large_file.exists()
        assert (queue_dir / "large123.failed").exists()
    
    def test_queue_entry_has_foreign_key_to_commit(self, test_db, test_repo, settings):
        """Test that queue_entry properly references the commit via foreign key.
        
        Requirements: 7.1
        """
        sha = "fk_test_123"
        write_queue_entry(test_repo, sha, "Test FK", ["test.py"], "2024-01-15T10:00:00Z")
        
        # Ingest
        ingest(test_db, settings, "test-proj", test_repo)
        
        # Verify both records exist
        commit = test_db.execute("SELECT * FROM commits WHERE sha = ?", (sha,)).fetchone()
        queue_entry = test_db.execute(
            "SELECT * FROM queue_entries WHERE commit_sha = ?", (sha,)
        ).fetchone()
        
        assert commit is not None
        assert queue_entry is not None
        assert queue_entry["commit_sha"] == commit["sha"]
        
        # Verify foreign key relationship exists
        # Note: CASCADE behavior depends on schema - in this test schema,
        # we're just verifying the FK reference is correct
        assert queue_entry["commit_sha"] == sha
        assert commit["sha"] == sha


class TestQueueEntryTracking:
    """Test that queue entries properly track processing state."""
    
    def test_queue_entry_initially_unprocessed(self, test_db, test_repo, settings):
        """Test that new queue entries have processed=0.
        
        Requirements: 7.1
        """
        sha = "unprocessed123"
        write_queue_entry(test_repo, sha, "Test", ["test.py"], "2024-01-15T10:00:00Z")
        ingest(test_db, settings, "test-proj", test_repo)
        
        queue_entry = test_db.execute(
            "SELECT * FROM queue_entries WHERE commit_sha = ?", (sha,)
        ).fetchone()
        
        assert queue_entry["processed"] == 0
        assert queue_entry["processed_at"] is None
    
    def test_multiple_ingests_same_commit_idempotent(self, test_db, test_repo, settings):
        """Test that ingesting the same commit multiple times is idempotent.
        
        Requirements: 31.1, 31.2
        """
        sha = "idempotent123"
        
        # First ingest
        write_queue_entry(test_repo, sha, "Test", ["test.py"], "2024-01-15T10:00:00Z")
        stats1 = ingest(test_db, settings, "test-proj", test_repo)
        assert stats1["ingested"] == 1
        
        # Verify one queue_entry exists
        count1 = test_db.execute(
            "SELECT COUNT(*) as count FROM queue_entries WHERE commit_sha = ?", (sha,)
        ).fetchone()
        assert count1["count"] == 1
        
        # Try to ingest same commit again
        write_queue_entry(test_repo, sha, "Test", ["test.py"], "2024-01-15T10:00:00Z")
        stats2 = ingest(test_db, settings, "test-proj", test_repo)
        assert stats2["duplicates"] == 1
        
        # Verify still only one queue_entry exists
        count2 = test_db.execute(
            "SELECT COUNT(*) as count FROM queue_entries WHERE commit_sha = ?", (sha,)
        ).fetchone()
        assert count2["count"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
