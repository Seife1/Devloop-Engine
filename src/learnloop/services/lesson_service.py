"""Assembles a bounded evidence bundle for the agent to teach from. No LLM calls here."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any

from learnloop.domain import clock
from learnloop.domain.errors import NotFoundError
from learnloop.domain.gap_analysis import rank_gaps
from learnloop.domain.teaching import level_for
from learnloop.services import capture_service
from learnloop.services.skill_service import standings

MAX_EVIDENCE = 5
MAX_FILES = 8
MAX_MISTAKES = 5
CLIP = 300

TEACHING_PROTOCOL = """\
Teach the learner ONE skill, using THEIR project's real code. Keep the whole session under ~10 minutes.
1. Read the evidence files named below in the IDE. Teach from what the AI actually wrote,
   not generic examples.
2. Follow `level`: guided = explain first with a worked example, hints allowed;
   standard = ask the learner to predict how it works BEFORE you reveal it;
   challenge = no hints; ask them to write or fix code unaided.
3. If `known_mistakes` is non-empty, target them directly with at least one question.
4. Explain at most 2 concepts, each in under 150 words. Do not lecture.
5. Call create_quiz with 3 questions (each with a reference_answer and 2-4 rubric points).
6. Ask ONE question at a time. WAIT for the learner's own answer. Never answer for them, never reveal the
   reference answer before they respond.
7. Grade each answer 0.0-1.0 against the rubric. Be strict; partial credit only for rubric
   points actually met.
8. Call record_quiz_result with each learner_answer pasted VERBATIM and its score. Add a short
   mistake_pattern ONLY when the learner got something wrong in a repeatable way.
9. Tell the learner the returned mastery WITH its attempts and confidence. Say plainly when confidence is low.
Never submit scores for work the AI did. Never invent learner answers."""


def _clip(s: str, n: int = CLIP) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


def get_teaching_context(
    conn: sqlite3.Connection,
    project_id: str | None = None,
    skill: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or clock.utcnow()
    if project_id:
        capture_service.require_project(conn, project_id)
    rows = standings(conn, project_id, now)
    ranked = rank_gaps(rows, limit=4)

    if skill:
        capture_service.validate_skills(conn, [skill])
        target = next((s for s in rows if s.skill_id == skill), None)
        if target is None:
            raise NotFoundError(
                f"No verified exposure or attempts for {skill!r} yet, so there is nothing from the "
                "learner's projects to teach. Pick a skill from find_gaps."
            )
    elif ranked:
        target = ranked[0]
    else:
        return {
            "skill": None,
            "message": "No gaps right now: nothing with verified exposure lacks demonstrated mastery. "
            "Commit more work (and explain it), or pass `skill` to review something already learned.",
        }

    evidence = []
    params: list[Any] = [target.skill_id]
    sql = (
        "SELECT e.commit_sha, c.message, c.files, i.summary, i.rationale, i.id AS intent_id"
        " FROM events e JOIN commits c ON c.sha = e.commit_sha JOIN intents i ON i.id = e.intent_id"
        " WHERE e.skill_id = ?"
    )
    if project_id:
        sql += " AND e.project_id = ?"
        params.append(project_id)
    sql += " ORDER BY e.created_at DESC LIMIT ?"
    params.append(MAX_EVIDENCE)
    intent_ids = []
    for r in conn.execute(sql, params):
        files = json.loads(r["files"])
        evidence.append(
            {
                "commit": r["commit_sha"][:10],
                "commit_message": _clip(r["message"], 120),
                "files": files[:MAX_FILES],
                "files_truncated": len(files) > MAX_FILES,
                "what_ai_said_it_did": _clip(r["summary"]),
                "why": _clip(r["rationale"]),
            }
        )
        intent_ids.append(r["intent_id"])

    decisions = []
    if intent_ids:
        marks = ",".join("?" * len(intent_ids))
        for d in conn.execute(
            f"SELECT choice, alternatives, tradeoffs FROM decisions WHERE intent_id IN ({marks})"
            " ORDER BY created_at DESC LIMIT 3",
            intent_ids,
        ):
            decisions.append(
                {
                    "choice": _clip(d["choice"], 120),
                    "alternatives_rejected": json.loads(d["alternatives"])[:4],
                    "tradeoffs": _clip(d["tradeoffs"]),
                }
            )

    mistakes = [
        {"pattern": m["pattern"], "times": m["count"], "last_seen": m["last_seen"][:10]}
        for m in conn.execute(
            "SELECT pattern, count, last_seen FROM mistakes WHERE skill_id=?"
            " ORDER BY count DESC, last_seen DESC LIMIT ?",
            (target.skill_id, MAX_MISTAKES),
        )
    ]

    return {
        "skill": {
            "id": target.skill_id,
            "name": target.name,
            "exposure": target.exposure,
            "mastery": None if target.mastery is None else round(target.mastery, 2),
            "attempts": target.attempts,
            "confidence": target.confidence,
        },
        "level": level_for(target.mastery, target.attempts),
        "evidence": evidence,
        "decisions": decisions,
        "known_mistakes": mistakes,
        "other_gaps": [s.skill_id for s in ranked if s.skill_id != target.skill_id][:3],
        "instructions": TEACHING_PROTOCOL,
    }
