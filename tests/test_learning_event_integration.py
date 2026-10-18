"""Integration tests for LearningEvent model showing real-world usage scenarios."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from learnloop.domain.learning_event import EventSource, EventType, LearningEvent


class TestLearningEventIntegration:
    """Integration tests demonstrating LearningEvent usage in realistic scenarios."""

    def test_create_implementation_event_from_conversation(self) -> None:
        """Simulate creating a learning event from AI conversation analysis."""
        # Simulating auto-tracker detecting implementation event
        project_id = str(uuid4())
        code_snippet = """
def calculate_complexity(code: str) -> float:
    lines = len(code.split('\\n'))
    cyclomatic = calculate_cyclomatic_complexity(code)
    return (lines * 0.1 + cyclomatic * 0.4) / 100
"""

        event = LearningEvent.create(
            id=str(uuid4()),
            project_id=project_id,
            event_type=EventType.IMPLEMENTATION,
            timestamp=datetime.now(timezone.utc),
            content={
                "code": code_snippet,
                "language": "python",
                "file": "src/complexity.py",
                "function": "calculate_complexity",
            },
            skills=["python.functions", "complexity.analysis"],
            confidence=0.87,  # High confidence from auto-tracker
            source=EventSource.CONVERSATION,
        )

        # Verify event meets storage threshold (Requirement 3.8: confidence > 0.7)
        assert event.confidence > 0.7
        assert event.event_type == EventType.IMPLEMENTATION
        assert event.source == EventSource.CONVERSATION

    def test_create_decision_event_with_alternatives(self) -> None:
        """Simulate capturing a technical decision with alternatives."""
        event = LearningEvent.create(
            id=str(uuid4()),
            project_id=str(uuid4()),
            event_type=EventType.DECISION,
            timestamp=datetime.now(timezone.utc),
            content={
                "decision": "Use SQLite for local storage",
                "alternatives": ["PostgreSQL", "MySQL", "In-memory"],
                "rationale": "Zero-friction setup, cross-platform compatibility",
                "tradeoffs": "Limited concurrency, local-only data",
            },
            skills=["database.design", "sqlite"],
            confidence=0.92,
            source=EventSource.CONVERSATION,
        )

        assert "alternatives" in event.content
        assert len(event.content["alternatives"]) == 3
        assert event.event_type == EventType.DECISION

    def test_create_low_confidence_event_filtered(self) -> None:
        """Simulate filtering out low-confidence events (Requirement 3.8)."""
        # Auto-tracker detects trivial code with low confidence
        event = LearningEvent.create(
            id=str(uuid4()),
            project_id=str(uuid4()),
            event_type=EventType.IMPLEMENTATION,
            timestamp=datetime.now(timezone.utc),
            content={
                "code": "x = 5",
                "language": "python",
            },
            skills=[],
            confidence=0.15,  # Below storage threshold of 0.7
            source=EventSource.CONVERSATION,
        )

        # This event would be filtered out by auto-tracker
        assert event.confidence < 0.7
        # In real system, this wouldn't be stored

    def test_create_commit_sourced_event(self) -> None:
        """Simulate creating an event from git commit."""
        event = LearningEvent.create(
            id=str(uuid4()),
            project_id=str(uuid4()),
            event_type=EventType.IMPLEMENTATION,
            timestamp=datetime.now(timezone.utc),
            content={
                "commit_sha": "abc123def456",
                "files": ["src/auth.py", "tests/test_auth.py"],
                "message": "Implement JWT authentication",
            },
            skills=["security.jwt", "authentication"],
            confidence=1.0,  # Commit is verified, full confidence
            source=EventSource.COMMIT,
        )

        assert event.source == EventSource.COMMIT
        assert event.confidence == 1.0
        assert "commit_sha" in event.content

    def test_create_manual_explanation_event(self) -> None:
        """Simulate user manually recording an explanation."""
        event = LearningEvent.create(
            id=str(uuid4()),
            project_id=str(uuid4()),
            event_type=EventType.EXPLANATION,
            timestamp=datetime.now(timezone.utc),
            content={
                "explanation": (
                    "JWT tokens work by encoding user claims with a secret key. "
                    "The server validates the signature without storing session state."
                ),
                "depth_score": 0.75,
            },
            skills=["security.jwt", "authentication.stateless"],
            confidence=1.0,  # User-provided, full confidence
            source=EventSource.MANUAL,
        )

        assert event.source == EventSource.MANUAL
        assert event.event_type == EventType.EXPLANATION
        assert "explanation" in event.content

    def test_multiple_events_for_session(self) -> None:
        """Simulate tracking multiple events in a coding session."""
        project_id = str(uuid4())
        session_events: list[LearningEvent] = []

        # Event 1: Initial question
        session_events.append(
            LearningEvent.create(
                id=str(uuid4()),
                project_id=project_id,
                event_type=EventType.QUESTION,
                timestamp=datetime.now(timezone.utc),
                content={"question": "How do I implement async database queries?"},
                skills=["python.async", "database.async"],
                confidence=0.8,
                source=EventSource.CONVERSATION,
            )
        )

        # Event 2: Implementation
        session_events.append(
            LearningEvent.create(
                id=str(uuid4()),
                project_id=project_id,
                event_type=EventType.IMPLEMENTATION,
                timestamp=datetime.now(timezone.utc),
                content={
                    "code": "async def query_db(): await conn.execute(...)",
                    "language": "python",
                },
                skills=["python.async", "aiosqlite"],
                confidence=0.89,
                source=EventSource.CONVERSATION,
            )
        )

        # Event 3: Decision made
        session_events.append(
            LearningEvent.create(
                id=str(uuid4()),
                project_id=project_id,
                event_type=EventType.DECISION,
                timestamp=datetime.now(timezone.utc),
                content={
                    "decision": "Use aiosqlite for async SQLite",
                    "alternatives": ["raw sqlite3 with threads"],
                },
                skills=["aiosqlite", "architecture.async"],
                confidence=0.91,
                source=EventSource.CONVERSATION,
            )
        )

        # Verify all events stored (confidence > 0.7)
        assert all(event.confidence > 0.7 for event in session_events)
        assert len(session_events) == 3
        assert all(event.project_id == project_id for event in session_events)

    def test_event_validation_prevents_corruption(self) -> None:
        """Verify validation prevents corrupted data (Requirement 23.3)."""
        # Try to create event with invalid confidence
        with pytest.raises(ValueError, match="confidence must be between 0.0 and 1.0"):
            LearningEvent.create(
                id=str(uuid4()),
                project_id=str(uuid4()),
                event_type=EventType.IMPLEMENTATION,
                timestamp=datetime.now(timezone.utc),
                content={"code": "test"},
                skills=[],
                confidence=1.5,  # Invalid!
                source=EventSource.CONVERSATION,
            )

        # Try to create event with future timestamp
        with pytest.raises(ValueError, match="timestamp cannot be in the future"):
            from datetime import timedelta

            LearningEvent.create(
                id=str(uuid4()),
                project_id=str(uuid4()),
                event_type=EventType.IMPLEMENTATION,
                timestamp=datetime.now(timezone.utc) + timedelta(hours=1),
                content={"code": "test"},
                skills=[],
                confidence=0.8,
                source=EventSource.CONVERSATION,
            )
