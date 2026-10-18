"""Integration tests for explanation depth calculation in record_explanation.

Tests Requirements:
- 10.1: Store explanation text with item reference
- 10.2: Validate self_rating between 1.0 and 5.0
- 10.4: Calculate explanation depth score
- 10.7: Generate quality feedback for low-quality explanations
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from learnloop.persistence.db import connect
from learnloop.services import knowledge_service


@pytest.fixture
def test_db(tmp_path: Path):
    """Create a test database with project and commits."""
    db_path = tmp_path / "test.db"
    conn = connect(db_path)
    
    # Create repo directory
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()
    
    # Create project
    conn.execute(
        "INSERT INTO projects (id, name, repo_path, created_at) VALUES ('test-proj', 'Test Project', ?, '2026-01-01T00:00:00Z')",
        (str(repo_dir.resolve()),),
    )
    
    # Seed known commit with files
    known_files = ["src/auth.py", "src/user.py", "tests/test_auth.py"]
    conn.execute(
        "INSERT INTO commits (sha, project_id, message, files, committed_at, status, origin)"
        " VALUES ('c1', 'test-proj', 'init', ?, '2026-01-01T00:00:00Z', 'verified', 'hook')",
        (json.dumps(known_files),),
    )
    conn.commit()
    
    return conn, "test-proj", tmp_path


def test_record_explanation_calculates_depth(test_db):
    """record_explanation should calculate and return explanation depth score."""
    conn, project_id, tmp_path = test_db
    
    # Register item
    knowledge_service.register_knowledge_item(
        conn,
        project_id=project_id,
        key="test-component",
        title="Auth Service",
        kind="component",
        band="intermediate",
        files=["src/auth.py"],
        summary="Authentication service",
        tags=["auth"],
    )
    
    explanation_text = """
    The Auth Service handles user authentication using JWT tokens.
    I implemented it because we need stateless authentication across
    multiple services. The algorithm validates tokens using HMAC-SHA256.
    
    I chose JWT instead of session-based auth because we don't want
    to manage session state. The tradeoff is we can't revoke tokens
    immediately, but that's acceptable for our use case.
    """
    
    result = knowledge_service.record_explanation(
        conn,
        project_id=project_id,
        key="test-component",
        learner_text=explanation_text,
        score=0.9,
        self_rating=4,
    )
    
    # Check that explanation_depth_score is calculated
    assert "explanation_depth_score" in result
    assert isinstance(result["explanation_depth_score"], float)
    assert 0.0 <= result["explanation_depth_score"] <= 1.0
    
    # This comprehensive explanation should score reasonably well
    assert result["explanation_depth_score"] > 0.3


def test_low_quality_explanation_gets_feedback(test_db):
    """Low-quality explanation should receive quality feedback."""
    conn, project_id, tmp_path = test_db
    
    knowledge_service.register_knowledge_item(
        conn,
        project_id=project_id,
        key="test-2",
        title="User Service",
        kind="component",
        band="basic",
        files=["src/user.py"],
        summary="User management",
        tags=["users"],
    )
    
    short_explanation = "It works fine and does authentication."
    
    result = knowledge_service.record_explanation(
        conn,
        project_id=project_id,
        key="test-2",
        learner_text=short_explanation,
        score=0.7,
        self_rating=2,
    )
    
    # Check depth score is low
    assert result["explanation_depth_score"] < 0.4
    
    # Check quality feedback is included
    assert "quality_feedback" in result
    assert result["quality_feedback"]["needs_improvement"]
    assert len(result["quality_feedback"]["suggestions"]) > 0


def test_high_quality_explanation_no_feedback(test_db):
    """High-quality explanation should not include improvement feedback."""
    conn, project_id, tmp_path = test_db
    
    knowledge_service.register_knowledge_item(
        conn,
        project_id=project_id,
        key="test-3",
        title="Auth Service",
        kind="component",
        band="advanced",
        files=["src/auth.py"],
        summary="Auth service",
        tags=["auth"],
    )
    
    comprehensive_explanation = """
    The Auth Service implements JWT-based authentication for our API.
    It intercepts incoming requests through middleware and validates
    the authorization header. The algorithm uses HMAC-SHA256 to verify
    token signatures and checks expiration timestamps.
    
    I chose this approach because we need stateless authentication that
    scales across multiple service instances without shared session storage.
    The tradeoff is that we can't immediately revoke tokens - they
    remain valid until expiration. To mitigate this, we use short expiration
    times (15 minutes) combined with refresh tokens.
    
    I considered using OAuth2 with a separate auth server, but that would
    add unnecessary complexity for our current scale. Another option was
    Passport.js, but implementing it directly gives us more control over
    the authentication flow and better understanding of the security model.
    
    For security, tokens are stored in httpOnly cookies to prevent XSS attacks.
    The refresh token rotation pattern prevents replay attacks if tokens are
    compromised.
    """
    
    result = knowledge_service.record_explanation(
        conn,
        project_id=project_id,
        key="test-3",
        learner_text=comprehensive_explanation,
        score=0.95,
        self_rating=5,
    )
    
    # Check depth score is high
    assert result["explanation_depth_score"] > 0.6
    
    # Check NO quality feedback is included
    assert "quality_feedback" not in result


def test_generate_prompt_for_item(test_db):
    """Should generate explanation prompt for existing item."""
    conn, project_id, tmp_path = test_db
    
    knowledge_service.register_knowledge_item(
        conn,
        project_id=project_id,
        key="prompt-test",
        title="Auth Service",
        kind="component",
        band="intermediate",
        files=["src/auth.py"],
        summary="Auth service",
        tags=["auth"],
    )
    
    prompt_data = knowledge_service.generate_item_explanation_prompt(
        conn,
        project_id=project_id,
        key="prompt-test",
    )
    
    assert "prompt" in prompt_data
    assert "questions" in prompt_data
    assert prompt_data["item_key"] == "prompt-test"
    assert "Auth Service" in prompt_data["prompt"]
    assert "Self-rating" in prompt_data["prompt"]
