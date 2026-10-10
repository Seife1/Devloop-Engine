from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from learnloop.persistence.db import migrate
from learnloop.services import briefing_service, capture_service


@pytest.fixture
def conn(tmp_path: Path):
    db_path = tmp_path / "briefing_500.db"
    c = sqlite3.connect(db_path)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    migrate(c, db_path)
    yield c
    c.close()


def test_briefing_with_500_items_stays_under_3kb(conn):
    p = capture_service.start_project(conn, "big-project", "/workspace/big-project")
    pid = p["id"]

    # Insert 500 knowledge items
    items_data = [
        (
            f"k_{i:04d}",
            pid,
            f"key_{i:04d}",
            f"Title {i}",
            "component",
            "basic" if i < 200 else ("intermediate" if i < 400 else "advanced"),
            f"Summary for component {i}",
            "explained" if i % 2 == 0 else "unexplained",
            1,
            "2026-03-01T00:00:00Z",
            "2026-03-01T00:00:00Z",
        )
        for i in range(500)
    ]
    conn.executemany(
        "INSERT INTO knowledge_items (id, project_id, key, title, kind, band, summary, status, depth, created_at, updated_at)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        items_data,
    )
    conn.commit()

    briefing = briefing_service.get_session_briefing(conn, pid)

    assert "readiness" in briefing
    readiness = briefing["readiness"]
    assert readiness["explained"] == 250
    assert readiness["unexplained"] == 250
    assert "250 of 500 parts explained" in readiness["headline"]

    payload_bytes = len(json.dumps(briefing).encode("utf-8"))
    assert payload_bytes <= 3072, f"Briefing payload exceeded 3KB: {payload_bytes} bytes"
