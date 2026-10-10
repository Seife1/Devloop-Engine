from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from learnloop.domain.errors import ValidationError
from learnloop.journal.concept_log import generate_concept_markdown
from learnloop.persistence.db import migrate
from learnloop.services import capture_service, knowledge_service


@pytest.fixture
def conn(tmp_path: Path):
    db_path = tmp_path / "self_rating.db"
    c = sqlite3.connect(db_path)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON")
    migrate(c, db_path)
    yield c
    c.close()


def test_self_rating_recording_and_validation(conn):
    p = capture_service.start_project(conn, "rating-p", "/workspace/rating-p")
    pid = p["id"]

    conn.execute(
        "INSERT INTO commits (sha, project_id, message, files, committed_at, status, origin, kind)"
        " VALUES ('c1', ?, 'init', '[\"f.py\"]', '2026-03-01T00:00:00Z', 'verified', 'hook', 'commit')",
        (pid,),
    )
    conn.commit()

    knowledge_service.register_knowledge_item(
        conn, pid, "k1", "Title 1", "component", "basic", ["f.py"], "summary"
    )

    # Valid rating 1..5
    res = knowledge_service.record_explanation(
        conn, pid, "k1", "My explanation", 0.9, self_rating=4
    )
    assert res["self_rating"] == 4

    # Verification in list_items
    items = knowledge_service.list_items(conn, pid)
    assert len(items["items"]) == 1
    assert items["items"][0]["self_rating"] == 4

    # Invalid ratings reject with ValidationError
    with pytest.raises(ValidationError):
        knowledge_service.record_explanation(
            conn, pid, "k1", "My explanation", 0.9, self_rating=0
        )

    with pytest.raises(ValidationError):
        knowledge_service.record_explanation(
            conn, pid, "k1", "My explanation", 0.9, self_rating=6
        )


def test_self_rating_rendered_in_concept_log(conn):
    p = capture_service.start_project(conn, "rating-log-p", "/workspace/rating-log-p")
    pid = p["id"]

    conn.execute(
        "INSERT INTO commits (sha, project_id, message, files, committed_at, status, origin, kind)"
        " VALUES ('c1', ?, 'init', '[\"app.py\"]', '2026-03-01T00:00:00Z', 'verified', 'hook', 'commit')",
        (pid,),
    )
    conn.commit()

    knowledge_service.register_knowledge_item(
        conn, pid, "comp1", "Component 1", "component", "basic", ["app.py"], "app summary"
    )

    # Explanation with self_rating
    knowledge_service.record_explanation(
        conn, pid, "comp1", "Explain app", 1.0, self_rating=5
    )

    md = generate_concept_markdown(conn, pid)
    assert 'self-rating: 5/5' in md
    assert '- **Latest explanation** (score 1.0, self-rating: 5/5): "Explain app"' in md
