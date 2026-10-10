from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from learnloop.persistence.db import migrate
from learnloop.services import (
    briefing_service,
    capture_service,
    knowledge_service,
    profile_service,
    readiness_service,
    tour_service,
)


@pytest.fixture
def conn(tmp_path: Path):
    db_path = tmp_path / "isolation.db"
    c = sqlite3.connect(db_path)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    migrate(c, db_path)
    yield c
    c.close()


def test_two_project_complete_isolation(conn):
    p_a = capture_service.start_project(conn, "project-alpha", "/workspace/alpha")
    p_b = capture_service.start_project(conn, "project-beta", "/workspace/beta")
    id_a = p_a["id"]
    id_b = p_b["id"]

    # Commits for project A
    conn.execute(
        "INSERT INTO commits (sha, project_id, message, files, committed_at, status, origin, kind)"
        " VALUES ('sha_a1', ?, 'alpha commit', '[\"main.py\"]', '2026-03-01T00:00:00Z', 'verified', 'hook', 'commit')",
        (id_a,),
    )
    # Commits for project B
    conn.execute(
        "INSERT INTO commits (sha, project_id, message, files, committed_at, status, origin, kind)"
        " VALUES ('sha_b1', ?, 'beta commit', '[\"app.py\"]', '2026-03-01T00:00:00Z', 'verified', 'hook', 'commit')",
        (id_b,),
    )
    conn.commit()

    # Knowledge items in A
    knowledge_service.register_knowledge_item(
        conn, id_a, "alpha_comp", "Alpha Comp", "component", "basic", ["main.py"], "Alpha summary"
    )
    # Knowledge items in B
    knowledge_service.register_knowledge_item(
        conn, id_b, "beta_comp", "Beta Comp", "component", "advanced", ["app.py"], "Beta summary"
    )

    # 1. Verify list_items isolation
    items_a = knowledge_service.list_items(conn, id_a)
    assert items_a["count"] == 1
    assert items_a["items"][0]["key"] == "alpha_comp"

    items_b = knowledge_service.list_items(conn, id_b)
    assert items_b["count"] == 1
    assert items_b["items"][0]["key"] == "beta_comp"

    # 2. Profile overrides isolation
    profile_service.set_learner_profile(conn, project_id=id_a, level="senior", audience="tech-lead")
    profile_service.set_learner_profile(conn, project_id=id_b, level="school", audience="classmate")

    prof_a = profile_service.get_effective_profile(conn, id_a)
    prof_b = profile_service.get_effective_profile(conn, id_b)
    assert prof_a["level"] == "senior"
    assert prof_a["audience"] == "tech-lead"
    assert prof_b["level"] == "school"
    assert prof_b["audience"] == "classmate"

    # 3. Explain item in A only
    knowledge_service.record_explanation(conn, id_a, "alpha_comp", "Explain alpha", 1.0, self_rating=5)

    readiness_a = readiness_service.get_project_readiness(conn, id_a)
    assert readiness_a["total_items"] == 1
    assert readiness_a["by_band"]["basic"]["explained"] == 1
    assert readiness_a["headline"] == "1 of 1 parts explained"

    readiness_b = readiness_service.get_project_readiness(conn, id_b)
    assert readiness_b["total_items"] == 1
    assert readiness_b["by_band"]["advanced"]["unexplained"] == 1
    assert readiness_b["headline"] == "0 of 1 parts explained"

    # 4. Tour isolation
    tour_a = tour_service.get_project_tour(conn, id_a)
    assert "main.py" in tour_a["entry_point_candidates"]
    assert "app.py" not in tour_a["entry_point_candidates"]
    assert len(tour_a["items_by_band"]["basic"]) == 1
    assert len(tour_a["items_by_band"]["advanced"]) == 0

    tour_b = tour_service.get_project_tour(conn, id_b)
    assert "app.py" in tour_b["entry_point_candidates"]
    assert "main.py" not in tour_b["entry_point_candidates"]
    assert len(tour_b["items_by_band"]["basic"]) == 0
    assert len(tour_b["items_by_band"]["advanced"]) == 1

    # 5. Briefing isolation
    briefing_a = briefing_service.get_session_briefing(conn, id_a)
    assert briefing_a["project_id"] == id_a
    assert briefing_a["readiness"]["explained"] == 1

    briefing_b = briefing_service.get_session_briefing(conn, id_b)
    assert briefing_b["project_id"] == id_b
    assert briefing_b["readiness"]["explained"] == 0
