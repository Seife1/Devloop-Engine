"""INTENT side of capture. Nothing here creates exposure; only reconciliation does."""

from __future__ import annotations

import difflib
import json
import sqlite3
import uuid
from datetime import datetime
from typing import Any

from learnloop.domain import clock
from learnloop.domain.errors import NotFoundError, ValidationError


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def require_project(conn: sqlite3.Connection, project_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    if row is None:
        raise NotFoundError(f"Unknown project_id {project_id!r}. Call start_project first.")
    return row


def validate_skills(conn: sqlite3.Connection, skills: list[str]) -> None:
    known = [r["id"] for r in conn.execute("SELECT id FROM skills")]
    unknown = [s for s in skills if s not in known]
    if unknown:
        hints = {u: difflib.get_close_matches(u, known, n=3) for u in unknown}
        raise ValidationError(f"Unknown skill id(s): {hints}. Use ids from the skill taxonomy.")


def start_project(
    conn: sqlite3.Connection, name: str, repo_path: str, now: datetime | None = None
) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM projects WHERE repo_path=?", (repo_path,)).fetchone()
    if row:
        return {**dict(row), "created": False}
    pid = _new_id()
    created = clock.iso(now or clock.utcnow())
    conn.execute(
        "INSERT INTO projects (id, name, repo_path, created_at) VALUES (?,?,?,?)",
        (pid, name, repo_path, created),
    )
    conn.commit()
    return {"id": pid, "name": name, "repo_path": repo_path, "created_at": created, "created": True}


def start_skill_session(
    conn: sqlite3.Connection,
    project_id: str,
    skills: list[str],
    summary: str,
    rationale: str,
    intent_id: str | None = None,
    commit_sha: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Declare intent. Idempotent on intent_id so agent retries don't duplicate."""
    require_project(conn, project_id)
    if not skills:
        raise ValidationError("Provide at least one skill id.")
    validate_skills(conn, skills)
    iid = intent_id or _new_id()
    if conn.execute("SELECT 1 FROM intents WHERE id=?", (iid,)).fetchone():
        return {"intent_id": iid, "created": False}
    conn.execute(
        "INSERT INTO intents (id, project_id, summary, rationale, commit_sha, created_at)"
        " VALUES (?,?,?,?,?,?)",
        (iid, project_id, summary, rationale, commit_sha, clock.iso(now or clock.utcnow())),
    )
    conn.executemany(
        "INSERT INTO intent_skills (intent_id, skill_id) VALUES (?,?)",
        [(iid, s) for s in dict.fromkeys(skills)],
    )
    conn.commit()
    return {"intent_id": iid, "created": True, "status": "open"}


def log_decision(
    conn: sqlite3.Connection,
    project_id: str,
    choice: str,
    alternatives: list[str],
    tradeoffs: str,
    intent_id: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    require_project(conn, project_id)
    did = _new_id()
    conn.execute(
        "INSERT INTO decisions (id, project_id, intent_id, choice, alternatives, tradeoffs, created_at)"
        " VALUES (?,?,?,?,?,?,?)",
        (
            did,
            project_id,
            intent_id,
            choice,
            json.dumps(alternatives),
            tradeoffs,
            clock.iso(now or clock.utcnow()),
        ),
    )
    conn.commit()
    return {"decision_id": did}


def flag_misunderstanding(
    conn: sqlite3.Connection,
    skill: str,
    pattern: str,
    confidence: str = "medium",
    now: datetime | None = None,
) -> dict[str, Any]:
    """Record a recurring mistake. Counts accumulate per (skill, pattern)."""
    validate_skills(conn, [skill])
    if confidence not in ("low", "medium", "high"):
        raise ValidationError("confidence must be low, medium or high")
    pattern = " ".join(pattern.split())
    conn.execute(
        "INSERT INTO mistakes (skill_id, pattern, confidence, last_seen) VALUES (?,?,?,?)"
        " ON CONFLICT(skill_id, pattern) DO UPDATE SET count = count + 1,"
        " last_seen = excluded.last_seen, confidence = excluded.confidence",
        (skill, pattern, confidence, clock.iso(now or clock.utcnow())),
    )
    conn.commit()
    row = conn.execute(
        "SELECT count FROM mistakes WHERE skill_id=? AND pattern=?", (skill, pattern)
    ).fetchone()
    return {"skill": skill, "pattern": pattern, "count": row["count"]}
