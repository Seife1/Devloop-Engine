"""Read model: exposure (from verified events) next to mastery (from the learner's attempts)."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any

from learnloop.domain import clock
from learnloop.domain.gap_analysis import SkillStanding, priority, rank_gaps
from learnloop.domain.mastery import MasteryState, effective_mastery

_QUERY = """
SELECT s.id, s.name,
  (SELECT COUNT(*) FROM events e WHERE e.skill_id = s.id
     AND (:pid IS NULL OR e.project_id = :pid)) AS exposure,
  m.mastery, m.attempts, m.updated_at
FROM skills s LEFT JOIN skill_mastery m ON m.skill_id = s.id
"""


def standings(
    conn: sqlite3.Connection, project_id: str | None = None, now: datetime | None = None
) -> list[SkillStanding]:
    now = now or clock.utcnow()
    out: list[SkillStanding] = []
    for r in conn.execute(_QUERY, {"pid": project_id}):
        attempts = r["attempts"] or 0
        mastery: float | None = None
        if attempts:
            mastery = effective_mastery(
                MasteryState(r["mastery"], attempts, clock.parse(r["updated_at"])), now
            )
        if r["exposure"] or attempts:
            out.append(SkillStanding(r["id"], r["name"], r["exposure"], mastery, attempts))
    return out


def _view(s: SkillStanding) -> dict[str, Any]:
    return {
        "skill": s.skill_id,
        "name": s.name,
        "exposure": s.exposure,
        "mastery": None if s.mastery is None else round(s.mastery, 2),
        "attempts": s.attempts,
        "confidence": s.confidence,
        "status": s.status,
    }


def get_skill_map(
    conn: sqlite3.Connection,
    project_id: str | None = None,
    limit: int = 10,
    now: datetime | None = None,
) -> dict[str, Any]:
    rows = sorted(standings(conn, project_id, now), key=lambda s: s.exposure, reverse=True)
    return {"skills": [_view(s) for s in rows[:limit]], "total": len(rows), "truncated": len(rows) > limit}


def find_gaps(
    conn: sqlite3.Connection,
    project_id: str | None = None,
    limit: int = 5,
    now: datetime | None = None,
) -> dict[str, Any]:
    ranked = rank_gaps(standings(conn, project_id, now), limit)
    return {"gaps": [{**_view(s), "priority": round(priority(s), 2)} for s in ranked]}
