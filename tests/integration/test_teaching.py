import json
from datetime import UTC, datetime, timedelta

import pytest

from learnloop.domain.errors import NotFoundError, ValidationError
from learnloop.services import capture_service as cap
from learnloop.services import lesson_service, quiz_service, reconcile_service, skill_service

T0 = datetime(2026, 3, 1, 10, 0, tzinfo=UTC)
Q = [
    {"kind": "predict", "prompt": f"q{i}", "reference_answer": "a", "rubric": ["p1", "p2"]} for i in range(3)
]


@pytest.fixture
def project(conn, tmp_path):
    return cap.start_project(conn, "demo", str(tmp_path), now=T0)


def add_verified(conn, project, sha, skill, minutes, files=("tests/test_a.py",), summary="mock http"):
    at = T0 + timedelta(minutes=minutes)
    cap.start_skill_session(
        conn,
        project["id"],
        [skill],
        summary,
        "avoid network",
        intent_id=f"i-{sha}",
        now=at - timedelta(minutes=1),
    )
    conn.execute(
        "INSERT INTO commits (sha, project_id, message, files, committed_at) VALUES (?,?,?,?,?)",
        (sha, project["id"], f"commit {sha}", json.dumps(list(files)), at.isoformat(timespec="seconds")),
    )
    conn.commit()
    reconcile_service.reconcile(conn, project["id"], now=at)


def good(n=3, score=1.0, **kw):
    return [
        {"ordinal": i, "learner_answer": f"my answer {i}", "score": score, "hints_used": 0, **kw}
        for i in range(1, n + 1)
    ]


def test_context_picks_top_gap_with_real_evidence(conn, project):
    add_verified(conn, project, "aaa111", "python.testing.mocking", 5)
    add_verified(conn, project, "bbb222", "python.testing.mocking", 15, files=("src/x.py",))
    add_verified(conn, project, "ccc333", "python.async", 25)
    ctx = lesson_service.get_teaching_context(conn, project["id"], now=T0 + timedelta(hours=1))
    assert ctx["skill"]["id"] == "python.testing.mocking"  # higher exposure, equal mastery
    assert ctx["level"] == "guided" and ctx["skill"]["confidence"] == "none"
    assert {e["commit"] for e in ctx["evidence"]} == {"aaa111", "bbb222"}
    assert ctx["evidence"][0]["what_ai_said_it_did"] == "mock http"
    assert "WAIT for the learner" in ctx["instructions"]


def test_no_gaps_returns_message_not_error(conn, project):
    ctx = lesson_service.get_teaching_context(conn, project["id"])
    assert ctx["skill"] is None and "No gaps" in ctx["message"]


def test_unexposed_skill_cannot_be_taught(conn, project):
    with pytest.raises(NotFoundError):
        lesson_service.get_teaching_context(conn, project["id"], skill="python.oop")


def test_context_is_bounded_with_heavy_history(conn, project):
    for i in range(60):
        add_verified(
            conn,
            project,
            f"s{i:03d}",
            "python",
            i * 2,
            files=tuple(f"src/f{j}.py" for j in range(40)),
            summary="x" * 5000,
        )
    ctx = lesson_service.get_teaching_context(conn, project["id"], now=T0 + timedelta(days=1))
    assert len(ctx["evidence"]) <= 5
    assert all(len(e["files"]) <= 8 and len(e["what_ai_said_it_did"]) <= 300 for e in ctx["evidence"])
    assert len(json.dumps(ctx)) < 8000


def test_quiz_moves_mastery_once_and_confidence_stays_honest(conn, project):
    add_verified(conn, project, "aaa111", "python.testing.mocking", 5)
    quiz = quiz_service.create_quiz(conn, "python.testing.mocking", Q, project["id"], now=T0)
    out = quiz_service.record_quiz_result(conn, quiz["quiz_id"], good(3, 1.0), now=T0)
    assert out["attempts"] == 1  # 3 questions = 1 attempt
    assert out["confidence"] == "low"
    assert 0.5 < out["mastery"] < 1.0  # one quiz never maxes it out


def test_cannot_record_same_quiz_twice(conn, project):
    quiz = quiz_service.create_quiz(conn, "python", Q, now=T0)
    quiz_service.record_quiz_result(conn, quiz["quiz_id"], good(3), now=T0)
    with pytest.raises(ValidationError, match="already recorded"):
        quiz_service.record_quiz_result(conn, quiz["quiz_id"], good(3), now=T0)


def test_score_without_learner_answer_is_rejected(conn):
    quiz = quiz_service.create_quiz(conn, "python", Q, now=T0)
    bad = good(3)
    bad[1]["learner_answer"] = "   "
    with pytest.raises(ValidationError, match="learner_answer is empty"):
        quiz_service.record_quiz_result(conn, quiz["quiz_id"], bad, now=T0)
    assert conn.execute("SELECT COUNT(*) FROM attempts").fetchone()[0] == 0  # nothing half-written


def test_missing_or_extra_questions_rejected(conn):
    quiz = quiz_service.create_quiz(conn, "python", Q, now=T0)
    with pytest.raises(ValidationError, match="exactly one result per question"):
        quiz_service.record_quiz_result(conn, quiz["quiz_id"], good(2), now=T0)


def test_hints_lower_the_effect_on_mastery(conn):
    a = quiz_service.create_quiz(conn, "python", Q, now=T0)
    b = quiz_service.create_quiz(conn, "python.oop", Q, now=T0)
    unaided = quiz_service.record_quiz_result(conn, a["quiz_id"], good(3, 1.0), now=T0)
    hinted = quiz_service.record_quiz_result(
        conn, b["quiz_id"], [{**r, "hints_used": 3} for r in good(3, 1.0)], now=T0
    )
    assert hinted["mastery"] < unaided["mastery"]


def test_wrong_answers_create_mistake_memory_that_feeds_next_lesson(conn, project):
    add_verified(conn, project, "aaa111", "python.testing.mocking", 5)
    for _ in range(2):
        quiz = quiz_service.create_quiz(conn, "python.testing.mocking", Q, project["id"], now=T0)
        res = good(3, 0.2, mistake_pattern="patches defining module")[:1] + good(3, 1.0)[1:]
        quiz_service.record_quiz_result(conn, quiz["quiz_id"], res, now=T0)
    ctx = lesson_service.get_teaching_context(conn, project["id"], skill="python.testing.mocking", now=T0)
    assert ctx["known_mistakes"][0] == {
        "pattern": "patches defining module",
        "times": 2,
        "last_seen": ctx["known_mistakes"][0]["last_seen"],
    }
    assert ctx["skill"]["attempts"] == 2


def test_weak_result_keeps_skill_in_gaps(conn, project):
    add_verified(conn, project, "aaa111", "python.testing.mocking", 5)
    quiz = quiz_service.create_quiz(conn, "python.testing.mocking", Q, project["id"], now=T0)
    quiz_service.record_quiz_result(conn, quiz["quiz_id"], good(3, 0.1), now=T0)
    gaps = skill_service.find_gaps(conn, project["id"], now=T0)["gaps"]
    assert gaps and gaps[0]["status"] == "gap"
