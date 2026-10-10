from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from learnloop.persistence.db import migrate
from learnloop.services.briefing_service import MAX_PAYLOAD_BYTES, get_session_briefing

NOW = datetime(2026, 3, 1, 10, 0, 0, tzinfo=UTC)


@pytest.fixture
def db_conn(tmp_path: Path):
    db_path = tmp_path / "test_briefing.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    migrate(conn, db_path)
    yield conn
    conn.close()


def test_briefing_suggested_next_tour_when_no_items(db_conn: sqlite3.Connection):
    db_conn.execute(
        "INSERT INTO projects (id, name, repo_path, created_at) VALUES ('p1', 'P1', '/repo', '2026-03-01T09:00:00+00:00')"
    )
    db_conn.commit()

    b = get_session_briefing(db_conn, "p1", now=NOW)
    assert b["suggested_next"] == "tour"
    assert b["due"] == []
    assert b["waiting"] == 0
    # Assert wording: no overdue or backlog keys
    assert "overdue" not in b
    assert "backlog" not in b
    assert "overdue" not in b["changes_since_briefing"]
    assert "backlog" not in b["changes_since_briefing"]


def test_briefing_suggested_next_explain_stale_when_stale_exists(db_conn: sqlite3.Connection):
    db_conn.execute(
        "INSERT INTO projects (id, name, repo_path, created_at) VALUES ('p1', 'P1', '/repo', '2026-03-01T09:00:00+00:00')"
    )
    # Baseline commit
    db_conn.execute(
        "INSERT INTO commits (sha, project_id, message, files, committed_at, status, origin)"
        " VALUES ('c1', 'p1', 'init', '[\"src/core.py\"]', '2026-03-01T09:00:00+00:00', 'verified', 'hook')"
    )
    db_conn.execute(
        "INSERT INTO knowledge_items (id, project_id, key, title, kind, band, summary, status, depth, baseline_commit, baseline_committed_at, created_at, updated_at)"
        " VALUES ('k1', 'p1', 'core', 'Core Engine', 'component', 'basic', 'Core logic', 'explained', 1, 'c1', '2026-03-01T09:00:00+00:00', '2026-03-01T09:00:00+00:00', '2026-03-01T09:00:00+00:00')"
    )
    db_conn.execute("INSERT INTO item_files (item_id, path) VALUES ('k1', 'src/core.py')")
    # Review schedule in future
    db_conn.execute(
        "INSERT INTO item_reviews (item_id, interval_days, ease, reps, due_at, last_reviewed_at)"
        " VALUES ('k1', 10, 2.3, 1, '2026-03-11T10:00:00+00:00', '2026-03-01T09:00:00+00:00')"
    )
    # Newer commit modifying src/core.py makes it stale!
    db_conn.execute(
        "INSERT INTO commits (sha, project_id, message, files, committed_at, status, origin)"
        " VALUES ('c2', 'p1', 'update core', '[\"src/core.py\"]', '2026-03-01T09:30:00+00:00', 'verified', 'hook')"
    )
    db_conn.commit()

    b = get_session_briefing(db_conn, "p1", now=NOW)
    assert b["changes_since_briefing"]["stale_items_count"] == 1
    assert b["suggested_next"] == "explain-stale"


def test_briefing_suggested_next_review_when_due_items_exist(db_conn: sqlite3.Connection):
    db_conn.execute(
        "INSERT INTO projects (id, name, repo_path, created_at) VALUES ('p1', 'P1', '/repo', '2026-03-01T09:00:00+00:00')"
    )
    db_conn.execute(
        "INSERT INTO commits (sha, project_id, message, files, committed_at, status, origin)"
        " VALUES ('c1', 'p1', 'init', '[\"src/core.py\"]', '2026-03-01T09:00:00+00:00', 'verified', 'hook')"
    )
    db_conn.execute(
        "INSERT INTO knowledge_items (id, project_id, key, title, kind, band, summary, status, depth, baseline_commit, baseline_committed_at, created_at, updated_at)"
        " VALUES ('k1', 'p1', 'core', 'Core Engine', 'component', 'basic', 'Core logic', 'explained', 1, 'c1', '2026-03-01T09:00:00+00:00', '2026-03-01T09:00:00+00:00', '2026-03-01T09:00:00+00:00')"
    )
    db_conn.execute("INSERT INTO item_files (item_id, path) VALUES ('k1', 'src/core.py')")
    # Due today
    db_conn.execute(
        "INSERT INTO item_reviews (item_id, interval_days, ease, reps, due_at, last_reviewed_at)"
        " VALUES ('k1', 1, 2.3, 0, '2026-03-01T09:00:00+00:00', '2026-02-28T09:00:00+00:00')"
    )
    db_conn.commit()

    b = get_session_briefing(db_conn, "p1", now=NOW)
    assert b["changes_since_briefing"]["stale_items_count"] == 0
    assert len(b["due"]) == 1
    assert b["suggested_next"] == "review"


def test_briefing_ignores_backfill_commits(db_conn: sqlite3.Connection):
    db_conn.execute(
        "INSERT INTO projects (id, name, repo_path, created_at, last_briefing_at)"
        " VALUES ('p1', 'P1', '/repo', '2026-03-01T00:00:00+00:00', '2026-03-01T01:00:00+00:00')"
    )
    # One real hook commit after last_briefing_at
    db_conn.execute(
        "INSERT INTO commits (sha, project_id, message, files, committed_at, status, origin)"
        " VALUES ('c_real', 'p1', 'feat: real commit', '[\"src/app.py\"]', '2026-03-01T02:00:00+00:00', 'unexplained', 'hook')"
    )
    # Two backfill commits after last_briefing_at
    db_conn.execute(
        "INSERT INTO commits (sha, project_id, message, files, committed_at, status, origin)"
        " VALUES ('c_bf1', 'p1', 'backfill commit 1', '[\"src/app.py\"]', '2026-03-01T03:00:00+00:00', 'unexplained', 'backfill')"
    )
    db_conn.execute(
        "INSERT INTO commits (sha, project_id, message, files, committed_at, status, origin)"
        " VALUES ('c_bf2', 'p1', 'backfill commit 2', '[\"src/app.py\"]', '2026-03-01T04:00:00+00:00', 'new', 'backfill')"
    )
    # One knowledge item to avoid suggested_next = 'tour'
    db_conn.execute(
        "INSERT INTO knowledge_items (id, project_id, key, title, kind, band, summary, status, depth, baseline_commit, baseline_committed_at, created_at, updated_at)"
        " VALUES ('k1', 'p1', 'app', 'App', 'component', 'basic', 'App summary', 'explained', 1, 'c_real', '2026-03-01T02:00:00+00:00', '2026-03-01T00:00:00+00:00', '2026-03-01T00:00:00+00:00')"
    )
    db_conn.execute("INSERT INTO item_files (item_id, path) VALUES ('k1', 'src/other.py')")
    db_conn.commit()

    b = get_session_briefing(db_conn, "p1", now=NOW)
    # Must count only 1 new commit, NOT 3
    assert b["changes_since_briefing"]["new_commits"] == 1
    # Must count only 1 unexplained commit, NOT 2
    assert b["changes_since_briefing"]["unexplained_commits"] == 1
    # Unexplained suggestions must only include c_real
    shas = [s["sha"] for s in b["changes_since_briefing"]["unexplained_suggestions"]]
    assert "c_real"[:7] in shas
    assert "c_bf1"[:7] not in shas


def test_briefing_payload_hard_cap_with_500_items_and_200_commits(db_conn: sqlite3.Connection):
    db_conn.execute(
        "INSERT INTO projects (id, name, repo_path, created_at) VALUES ('p1', 'Scale Project', '/repo', '2026-03-01T00:00:00+00:00')"
    )
    # Insert 200 commits
    commit_rows = [
        (
            f"sha_{i:04d}",
            "p1",
            f"Commit message number {i} with a reasonably detailed description",
            json.dumps([f"src/module_{i % 20}/file_{i}.py", "src/shared.py"]),
            f"2026-03-01T0{i % 10}:00:00+00:00",
            "unexplained" if i % 2 == 0 else "verified",
            "hook",
        )
        for i in range(200)
    ]
    db_conn.executemany(
        "INSERT INTO commits (sha, project_id, message, files, committed_at, status, origin) VALUES (?,?,?,?,?,?,?)",
        commit_rows,
    )

    # Insert 500 knowledge items with review schedules
    item_rows = []
    file_rows = []
    review_rows = []
    for i in range(500):
        item_id = f"item_{i:04d}"
        key = f"key_{i:04d}"
        title = f"Component Title for Item {i:04d}"
        summary = f"Summary of item {i:04d} with plenty of explanation text to test scale cap limits."
        item_rows.append(
            (
                item_id,
                "p1",
                key,
                title,
                "component",
                "basic",
                summary,
                "explained",
                1,
                "sha_0001",
                "2026-03-01T00:00:00+00:00",
                "2026-03-01T00:00:00+00:00",
                "2026-03-01T00:00:00+00:00",
            )
        )
        file_rows.append((item_id, f"src/module_{i % 20}/file_{i}.py"))
        # Make first 20 due today
        due_at = "2026-03-01T08:00:00+00:00" if i < 20 else "2026-03-10T10:00:00+00:00"
        review_rows.append(
            (item_id, 1, 2.3, 0, due_at, "2026-02-28T10:00:00+00:00")
        )

    db_conn.executemany(
        "INSERT INTO knowledge_items (id, project_id, key, title, kind, band, summary, status, depth, baseline_commit, baseline_committed_at, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        item_rows,
    )
    db_conn.executemany("INSERT INTO item_files (item_id, path) VALUES (?, ?)", file_rows)
    db_conn.executemany(
        "INSERT INTO item_reviews (item_id, interval_days, ease, reps, due_at, last_reviewed_at) VALUES (?, ?, ?, ?, ?, ?)",
        review_rows,
    )
    db_conn.commit()

    b = get_session_briefing(db_conn, "p1", now=NOW)
    payload_json = json.dumps(b)
    payload_bytes = len(payload_json.encode("utf-8"))

    # Assert strictly <= MAX_PAYLOAD_BYTES (3072 bytes)
    assert payload_bytes <= MAX_PAYLOAD_BYTES, f"Payload {payload_bytes} exceeded {MAX_PAYLOAD_BYTES} bytes"
    # Assert max 3 items in due
    assert len(b["due"]) <= 3
    # Assert waiting count captures remaining
    assert b["waiting"] >= 17


def test_briefing_updates_last_briefing_at(db_conn: sqlite3.Connection):
    db_conn.execute(
        "INSERT INTO projects (id, name, repo_path, created_at, last_briefing_at)"
        " VALUES ('p1', 'P1', '/repo', '2026-03-01T00:00:00+00:00', NULL)"
    )
    db_conn.commit()

    get_session_briefing(db_conn, "p1", now=NOW)

    row = db_conn.execute("SELECT last_briefing_at FROM projects WHERE id='p1'").fetchone()
    assert row["last_briefing_at"] == "2026-03-01T10:00:00+00:00"


def test_briefing_auto_ingests_queue_before_computing(db_conn: sqlite3.Connection, tmp_path: Path):
    """Prove get_session_briefing ingests the queue first: test commit -> briefing without ingest_queue."""
    from learnloop.capture.queue import write_queue_entry

    repo = tmp_path / "autoingest_repo"
    repo.mkdir()

    # Register project pointing to repo
    db_conn.execute(
        "INSERT INTO projects (id, name, repo_path, created_at, last_briefing_at)"
        " VALUES ('p_auto', 'Auto Ingest Repo', ?, '2026-03-01T08:00:00+00:00', NULL)",
        (str(repo),),
    )
    db_conn.commit()

    # Write commit to queue on disk (simulating post-commit hook)
    sha = "c0ffee1234567890abcdef"
    qfile = write_queue_entry(
        repo=repo,
        sha=sha,
        message="feat: auto ingest commit",
        files=["src/auto.py"],
        committed_at="2026-03-01T09:30:00+00:00",
        origin="hook",
        kind="commit",
    )
    assert qfile.exists()

    # Verify DB does NOT have the commit yet
    assert db_conn.execute("SELECT COUNT(*) FROM commits WHERE sha=?", (sha,)).fetchone()[0] == 0

    # Call get_session_briefing WITHOUT calling ingest_queue
    b = get_session_briefing(db_conn, "p_auto", now=NOW)

    # Prove queue file was ingested and unlinked
    assert not qfile.exists()

    # Prove commit now exists in DB commits table
    commit_row = db_conn.execute("SELECT * FROM commits WHERE sha=?", (sha,)).fetchone()
    assert commit_row is not None
    assert commit_row["message"] == "feat: auto ingest commit"
    assert commit_row["origin"] == "hook"
    assert commit_row["kind"] == "commit"

    # Prove briefing captured it
    assert b["changes_since_briefing"]["new_commits"] == 1
