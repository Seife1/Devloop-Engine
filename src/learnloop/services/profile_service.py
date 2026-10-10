"""Learner profile service. Manages singleton learner preferences."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any

from learnloop.domain import clock
from learnloop.domain.errors import ValidationError

VALID_LEVELS = {"school", "beginner", "junior", "mid", "senior"}
VALID_GOALS = {"learn", "interview", "both"}
VALID_AUDIENCES = {"self", "classmate", "recruiter", "tech-lead"}


def get_learner_profile(conn: sqlite3.Connection) -> dict[str, Any]:
    """Retrieve the singleton learner profile (id=1), creating default if absent."""
    row = conn.execute("SELECT * FROM learner_profile WHERE id=1").fetchone()
    if row:
        return {
            "level": row["level"],
            "goal": row["goal"],
            "session_minutes": row["session_minutes"],
            "audience": row["audience"],
            "updated_at": row["updated_at"],
        }
    now_s = clock.iso(clock.utcnow())
    conn.execute(
        "INSERT OR IGNORE INTO learner_profile (id, level, goal, session_minutes, audience, updated_at)"
        " VALUES (1, 'beginner', 'both', 5, 'self', ?)",
        (now_s,),
    )
    conn.commit()
    return {
        "level": "beginner",
        "goal": "both",
        "session_minutes": 5,
        "audience": "self",
        "updated_at": now_s,
    }


def get_effective_profile(conn: sqlite3.Connection, project_id: str) -> dict[str, Any]:
    """Retrieve effective learner profile for a project (override if present, else global)."""
    global_profile = get_learner_profile(conn)
    row = conn.execute("SELECT * FROM project_profile WHERE project_id=?", (project_id,)).fetchone()
    if not row:
        return global_profile
    effective = dict(global_profile)
    for k in ("level", "goal", "audience", "session_minutes"):
        if row[k] is not None:
            effective[k] = row[k]
    effective["updated_at"] = row["updated_at"]
    return effective


def set_learner_profile(
    conn: sqlite3.Connection,
    level: str | None = None,
    goal: str | None = None,
    session_minutes: int | None = None,
    audience: str | None = None,
    project_id: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Partially update learner profile with validation.

    If project_id is given, updates or creates a project-level override.
    Otherwise updates global profile (id=1).
    """
    if project_id is not None:
        from learnloop.services.capture_service import require_project

        require_project(conn, project_id)
        current = get_effective_profile(conn, project_id)
    else:
        current = get_learner_profile(conn)

    new_level = level.strip().lower() if level is not None else current["level"]
    if new_level not in VALID_LEVELS:
        raise ValidationError(f"Invalid level {level!r}. Expected one of: {sorted(VALID_LEVELS)}")

    new_goal = goal.strip().lower() if goal is not None else current["goal"]
    if new_goal not in VALID_GOALS:
        raise ValidationError(f"Invalid goal {goal!r}. Expected one of: {sorted(VALID_GOALS)}")

    new_session_minutes = session_minutes if session_minutes is not None else current["session_minutes"]
    if not (3 <= new_session_minutes <= 30):
        raise ValidationError(
            f"Invalid session_minutes {session_minutes}. Must be between 3 and 30 minutes."
        )

    new_audience = audience.strip().lower() if audience is not None else current["audience"]
    if new_audience not in VALID_AUDIENCES:
        raise ValidationError(
            f"Invalid audience {audience!r}. Expected one of: {sorted(VALID_AUDIENCES)}"
        )

    now_s = clock.iso(now or clock.utcnow())

    if project_id is not None:
        conn.execute(
            """
            INSERT INTO project_profile (project_id, level, goal, session_minutes, audience, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(project_id) DO UPDATE SET
                level=excluded.level,
                goal=excluded.goal,
                session_minutes=excluded.session_minutes,
                audience=excluded.audience,
                updated_at=excluded.updated_at
            """,
            (project_id, new_level, new_goal, new_session_minutes, new_audience, now_s),
        )
        conn.commit()
        return {
            "project_id": project_id,
            "level": new_level,
            "goal": new_goal,
            "session_minutes": new_session_minutes,
            "audience": new_audience,
            "updated_at": now_s,
        }

    conn.execute(
        "UPDATE learner_profile SET level=?, goal=?, session_minutes=?, audience=?, updated_at=? WHERE id=1",
        (new_level, new_goal, new_session_minutes, new_audience, now_s),
    )
    conn.commit()

    return {
        "level": new_level,
        "goal": new_goal,
        "session_minutes": new_session_minutes,
        "audience": new_audience,
        "updated_at": now_s,
    }
