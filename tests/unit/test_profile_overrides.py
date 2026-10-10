from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from learnloop.persistence.db import migrate
from learnloop.services import briefing_service, capture_service, profile_service, tour_service


@pytest.fixture
def conn(tmp_path: Path):
    db_path = tmp_path / "profile_override.db"
    c = sqlite3.connect(db_path)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    migrate(c, db_path)
    yield c
    c.close()


def test_profile_project_override(conn):
    p1 = capture_service.start_project(conn, "proj1", "/workspace/proj1")
    p2 = capture_service.start_project(conn, "proj2", "/workspace/proj2")

    # Global profile defaults to beginner, self, 5
    glob = profile_service.get_learner_profile(conn)
    assert glob["level"] == "beginner"
    assert glob["audience"] == "self"

    # Set project override for p1
    res1 = profile_service.set_learner_profile(
        conn, project_id=p1["id"], level="senior", audience="tech-lead"
    )
    assert res1["level"] == "senior"
    assert res1["audience"] == "tech-lead"
    assert res1["project_id"] == p1["id"]

    # p1 gets effective override
    eff1 = profile_service.get_effective_profile(conn, p1["id"])
    assert eff1["level"] == "senior"
    assert eff1["audience"] == "tech-lead"

    # p2 still gets global profile
    eff2 = profile_service.get_effective_profile(conn, p2["id"])
    assert eff2["level"] == "beginner"
    assert eff2["audience"] == "self"

    # Tour for p1 sees the senior profile
    tour1 = tour_service.get_project_tour(conn, p1["id"])
    assert tour1["learner_profile"]["level"] == "senior"

    # Briefing for p1 uses the override
    brief1 = briefing_service.get_session_briefing(conn, p1["id"])
    assert brief1["project_id"] == p1["id"]
