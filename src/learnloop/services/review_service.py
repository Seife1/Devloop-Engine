"""Spaced repetition review service for knowledge items."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any

from learnloop.capture.redaction import redact
from learnloop.domain import clock
from learnloop.domain.depth import start_depth
from learnloop.domain.errors import NotFoundError, ValidationError
from learnloop.domain.scheduling import (
    calculate_snooze_until,
    initial_schedule,
    update_schedule,
)
from learnloop.domain.staleness import compute_item_staleness
from learnloop.journal.concept_log import regenerate_concept_log
from learnloop.services.capture_service import require_project
from learnloop.services.knowledge_service import _auto_ingest
from learnloop.services.profile_service import get_learner_profile

REVIEW_PROTOCOL = """\
Spaced Review Protocol:
1. Overdue items are simply re-spaced; there is never an urgent backlog or penalty.
2. Ask ONE question at a time and wait for the learner's own verbatim answer.
3. Ask something NEW: review the previously asked questions and vary your angle.
4. Vary question formats: explain, predict, spot-the-bug, "explain to a beginner", \
"defend this to an interviewer", and what-if scenarios.
5. Tune questions to the learner's profile level, target audience, and current depth.
6. Grade fairly from 0.0 to 1.0 against a clear rubric and record with record_review.\
"""


def _ensure_review_schedule(
    conn: sqlite3.Connection,
    item_id: str,
    now: datetime | None = None,
    is_stale: bool = False,
) -> None:
    """Ensure an item_reviews row exists for the given knowledge item."""
    row = conn.execute("SELECT * FROM item_reviews WHERE item_id=?", (item_id,)).fetchone()
    if not row:
        init_st = initial_schedule(now=now, is_stale=is_stale)
        conn.execute(
            "INSERT INTO item_reviews (item_id, interval_days, ease, reps, due_at, last_reviewed_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (
                item_id,
                init_st.interval_days,
                init_st.ease,
                init_st.reps,
                init_st.due_at,
                init_st.last_reviewed_at,
            ),
        )
        conn.commit()


def review_due(
    conn: sqlite3.Connection,
    project_id: str,
    limit: int = 3,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Return at most `limit` due items, ordered with stale items and most overdue first.

    Auto-ingests the project's commit queue before querying.
    `waiting` is returned as a plain integer count with no guilt-inducing wording.
    """
    _auto_ingest(conn, project_id)
    require_project(conn, project_id)
    profile = get_learner_profile(conn)

    now_dt = now or clock.utcnow()
    now_s = clock.iso(now_dt)

    # Get items with their review state
    query = """
    SELECT
      k.id, k.key, k.title, k.summary, k.status, k.depth, k.baseline_commit, k.baseline_committed_at,
      r.interval_days, r.ease, r.reps, r.due_at, r.snoozed_until, r.last_reviewed_at
    FROM knowledge_items k
    LEFT JOIN item_reviews r ON r.item_id = k.id
    WHERE k.project_id = ?
    """
    rows = conn.execute(query, (project_id,)).fetchall()

    # Pre-fetch project commits for staleness check
    commit_rows = conn.execute(
        "SELECT sha, message, committed_at, files FROM commits WHERE project_id=?"
        " AND (origin IS NULL OR origin != 'backfill') ORDER BY committed_at DESC",
        (project_id,),
    ).fetchall()
    commits = []
    for c in commit_rows:
        try:
            flist = json.loads(c["files"])
        except Exception:  # noqa: BLE001
            flist = []
        commits.append(
            {
                "sha": c["sha"],
                "message": c["message"],
                "committed_at": c["committed_at"],
                "files": flist,
            }
        )

    due_candidates: list[dict[str, Any]] = []

    for r in rows:
        item_id = r["id"]

        # Get item files
        file_rows = conn.execute(
            "SELECT path FROM item_files WHERE item_id=? ORDER BY path ASC", (item_id,)
        ).fetchall()
        item_files = [f["path"] for f in file_rows]

        # Check staleness
        is_stale = False
        staleness = compute_item_staleness(
            status=r["status"],
            item_files=item_files,
            baseline_commit=r["baseline_commit"],
            baseline_committed_at=r["baseline_committed_at"],
            commits=commits,
        )
        if staleness is not None:
            is_stale = True

        # Review schedule state
        due_at = r["due_at"]
        snoozed_until = r["snoozed_until"]

        # Check if due:
        # 1. Stale items are due immediately unless snoozed in the future
        # 2. Or due_at <= now_s
        # 3. And not snoozed past now_s
        is_snoozed = snoozed_until is not None and snoozed_until > now_s
        if is_snoozed:
            continue

        item_is_due = is_stale or (due_at is not None and due_at <= now_s)

        if item_is_due:
            # Questions already asked
            q_rows = conn.execute(
                "SELECT question FROM item_questions WHERE item_id=?"
                " ORDER BY created_at DESC, id DESC LIMIT 3",
                (item_id,),
            ).fetchall()
            last_questions = [q["question"] for q in q_rows]

            # Latest explanation
            exp_row = conn.execute(
                "SELECT learner_text FROM explanations WHERE item_id=?"
                " ORDER BY created_at DESC, id DESC LIMIT 1",
                (item_id,),
            ).fetchone()
            last_exp = exp_row["learner_text"][:300] if exp_row else ""

            # Depth to ask: profile level base + item depth progression
            lvl_depth = start_depth(profile["level"])
            current_item_depth = int(r["depth"])
            depth_to_ask = max(lvl_depth, min(5, current_item_depth))

            due_candidates.append(
                {
                    "item_id": item_id,
                    "key": r["key"],
                    "title": r["title"],
                    "summary": r["summary"],
                    "files": item_files,
                    "depth_to_ask": depth_to_ask,
                    "is_stale": is_stale,
                    "due_at": due_at or now_s,
                    "last_questions": last_questions,
                    "last_explanation": last_exp,
                }
            )

    # Sort candidates: stale items first (True > False), then most overdue first (due_at ASC)
    due_candidates.sort(key=lambda x: (not x["is_stale"], x["due_at"], x["key"]))

    clamped_limit = min(max(1, limit), 3)
    selected = due_candidates[:clamped_limit]
    waiting_count = max(0, len(due_candidates) - clamped_limit)

    items = [
        {
            "key": it["key"],
            "title": it["title"],
            "files": it["files"],
            "summary": it["summary"][:160],
            "depth_to_ask": it["depth_to_ask"],
            "is_stale": it["is_stale"],
            "last_questions": it["last_questions"],
            "last_learner_explanation": it["last_explanation"],
        }
        for it in selected
    ]

    return {
        "items": items,
        "waiting": waiting_count,
        "protocol": REVIEW_PROTOCOL,
    }


def record_review(
    conn: sqlite3.Connection,
    project_id: str,
    key: str,
    question: str,
    learner_answer: str,
    score: float,
    review_id: int | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Record the result of a spaced review attempt.

    - Auto-ingests queue.
    - Rejects empty learner_answer.
    - Redacts question and learner_answer before DB write.
    - Idempotent on review_id.
    - Stores the question in item_questions.
    - Reschedules item via domain/scheduling.
    - Bumps depth by 1 (max 5) only if score >= 0.8 at current depth.
    - Sets status to explained (score >= 0.8) or shaky (< 0.8).
    - Regenerates .learn/concepts.md via safe-write path.
    """
    _auto_ingest(conn, project_id)
    project = require_project(conn, project_id)

    cleaned_answer = learner_answer.strip()
    if not cleaned_answer:
        raise ValidationError("learner_answer cannot be empty.")

    cleaned_question = question.strip()
    if not cleaned_question:
        raise ValidationError("question cannot be empty.")

    if not (0.0 <= score <= 1.0):
        raise ValidationError(f"Score must be between 0.0 and 1.0, got {score}")

    item = conn.execute(
        "SELECT * FROM knowledge_items WHERE project_id=? AND key=?", (project_id, key.strip())
    ).fetchone()
    if not item:
        raise NotFoundError(f"Knowledge item with key {key!r} not found in project {project_id!r}.")

    item_id = item["id"]

    # Idempotency check on review_id if provided
    if review_id is not None:
        existing_exp = conn.execute(
            "SELECT * FROM explanations WHERE id=?", (review_id,)
        ).fetchone()
        if existing_exp:
            review_state = conn.execute(
                "SELECT * FROM item_reviews WHERE item_id=?", (item_id,)
            ).fetchone()
            return {
                "review_id": existing_exp["id"],
                "key": item["key"],
                "score": existing_exp["score"],
                "status": item["status"],
                "depth": item["depth"],
                "interval_days": review_state["interval_days"] if review_state else 1,
                "due_at": review_state["due_at"] if review_state else clock.iso(clock.utcnow()),
                "created": False,
                "concept_log_written": True,
            }

    profile = get_learner_profile(conn)
    now_dt = now or clock.utcnow()
    now_s = clock.iso(now_dt)

    # Redact free text before storing
    redacted_question = redact(cleaned_question)
    redacted_answer = redact(cleaned_answer)

    # Status transition
    new_status = "explained" if score >= 0.8 else "shaky"

    # Depth progression rule: bump by 1 (max 5) only after score >= 0.8 at current depth
    current_depth = int(item["depth"])
    if score >= 0.8:
        new_depth = min(5, current_depth + 1)
    else:
        new_depth = current_depth

    # Store question in item_questions
    conn.execute(
        "INSERT INTO item_questions (item_id, question, depth, created_at) VALUES (?, ?, ?, ?)",
        (item_id, redacted_question, current_depth, now_s),
    )

    # Store explanation audit trail in explanations
    if review_id is not None:
        conn.execute(
            "INSERT INTO explanations (id, item_id, audience, depth, learner_text, score, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                review_id,
                item_id,
                profile["audience"],
                new_depth,
                redacted_answer,
                score,
                now_s,
            ),
        )
        saved_review_id = review_id
    else:
        cur = conn.execute(
            "INSERT INTO explanations (item_id, audience, depth, learner_text, score, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (
                item_id,
                profile["audience"],
                new_depth,
                redacted_answer,
                score,
                now_s,
            ),
        )
        saved_review_id = int(cur.lastrowid or 0)

    # Update knowledge item
    conn.execute(
        "UPDATE knowledge_items SET status=?, depth=?, updated_at=? WHERE id=?",
        (new_status, new_depth, now_s, item_id),
    )

    # Update spaced repetition schedule
    review_row = conn.execute("SELECT * FROM item_reviews WHERE item_id=?", (item_id,)).fetchone()
    if review_row:
        sched = update_schedule(
            interval_days=int(review_row["interval_days"]),
            ease=float(review_row["ease"]),
            reps=int(review_row["reps"]),
            score=score,
            now=now_dt,
            is_stale=False,
        )
        conn.execute(
            "UPDATE item_reviews SET interval_days=?, ease=?, reps=?, due_at=?,"
            " snoozed_until=NULL, last_reviewed_at=? WHERE item_id=?",
            (
                sched.interval_days,
                sched.ease,
                sched.reps,
                sched.due_at,
                sched.last_reviewed_at,
                item_id,
            ),
        )
    else:
        init_st = initial_schedule(now=now_dt, is_stale=False)
        sched = update_schedule(
            interval_days=init_st.interval_days,
            ease=init_st.ease,
            reps=init_st.reps,
            score=score,
            now=now_dt,
            is_stale=False,
        )
        conn.execute(
            "INSERT INTO item_reviews"
            " (item_id, interval_days, ease, reps, due_at, snoozed_until, last_reviewed_at)"
            " VALUES (?, ?, ?, ?, ?, NULL, ?)",
            (
                item_id,
                sched.interval_days,
                sched.ease,
                sched.reps,
                sched.due_at,
                sched.last_reviewed_at,
            ),
        )

    conn.commit()

    written = regenerate_concept_log(conn, project_id, project["repo_path"])

    return {
        "review_id": saved_review_id,
        "key": item["key"],
        "status": new_status,
        "depth": new_depth,
        "score": score,
        "interval_days": sched.interval_days,
        "due_at": sched.due_at,
        "created": True,
        "concept_log_written": written,
    }


def snooze_item(
    conn: sqlite3.Connection,
    project_id: str,
    key: str,
    days: int,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Snooze reviews for a knowledge item between 1 and 30 days."""
    _auto_ingest(conn, project_id)
    require_project(conn, project_id)

    item = conn.execute(
        "SELECT id, key FROM knowledge_items WHERE project_id=? AND key=?",
        (project_id, key.strip()),
    ).fetchone()
    if not item:
        raise NotFoundError(f"Knowledge item with key {key!r} not found in project {project_id!r}.")

    item_id = item["id"]
    snooze_ts = calculate_snooze_until(days, now=now)

    _ensure_review_schedule(conn, item_id, now=now)
    conn.execute(
        "UPDATE item_reviews SET snoozed_until=? WHERE item_id=?",
        (snooze_ts, item_id),
    )
    conn.commit()

    return {
        "key": item["key"],
        "snoozed_until": snooze_ts,
        "days": days,
    }
