"""Reconciliation: join INTENT (agent) with OUTCOME (git). Exposure exists only where both agree.

intent + commit  -> verified, exposure counted
intent only      -> stays open, abandoned after N days, no exposure
commit only      -> 'unexplained', no exposure until the agent explains it
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from typing import Any

from learnloop.capture.skill_mapper import suggest_skills
from learnloop.domain import clock


def _verify(
    conn: sqlite3.Connection, project_id: str, sha: str, intents: list[sqlite3.Row], now: str
) -> None:
    for intent in intents:
        conn.execute("UPDATE intents SET status='verified', commit_sha=? WHERE id=?", (sha, intent["id"]))
        for r in conn.execute(
            "SELECT skill_id FROM intent_skills WHERE intent_id=?", (intent["id"],)
        ).fetchall():
            conn.execute(
                "INSERT OR IGNORE INTO events (project_id, skill_id, commit_sha, intent_id, created_at)"
                " VALUES (?,?,?,?,?)",
                (project_id, r["skill_id"], sha, intent["id"], now),
            )
    conn.execute("UPDATE commits SET status='verified' WHERE sha=?", (sha,))


def reconcile(
    conn: sqlite3.Connection, project_id: str, abandon_days: int = 14, now: datetime | None = None
) -> dict[str, Any]:
    now_dt = now or clock.utcnow()
    now_s = clock.iso(now_dt)
    verified = 0
    commits = conn.execute(
        "SELECT * FROM commits WHERE project_id=? AND status IN ('new','unexplained') ORDER BY committed_at",
        (project_id,),
    ).fetchall()
    for c in commits:
        # 1) explicit link: intent declared this commit_sha
        intents = conn.execute(
            "SELECT * FROM intents WHERE project_id=? AND status='open' AND commit_sha=?",
            (project_id, c["sha"]),
        ).fetchall()
        # 2) otherwise, open unlinked intents declared before the commit (only for new commits)
        if not intents and c["status"] == "new":
            intents = conn.execute(
                "SELECT * FROM intents WHERE project_id=? AND status='open'"
                " AND commit_sha IS NULL AND created_at <= ?",
                (project_id, c["committed_at"]),
            ).fetchall()
        if intents:
            _verify(conn, project_id, c["sha"], intents, now_s)
            verified += 1
        elif c["status"] == "new":
            conn.execute("UPDATE commits SET status='unexplained' WHERE sha=?", (c["sha"],))

    cutoff = clock.iso(now_dt - timedelta(days=abandon_days))
    abandoned = conn.execute(
        "UPDATE intents SET status='abandoned' WHERE project_id=? AND status='open' AND created_at < ?",
        (project_id, cutoff),
    ).rowcount
    conn.commit()

    unexplained = [
        {
            "sha": r["sha"],
            "message": r["message"],
            "suggested_skills": suggest_skills(conn, json.loads(r["files"])),
        }
        for r in conn.execute(
            "SELECT * FROM commits WHERE project_id=? AND status='unexplained' ORDER BY committed_at",
            (project_id,),
        )
    ]
    return {"commits_verified": verified, "intents_abandoned": abandoned, "unexplained": unexplained}
