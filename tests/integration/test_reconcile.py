import json
from datetime import UTC, datetime, timedelta

import pytest

from learnloop.capture import queue
from learnloop.domain.errors import ValidationError
from learnloop.services import capture_service as cap
from learnloop.services import practice_service, reconcile_service, skill_service

T0 = datetime(2026, 3, 1, 10, 0, tzinfo=UTC)


@pytest.fixture
def project(conn, tmp_path):
    return cap.start_project(conn, "demo", str(tmp_path), now=T0)


def commit(conn, project, sha, files, at):
    conn.execute(
        "INSERT INTO commits (sha, project_id, message, files, committed_at) VALUES (?,?,?,?,?)",
        (sha, project["id"], "msg", json.dumps(files), at.isoformat(timespec="seconds")),
    )
    conn.commit()


def exposure(conn, skill):
    return conn.execute("SELECT COUNT(*) FROM events WHERE skill_id=?", (skill,)).fetchone()[0]


def test_intent_alone_gives_no_exposure(conn, project):
    cap.start_skill_session(conn, project["id"], ["python.testing"], "tests", "why", now=T0)
    reconcile_service.reconcile(conn, project["id"], now=T0 + timedelta(hours=1))
    assert exposure(conn, "python.testing") == 0


def test_intent_plus_commit_is_verified_exposure(conn, project):
    cap.start_skill_session(conn, project["id"], ["python.testing"], "tests", "why", now=T0)
    commit(conn, project, "abc", ["tests/test_a.py"], T0 + timedelta(minutes=30))
    r = reconcile_service.reconcile(conn, project["id"], now=T0 + timedelta(hours=1))
    assert r["commits_verified"] == 1 and r["unexplained"] == []
    assert exposure(conn, "python.testing") == 1


def test_commit_without_intent_is_unexplained_with_suggestions(conn, project):
    commit(conn, project, "abc", ["tests/test_a.py", "src/a.py"], T0)
    r = reconcile_service.reconcile(conn, project["id"], now=T0)
    assert r["unexplained"][0]["sha"] == "abc"
    assert "python.testing" in r["unexplained"][0]["suggested_skills"]
    assert exposure(conn, "python.testing") == 0  # suggestions never count


def test_explaining_a_commit_later_verifies_it(conn, project):
    commit(conn, project, "abc", ["src/a.py"], T0)
    reconcile_service.reconcile(conn, project["id"], now=T0)
    cap.start_skill_session(
        conn, project["id"], ["python"], "s", "r", commit_sha="abc", now=T0 + timedelta(days=1)
    )
    r = reconcile_service.reconcile(conn, project["id"], now=T0 + timedelta(days=1))
    assert r["unexplained"] == [] and exposure(conn, "python") == 1


def test_stale_intents_are_abandoned(conn, project):
    cap.start_skill_session(conn, project["id"], ["python"], "s", "r", now=T0)
    r = reconcile_service.reconcile(conn, project["id"], abandon_days=14, now=T0 + timedelta(days=15))
    assert r["intents_abandoned"] == 1 and exposure(conn, "python") == 0


def test_start_skill_session_is_idempotent(conn, project):
    a = cap.start_skill_session(conn, project["id"], ["python"], "s", "r", intent_id="x", now=T0)
    b = cap.start_skill_session(conn, project["id"], ["python"], "s", "r", intent_id="x", now=T0)
    assert a["created"] and not b["created"]
    assert conn.execute("SELECT COUNT(*) FROM intents").fetchone()[0] == 1


def test_unknown_skill_error_suggests_close_matches(conn, project):
    with pytest.raises(ValidationError, match="python.testing"):
        cap.start_skill_session(conn, project["id"], ["python.testin"], "s", "r")


def test_exposure_is_not_mastery(conn, project):
    cap.start_skill_session(conn, project["id"], ["python.testing.mocking"], "s", "r", now=T0)
    commit(conn, project, "abc", ["tests/test_a.py"], T0 + timedelta(minutes=1))
    reconcile_service.reconcile(conn, project["id"], now=T0 + timedelta(hours=1))
    gaps = skill_service.find_gaps(conn, now=T0 + timedelta(hours=1))["gaps"]
    assert gaps[0]["skill"] == "python.testing.mocking" and gaps[0]["status"] == "untested"
    practice_service.submit_attempt(conn, "python.testing.mocking", 1.0, now=T0)
    # one perfect attempt: improved, but low confidence is still reported
    entry = skill_service.get_skill_map(conn, now=T0)["skills"][0]
    assert entry["attempts"] == 1 and entry["confidence"] == "low"


def test_repeated_mistakes_accumulate(conn):
    for _ in range(3):
        r = cap.flag_misunderstanding(conn, "python.testing.mocking", "patches defining module")
    assert r["count"] == 3


def test_queue_ingest_dedupes_redacts_and_quarantines(conn, settings, project, tmp_path):
    queue.write_queue_entry(tmp_path, "s1", "fix token = abc123secret", ["src/a.py", ".env"], T0.isoformat())
    bad = queue.queue_dir(tmp_path) / "bad.json"
    bad.write_text("{not json")
    stats = queue.ingest(conn, settings, project["id"], tmp_path)
    assert stats == {"ingested": 1, "duplicates": 0, "rejected": 1}
    row = conn.execute("SELECT * FROM commits WHERE sha='s1'").fetchone()
    assert "abc123secret" not in row["message"]
    assert json.loads(row["files"]) == ["src/a.py"]
    queue.write_queue_entry(tmp_path, "s1", "again", ["src/a.py"], T0.isoformat())
    assert queue.ingest(conn, settings, project["id"], tmp_path)["duplicates"] == 1
