"""Core domain models for LearnLoop MCP redesign with validation.

These models represent the fundamental data structures used throughout LearnLoop,
with built-in validation rules to ensure data integrity.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Final

from learnloop.domain.errors import ValidationError

# SM-2 Algorithm Constants
MIN_EASINESS: Final[float] = 1.3
MAX_EASINESS: Final[float] = 2.5
DEFAULT_EASINESS: Final[float] = 2.5


class DepthBand(Enum):
    """Classification of knowledge complexity."""

    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class IntentStatus(Enum):
    """Status of an intent record throughout its lifecycle."""

    OPEN = "open"
    MATCHED = "matched"
    ABANDONED = "abandoned"


@dataclass(frozen=False)
class IntentRecord:
    """A user's stated learning goal before implementing a feature.

    Validation Rules (Requirements 4.1-4.3, 23.4-23.5):
    - If status == MATCHED, then matched_commit_sha must not be None
    - If status != OPEN, then closed_at must not be None
    - closed_at must be >= created_at when not None
    - files list must not be empty
    """

    id: str
    session_id: str
    project_id: str
    intent_description: str
    files: list[str]
    skills: list[str]
    created_at: datetime
    status: IntentStatus
    matched_commit_sha: str | None = None
    closed_at: datetime | None = None

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        # Validate matched status requires commit_sha (Requirement 23.4)
        if self.status == IntentStatus.MATCHED and self.matched_commit_sha is None:
            raise ValidationError("matched_commit_sha must not be None when status is MATCHED")

        # Validate closed status requires closed_at (Requirement 23.5)
        if self.status != IntentStatus.OPEN and self.closed_at is None:
            raise ValidationError("closed_at must not be None when status is not OPEN")

        # Validate closed_at is after created_at (Requirement 23.5)
        if self.closed_at is not None and self.closed_at < self.created_at:
            raise ValidationError("closed_at must be >= created_at")

        # Validate files list is not empty
        if not self.files:
            raise ValidationError("files list must not be empty")


@dataclass(frozen=False)
class KnowledgeItem:
    """A documented concept or skill with tracked files and review schedule.

    Validation Rules (Requirements 9.1-9.3, 23.8):
    - key must be unique within project
    - title must be non-empty and <= 100 characters
    - summary must be non-empty and <= 500 characters
    - tracked_files must be non-empty list
    - self_rating must be between 1.0 and 5.0 when not None
    - if is_stale is True, stale_since must not be None
    """

    id: str
    project_id: str
    key: str
    title: str
    summary: str
    tracked_files: list[str]
    depth_band: DepthBand
    created_at: datetime
    last_explained_at: datetime | None = None
    self_rating: float | None = None
    is_stale: bool = False
    stale_since: datetime | None = None

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        # Validate title length
        if not self.title or len(self.title) > 100:
            raise ValidationError(f"Title must be 1-100 characters, got {len(self.title)}")

        # Validate summary length
        if not self.summary or len(self.summary) > 500:
            raise ValidationError(f"Summary must be 1-500 characters, got {len(self.summary)}")

        # Validate tracked files
        if not self.tracked_files:
            raise ValidationError("tracked_files must contain at least one file")

        # Validate self_rating range (Requirement 23.8)
        if self.self_rating is not None:
            if not (1.0 <= self.self_rating <= 5.0):
                raise ValidationError(f"self_rating must be between 1.0 and 5.0, got {self.self_rating}")

        # Validate staleness consistency
        if self.is_stale and self.stale_since is None:
            raise ValidationError("stale_since must not be None when is_stale is True")

        # Validate last_explained_at is not in future
        if self.last_explained_at is not None:
            now = datetime.utcnow()
            if self.last_explained_at > now:
                raise ValidationError("last_explained_at cannot be in the future")


@dataclass(frozen=False)
class ReviewSchedule:
    """SM-2 spaced repetition schedule for a knowledge item.

    Validation Rules (Requirements 15.2-15.4, 23.9-23.11):
    - easiness must be between 1.3 and 2.5 inclusive
    - interval must be positive integer (>= 1)
    - repetitions must be non-negative integer (>= 0)
    - if repetitions > 0, last_reviewed_at must not be None
    - due_at must be >= last_reviewed_at when last_reviewed_at is not None
    """

    id: str
    item_id: str
    interval: int
    easiness: float
    repetitions: int
    due_at: datetime
    snoozed_until: datetime | None = None
    last_reviewed_at: datetime | None = None
    success_streak: int = 0

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        # Validate easiness factor range (Requirements 15.2, 15.10, 23.9)
        if not (MIN_EASINESS <= self.easiness <= MAX_EASINESS):
            raise ValidationError(
                f"easiness must be between {MIN_EASINESS} and {MAX_EASINESS}, got {self.easiness}"
            )

        # Validate interval is positive (Requirements 15.3, 23.10)
        if self.interval < 1:
            raise ValidationError(f"interval must be positive (>= 1), got {self.interval}")

        # Validate repetitions is non-negative (Requirements 15.4, 23.11)
        if self.repetitions < 0:
            raise ValidationError(f"repetitions must be non-negative (>= 0), got {self.repetitions}")

        # Validate success_streak is non-negative
        if self.success_streak < 0:
            raise ValidationError(f"success_streak must be non-negative (>= 0), got {self.success_streak}")

        # Validate review history consistency (Requirement 15.12)
        if self.repetitions > 0 and self.last_reviewed_at is None:
            raise ValidationError("last_reviewed_at must not be None when repetitions > 0")

        # Validate due_at is after last_reviewed_at (Requirement 15.12)
        if self.last_reviewed_at is not None and self.due_at < self.last_reviewed_at:
            raise ValidationError("due_at must be >= last_reviewed_at")


def create_initial_review_schedule(
    item_id: str,
    schedule_id: str | None = None,
) -> ReviewSchedule:
    """Create initial SM-2 schedule for a newly registered knowledge item.

    Per Requirements 15.1-15.4:
    - Initial easiness: 2.5
    - Initial interval: 1 day
    - Initial repetitions: 0
    - Due date: 1 day from now
    """
    import uuid
    from datetime import timedelta

    now = datetime.utcnow()
    due = now + timedelta(days=1)

    return ReviewSchedule(
        id=schedule_id or str(uuid.uuid4()),
        item_id=item_id,
        interval=1,
        easiness=DEFAULT_EASINESS,
        repetitions=0,
        due_at=due,
        last_reviewed_at=None,
        success_streak=0,
    )


@dataclass(frozen=False)
class ExposureRecord:
    """Verified exposure record linking intent to commit.

    Represents a verified learning event where an intent was matched with
    a commit, proving that code was actually written. Includes optional
    explanation data for depth tracking.

    Validation Rules (Requirements 7.6, 23.6-23.7):
    - commit_sha must be exactly 40 hexadecimal characters
    - If explanation_recorded is True, explanation_depth must not be None
    - explanation_depth must be between 0.0 and 1.0 when not None
    - verified_at must not be in the future
    """

    id: str
    project_id: str
    intent_id: str
    commit_sha: str
    skills: list[str]
    files: list[str]
    verified_at: datetime
    explanation_recorded: bool = False
    explanation_depth: float | None = None

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        import re

        # Validate commit SHA format - exactly 40 hex characters (Requirement 7.6)
        if not re.match(r"^[0-9a-f]{40}$", self.commit_sha):
            raise ValidationError(f"commit_sha must be 40 hex characters, got: {self.commit_sha}")

        # Validate verified_at timestamp not in future
        now = datetime.utcnow()
        if self.verified_at > now:
            raise ValidationError("verified_at cannot be in the future")

        # Validate explanation depth constraints (Requirements 23.6, 23.7)
        if self.explanation_recorded and self.explanation_depth is None:
            raise ValidationError("explanation_depth must be set when explanation_recorded is True")

        if self.explanation_depth is not None:
            if not (0.0 <= self.explanation_depth <= 1.0):
                raise ValidationError(
                    f"explanation_depth must be between 0.0 and 1.0, got: {self.explanation_depth}"
                )
