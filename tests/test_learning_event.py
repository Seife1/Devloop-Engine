"""Unit tests for LearningEvent model.

Tests cover validation rules from Requirements 3.7 and 23.3.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from learnloop.domain.learning_event import EventSource, EventType, LearningEvent


class TestLearningEvent:
    """Test LearningEvent validation and behavior."""

    def test_valid_learning_event(self) -> None:
        """Test creating a valid LearningEvent with all required fields."""
        now = datetime.now(timezone.utc)
        event = LearningEvent(
            id=str(uuid4()),
            project_id=str(uuid4()),
            event_type=EventType.IMPLEMENTATION,
            timestamp=now,
            content={"code": "def hello(): pass", "language": "python"},
            skills=["python.functions", "python.syntax"],
            confidence=0.85,
            source=EventSource.CONVERSATION,
        )

        assert event.event_type == EventType.IMPLEMENTATION
        assert event.confidence == 0.85
        assert event.source == EventSource.CONVERSATION
        assert len(event.skills) == 2

    def test_learning_event_confidence_minimum(self) -> None:
        """Test LearningEvent with minimum confidence 0.0 (Requirements 3.7, 23.3)."""
        now = datetime.now(timezone.utc)
        event = LearningEvent(
            id=str(uuid4()),
            project_id=str(uuid4()),
            event_type=EventType.QUESTION,
            timestamp=now,
            content={"question": "How does this work?"},
            skills=[],
            confidence=0.0,
            source=EventSource.MANUAL,
        )

        assert event.confidence == 0.0

    def test_learning_event_confidence_maximum(self) -> None:
        """Test LearningEvent with maximum confidence 1.0 (Requirements 3.7, 23.3)."""
        now = datetime.now(timezone.utc)
        event = LearningEvent(
            id=str(uuid4()),
            project_id=str(uuid4()),
            event_type=EventType.EXPLANATION,
            timestamp=now,
            content={"explanation": "This works by..."},
            skills=["architecture.design"],
            confidence=1.0,
            source=EventSource.MANUAL,
        )

        assert event.confidence == 1.0

    def test_learning_event_confidence_below_minimum(self) -> None:
        """Test that confidence below 0.0 raises ValueError (Requirements 3.7, 23.3)."""
        now = datetime.now(timezone.utc)

        with pytest.raises(ValueError, match="confidence must be between 0.0 and 1.0"):
            LearningEvent(
                id=str(uuid4()),
                project_id=str(uuid4()),
                event_type=EventType.IMPLEMENTATION,
                timestamp=now,
                content={"code": "test"},
                skills=[],
                confidence=-0.1,
                source=EventSource.CONVERSATION,
            )

    def test_learning_event_confidence_above_maximum(self) -> None:
        """Test that confidence above 1.0 raises ValueError (Requirements 3.7, 23.3)."""
        now = datetime.now(timezone.utc)

        with pytest.raises(ValueError, match="confidence must be between 0.0 and 1.0"):
            LearningEvent(
                id=str(uuid4()),
                project_id=str(uuid4()),
                event_type=EventType.IMPLEMENTATION,
                timestamp=now,
                content={"code": "test"},
                skills=[],
                confidence=1.5,
                source=EventSource.CONVERSATION,
            )

    def test_learning_event_timestamp_not_future(self) -> None:
        """Test that timestamp in the future raises ValueError."""
        future = datetime.now(timezone.utc) + timedelta(hours=1)

        with pytest.raises(ValueError, match="timestamp cannot be in the future"):
            LearningEvent(
                id=str(uuid4()),
                project_id=str(uuid4()),
                event_type=EventType.IMPLEMENTATION,
                timestamp=future,
                content={"code": "test"},
                skills=[],
                confidence=0.8,
                source=EventSource.CONVERSATION,
            )

    def test_learning_event_timestamp_past_valid(self) -> None:
        """Test that past timestamp is valid."""
        past = datetime.now(timezone.utc) - timedelta(days=1)
        event = LearningEvent(
            id=str(uuid4()),
            project_id=str(uuid4()),
            event_type=EventType.DECISION,
            timestamp=past,
            content={"decision": "Use async", "alternatives": ["sync", "threading"]},
            skills=["python.async"],
            confidence=0.75,
            source=EventSource.COMMIT,
        )

        assert event.timestamp == past

    def test_learning_event_timestamp_now_valid(self) -> None:
        """Test that current timestamp is valid."""
        now = datetime.now(timezone.utc)
        event = LearningEvent(
            id=str(uuid4()),
            project_id=str(uuid4()),
            event_type=EventType.IMPLEMENTATION,
            timestamp=now,
            content={"code": "test"},
            skills=[],
            confidence=0.8,
            source=EventSource.CONVERSATION,
        )

        # Should not raise
        assert event.timestamp == now

    def test_learning_event_timezone_naive_timestamp(self) -> None:
        """Test that timezone-naive timestamps are converted to UTC."""
        naive_time = datetime(2024, 1, 1, 12, 0, 0)  # No timezone
        event = LearningEvent(
            id=str(uuid4()),
            project_id=str(uuid4()),
            event_type=EventType.IMPLEMENTATION,
            timestamp=naive_time,
            content={"code": "test"},
            skills=[],
            confidence=0.8,
            source=EventSource.CONVERSATION,
        )

        # Should not raise since it's in the past
        assert event.timestamp == naive_time

    def test_learning_event_empty_skills_valid(self) -> None:
        """Test that empty skills list is valid."""
        now = datetime.now(timezone.utc)
        event = LearningEvent(
            id=str(uuid4()),
            project_id=str(uuid4()),
            event_type=EventType.QUESTION,
            timestamp=now,
            content={"question": "Generic question"},
            skills=[],
            confidence=0.5,
            source=EventSource.CONVERSATION,
        )

        assert event.skills == []

    def test_learning_event_skills_none_invalid(self) -> None:
        """Test that None skills raises ValueError."""
        now = datetime.now(timezone.utc)

        with pytest.raises(ValueError, match="skills must be a list, not None"):
            LearningEvent(
                id=str(uuid4()),
                project_id=str(uuid4()),
                event_type=EventType.IMPLEMENTATION,
                timestamp=now,
                content={"code": "test"},
                skills=None,  # type: ignore
                confidence=0.8,
                source=EventSource.CONVERSATION,
            )

    def test_learning_event_content_not_dict_invalid(self) -> None:
        """Test that non-dict content raises ValueError."""
        now = datetime.now(timezone.utc)

        with pytest.raises(ValueError, match="content must be a dict"):
            LearningEvent(
                id=str(uuid4()),
                project_id=str(uuid4()),
                event_type=EventType.IMPLEMENTATION,
                timestamp=now,
                content="invalid content",  # type: ignore
                skills=[],
                confidence=0.8,
                source=EventSource.CONVERSATION,
            )

    def test_learning_event_all_event_types(self) -> None:
        """Test creating events with all EventType values."""
        now = datetime.now(timezone.utc)

        for event_type in EventType:
            event = LearningEvent(
                id=str(uuid4()),
                project_id=str(uuid4()),
                event_type=event_type,
                timestamp=now,
                content={"test": "data"},
                skills=[],
                confidence=0.8,
                source=EventSource.CONVERSATION,
            )
            assert event.event_type == event_type

    def test_learning_event_all_event_sources(self) -> None:
        """Test creating events with all EventSource values."""
        now = datetime.now(timezone.utc)

        for source in EventSource:
            event = LearningEvent(
                id=str(uuid4()),
                project_id=str(uuid4()),
                event_type=EventType.IMPLEMENTATION,
                timestamp=now,
                content={"test": "data"},
                skills=[],
                confidence=0.8,
                source=source,
            )
            assert event.source == source

    def test_learning_event_factory_method(self) -> None:
        """Test creating LearningEvent using factory method."""
        now = datetime.now(timezone.utc)
        event_id = str(uuid4())
        project_id = str(uuid4())

        event = LearningEvent.create(
            id=event_id,
            project_id=project_id,
            event_type=EventType.DECISION,
            timestamp=now,
            content={"decision": "Use FastAPI", "rationale": "Performance"},
            skills=["python.fastapi", "architecture.api"],
            confidence=0.92,
            source=EventSource.COMMIT,
        )

        assert event.id == event_id
        assert event.project_id == project_id
        assert event.event_type == EventType.DECISION
        assert event.timestamp == now
        assert event.confidence == 0.92
        assert event.source == EventSource.COMMIT
        assert len(event.skills) == 2

    def test_learning_event_immutable(self) -> None:
        """Test that LearningEvent is immutable (frozen dataclass)."""
        now = datetime.now(timezone.utc)
        event = LearningEvent(
            id=str(uuid4()),
            project_id=str(uuid4()),
            event_type=EventType.IMPLEMENTATION,
            timestamp=now,
            content={"code": "test"},
            skills=[],
            confidence=0.8,
            source=EventSource.CONVERSATION,
        )

        # Should not be able to modify frozen dataclass
        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            event.confidence = 0.9  # type: ignore

    def test_learning_event_mid_range_confidence(self) -> None:
        """Test LearningEvent with mid-range confidence values."""
        now = datetime.now(timezone.utc)

        # Test various mid-range values
        for confidence in [0.25, 0.5, 0.7, 0.75, 0.85]:
            event = LearningEvent(
                id=str(uuid4()),
                project_id=str(uuid4()),
                event_type=EventType.IMPLEMENTATION,
                timestamp=now,
                content={"code": "test"},
                skills=[],
                confidence=confidence,
                source=EventSource.CONVERSATION,
            )
            assert event.confidence == confidence

    def test_learning_event_complex_content(self) -> None:
        """Test LearningEvent with complex nested content dict."""
        now = datetime.now(timezone.utc)
        complex_content = {
            "code": "def calculate(x, y): return x + y",
            "language": "python",
            "complexity": {
                "cyclomatic": 1,
                "nesting": 0,
                "lines": 1,
            },
            "context": {
                "file": "calculator.py",
                "function": "calculate",
            },
        }

        event = LearningEvent(
            id=str(uuid4()),
            project_id=str(uuid4()),
            event_type=EventType.IMPLEMENTATION,
            timestamp=now,
            content=complex_content,
            skills=["python.functions", "python.operators"],
            confidence=0.88,
            source=EventSource.CONVERSATION,
        )

        assert event.content == complex_content
        assert event.content["complexity"]["cyclomatic"] == 1
        assert event.content["context"]["file"] == "calculator.py"
