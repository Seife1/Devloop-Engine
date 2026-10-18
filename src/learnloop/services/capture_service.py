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
from learnloop.domain.path_utils import normalise_path


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def require_project(conn: sqlite3.Connection, project_id: str) -> sqlite3.Row:
    row = conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    if not isinstance(row, sqlite3.Row):
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
    skills: list[str] | None = None,
    summary: str = "",
    rationale: str = "",
    intent_id: str | None = None,
    commit_sha: str | None = None,
    files: list[str] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Declare intent. Idempotent on intent_id so agent retries don't duplicate."""
    require_project(conn, project_id)
    skills_list = skills or []
    if skills_list:
        validate_skills(conn, skills_list)
    normalised_files: list[str] = []
    if files:
        if len(files) > 20:
            raise ValidationError("Provide at most 20 files.")
        normalised_files = list(dict.fromkeys(normalise_path(f) for f in files))

    iid = intent_id or _new_id()
    if conn.execute("SELECT 1 FROM intents WHERE id=?", (iid,)).fetchone():
        return {"intent_id": iid, "created": False}
    conn.execute(
        "INSERT INTO intents (id, project_id, summary, rationale, commit_sha, created_at)"
        " VALUES (?,?,?,?,?,?)",
        (iid, project_id, summary, rationale, commit_sha, clock.iso(now or clock.utcnow())),
    )
    if skills_list:
        conn.executemany(
            "INSERT INTO intent_skills (intent_id, skill_id) VALUES (?,?)",
            [(iid, s) for s in dict.fromkeys(skills_list)],
        )
    if normalised_files:
        conn.executemany(
            "INSERT INTO intent_files (intent_id, path, touched) VALUES (?,?,NULL)",
            [(iid, f) for f in normalised_files],
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


def start_skill_session_v2(
    conn: sqlite3.Connection,
    project_id: str,
    session_id: str,
    intent_description: str,
    files: list[str],
    skills: list[str] | None = None,
    intent_id: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Create intent record using new intent_records schema with session_id.
    
    This is the MCP-native implementation that uses the intent_records table
    with proper session tracking.
    
    Args:
        conn: Database connection
        project_id: Project ID
        session_id: MCP session identifier
        intent_description: What the user intends to implement
        files: List of file paths to be modified (required, non-empty)
        skills: Optional list of skill identifiers
        intent_id: Optional intent ID for idempotency
        now: Optional timestamp for testing
    
    Returns:
        Dict with intent_id, created status, and intent status
    
    Raises:
        ValidationError: If validation fails
    
    Requirements:
        - 4.1: Create IntentRecord when user calls start_skill_session
        - 4.2: Capture intent description, file list, and skills  
        - 4.3: Mark with status "open" upon creation
        - 4.4: Store session_id and timestamp
        - 4.5: Allow multiple open intents per project
        - 4.6: Respond in under 50ms
    """
    require_project(conn, project_id)
    
    # Validate inputs (Requirement 4.2)
    if not intent_description or not intent_description.strip():
        raise ValidationError("intent_description must not be empty")
    
    if not files or len(files) == 0:
        raise ValidationError("files list must not be empty (Requirement 4.2)")
    
    if len(files) > 50:
        raise ValidationError("files list cannot exceed 50 items")
    
    # Normalize inputs
    skills_list = skills or []
    if skills_list:
        validate_skills(conn, skills_list)
    
    normalised_files: list[str] = []
    if files:
        normalised_files = list(dict.fromkeys(normalise_path(f) for f in files))
    
    # Generate or use provided intent ID for idempotency
    iid = intent_id or _new_id()
    
    # Check if already exists (idempotent)
    existing = conn.execute(
        "SELECT id, status FROM intent_records WHERE id=?", (iid,)
    ).fetchone()
    if existing:
        return {"intent_id": iid, "created": False, "status": existing["status"]}
    
    # Create intent with OPEN status (Requirements 4.3, 4.4)
    created_at = clock.iso(now or clock.utcnow())
    conn.execute(
        """
        INSERT INTO intent_records 
        (id, session_id, project_id, intent_description, files_json, skills_json, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            iid,
            session_id,
            project_id,
            intent_description,
            json.dumps(normalised_files),
            json.dumps(skills_list),
            "open",
            created_at,
        ),
    )
    conn.commit()
    
    return {"intent_id": iid, "created": True, "status": "open"}
