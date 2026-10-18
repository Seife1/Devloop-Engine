"""Learning event model with validation for auto-tracking.

A LearningEvent represents a detected learning opportunity from AI assistant context.
Events are automatically detected through conversation analysis and assigned confidence scores.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class EventType(Enum):
    """Type of learning event detected."""

    IMPLEMENTATION = "implementation"
    DECISION = "decision"
    QUESTION = "question"
    EXPLANATION = "explanation"


class EventSource(Enum):
    """Source from which the learning event was detected."""

    CONVERSATION = "conversation"
    COMMIT = "commit"
    MANUAL = "manual"


@dataclass(frozen=True)
class LearningEvent:
    """Immutable learning event with validation.

    Represents an automatically detected learning opportunity from AI conversations,
    commits, or manual entries. Each event has a confidence score indicating
    detection certainty.

    Attributes:
        id: Unique identifier (UUID string)
        project_id: Reference to the project (UUID string)
        event_type: Type of learning event (implementation, decision, etc.)
        timestamp: When the event occurred (UTC)
        content: Type-specific content (dict)
        skills: List of skill identifiers associated with this event
        confidence: Detection confidence score (0.0 to 1.0)
        source: Where the event was detected from

    Raises:
        ValueError: If validation constraints are violated
    """

    id: str
    project_id: str
    event_type: EventType
    timestamp: datetime
    content: dict[str, Any]
    skills: list[str]
    confidence: float
    source: EventSource

    def __post_init__(self) -> None:
        """Validate the learning event after initialization.

        Validates:
        - Confidence score is between 0.0 and 1.0 (Requirement 3.7, 23.3)
        - Timestamp is not in the future
        - Skills list is not None (can be empty)
        - Content is a valid dict
        """
        # Requirement 23.3: Learning_Event SHALL enforce confidence between 0.0 and 1.0
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be between 0.0 and 1.0, got {self.confidence}")

        # Validate timestamp is not in the future
        now = datetime.now(timezone.utc)
        # Make timestamp timezone-aware if it isn't already
        event_time = self.timestamp if self.timestamp.tzinfo else self.timestamp.replace(tzinfo=timezone.utc)
        if event_time > now:
            raise ValueError(f"timestamp cannot be in the future: {self.timestamp}")

        # Validate skills is a list (can be empty)
        if self.skills is None:
            raise ValueError("skills must be a list, not None")

        # Validate content is a dict
        if not isinstance(self.content, dict):
            raise ValueError(f"content must be a dict, got {type(self.content)}")

    @classmethod
    def create(
        cls,
        id: str,
        project_id: str,
        event_type: EventType,
        timestamp: datetime,
        content: dict[str, Any],
        skills: list[str],
        confidence: float,
        source: EventSource,
    ) -> LearningEvent:
        """Create a new LearningEvent with validation.

        Factory method that ensures all validation constraints are met.

        Args:
            id: Unique identifier (UUID string)
            project_id: Reference to the project (UUID string)
            event_type: Type of learning event
            timestamp: When the event occurred (UTC)
            content: Type-specific content
            skills: List of skill identifiers
            confidence: Detection confidence score (0.0 to 1.0)
            source: Where the event was detected from

        Returns:
            Validated LearningEvent instance

        Raises:
            ValueError: If validation fails
        """
        return cls(
            id=id,
            project_id=project_id,
            event_type=event_type,
            timestamp=timestamp,
            content=content,
            skills=skills,
            confidence=confidence,
            source=source,
        )
