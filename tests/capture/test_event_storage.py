"""Unit tests for learning event storage with filtering and deduplication.

Tests Requirement 3.8: Store significant learning events in database
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from learnloop.capture.event_storage import (
    CONFIDENCE_THRESHOLD,
    get_learning_events_by_project,
    store_learning_event,
    store_learning_events,
)
from learnloop.domain.learning_event import EventSource, EventType, LearningEvent


@pytest.fixture
def db_conn(tmp_path):
    """Create a temporary database with learning_events table."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    
    # Create projects table
    conn.execute("""
        CREATE TABLE projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            repo_path TEXT NOT NULL
        )
    """)
    
    # Create learning_events table
    conn.execute("""
        CREATE TABLE learning_events (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            event_type TEXT NOT NULL CHECK (event_type IN ('implementation', 'decision', 'question', 'explanation')),
            source TEXT NOT NULL CHECK (source IN ('conversation', 'commit', 'manual')),
            timestamp TEXT NOT NULL,
            content_json TEXT NOT NULL,
            skills_json TEXT NOT NULL,
            confidence REAL NOT NULL CHECK (confidence BETWEEN 0.0 AND 1.0),
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    
    # Insert test project
    conn.execute(
        "INSERT INTO projects (id, name, repo_path) VALUES (?, ?, ?)",
        ("test-project", "Test Project", "/test/path")
    )
    conn.commit()
    
    yield conn
    conn.close()


def create_test_event(
    project_id: str = "test-project",
    confidence: float = 0.8,
    event_type: EventType = EventType.IMPLEMENTATION,
    content: dict | None = None,
    unique_content: bool = True
) -> LearningEvent:
    """Helper to create test learning events.
    
    Args:
        unique_content: If True, adds unique identifier to content to avoid deduplication
    """
    if content is None:
        if unique_content:
            # Make content unique by adding a UUID to avoid unintended deduplication
            content = {"code": f"def test_{uuid4().hex[:8]}(): pass", "language": "python"}
        else:
            content = {"code": "def test(): pass", "language": "python"}
    
    return LearningEvent(
        id=str(uuid4()),
        project_id=project_id,
        event_type=event_type,
        timestamp=datetime.now(timezone.utc),
        content=content,
        skills=["python", "testing"],
        confidence=confidence,
        source=EventSource.CONVERSATION
    )


class TestStoreLearningEvent:
    """Test storing single learning events."""
    
    def test_store_event_above_threshold(self, db_conn):
        """Test storing event with confidence above threshold (Requirement 3.8)."""
        event = create_test_event(confidence=0.75)
        
        result = store_learning_event(db_conn, event)
        
        assert result['stored'] is True
        assert result['event_id'] == event.id
        
        # Verify in database
        row = db_conn.execute(
            "SELECT * FROM learning_events WHERE id = ?",
            (event.id,)
        ).fetchone()
        assert row is not None
        assert row['confidence'] == 0.75
    
    def test_store_event_at_threshold(self, db_conn):
        """Test that events exactly at threshold are not stored."""
        event = create_test_event(confidence=CONFIDENCE_THRESHOLD)
        
        result = store_learning_event(db_conn, event)
        
        assert result['stored'] is False
        assert 'confidence' in result['reason']
    
    def test_store_event_below_threshold(self, db_conn):
        """Test filtering events below confidence threshold (Requirement 3.8)."""
        event = create_test_event(confidence=0.5)
        
        result = store_learning_event(db_conn, event)
        
        assert result['stored'] is False
        assert 'confidence' in result['reason']
        
        # Verify not in database
        row = db_conn.execute(
            "SELECT * FROM learning_events WHERE id = ?",
            (event.id,)
        ).fetchone()
        assert row is None
    
    def test_store_event_minimum_passing_confidence(self, db_conn):
        """Test storing event just above threshold."""
        event = create_test_event(confidence=0.71)
        
        result = store_learning_event(db_conn, event)
        
        assert result['stored'] is True
    
    def test_store_event_maximum_confidence(self, db_conn):
        """Test storing event with maximum confidence."""
        event = create_test_event(confidence=1.0)
        
        result = store_learning_event(db_conn, event)
        
        assert result['stored'] is True
    
    def test_store_duplicate_event_detected(self, db_conn):
        """Test deduplication of identical events (Requirement 3.8)."""
        content = {"code": "x = 1", "language": "python"}
        event1 = create_test_event(content=content, confidence=0.8, unique_content=False)
        event2 = create_test_event(content=content, confidence=0.85, unique_content=False)
        
        # Store first event
        result1 = store_learning_event(db_conn, event1)
        assert result1['stored'] is True
        
        # Try to store duplicate
        result2 = store_learning_event(db_conn, event2)
        assert result2['stored'] is False
        assert 'duplicate' in result2['reason']
    
    def test_store_different_events_not_duplicate(self, db_conn):
        """Test that different events are not considered duplicates."""
        event1 = create_test_event(content={"code": "x = 1"}, confidence=0.8)
        event2 = create_test_event(content={"code": "y = 2"}, confidence=0.8)
        
        result1 = store_learning_event(db_conn, event1)
        result2 = store_learning_event(db_conn, event2)
        
        assert result1['stored'] is True
        assert result2['stored'] is True
    
    def test_store_duplicate_different_type_allowed(self, db_conn):
        """Test that same content with different event type is allowed."""
        content = {"code": "x = 1"}
        event1 = create_test_event(
            content=content,
            confidence=0.8,
            event_type=EventType.IMPLEMENTATION
        )
        event2 = create_test_event(
            content=content,
            confidence=0.8,
            event_type=EventType.DECISION
        )
        
        result1 = store_learning_event(db_conn, event1)
        result2 = store_learning_event(db_conn, event2)
        
        # Both should be stored since they're different types
        assert result1['stored'] is True
        assert result2['stored'] is True
    
    def test_store_without_deduplication(self, db_conn):
        """Test storing with deduplication disabled."""
        content = {"code": "x = 1"}
        event1 = create_test_event(content=content, confidence=0.8, unique_content=False)
        event2 = create_test_event(content=content, confidence=0.8, unique_content=False)
        
        result1 = store_learning_event(db_conn, event1, deduplicate=True)
        result2 = store_learning_event(db_conn, event2, deduplicate=False)
        
        assert result1['stored'] is True
        assert result2['stored'] is True  # Should store despite duplicate
    
    def test_store_event_with_empty_skills(self, db_conn):
        """Test storing event with empty skills list."""
        event = LearningEvent(
            id=str(uuid4()),
            project_id="test-project",
            event_type=EventType.IMPLEMENTATION,
            timestamp=datetime.now(timezone.utc),
            content={"code": "test"},
            skills=[],  # Empty skills
            confidence=0.8,
            source=EventSource.CONVERSATION
        )
        
        result = store_learning_event(db_conn, event)
        
        assert result['stored'] is True
    
    def test_store_event_with_complex_content(self, db_conn):
        """Test storing event with complex nested content."""
        event = create_test_event(
            content={
                "code": "def complex(): pass",
                "metadata": {
                    "language": "python",
                    "complexity": 0.5,
                    "features": ["async", "decorators"]
                }
            },
            confidence=0.8
        )
        
        result = store_learning_event(db_conn, event)
        
        assert result['stored'] is True
    
    def test_store_event_duplicate_id_fails(self, db_conn):
        """Test that storing event with duplicate ID fails gracefully."""
        event_id = str(uuid4())
        event1 = LearningEvent(
            id=event_id,
            project_id="test-project",
            event_type=EventType.IMPLEMENTATION,
            timestamp=datetime.now(timezone.utc),
            content={"code": "x = 1"},
            skills=["python"],
            confidence=0.8,
            source=EventSource.CONVERSATION
        )
        event2 = LearningEvent(
            id=event_id,  # Same ID
            project_id="test-project",
            event_type=EventType.IMPLEMENTATION,
            timestamp=datetime.now(timezone.utc),
            content={"code": "y = 2"},  # Different content
            skills=["python"],
            confidence=0.9,
            source=EventSource.CONVERSATION
        )
        
        result1 = store_learning_event(db_conn, event1)
        result2 = store_learning_event(db_conn, event2)
        
        assert result1['stored'] is True
        assert result2['stored'] is False
        assert 'integrity' in result2['reason'].lower()


class TestStoreLearningEvents:
    """Test batch storing of learning events."""
    
    def test_store_multiple_events(self, db_conn):
        """Test storing multiple events at once."""
        events = [
            create_test_event(confidence=0.8),
            create_test_event(confidence=0.9),
            create_test_event(confidence=0.75)
        ]
        
        result = store_learning_events(db_conn, events)
        
        assert result['stored_count'] == 3
        assert result['filtered_count'] == 0
        assert result['duplicate_count'] == 0
        assert len(result['stored_ids']) == 3
    
    def test_store_events_with_filtering(self, db_conn):
        """Test that low confidence events are filtered in batch."""
        events = [
            create_test_event(confidence=0.8),   # Should store
            create_test_event(confidence=0.5),   # Should filter
            create_test_event(confidence=0.9),   # Should store
            create_test_event(confidence=0.6),   # Should filter
        ]
        
        result = store_learning_events(db_conn, events)
        
        assert result['stored_count'] == 2
        assert result['filtered_count'] == 2
        assert result['duplicate_count'] == 0
    
    def test_store_events_with_duplicates(self, db_conn):
        """Test deduplication in batch storage."""
        content = {"code": "x = 1"}
        events = [
            create_test_event(content=content, confidence=0.8, unique_content=False),
            create_test_event(content=content, confidence=0.85, unique_content=False),  # Duplicate
            create_test_event(content={"code": "y = 2"}, confidence=0.9, unique_content=False)
        ]
        
        result = store_learning_events(db_conn, events)
        
        assert result['stored_count'] == 2
        assert result['duplicate_count'] == 1
    
    def test_store_events_mixed_results(self, db_conn):
        """Test batch with mixed results (stored, filtered, duplicated)."""
        content = {"code": "test"}
        events = [
            create_test_event(content=content, confidence=0.8, unique_content=False),  # Store
            create_test_event(confidence=0.5),                    # Filter
            create_test_event(content=content, confidence=0.9, unique_content=False),  # Duplicate
            create_test_event(confidence=0.75),                   # Store
        ]
        
        result = store_learning_events(db_conn, events)
        
        assert result['stored_count'] == 2
        assert result['filtered_count'] == 1
        assert result['duplicate_count'] == 1
    
    def test_store_empty_event_list(self, db_conn):
        """Test storing empty list of events."""
        result = store_learning_events(db_conn, [])
        
        assert result['stored_count'] == 0
        assert result['filtered_count'] == 0
        assert result['duplicate_count'] == 0


class TestGetLearningEvents:
    """Test retrieving learning events from database."""
    
    def test_get_events_by_project(self, db_conn):
        """Test retrieving all events for a project."""
        events = [
            create_test_event(confidence=0.8),
            create_test_event(confidence=0.9)
        ]
        store_learning_events(db_conn, events)
        
        retrieved = get_learning_events_by_project(db_conn, "test-project")
        
        assert len(retrieved) == 2
        assert all(e.project_id == "test-project" for e in retrieved)
    
    def test_get_events_filter_by_type(self, db_conn):
        """Test filtering events by type."""
        events = [
            create_test_event(event_type=EventType.IMPLEMENTATION, confidence=0.8),
            create_test_event(event_type=EventType.DECISION, confidence=0.9)
        ]
        store_learning_events(db_conn, events)
        
        retrieved = get_learning_events_by_project(
            db_conn,
            "test-project",
            event_type=EventType.IMPLEMENTATION
        )
        
        assert len(retrieved) == 1
        assert retrieved[0].event_type == EventType.IMPLEMENTATION
    
    def test_get_events_filter_by_confidence(self, db_conn):
        """Test filtering events by minimum confidence."""
        events = [
            create_test_event(confidence=0.75),
            create_test_event(confidence=0.85),
            create_test_event(confidence=0.95)
        ]
        store_learning_events(db_conn, events)
        
        retrieved = get_learning_events_by_project(
            db_conn,
            "test-project",
            min_confidence=0.8
        )
        
        assert len(retrieved) == 2
        assert all(e.confidence >= 0.8 for e in retrieved)
    
    def test_get_events_with_limit(self, db_conn):
        """Test limiting number of results."""
        events = [create_test_event(confidence=0.8) for _ in range(5)]
        store_learning_events(db_conn, events)
        
        retrieved = get_learning_events_by_project(
            db_conn,
            "test-project",
            limit=3
        )
        
        assert len(retrieved) == 3
    
    def test_get_events_ordered_by_timestamp(self, db_conn):
        """Test that events are returned in descending timestamp order."""
        now = datetime.now(timezone.utc)
        events = [
            LearningEvent(
                id=str(uuid4()),
                project_id="test-project",
                event_type=EventType.IMPLEMENTATION,
                timestamp=now - timedelta(hours=i),
                content={"code": f"test{i}"},
                skills=["python"],
                confidence=0.8,
                source=EventSource.CONVERSATION
            )
            for i in range(3)
        ]
        store_learning_events(db_conn, events)
        
        retrieved = get_learning_events_by_project(db_conn, "test-project")
        
        # Should be in descending order (most recent first)
        assert len(retrieved) == 3
        for i in range(len(retrieved) - 1):
            assert retrieved[i].timestamp >= retrieved[i + 1].timestamp
    
    def test_get_events_no_results(self, db_conn):
        """Test querying when no events exist."""
        retrieved = get_learning_events_by_project(db_conn, "test-project")
        
        assert len(retrieved) == 0
    
    def test_get_events_nonexistent_project(self, db_conn):
        """Test querying for nonexistent project returns empty list."""
        event = create_test_event(confidence=0.8)
        store_learning_event(db_conn, event)
        
        retrieved = get_learning_events_by_project(db_conn, "nonexistent-project")
        
        assert len(retrieved) == 0


class TestDeduplicationTimeWindow:
    """Test deduplication time window behavior."""
    
    def test_duplicate_outside_window_allowed(self, db_conn):
        """Test that duplicates outside 24h window are allowed."""
        # Store event with old timestamp
        old_event = LearningEvent(
            id=str(uuid4()),
            project_id="test-project",
            event_type=EventType.IMPLEMENTATION,
            timestamp=datetime.now(timezone.utc) - timedelta(hours=25),
            content={"code": "x = 1"},
            skills=["python"],
            confidence=0.8,
            source=EventSource.CONVERSATION
        )
        
        # Manually insert with old timestamp to bypass deduplication
        import json
        db_conn.execute(
            """
            INSERT INTO learning_events
            (id, project_id, event_type, source, timestamp, content_json, skills_json, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                old_event.id,
                old_event.project_id,
                old_event.event_type.value,
                old_event.source.value,
                (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat(),
                json.dumps(old_event.content),
                json.dumps(old_event.skills),
                old_event.confidence
            )
        )
        db_conn.commit()
        
        # Try to store new event with same content
        new_event = create_test_event(content={"code": "x = 1"}, confidence=0.8, unique_content=False)
        result = store_learning_event(db_conn, new_event)
        
        # Should be allowed since old event is outside window
        assert result['stored'] is True


class TestConfidenceThreshold:
    """Test confidence threshold constant."""
    
    def test_confidence_threshold_value(self):
        """Test that confidence threshold is set correctly (Requirement 3.8)."""
        assert CONFIDENCE_THRESHOLD == 0.7
    
    def test_events_at_boundary(self, db_conn):
        """Test events at boundary conditions."""
        # Event at threshold should not be stored
        event_at = create_test_event(confidence=0.7)
        result_at = store_learning_event(db_conn, event_at)
        assert result_at['stored'] is False
        
        # Event just above threshold should be stored
        event_above = create_test_event(confidence=0.7001)
        result_above = store_learning_event(db_conn, event_above)
        assert result_above['stored'] is True
