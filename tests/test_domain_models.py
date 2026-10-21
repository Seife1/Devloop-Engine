"""Unit tests for KnowledgeItem and ReviewSchedule models.

Tests cover validation rules from Requirements 9.1-9.3, 15.2-15.4, 23.8-23.11.
"""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from learnloop.domain.errors import ValidationError
from learnloop.domain.models import (
    DEFAULT_EASINESS,
    MAX_EASINESS,
    MIN_EASINESS,
    DepthBand,
    IntentRecord,
    IntentStatus,
    KnowledgeItem,
    ReviewSchedule,
    create_initial_review_schedule,
)


class TestIntentRecord:
    """Test IntentRecord validation and behavior."""

    def test_valid_open_intent(self) -> None:
        """Test creating a valid IntentRecord with OPEN status."""
        now = datetime.utcnow()
        intent = IntentRecord(
            id=str(uuid4()),
            session_id="session-123",
            project_id=str(uuid4()),
            intent_description="Implement user authentication",
            files=["src/auth/login.py", "src/auth/tokens.py"],
            skills=["python.authentication", "python.jwt"],
            created_at=now,
            status=IntentStatus.OPEN,
        )

        assert intent.status == IntentStatus.OPEN
        assert intent.matched_commit_sha is None
        assert intent.closed_at is None
        assert len(intent.files) == 2
        assert len(intent.skills) == 2

    def test_valid_matched_intent(self) -> None:
        """Test creating a valid IntentRecord with MATCHED status (Requirement 23.4)."""
        now = datetime.utcnow()
        closed = now + timedelta(minutes=30)
        intent = IntentRecord(
            id=str(uuid4()),
            session_id="session-123",
            project_id=str(uuid4()),
            intent_description="Implement user authentication",
            files=["src/auth/login.py"],
            skills=["python.authentication"],
            created_at=now,
            status=IntentStatus.MATCHED,
            matched_commit_sha="abc123def456",
            closed_at=closed,
        )

        assert intent.status == IntentStatus.MATCHED
        assert intent.matched_commit_sha == "abc123def456"
        assert intent.closed_at == closed

    def test_valid_abandoned_intent(self) -> None:
        """Test creating a valid IntentRecord with ABANDONED status (Requirement 23.5)."""
        now = datetime.utcnow()
        closed = now + timedelta(days=14)
        intent = IntentRecord(
            id=str(uuid4()),
            session_id="session-123",
            project_id=str(uuid4()),
            intent_description="Implement user authentication",
            files=["src/auth/login.py"],
            skills=["python.authentication"],
            created_at=now,
            status=IntentStatus.ABANDONED,
            closed_at=closed,
        )

        assert intent.status == IntentStatus.ABANDONED
        assert intent.matched_commit_sha is None
        assert intent.closed_at == closed

    def test_matched_status_without_commit_sha(self) -> None:
        """Test that MATCHED status requires matched_commit_sha (Requirement 23.4)."""
        now = datetime.utcnow()
        closed = now + timedelta(minutes=30)

        with pytest.raises(
            ValidationError, match="matched_commit_sha must not be None when status is MATCHED"
        ):
            IntentRecord(
                id=str(uuid4()),
                session_id="session-123",
                project_id=str(uuid4()),
                intent_description="Implement user authentication",
                files=["src/auth/login.py"],
                skills=["python.authentication"],
                created_at=now,
                status=IntentStatus.MATCHED,
                matched_commit_sha=None,
                closed_at=closed,
            )

    def test_matched_status_without_closed_at(self) -> None:
        """Test that MATCHED status requires closed_at (Requirement 23.5)."""
        now = datetime.utcnow()

        with pytest.raises(ValidationError, match="closed_at must not be None when status is not OPEN"):
            IntentRecord(
                id=str(uuid4()),
                session_id="session-123",
                project_id=str(uuid4()),
                intent_description="Implement user authentication",
                files=["src/auth/login.py"],
                skills=["python.authentication"],
                created_at=now,
                status=IntentStatus.MATCHED,
                matched_commit_sha="abc123def456",
                closed_at=None,
            )

    def test_abandoned_status_without_closed_at(self) -> None:
        """Test that ABANDONED status requires closed_at (Requirement 23.5)."""
        now = datetime.utcnow()

        with pytest.raises(ValidationError, match="closed_at must not be None when status is not OPEN"):
            IntentRecord(
                id=str(uuid4()),
                session_id="session-123",
                project_id=str(uuid4()),
                intent_description="Implement user authentication",
                files=["src/auth/login.py"],
                skills=["python.authentication"],
                created_at=now,
                status=IntentStatus.ABANDONED,
                closed_at=None,
            )

    def test_closed_at_before_created_at(self) -> None:
        """Test that closed_at must be >= created_at (Requirement 23.5)."""
        now = datetime.utcnow()
        past = now - timedelta(minutes=1)

        with pytest.raises(ValidationError, match="closed_at must be >= created_at"):
            IntentRecord(
                id=str(uuid4()),
                session_id="session-123",
                project_id=str(uuid4()),
                intent_description="Implement user authentication",
                files=["src/auth/login.py"],
                skills=["python.authentication"],
                created_at=now,
                status=IntentStatus.MATCHED,
                matched_commit_sha="abc123def456",
                closed_at=past,
            )

    def test_empty_files_list(self) -> None:
        """Test that files list must not be empty."""
        now = datetime.utcnow()

        with pytest.raises(ValidationError, match="files list must not be empty"):
            IntentRecord(
                id=str(uuid4()),
                session_id="session-123",
                project_id=str(uuid4()),
                intent_description="Implement user authentication",
                files=[],
                skills=["python.authentication"],
                created_at=now,
                status=IntentStatus.OPEN,
            )

    def test_open_status_with_commit_sha(self) -> None:
        """Test that OPEN status can have matched_commit_sha as None."""
        now = datetime.utcnow()
        intent = IntentRecord(
            id=str(uuid4()),
            session_id="session-123",
            project_id=str(uuid4()),
            intent_description="Implement user authentication",
            files=["src/auth/login.py"],
            skills=["python.authentication"],
            created_at=now,
            status=IntentStatus.OPEN,
            matched_commit_sha=None,
            closed_at=None,
        )

        assert intent.status == IntentStatus.OPEN
        assert intent.matched_commit_sha is None
        assert intent.closed_at is None

    def test_matched_intent_with_multiple_files(self) -> None:
        """Test IntentRecord with multiple files."""
        now = datetime.utcnow()
        closed = now + timedelta(minutes=30)
        files = [
            "src/auth/login.py",
            "src/auth/tokens.py",
            "src/auth/middleware.py",
            "tests/test_auth.py",
        ]
        intent = IntentRecord(
            id=str(uuid4()),
            session_id="session-123",
            project_id=str(uuid4()),
            intent_description="Implement authentication system",
            files=files,
            skills=["python.authentication", "python.jwt", "python.testing"],
            created_at=now,
            status=IntentStatus.MATCHED,
            matched_commit_sha="abc123def456",
            closed_at=closed,
        )

        assert len(intent.files) == 4
        assert len(intent.skills) == 3


class TestKnowledgeItem:
    """Test KnowledgeItem validation and behavior."""

    def test_valid_knowledge_item(self) -> None:
        """Test creating a valid KnowledgeItem with all required fields."""
        now = datetime.utcnow()
        item = KnowledgeItem(
            id=str(uuid4()),
            project_id=str(uuid4()),
            key="auth-implementation",
            title="User Authentication System",
            summary="Implemented JWT-based authentication with refresh tokens and session management.",
            tracked_files=["src/auth/login.py", "src/auth/tokens.py"],
            depth_band=DepthBand.INTERMEDIATE,
            created_at=now,
        )

        assert item.key == "auth-implementation"
        assert item.title == "User Authentication System"
        assert len(item.tracked_files) == 2
        assert item.self_rating is None
        assert not item.is_stale

    def test_knowledge_item_with_self_rating(self) -> None:
        """Test KnowledgeItem with valid self_rating (Requirement 23.8)."""
        now = datetime.utcnow()

        # Test minimum valid rating
        item1 = KnowledgeItem(
            id=str(uuid4()),
            project_id=str(uuid4()),
            key="test-1",
            title="Test Item",
            summary="Testing self rating minimum",
            tracked_files=["test.py"],
            depth_band=DepthBand.BASIC,
            created_at=now,
            self_rating=1.0,
        )
        assert item1.self_rating == 1.0

        # Test maximum valid rating
        item2 = KnowledgeItem(
            id=str(uuid4()),
            project_id=str(uuid4()),
            key="test-2",
            title="Test Item",
            summary="Testing self rating maximum",
            tracked_files=["test.py"],
            depth_band=DepthBand.BASIC,
            created_at=now,
            self_rating=5.0,
        )
        assert item2.self_rating == 5.0

        # Test mid-range rating
        item3 = KnowledgeItem(
            id=str(uuid4()),
            project_id=str(uuid4()),
            key="test-3",
            title="Test Item",
            summary="Testing self rating mid-range",
            tracked_files=["test.py"],
            depth_band=DepthBand.BASIC,
            created_at=now,
            self_rating=3.5,
        )
        assert item3.self_rating == 3.5

    def test_knowledge_item_self_rating_below_minimum(self) -> None:
        """Test that self_rating below 1.0 raises ValidationError (Requirement 23.8)."""
        now = datetime.utcnow()

        with pytest.raises(ValidationError, match="self_rating must be between 1.0 and 5.0"):
            KnowledgeItem(
                id=str(uuid4()),
                project_id=str(uuid4()),
                key="test",
                title="Test Item",
                summary="Invalid rating",
                tracked_files=["test.py"],
                depth_band=DepthBand.BASIC,
                created_at=now,
                self_rating=0.5,
            )

    def test_knowledge_item_self_rating_above_maximum(self) -> None:
        """Test that self_rating above 5.0 raises ValidationError (Requirement 23.8)."""
        now = datetime.utcnow()

        with pytest.raises(ValidationError, match="self_rating must be between 1.0 and 5.0"):
            KnowledgeItem(
                id=str(uuid4()),
                project_id=str(uuid4()),
                key="test",
                title="Test Item",
                summary="Invalid rating",
                tracked_files=["test.py"],
                depth_band=DepthBand.BASIC,
                created_at=now,
                self_rating=5.5,
            )

    def test_knowledge_item_empty_title(self) -> None:
        """Test that empty title raises ValidationError (Requirement 9.2)."""
        now = datetime.utcnow()

        with pytest.raises(ValidationError, match="Title must be 1-100 characters"):
            KnowledgeItem(
                id=str(uuid4()),
                project_id=str(uuid4()),
                key="test",
                title="",
                summary="Valid summary",
                tracked_files=["test.py"],
                depth_band=DepthBand.BASIC,
                created_at=now,
            )

    def test_knowledge_item_title_too_long(self) -> None:
        """Test that title over 100 characters raises ValidationError (Requirement 9.2)."""
        now = datetime.utcnow()
        long_title = "A" * 101

        with pytest.raises(ValidationError, match="Title must be 1-100 characters"):
            KnowledgeItem(
                id=str(uuid4()),
                project_id=str(uuid4()),
                key="test",
                title=long_title,
                summary="Valid summary",
                tracked_files=["test.py"],
                depth_band=DepthBand.BASIC,
                created_at=now,
            )

    def test_knowledge_item_empty_summary(self) -> None:
        """Test that empty summary raises ValidationError (Requirement 9.3)."""
        now = datetime.utcnow()

        with pytest.raises(ValidationError, match="Summary must be 1-500 characters"):
            KnowledgeItem(
                id=str(uuid4()),
                project_id=str(uuid4()),
                key="test",
                title="Valid Title",
                summary="",
                tracked_files=["test.py"],
                depth_band=DepthBand.BASIC,
                created_at=now,
            )

    def test_knowledge_item_summary_too_long(self) -> None:
        """Test that summary over 500 characters raises ValidationError (Requirement 9.3)."""
        now = datetime.utcnow()
        long_summary = "A" * 501

        with pytest.raises(ValidationError, match="Summary must be 1-500 characters"):
            KnowledgeItem(
                id=str(uuid4()),
                project_id=str(uuid4()),
                key="test",
                title="Valid Title",
                summary=long_summary,
                tracked_files=["test.py"],
                depth_band=DepthBand.BASIC,
                created_at=now,
            )

    def test_knowledge_item_empty_tracked_files(self) -> None:
        """Test that empty tracked_files raises ValidationError (Requirement 9.4)."""
        now = datetime.utcnow()

        with pytest.raises(ValidationError, match="tracked_files must contain at least one file"):
            KnowledgeItem(
                id=str(uuid4()),
                project_id=str(uuid4()),
                key="test",
                title="Valid Title",
                summary="Valid summary",
                tracked_files=[],
                depth_band=DepthBand.BASIC,
                created_at=now,
            )

    def test_knowledge_item_stale_without_stale_since(self) -> None:
        """Test that is_stale=True requires stale_since."""
        now = datetime.utcnow()

        with pytest.raises(ValidationError, match="stale_since must not be None when is_stale is True"):
            KnowledgeItem(
                id=str(uuid4()),
                project_id=str(uuid4()),
                key="test",
                title="Valid Title",
                summary="Valid summary",
                tracked_files=["test.py"],
                depth_band=DepthBand.BASIC,
                created_at=now,
                is_stale=True,
                stale_since=None,
            )

    def test_knowledge_item_stale_with_stale_since(self) -> None:
        """Test valid stale KnowledgeItem with stale_since."""
        now = datetime.utcnow()
        stale_time = now - timedelta(days=2)

        item = KnowledgeItem(
            id=str(uuid4()),
            project_id=str(uuid4()),
            key="test",
            title="Valid Title",
            summary="Valid summary",
            tracked_files=["test.py"],
            depth_band=DepthBand.BASIC,
            created_at=now,
            is_stale=True,
            stale_since=stale_time,
        )

        assert item.is_stale
        assert item.stale_since == stale_time

    def test_knowledge_item_future_last_explained_at(self) -> None:
        """Test that last_explained_at in future raises ValidationError."""
        now = datetime.utcnow()
        future = now + timedelta(days=1)

        with pytest.raises(ValidationError, match="last_explained_at cannot be in the future"):
            KnowledgeItem(
                id=str(uuid4()),
                project_id=str(uuid4()),
                key="test",
                title="Valid Title",
                summary="Valid summary",
                tracked_files=["test.py"],
                depth_band=DepthBand.BASIC,
                created_at=now,
                last_explained_at=future,
            )


class TestReviewSchedule:
    """Test ReviewSchedule validation and behavior."""

    def test_valid_review_schedule(self) -> None:
        """Test creating a valid ReviewSchedule with all required fields."""
        now = datetime.utcnow()
        due = now + timedelta(days=3)

        schedule = ReviewSchedule(
            id=str(uuid4()),
            item_id=str(uuid4()),
            interval=3,
            easiness=2.3,
            repetitions=2,
            due_at=due,
            last_reviewed_at=now,
        )

        assert schedule.interval == 3
        assert schedule.easiness == 2.3
        assert schedule.repetitions == 2
        assert schedule.success_streak == 0

    def test_review_schedule_easiness_minimum(self) -> None:
        """Test ReviewSchedule with minimum easiness (Requirements 15.2, 23.9)."""
        now = datetime.utcnow()
        due = now + timedelta(days=1)

        schedule = ReviewSchedule(
            id=str(uuid4()),
            item_id=str(uuid4()),
            interval=1,
            easiness=MIN_EASINESS,
            repetitions=0,
            due_at=due,
        )

        assert schedule.easiness == MIN_EASINESS

    def test_review_schedule_easiness_maximum(self) -> None:
        """Test ReviewSchedule with maximum easiness (Requirements 15.2, 23.9)."""
        now = datetime.utcnow()
        due = now + timedelta(days=1)

        schedule = ReviewSchedule(
            id=str(uuid4()),
            item_id=str(uuid4()),
            interval=1,
            easiness=MAX_EASINESS,
            repetitions=0,
            due_at=due,
        )

        assert schedule.easiness == MAX_EASINESS

    def test_review_schedule_easiness_below_minimum(self) -> None:
        """Test that easiness below 1.3 raises ValidationError (Requirements 15.10, 23.9)."""
        now = datetime.utcnow()
        due = now + timedelta(days=1)

        with pytest.raises(ValidationError, match="easiness must be between 1.3 and 2.5"):
            ReviewSchedule(
                id=str(uuid4()),
                item_id=str(uuid4()),
                interval=1,
                easiness=1.2,
                repetitions=0,
                due_at=due,
            )

    def test_review_schedule_easiness_above_maximum(self) -> None:
        """Test that easiness above 2.5 raises ValidationError (Requirements 15.10, 23.9)."""
        now = datetime.utcnow()
        due = now + timedelta(days=1)

        with pytest.raises(ValidationError, match="easiness must be between 1.3 and 2.5"):
            ReviewSchedule(
                id=str(uuid4()),
                item_id=str(uuid4()),
                interval=1,
                easiness=2.6,
                repetitions=0,
                due_at=due,
            )

    def test_review_schedule_interval_zero(self) -> None:
        """Test that interval of 0 raises ValidationError (Requirements 15.3, 23.10)."""
        now = datetime.utcnow()
        due = now + timedelta(days=1)

        with pytest.raises(ValidationError, match="interval must be positive"):
            ReviewSchedule(
                id=str(uuid4()),
                item_id=str(uuid4()),
                interval=0,
                easiness=2.3,
                repetitions=0,
                due_at=due,
            )

    def test_review_schedule_interval_negative(self) -> None:
        """Test that negative interval raises ValidationError (Requirements 15.3, 23.10)."""
        now = datetime.utcnow()
        due = now + timedelta(days=1)

        with pytest.raises(ValidationError, match="interval must be positive"):
            ReviewSchedule(
                id=str(uuid4()),
                item_id=str(uuid4()),
                interval=-1,
                easiness=2.3,
                repetitions=0,
                due_at=due,
            )

    def test_review_schedule_repetitions_negative(self) -> None:
        """Test that negative repetitions raises ValidationError (Requirements 15.4, 23.11)."""
        now = datetime.utcnow()
        due = now + timedelta(days=1)

        with pytest.raises(ValidationError, match="repetitions must be non-negative"):
            ReviewSchedule(
                id=str(uuid4()),
                item_id=str(uuid4()),
                interval=1,
                easiness=2.3,
                repetitions=-1,
                due_at=due,
            )

    def test_review_schedule_repetitions_zero(self) -> None:
        """Test that repetitions of 0 is valid (Requirements 15.4, 23.11)."""
        now = datetime.utcnow()
        due = now + timedelta(days=1)

        schedule = ReviewSchedule(
            id=str(uuid4()),
            item_id=str(uuid4()),
            interval=1,
            easiness=2.3,
            repetitions=0,
            due_at=due,
        )

        assert schedule.repetitions == 0

    def test_review_schedule_repetitions_without_last_reviewed(self) -> None:
        """Test that repetitions > 0 requires last_reviewed_at (Requirement 15.12)."""
        now = datetime.utcnow()
        due = now + timedelta(days=1)

        with pytest.raises(ValidationError, match="last_reviewed_at must not be None when repetitions > 0"):
            ReviewSchedule(
                id=str(uuid4()),
                item_id=str(uuid4()),
                interval=1,
                easiness=2.3,
                repetitions=1,
                due_at=due,
                last_reviewed_at=None,
            )

    def test_review_schedule_due_at_before_last_reviewed(self) -> None:
        """Test that due_at must be >= last_reviewed_at (Requirement 15.12)."""
        now = datetime.utcnow()
        past = now - timedelta(days=1)

        with pytest.raises(ValidationError, match="due_at must be >= last_reviewed_at"):
            ReviewSchedule(
                id=str(uuid4()),
                item_id=str(uuid4()),
                interval=1,
                easiness=2.3,
                repetitions=1,
                due_at=past,
                last_reviewed_at=now,
            )

    def test_review_schedule_success_streak_negative(self) -> None:
        """Test that negative success_streak raises ValidationError."""
        now = datetime.utcnow()
        due = now + timedelta(days=1)

        with pytest.raises(ValidationError, match="success_streak must be non-negative"):
            ReviewSchedule(
                id=str(uuid4()),
                item_id=str(uuid4()),
                interval=1,
                easiness=2.3,
                repetitions=0,
                due_at=due,
                success_streak=-1,
            )


class TestCreateInitialReviewSchedule:
    """Test initial schedule creation."""

    def test_create_initial_schedule(self) -> None:
        """Test creating initial schedule with default parameters (Requirements 15.1-15.4)."""
        item_id = str(uuid4())
        schedule = create_initial_review_schedule(item_id)

        # Verify initial parameters
        assert schedule.item_id == item_id
        assert schedule.interval == 1
        assert schedule.easiness == DEFAULT_EASINESS
        assert schedule.repetitions == 0
        assert schedule.success_streak == 0
        assert schedule.last_reviewed_at is None

        # Verify due date is approximately 1 day from now
        from datetime import timezone
        now = datetime.now(timezone.utc)
        expected_due = now + timedelta(days=1)
        time_diff = abs((schedule.due_at - expected_due).total_seconds())
        assert time_diff < 2  # Allow 2 seconds tolerance

    def test_create_initial_schedule_with_custom_id(self) -> None:
        """Test creating initial schedule with custom schedule ID."""
        item_id = str(uuid4())
        schedule_id = str(uuid4())
        schedule = create_initial_review_schedule(item_id, schedule_id)

        assert schedule.id == schedule_id
        assert schedule.item_id == item_id
