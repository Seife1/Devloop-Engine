"""Read model: exposure (from verified events) next to mastery (from the learner's attempts)."""

from __future__ import annotations

import difflib
import re
import sqlite3
from datetime import datetime
from typing import Any

from learnloop.domain import clock
from learnloop.domain.errors import ValidationError
from learnloop.domain.gap_analysis import SkillStanding, priority, rank_gaps
from learnloop.domain.mastery import MasteryState, effective_mastery

_SKILL_ID_RE = re.compile(r"^[a-z][a-z0-9_-]*(\.[a-z][a-z0-9_-]*){1,3}$")

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


def propose_skill(
    conn: sqlite3.Connection,
    id: str,
    name: str,
    rationale: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    if not isinstance(id, str) or not _SKILL_ID_RE.match(id):
        raise ValidationError(
            f"Invalid skill id {id!r}. Must match '^[a-z][a-z0-9_-]*(\\.[a-z][a-z0-9_-]*){{1,3}}$' "
            "(2 to 4 dot-separated lowercase alphanumeric segments; new root skills are not allowed)."
        )
    if not isinstance(name, str) or not name.strip():
        raise ValidationError("Name cannot be empty.")
    if len(name) > 80:
        raise ValidationError(f"Name exceeds 80 characters ({len(name)} chars).")

    if not isinstance(rationale, str) or not rationale.strip():
        raise ValidationError("Rationale cannot be empty.")
    if len(rationale) > 300:
        raise ValidationError(f"Rationale exceeds 300 characters ({len(rationale)} chars).")

    existing = conn.execute("SELECT * FROM skills WHERE id=?", (id,)).fetchone()
    if existing:
        if existing["name"] == name and existing["rationale"] == rationale:
            return {"id": id, "name": name, "source": existing["source"], "created": False}
        raise ValidationError(f"Skill {id!r} already exists.")

    parent_id = id.rsplit(".", 1)[0]
    parent = conn.execute("SELECT 1 FROM skills WHERE id=?", (parent_id,)).fetchone()
    if not parent:
        raise ValidationError(
            f"Parent skill {parent_id!r} does not exist. A proposed skill must have an existing parent."
        )

    siblings = conn.execute("SELECT id, name FROM skills WHERE parent_id=?", (parent_id,)).fetchall()
    short_id = id.rsplit(".", 1)[-1].lower()
    for sib in siblings:
        ratio_id = difflib.SequenceMatcher(None, id.lower(), sib["id"].lower()).ratio()
        short_sib_id = sib["id"].rsplit(".", 1)[-1].lower()
        ratio_short = difflib.SequenceMatcher(None, short_id, short_sib_id).ratio()
        ratio_name = difflib.SequenceMatcher(None, name.lower(), sib["name"].lower()).ratio()

        if max(ratio_id, ratio_short, ratio_name) >= 0.85:
            raise ValidationError(
                f"Skill proposal {id!r} is too similar to existing skill {sib['id']!r} ({sib['name']!r}). "
                f"Use {sib['id']!r} instead."
            )

    now_dt = now or clock.utcnow()
    today_prefix = now_dt.strftime("%Y-%m-%d")
    count_today = conn.execute(
        "SELECT COUNT(*) FROM skills WHERE source='proposed' AND proposed_at LIKE ?",
        (f"{today_prefix}%",),
    ).fetchone()[0]
    if count_today >= 5:
        raise ValidationError("Daily limit reached: maximum 5 skill proposals per UTC day.")

    now_s = clock.iso(now_dt)
    conn.execute(
        "INSERT INTO skills (id, name, parent_id, source, proposed_at, rationale) VALUES (?,?,?,?,?,?)",
        (id, name, parent_id, "proposed", now_s, rationale),
    )
    conn.commit()
    return {"id": id, "name": name, "source": "proposed", "created": True}
