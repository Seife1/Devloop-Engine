from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from learnloop.domain.errors import NotFoundError
from learnloop.persistence.db import migrate
from learnloop.services import capture_service, knowledge_service, readiness_service


@pytest.fixture
def conn(tmp_path: Path):
    db_path = tmp_path / "readiness.db"
    c = sqlite3.connect(db_path)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    migrate(c, db_path)
    yield c
    c.close()


def test_readiness_empty_project(conn):
    p = capture_service.start_project(conn, "test-p", "/workspace/test-p")
    res = readiness_service.get_project_readiness(conn, p["id"])

    assert res["total_items"] == 0
    assert res["stale_count"] == 0
    assert res["due_count"] == 0
    assert res["headline"] == "0 of 0 parts explained"
    assert res["by_band"] == {
        "basic": {"explained": 0, "shaky": 0, "unexplained": 0},
        "intermediate": {"explained": 0, "shaky": 0, "unexplained": 0},
        "advanced": {"explained": 0, "shaky": 0, "unexplained": 0},
    }
    # Strictly count-based: no score, percentage, or mastery keys
    for key in res.keys():
        assert "score" not in key
        assert "percent" not in key
        assert "mastery" not in key


def test_readiness_resolves_default_project(conn):
    capture_service.start_project(conn, "test-p1", "/workspace/test-p1")
    p2 = capture_service.start_project(conn, "test-p2", "/workspace/test-p2")

    # Omitting project_id resolves newest project
    res = readiness_service.get_project_readiness(conn, None)
    assert res["total_items"] == 0
    assert p2["name"] == "test-p2"


def test_readiness_no_projects_raises_not_found(tmp_path: Path):
    db_path = tmp_path / "empty.db"
    c = sqlite3.connect(db_path)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    migrate(c, db_path)
    with pytest.raises(NotFoundError):
        readiness_service.get_project_readiness(c, None)
    c.close()


def test_readiness_counts_and_headline_formatting(conn):
    p = capture_service.start_project(conn, "p", "/repo")
    pid = p["id"]

    # Ingest commits so files are known
    conn.execute(
        "INSERT INTO commits (sha, project_id, message, files, committed_at, status, origin, kind)"
        " VALUES ('c1', ?, 'initial', '[\"a.py\", \"b.py\", \"c.py\"]', '2026-03-01T00:00:00Z', 'verified', 'hook', 'commit')",
        (pid,),
    )
    conn.commit()

    # Register items: 2 basic, 1 intermediate
    knowledge_service.register_knowledge_item(
        conn, pid, "k1", "Title 1", "component", "basic", ["a.py"], "summary"
    )
    knowledge_service.register_knowledge_item(
        conn, pid, "k2", "Title 2", "component", "basic", ["b.py"], "summary"
    )
    knowledge_service.register_knowledge_item(
        conn, pid, "k3", "Title 3", "component", "intermediate", ["c.py"], "summary"
    )

    # 1 explained, 1 shaky, 1 unexplained
    knowledge_service.record_explanation(conn, pid, "k1", "I explain k1", 0.9)
    knowledge_service.record_explanation(conn, pid, "k2", "I explain k2 shaky", 0.5)

    res = readiness_service.get_project_readiness(conn, pid)
    assert res["total_items"] == 3
    assert res["by_band"]["basic"]["explained"] == 1
    assert res["by_band"]["basic"]["shaky"] == 1
    assert res["by_band"]["intermediate"]["unexplained"] == 1
    assert res["stale_count"] == 0
    assert res["due_count"] == 0
    assert res["headline"] == "1 of 3 parts explained"

    # Now make k1 due for review by setting due_at in the past
    conn.execute("UPDATE item_reviews SET due_at='2026-01-01T00:00:00Z'")
    conn.commit()

    res_due = readiness_service.get_project_readiness(conn, pid, now=datetime(2026, 3, 2, tzinfo=UTC))
    assert res_due["due_count"] == 1
    assert res_due["headline"] == "1 of 3 parts explained (1 due for review)"

    # Now make k1 stale by adding newer commit touching a.py
    conn.execute(
        "INSERT INTO commits (sha, project_id, message, files, committed_at, status, origin, kind)"
        " VALUES ('c2', ?, 'update a', '[\"a.py\"]', '2026-03-05T00:00:00Z', 'verified', 'hook', 'commit')",
        (pid,),
    )
    conn.commit()

    res_both = readiness_service.get_project_readiness(conn, pid, now=datetime(2026, 3, 6, tzinfo=UTC))
    assert res_both["stale_count"] == 1
    assert res_both["due_count"] == 1
    assert res_both["headline"] == "1 of 3 parts explained (1 stale, 1 due for review)"
