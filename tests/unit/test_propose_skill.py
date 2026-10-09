from datetime import UTC, datetime

import pytest

from learnloop.domain.errors import ValidationError
from learnloop.services import skill_service

T0 = datetime(2026, 3, 1, 10, 0, tzinfo=UTC)


def test_valid_proposal(conn):
    res = skill_service.propose_skill(
        conn,
        "python.networking",
        "Networking",
        "Sockets and low-level HTTP handling",
        now=T0,
    )
    assert res["created"] is True
    assert res["source"] == "proposed"
    assert res["id"] == "python.networking"

    row = conn.execute("SELECT * FROM skills WHERE id='python.networking'").fetchone()
    assert row is not None
    assert row["source"] == "proposed"
    assert row["rationale"] == "Sockets and low-level HTTP handling"
    assert row["proposed_at"] is not None


def test_rejection_invalid_id_regex(conn):
    # Root skill not allowed
    with pytest.raises(ValidationError, match="Invalid skill id"):
        skill_service.propose_skill(conn, "rust", "Rust", "Systems language", now=T0)

    # Uppercase not allowed
    with pytest.raises(ValidationError, match="Invalid skill id"):
        skill_service.propose_skill(conn, "python.Async", "Async", "Async logic", now=T0)

    # Too many segments (> 4)
    with pytest.raises(ValidationError, match="Invalid skill id"):
        skill_service.propose_skill(conn, "a.b.c.d.e", "Too deep", "Deep nested", now=T0)

    # Invalid characters
    with pytest.raises(ValidationError, match="Invalid skill id"):
        skill_service.propose_skill(conn, "python.test$foo", "Invalid", "Special chars", now=T0)


def test_rejection_missing_parent(conn):
    with pytest.raises(ValidationError, match="Parent skill 'nonexistent' does not exist"):
        skill_service.propose_skill(
            conn, "nonexistent.feature", "Feature", "Feature without parent", now=T0
        )


def test_rejection_already_exists(conn):
    # python.testing is an existing seed skill
    with pytest.raises(ValidationError, match="already exists"):
        skill_service.propose_skill(conn, "python.testing", "Different Name", "Different rationale", now=T0)


def test_idempotent_reproposal(conn):
    res1 = skill_service.propose_skill(
        conn, "python.parsing", "Parsing", "Writing parsers", now=T0
    )
    assert res1["created"] is True

    # Same proposal again succeeds idempotently
    res2 = skill_service.propose_skill(
        conn, "python.parsing", "Parsing", "Writing parsers", now=T0
    )
    assert res2["created"] is False
    assert res2["id"] == "python.parsing"


def test_rejection_near_duplicate(conn):
    # 'python.texting' is 1 char off from 'python.testing' (ratio ~0.86)
    with pytest.raises(ValidationError, match="too similar to existing skill 'python.testing'"):
        skill_service.propose_skill(conn, "python.texting", "Texting", "SMS libraries", now=T0)

    # Near duplicate by name against existing sibling
    with pytest.raises(ValidationError, match="too similar to existing skill"):
        skill_service.propose_skill(conn, "python.unit-tests", "Testing", "Unit testing", now=T0)


def test_daily_limit(conn):
    names = ["alpha", "bravo", "charlie", "delta", "echo", "foxtrot"]
    # Propose 5 skills in the same UTC day
    for i in range(5):
        res = skill_service.propose_skill(
            conn,
            f"python.{names[i]}",
            f"Skill {names[i]}",
            f"Rationale for {names[i]}",
            now=T0,
        )
        assert res["created"] is True

    # 6th proposal should fail
    with pytest.raises(ValidationError, match="Daily limit reached"):
        skill_service.propose_skill(
            conn, f"python.{names[5]}", f"Skill {names[5]}", f"Rationale for {names[5]}", now=T0
        )


def test_rationale_and_name_validation(conn):
    # Empty name
    with pytest.raises(ValidationError, match="Name cannot be empty"):
        skill_service.propose_skill(conn, "python.temp", "", "Valid rationale", now=T0)

    # Empty rationale
    with pytest.raises(ValidationError, match="Rationale cannot be empty"):
        skill_service.propose_skill(conn, "python.temp", "Temp", "", now=T0)

    # Rationale > 300 chars
    with pytest.raises(ValidationError, match="Rationale exceeds 300 characters"):
        skill_service.propose_skill(conn, "python.temp", "Temp", "x" * 301, now=T0)
