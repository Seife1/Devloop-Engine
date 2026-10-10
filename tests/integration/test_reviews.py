from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from learnloop.domain.errors import NotFoundError, ValidationError
from learnloop.persistence.db import migrate
from learnloop.services.knowledge_service import register_knowledge_item
from learnloop.services.review_service import (
    record_review,
    review_due,
    snooze_item,
)

NOW = datetime(2026, 3, 1, 10, 0, 0, tzinfo=UTC)


@pytest.fixture
def test_setup(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".learn").mkdir()
    (repo / ".learn" / "concepts.md").write_text("# Concepts\n", encoding="utf-8")

    db_path = tmp_path / "reviews.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    migrate(conn, db_path)

    conn.execute(
        "INSERT INTO projects (id, name, repo_path, created_at) VALUES ('p1', 'Project', ?, '2026-03-01T00:00:00+00:00')",
        (str(repo),),
    )
    conn.execute(
        "INSERT INTO commits (sha, project_id, message, files, committed_at, status, origin)"
        " VALUES ('c_base', 'p1', 'base', '[\"src/auth.py\", \"src/cache.py\", \"src/db.py\", \"src/billing.py\", \"src/a.py\", \"src/b.py\", \"src/c.py\", \"src/d.py\"]', '2026-03-01T00:00:00+00:00', 'verified', 'hook')"
    )
    conn.commit()

    return {"conn": conn, "repo": repo, "project_id": "p1"}


def test_review_due_ordering_and_waiting_count(test_setup: dict):
    conn = test_setup["conn"]
    p_id = test_setup["project_id"]

    # Insert a baseline commit
    conn.execute(
        "INSERT INTO commits (sha, project_id, message, files, committed_at, status, origin)"
        " VALUES ('c1', 'p1', 'init', '[\"src/a.py\", \"src/b.py\", \"src/c.py\", \"src/d.py\"]', '2026-03-01T08:00:00+00:00', 'verified', 'hook')"
    )

    # Register 4 knowledge items
    for key in ("item-a", "item-b", "item-c", "item-d"):
        register_knowledge_item(
            conn,
            project_id=p_id,
            key=key,
            title=f"Title {key}",
            kind="component",
            band="basic",
            summary=f"Summary for {key}",
            files=[f"src/{key[-1]}.py"],
        )

    # item-a: due today at 09:00 (not stale)
    conn.execute(
        "INSERT INTO item_reviews (item_id, interval_days, ease, reps, due_at, last_reviewed_at)"
        " VALUES ((SELECT id FROM knowledge_items WHERE key='item-a'), 1, 2.3, 0, '2026-03-01T09:00:00+00:00', '2026-02-28T09:00:00+00:00')"
    )
    # item-b: due today at 08:00 (older due_at, not stale)
    conn.execute(
        "INSERT INTO item_reviews (item_id, interval_days, ease, reps, due_at, last_reviewed_at)"
        " VALUES ((SELECT id FROM knowledge_items WHERE key='item-b'), 1, 2.3, 0, '2026-03-01T08:00:00+00:00', '2026-02-28T08:00:00+00:00')"
    )
    # item-c: due in 5 days, but STALE (should jump queue and appear FIRST!)
    conn.execute(
        "UPDATE knowledge_items SET status='explained', baseline_commit='c1', baseline_committed_at='2026-03-01T08:00:00+00:00' WHERE key='item-c'"
    )
    conn.execute(
        "INSERT INTO item_reviews (item_id, interval_days, ease, reps, due_at, last_reviewed_at)"
        " VALUES ((SELECT id FROM knowledge_items WHERE key='item-c'), 5, 2.3, 1, '2026-03-06T10:00:00+00:00', '2026-03-01T08:00:00+00:00')"
    )
    # Commit modifying src/c.py at 09:30 makes item-c stale
    conn.execute(
        "INSERT INTO commits (sha, project_id, message, files, committed_at, status, origin)"
        " VALUES ('c2', 'p1', 'touch c', '[\"src/c.py\"]', '2026-03-01T09:30:00+00:00', 'verified', 'hook')"
    )
    # item-d: due today at 09:30
    conn.execute(
        "INSERT INTO item_reviews (item_id, interval_days, ease, reps, due_at, last_reviewed_at)"
        " VALUES ((SELECT id FROM knowledge_items WHERE key='item-d'), 1, 2.3, 0, '2026-03-01T09:30:00+00:00', '2026-02-28T09:30:00+00:00')"
    )
    conn.commit()

    res = review_due(conn, p_id, limit=3, now=NOW)
    items = res["items"]
    # Total due candidates: item-c (stale), item-b (08:00), item-a (09:00), item-d (09:30) = 4 items
    # Limit is 3 -> 3 returned, 1 waiting
    assert len(items) == 3
    assert res["waiting"] == 1

    # Stale item-c must be first!
    assert items[0]["key"] == "item-c"
    assert items[0]["is_stale"] is True

    # Then sorted by due_at: item-b (08:00) before item-a (09:00)
    assert items[1]["key"] == "item-b"
    assert items[2]["key"] == "item-a"

    # Protocol must be included
    assert "Spaced Review Protocol:" in res["protocol"]


def test_record_review_redacts_free_text_secrets(test_setup: dict):
    conn = test_setup["conn"]
    p_id = test_setup["project_id"]

    register_knowledge_item(
        conn,
        project_id=p_id,
        key="auth-service",
        title="Auth Service",
        kind="component",
        band="intermediate",
        summary="Authentication module",
        files=["src/auth.py"],
    )

    fake_secret_q = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"
    fake_secret_a = "sk-proj-1234567890abcdefghijklmnopqrstuvwxyz"

    question_text = f"How does the auth token {fake_secret_q} get validated?"
    learner_text = f"We verify the token against {fake_secret_a} using HMAC."

    rec = record_review(
        conn,
        project_id=p_id,
        key="auth-service",
        question=question_text,
        learner_answer=learner_text,
        score=0.9,
        now=NOW,
    )
    assert rec["created"] is True
    assert rec["concept_log_written"] is True
    assert rec["depth"] == 2  # score >= 0.8 bumps depth from 1 to 2
    assert rec["status"] == "explained"

    # Check question stored in item_questions has secret redacted
    q_row = conn.execute("SELECT * FROM item_questions WHERE item_id=(SELECT id FROM knowledge_items WHERE key='auth-service')").fetchone()
    assert fake_secret_q not in q_row["question"]
    assert "[REDACTED]" in q_row["question"]

    # Check answer stored in explanations has secret redacted
    exp_row = conn.execute("SELECT * FROM explanations WHERE item_id=(SELECT id FROM knowledge_items WHERE key='auth-service')").fetchone()
    assert fake_secret_a not in exp_row["learner_text"]
    assert "[REDACTED]" in exp_row["learner_text"]


def test_record_review_validation_and_depth_bump(test_setup: dict):
    conn = test_setup["conn"]
    p_id = test_setup["project_id"]

    register_knowledge_item(
        conn,
        project_id=p_id,
        key="cache-layer",
        title="Cache Layer",
        kind="component",
        band="basic",
        summary="Redis cache",
        files=["src/cache.py"],
    )

    # Empty answer rejected
    with pytest.raises(ValidationError, match="learner_answer cannot be empty"):
        record_review(
            conn,
            project_id=p_id,
            key="cache-layer",
            question="What cache strategy is used?",
            learner_answer="   ",
            score=0.5,
            now=NOW,
        )

    # Empty question rejected
    with pytest.raises(ValidationError, match="question cannot be empty"):
        record_review(
            conn,
            project_id=p_id,
            key="cache-layer",
            question="   ",
            learner_answer="We use LRU cache.",
            score=0.5,
            now=NOW,
        )

    # Non-existent item rejected
    with pytest.raises(NotFoundError):
        record_review(
            conn,
            project_id=p_id,
            key="non-existent",
            question="What is this?",
            learner_answer="Something",
            score=0.5,
            now=NOW,
        )

    # Low score (< 0.8) does NOT bump depth and marks status 'shaky'
    rec_low = record_review(
        conn,
        project_id=p_id,
        key="cache-layer",
        question="What eviction policy is configured?",
        learner_answer="I am not sure, maybe FIFO?",
        score=0.4,
        now=NOW,
    )
    assert rec_low["depth"] == 1  # Depth stays 1
    assert rec_low["status"] == "shaky"

    # High score (>= 0.8) bumps depth to 2 and marks status 'explained'
    rec_high = record_review(
        conn,
        project_id=p_id,
        key="cache-layer",
        question="What eviction policy is configured?",
        learner_answer="It uses Redis allkeys-lru with maxmemory 2gb.",
        score=0.9,
        now=NOW,
    )
    assert rec_high["depth"] == 2
    assert rec_high["status"] == "explained"


def test_record_review_idempotency(test_setup: dict):
    conn = test_setup["conn"]
    p_id = test_setup["project_id"]

    register_knowledge_item(
        conn,
        project_id=p_id,
        key="db-pool",
        title="DB Pool",
        kind="component",
        band="basic",
        summary="Connection pool",
        files=["src/db.py"],
    )

    # Record first time with review_id=999
    rec1 = record_review(
        conn,
        project_id=p_id,
        key="db-pool",
        question="Why use a connection pool?",
        learner_answer="To reuse database connections and reduce handshake latency.",
        score=0.9,
        review_id=999,
        now=NOW,
    )
    assert rec1["created"] is True
    assert rec1["review_id"] == 999

    # Record second time with same review_id=999
    rec2 = record_review(
        conn,
        project_id=p_id,
        key="db-pool",
        question="Why use a connection pool?",
        learner_answer="To reuse database connections and reduce handshake latency.",
        score=0.9,
        review_id=999,
        now=NOW,
    )
    assert rec2["created"] is False
    assert rec2["review_id"] == 999


def test_snooze_item_removes_from_due(test_setup: dict):
    conn = test_setup["conn"]
    p_id = test_setup["project_id"]

    register_knowledge_item(
        conn,
        project_id=p_id,
        key="billing",
        title="Billing Engine",
        kind="component",
        band="intermediate",
        summary="Stripe webhooks",
        files=["src/billing.py"],
    )
    # Make due today
    conn.execute(
        "INSERT INTO item_reviews (item_id, interval_days, ease, reps, due_at, last_reviewed_at)"
        " VALUES ((SELECT id FROM knowledge_items WHERE key='billing'), 1, 2.3, 0, '2026-03-01T08:00:00+00:00', '2026-02-28T08:00:00+00:00')"
    )
    conn.commit()

    # Before snooze: item is due
    due_before = review_due(conn, p_id, limit=3, now=NOW)
    assert len(due_before["items"]) == 1
    assert due_before["items"][0]["key"] == "billing"

    # Snooze for 7 days
    snooze_res = snooze_item(conn, p_id, key="billing", days=7, now=NOW)
    assert snooze_res["days"] == 7
    assert snooze_res["snoozed_until"] == "2026-03-08T10:00:00+00:00"

    # After snooze: item is NOT due
    due_after = review_due(conn, p_id, limit=3, now=NOW)
    assert len(due_after["items"]) == 0
    assert due_after["waiting"] == 0
