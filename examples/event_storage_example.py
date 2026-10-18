"""Example usage of learning event storage module.

This example demonstrates how to:
1. Create learning events from detected code
2. Filter events by confidence threshold
3. Store events with automatic deduplication
4. Retrieve stored events
"""

import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

from learnloop.capture.event_storage import (
    CONFIDENCE_THRESHOLD,
    get_learning_events_by_project,
    store_learning_event,
    store_learning_events,
)
from learnloop.domain.learning_event import EventSource, EventType, LearningEvent


def setup_database() -> sqlite3.Connection:
    """Create an in-memory database for the example."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    
    # Create minimal schema
    conn.execute("""
        CREATE TABLE projects (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            repo_path TEXT NOT NULL
        )
    """)
    
    conn.execute("""
        CREATE TABLE learning_events (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(id),
            event_type TEXT NOT NULL,
            source TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            content_json TEXT NOT NULL,
            skills_json TEXT NOT NULL,
            confidence REAL NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    
    # Insert example project
    conn.execute(
        "INSERT INTO projects (id, name, repo_path) VALUES (?, ?, ?)",
        ("project-1", "My Project", "/path/to/project")
    )
    conn.commit()
    
    return conn


def main():
    """Run the example."""
    print("Learning Event Storage Example")
    print("=" * 50)
    
    # Setup
    conn = setup_database()
    project_id = "project-1"
    
    print(f"\nConfidence threshold: {CONFIDENCE_THRESHOLD}")
    
    # Example 1: Store a high-confidence event
    print("\n1. Storing high-confidence event...")
    high_confidence_event = LearningEvent(
        id=str(uuid4()),
        project_id=project_id,
        event_type=EventType.IMPLEMENTATION,
        timestamp=datetime.now(timezone.utc),
        content={
            "code": "async def fetch_data(url: str) -> dict:\n    return await http.get(url)",
            "language": "python",
            "description": "Async function with type hints"
        },
        skills=["python", "async", "typing"],
        confidence=0.85,
        source=EventSource.CONVERSATION
    )
    
    result = store_learning_event(conn, high_confidence_event)
    print(f"   Result: {result}")
    
    # Example 2: Try to store a low-confidence event (will be filtered)
    print("\n2. Trying to store low-confidence event...")
    low_confidence_event = LearningEvent(
        id=str(uuid4()),
        project_id=project_id,
        event_type=EventType.IMPLEMENTATION,
        timestamp=datetime.now(timezone.utc),
        content={"code": "x = 1", "language": "python"},
        skills=["python"],
        confidence=0.5,  # Below threshold
        source=EventSource.CONVERSATION
    )
    
    result = store_learning_event(conn, low_confidence_event)
    print(f"   Result: {result}")
    
    # Example 3: Try to store a duplicate (will be deduplicated)
    print("\n3. Trying to store duplicate event...")
    duplicate_event = LearningEvent(
        id=str(uuid4()),
        project_id=project_id,
        event_type=EventType.IMPLEMENTATION,
        timestamp=datetime.now(timezone.utc),
        content={
            "code": "async def fetch_data(url: str) -> dict:\n    return await http.get(url)",
            "language": "python",
            "description": "Async function with type hints"
        },
        skills=["python", "async"],
        confidence=0.9,
        source=EventSource.CONVERSATION
    )
    
    result = store_learning_event(conn, duplicate_event)
    print(f"   Result: {result}")
    
    # Example 4: Store multiple events at once
    print("\n4. Storing multiple events in batch...")
    events = [
        LearningEvent(
            id=str(uuid4()),
            project_id=project_id,
            event_type=EventType.DECISION,
            timestamp=datetime.now(timezone.utc),
            content={
                "decision": "Use SQLite for local storage",
                "alternatives": ["PostgreSQL", "MongoDB"],
                "rationale": "Simplicity and no server required"
            },
            skills=["databases", "architecture"],
            confidence=0.75,
            source=EventSource.CONVERSATION
        ),
        LearningEvent(
            id=str(uuid4()),
            project_id=project_id,
            event_type=EventType.IMPLEMENTATION,
            timestamp=datetime.now(timezone.utc),
            content={
                "code": "class DataProcessor:\n    def process(self, data): pass",
                "language": "python"
            },
            skills=["python", "oop"],
            confidence=0.6,  # Below threshold - will be filtered
            source=EventSource.COMMIT
        ),
        LearningEvent(
            id=str(uuid4()),
            project_id=project_id,
            event_type=EventType.QUESTION,
            timestamp=datetime.now(timezone.utc),
            content={
                "question": "How to handle database connection pooling?",
                "context": "Performance optimization"
            },
            skills=["databases", "performance"],
            confidence=0.8,
            source=EventSource.CONVERSATION
        ),
    ]
    
    result = store_learning_events(conn, events)
    print(f"   Result: {result}")
    
    # Example 5: Retrieve stored events
    print("\n5. Retrieving stored events...")
    all_events = get_learning_events_by_project(conn, project_id)
    print(f"   Total events stored: {len(all_events)}")
    
    for i, event in enumerate(all_events, 1):
        print(f"\n   Event {i}:")
        print(f"     Type: {event.event_type.value}")
        print(f"     Confidence: {event.confidence}")
        print(f"     Skills: {', '.join(event.skills)}")
        print(f"     Source: {event.source.value}")
    
    # Example 6: Filter events by type
    print("\n6. Filtering events by type...")
    decision_events = get_learning_events_by_project(
        conn,
        project_id,
        event_type=EventType.DECISION
    )
    print(f"   Decision events: {len(decision_events)}")
    
    # Example 7: Filter by confidence
    print("\n7. Filtering events by confidence...")
    high_conf_events = get_learning_events_by_project(
        conn,
        project_id,
        min_confidence=0.8
    )
    print(f"   High confidence events (≥0.8): {len(high_conf_events)}")
    
    # Cleanup
    conn.close()
    
    print("\n" + "=" * 50)
    print("Example completed successfully!")


if __name__ == "__main__":
    main()
