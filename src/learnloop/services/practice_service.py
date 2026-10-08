"""Records the learner's graded attempts and updates mastery. The agent grades; the server computes."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any

from learnloop.domain import clock, mastery
from learnloop.domain.errors import ValidationError
from learnloop.services.capture_service import validate_skills


def submit_attempt(
    conn: sqlite3.Connection,
    skill: str,
    score: float,
    hints_used: int = 0,
    now: datetime | None = None,
) -> dict[str, Any]:
    validate_skills(conn, [skill])
    if not 0.0 <= score <= 1.0:
        raise ValidationError("score must be between 0.0 and 1.0")
    now = now or clock.utcnow()
    adjusted = mastery.adjust_for_hints(score, hints_used)
    row = conn.execute("SELECT * FROM skill_mastery WHERE skill_id=?", (skill,)).fetchone()
    state = (
        mastery.MasteryState(row["mastery"], row["attempts"], clock.parse(row["updated_at"]))
        if row
        else mastery.MasteryState()
    )
    new = mastery.update(state, adjusted, now)
    conn.execute(
        "INSERT INTO attempts (skill_id, raw_score, hints_used, created_at) VALUES (?,?,?,?)",
        (skill, score, hints_used, clock.iso(now)),
    )
    conn.execute(
        "INSERT INTO skill_mastery (skill_id, mastery, attempts, updated_at) VALUES (?,?,?,?)"
        " ON CONFLICT(skill_id) DO UPDATE SET mastery=excluded.mastery,"
        " attempts=excluded.attempts, updated_at=excluded.updated_at",
        (skill, new.mastery, new.attempts, clock.iso(now)),
    )
    conn.commit()
    return {
        "skill": skill,
        "mastery": round(new.mastery, 2),
        "attempts": new.attempts,
        "confidence": mastery.confidence(new.attempts),
    }
