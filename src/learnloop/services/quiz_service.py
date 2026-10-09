"""Quizzes: the agent writes questions + rubric; the learner answers; the agent grades.
The server stores everything and is the only thing that moves mastery.

One quiz = ONE mastery attempt (mean score), so confidence reflects independent quizzes,
not how many questions were asked in a single sitting."""

from __future__ import annotations

import json
import math
import sqlite3
import uuid
from datetime import datetime
from typing import Any

from learnloop.domain import clock, mastery
from learnloop.domain.errors import NotFoundError, ValidationError
from learnloop.domain.path_utils import normalise_path
from learnloop.domain.teaching import level_for
from learnloop.services import capture_service, practice_service
from learnloop.services.skill_service import standings


def create_quiz(
    conn: sqlite3.Connection,
    skill: str,
    questions: list[dict[str, Any]],
    project_id: str | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    capture_service.validate_skills(conn, [skill])
    if project_id:
        capture_service.require_project(conn, project_id)
    if not 1 <= len(questions) <= 6:
        raise ValidationError("A quiz needs 1 to 6 questions.")

    # Find verified candidate files for this skill (scoped to project_id if given)
    query = (
        "SELECT c.files FROM events e JOIN commits c ON c.sha = e.commit_sha WHERE e.skill_id = ?"
    )
    params: list[Any] = [skill]
    if project_id:
        query += " AND e.project_id = ?"
        params.append(project_id)
    rows = conn.execute(query, params).fetchall()
    has_verified = len(rows) > 0
    candidate_files: set[str] = set()
    for r in rows:
        candidate_files.update(json.loads(r["files"]))
    sorted_candidates = sorted(candidate_files)

    processed_questions = []
    grounded_count = 0
    generic_count = 0
    for q in questions:
        sf = q.get("source_file")
        if sf is not None and str(sf).strip():
            normalised_sf = normalise_path(str(sf))
            if normalised_sf not in candidate_files:
                candidates_preview = sorted_candidates[:8]
                raise ValidationError(
                    f"Question source_file {sf!r} does not appear in verified commits for {skill!r}. "
                    f"Valid candidate files: {candidates_preview}"
                )
            grounding = "project"
            grounded_count += 1
            source_file_val: str | None = normalised_sf
        else:
            grounding = "generic"
            generic_count += 1
            source_file_val = None
        processed_questions.append({**q, "source_file": source_file_val, "grounding": grounding})

    if has_verified:
        required_grounded = math.ceil(len(questions) / 2)
        if grounded_count < required_grounded:
            candidates_preview = sorted_candidates[:8]
            raise ValidationError(
                f"At least {required_grounded} of {len(questions)} questions must be grounded with "
                f"source_file from the learner's code (got {grounded_count}). "
                f"Pick files from: {candidates_preview}"
            )

    s = next((x for x in standings(conn) if x.skill_id == skill), None)
    level = level_for(s.mastery, s.attempts) if s else "guided"
    qid = uuid.uuid4().hex[:12]
    conn.execute(
        "INSERT INTO quizzes (id, skill_id, project_id, level, created_at) VALUES (?,?,?,?,?)",
        (qid, skill, project_id, level, clock.iso(now or clock.utcnow())),
    )
    conn.executemany(
        "INSERT INTO quiz_questions "
        "(quiz_id, ordinal, kind, prompt, reference_answer, rubric, source_file, grounding) "
        "VALUES (?,?,?,?,?,?,?,?)",
        [
            (
                qid,
                i,
                q["kind"],
                q["prompt"],
                q["reference_answer"],
                json.dumps(q["rubric"]),
                q["source_file"],
                q["grounding"],
            )
            for i, q in enumerate(processed_questions, start=1)
        ],
    )
    conn.commit()
    return {
        "quiz_id": qid,
        "questions": len(questions),
        "level": level,
        "grounded": grounded_count,
        "generic": generic_count,
    }


def record_quiz_result(
    conn: sqlite3.Connection,
    quiz_id: str,
    results: list[dict[str, Any]],
    now: datetime | None = None,
) -> dict[str, Any]:
    quiz = conn.execute("SELECT * FROM quizzes WHERE id=?", (quiz_id,)).fetchone()
    if quiz is None:
        raise NotFoundError(f"Unknown quiz_id {quiz_id!r}. Call create_quiz first.")
    if quiz["status"] == "recorded":
        raise ValidationError("This quiz was already recorded; create a new quiz to try again.")

    expected = {
        r["ordinal"] for r in conn.execute("SELECT ordinal FROM quiz_questions WHERE quiz_id=?", (quiz_id,))
    }
    got = [r["ordinal"] for r in results]
    if set(got) != expected or len(got) != len(expected):
        raise ValidationError(
            f"Provide exactly one result per question; expected ordinals "
            f"{sorted(expected)}, got {sorted(got)}."
        )
    for r in results:
        if not r["learner_answer"].strip():
            raise ValidationError(
                f"Question {r['ordinal']}: learner_answer is empty. Record the learner's own answer "
                "verbatim; a score without an answer is not accepted."
            )

    now = now or clock.utcnow()
    now_s = clock.iso(now)
    raw = sum(r["score"] for r in results) / len(results)
    adjusted = sum(mastery.adjust_for_hints(r["score"], r["hints_used"]) for r in results) / len(results)
    hints = sum(r["hints_used"] for r in results)

    conn.executemany(
        "INSERT INTO quiz_answers (quiz_id, ordinal, learner_answer, score, hints_used, created_at)"
        " VALUES (?,?,?,?,?,?)",
        [(quiz_id, r["ordinal"], r["learner_answer"], r["score"], r["hints_used"], now_s) for r in results],
    )
    outcome = practice_service.record_attempt(conn, quiz["skill_id"], raw, adjusted, hints, now, quiz_id)
    conn.execute("UPDATE quizzes SET status='recorded' WHERE id=?", (quiz_id,))
    conn.commit()

    flagged = []
    for r in results:
        if r.get("mistake_pattern") and r["score"] < 0.7:
            flagged.append(
                capture_service.flag_misunderstanding(
                    conn, quiz["skill_id"], r["mistake_pattern"], "medium", now
                )
            )
    grounded = conn.execute(
        "SELECT COUNT(*) FROM quiz_questions WHERE quiz_id=? AND grounding='project'", (quiz_id,)
    ).fetchone()[0]
    generic = conn.execute(
        "SELECT COUNT(*) FROM quiz_questions WHERE quiz_id=? AND grounding='generic'", (quiz_id,)
    ).fetchone()[0]
    return {
        **outcome,
        "quiz_score": round(raw, 2),
        "mistakes_recorded": len(flagged),
        "grounded": grounded,
        "generic": generic,
    }
