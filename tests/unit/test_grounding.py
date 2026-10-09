import json
from datetime import UTC, datetime, timedelta

import pytest

from learnloop.domain.errors import ValidationError
from learnloop.services import capture_service as cap
from learnloop.services import quiz_service, reconcile_service

T0 = datetime(2026, 3, 1, 10, 0, tzinfo=UTC)


def make_q(prompt: str, source_file: str | None = None) -> dict:
    q = {
        "kind": "explain",
        "prompt": prompt,
        "reference_answer": "ans",
        "rubric": ["point 1", "point 2"],
    }
    if source_file is not None:
        q["source_file"] = source_file
    return q


def seed_verified_commit(conn, project_id, sha, skill, files):
    cap.start_skill_session(
        conn,
        project_id,
        [skill],
        "summary",
        "rationale",
        intent_id=f"intent-{sha}",
        now=T0,
    )
    conn.execute(
        "INSERT INTO commits (sha, project_id, message, files, committed_at) VALUES (?,?,?,?,?)",
        (sha, project_id, "msg", json.dumps(files), T0.isoformat(timespec="seconds")),
    )
    conn.commit()
    reconcile_service.reconcile(conn, project_id, now=T0 + timedelta(minutes=5))


@pytest.fixture
def project(conn, tmp_path):
    return cap.start_project(conn, "test-proj", str(tmp_path), now=T0)


def test_grounded_question_accepted(conn, project):
    seed_verified_commit(conn, project["id"], "c1", "python.testing", ["tests/test_foo.py", "src/foo.py"])

    questions = [
        make_q("Explain fixture setup", source_file="tests/test_foo.py"),
        make_q("Explain foo function", source_file="src/foo.py"),
        make_q("Generic testing question", source_file=None),
    ]

    res = quiz_service.create_quiz(conn, "python.testing", questions, project_id=project["id"], now=T0)
    assert res["questions"] == 3
    assert res["grounded"] == 2
    assert res["generic"] == 1

    rows = conn.execute(
        "SELECT ordinal, source_file, grounding FROM quiz_questions WHERE quiz_id=? ORDER BY ordinal",
        (res["quiz_id"],),
    ).fetchall()
    assert rows[0]["grounding"] == "project" and rows[0]["source_file"] == "tests/test_foo.py"
    assert rows[1]["grounding"] == "project" and rows[1]["source_file"] == "src/foo.py"
    assert rows[2]["grounding"] == "generic" and rows[2]["source_file"] is None


def test_fabricated_path_rejected_with_candidates(conn, project):
    seed_verified_commit(conn, project["id"], "c1", "python.testing", ["src/real.py"])

    questions = [
        make_q("Explain fake file", source_file="src/fake.py"),
        make_q("Generic question", source_file=None),
    ]

    with pytest.raises(ValidationError) as exc:
        quiz_service.create_quiz(conn, "python.testing", questions, project_id=project["id"], now=T0)

    msg = str(exc.value)
    assert "src/fake.py" in msg
    assert "src/real.py" in msg


def test_majority_rule_enforced_when_evidence_exists(conn, project):
    seed_verified_commit(conn, project["id"], "c1", "python.testing", ["src/test.py"])

    # 3 questions require ceil(3/2) = 2 grounded questions
    questions = [
        make_q("Grounded question", source_file="src/test.py"),
        make_q("Generic question 1", source_file=None),
        make_q("Generic question 2", source_file=None),
    ]

    with pytest.raises(ValidationError, match="At least 2 of 3 questions must be grounded"):
        quiz_service.create_quiz(conn, "python.testing", questions, project_id=project["id"], now=T0)


def test_no_evidence_skill_allows_generic(conn, project):
    # python.oop has no verified events
    questions = [
        make_q("Explain classes 1"),
        make_q("Explain classes 2"),
        make_q("Explain classes 3"),
    ]

    res = quiz_service.create_quiz(conn, "python.oop", questions, project_id=project["id"], now=T0)
    assert res["questions"] == 3
    assert res["grounded"] == 0
    assert res["generic"] == 3


def test_path_normalisation_windows_backslashes(conn, project):
    seed_verified_commit(conn, project["id"], "c1", "python.testing", ["src/module.py"])

    questions = [
        make_q("Grounded with backslash", source_file=r"src\module.py"),
        make_q("Grounded with leading dot-slash", source_file="./src/module.py"),
    ]

    res = quiz_service.create_quiz(conn, "python.testing", questions, project_id=project["id"], now=T0)
    assert res["grounded"] == 2

    rows = conn.execute(
        "SELECT source_file, grounding FROM quiz_questions WHERE quiz_id=? ORDER BY ordinal",
        (res["quiz_id"],),
    ).fetchall()
    assert rows[0]["source_file"] == "src/module.py"
    assert rows[1]["source_file"] == "src/module.py"


def test_project_scoping(conn, tmp_path):
    p_a = cap.start_project(conn, "proj-a", str(tmp_path / "a"), now=T0)
    p_b = cap.start_project(conn, "proj-b", str(tmp_path / "b"), now=T0)

    seed_verified_commit(conn, p_a["id"], "ca", "python", ["src/a.py"])
    seed_verified_commit(conn, p_b["id"], "cb", "python", ["src/b.py"])

    # Under p_a, citing src/b.py must be rejected
    questions = [make_q("Q", source_file="src/b.py")]
    with pytest.raises(ValidationError, match="src/b.py"):
        quiz_service.create_quiz(conn, "python", questions, project_id=p_a["id"], now=T0)

    # Under p_a, citing src/a.py succeeds
    ok_questions = [make_q("Q", source_file="src/a.py")]
    res = quiz_service.create_quiz(conn, "python", ok_questions, project_id=p_a["id"], now=T0)
    assert res["grounded"] == 1


def test_record_quiz_result_returns_grounded_counts(conn, project):
    seed_verified_commit(conn, project["id"], "c1", "python.testing", ["src/a.py"])
    questions = [
        make_q("Grounded", source_file="src/a.py"),
        make_q("Generic", source_file=None),
    ]
    quiz = quiz_service.create_quiz(conn, "python.testing", questions, project_id=project["id"], now=T0)

    results = [
        {"ordinal": 1, "learner_answer": "ans 1", "score": 1.0, "hints_used": 0},
        {"ordinal": 2, "learner_answer": "ans 2", "score": 0.8, "hints_used": 0},
    ]
    res = quiz_service.record_quiz_result(conn, quiz["quiz_id"], results, now=T0)
    assert res["grounded"] == 1
    assert res["generic"] == 1
