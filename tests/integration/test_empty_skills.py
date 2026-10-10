from __future__ import annotations

import sqlite3
from datetime import UTC
from pathlib import Path

import pytest

from learnloop.persistence.db import migrate
from learnloop.services import capture_service, reconcile_service


@pytest.fixture
def conn(tmp_path: Path):
    db_path = tmp_path / "empty_skills.db"
    c = sqlite3.connect(db_path)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    migrate(c, db_path)
    yield c
    c.close()


def test_start_skill_session_with_empty_skills_reconciles_zero_events(conn):
    p = capture_service.start_project(conn, "daily-proj", "/workspace/daily")
    pid = p["id"]

    from datetime import datetime

    t0 = datetime(2026, 2, 28, tzinfo=UTC)
    res = capture_service.start_skill_session(
        conn,
        project_id=pid,
        skills=[],
        summary="Building daily feature",
        rationale="Client request",
        intent_id="intent-1",
        now=t0,
    )
    assert res["created"] is True

    # Check intent row created
    intent_row = conn.execute("SELECT * FROM intents WHERE id='intent-1'").fetchone()
    assert intent_row["status"] == "open"

    # Check 0 intent_skills rows
    isk = conn.execute("SELECT COUNT(*) FROM intent_skills WHERE intent_id='intent-1'").fetchone()[0]
    assert isk == 0

    # Simulate commit arrival
    conn.execute(
        "INSERT INTO commits (sha, project_id, message, files, committed_at, status, origin, kind)"
        " VALUES ('sha1', ?, 'feat: daily feature', '[\"feature.py\"]', '2026-03-01T00:00:00Z', 'new', 'hook', 'commit')",
        (pid,),
    )
    conn.commit()

    # Reconcile
    reconciled = reconcile_service.reconcile(conn, pid)
    assert reconciled["unexplained"] == []

    # Commit and intent are verified
    c_row = conn.execute("SELECT * FROM commits WHERE sha='sha1'").fetchone()
    assert c_row["status"] == "verified"

    i_row = conn.execute("SELECT * FROM intents WHERE id='intent-1'").fetchone()
    assert i_row["status"] == "verified"
    assert i_row["commit_sha"] == "sha1"

    # Events table has 0 rows (no skills were associated)
    events_count = conn.execute("SELECT COUNT(*) FROM events WHERE project_id=?", (pid,)).fetchone()[0]
    assert events_count == 0
