"""Learning event storage with filtering and deduplication.

Implements Requirement 3.8: Store significant learning events in database
with confidence threshold filtering and content-based deduplication.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime
from typing import Any

from learnloop.domain.learning_event import EventSource, EventType, LearningEvent


# Confidence threshold for storing events (Requirement 3.8)
CONFIDENCE_THRESHOLD = 0.7


def _generate_content_hash(content: dict[str, Any]) -> str:
    """Generate a hash of event content for deduplication.
    
    Args:
        content: Event content dictionary
        
    Returns:
        SHA256 hash of normalized content
    """
    # Normalize content to consistent JSON representation
    normalized = json.dumps(content, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()


def _is_duplicate_event(
    conn: sqlite3.Connection,
    project_id: str,
    content_hash: str,
    event_type: str,
    window_hours: int = 24
) -> bool:
    """Check if a similar event already exists in the database.
    
    Deduplicates based on content hash and event type within a time window.
    
    Args:
        conn: Database connection
        project_id: Project identifier
        content_hash: Hash of event content
        event_type: Type of event (implementation, decision, etc.)
        window_hours: Time window for deduplication in hours
        
    Returns:
        True if a duplicate event exists, False otherwise
    """
    # Query for similar events within the time window
    query = """
        SELECT COUNT(*) as count
        FROM learning_events
        WHERE project_id = ?
          AND event_type = ?
          AND datetime(timestamp) >= datetime('now', ? || ' hours')
    """
    
    # We'll check content similarity by comparing the stored content
    # This is a simple approach - could be enhanced with more sophisticated similarity
    result = conn.execute(query, (project_id, event_type, -window_hours)).fetchone()
    
    if not result or result['count'] == 0:
        return False
    
    # Check if any recent event has the same content hash
    similar_events = conn.execute(
        """
        SELECT content_json
        FROM learning_events
        WHERE project_id = ?
          AND event_type = ?
          AND datetime(timestamp) >= datetime('now', ? || ' hours')
        """,
        (project_id, event_type, -window_hours)
    ).fetchall()
    
    for event in similar_events:
        try:
            stored_content = json.loads(event['content_json'])
            stored_hash = _generate_content_hash(stored_content)
            if stored_hash == content_hash:
                return True
        except (json.JSONDecodeError, KeyError):
            continue
    
    return False


def store_learning_event(
    conn: sqlite3.Connection,
    event: LearningEvent,
    deduplicate: bool = True
) -> dict[str, Any]:
    """Store a learning event in the database with filtering and deduplication.
    
    Implements Requirement 3.8: Store significant learning events
    - Filters events by confidence threshold (>0.7)
    - Deduplicates based on content similarity
    - Stores in learning_events table
    
    Args:
        conn: Database connection
        event: LearningEvent instance to store
        deduplicate: Whether to check for duplicates (default True)
        
    Returns:
        Dict with:
            - stored: bool indicating if event was stored
            - event_id: str event ID if stored
            - reason: str explaining why event wasn't stored (if not stored)
            
    Raises:
        ValueError: If event validation fails
    """
    # Requirement 3.8: Filter by confidence threshold (>0.7)
    if event.confidence <= CONFIDENCE_THRESHOLD:
        return {
            'stored': False,
            'reason': f'confidence {event.confidence} <= threshold {CONFIDENCE_THRESHOLD}'
        }
    
    # Generate content hash for deduplication
    content_hash = _generate_content_hash(event.content)
    
    # Check for duplicates if requested
    if deduplicate:
        if _is_duplicate_event(
            conn,
            event.project_id,
            content_hash,
            event.event_type.value
        ):
            return {
                'stored': False,
                'reason': 'duplicate event detected'
            }
    
    # Serialize event data for storage
    content_json = json.dumps(event.content)
    skills_json = json.dumps(event.skills)
    timestamp_iso = event.timestamp.isoformat()
    
    # Insert into database
    try:
        conn.execute(
            """
            INSERT INTO learning_events
            (id, project_id, event_type, source, timestamp, content_json, skills_json, confidence)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.id,
                event.project_id,
                event.event_type.value,
                event.source.value,
                timestamp_iso,
                content_json,
                skills_json,
                event.confidence
            )
        )
        conn.commit()
        
        return {
            'stored': True,
            'event_id': event.id
        }
    
    except sqlite3.IntegrityError as e:
        # Event ID might already exist
        return {
            'stored': False,
            'reason': f'database integrity error: {str(e)}'
        }


def store_learning_events(
    conn: sqlite3.Connection,
    events: list[LearningEvent],
    deduplicate: bool = True
) -> dict[str, Any]:
    """Store multiple learning events with filtering and deduplication.
    
    Batch version of store_learning_event for processing multiple events.
    
    Args:
        conn: Database connection
        events: List of LearningEvent instances to store
        deduplicate: Whether to check for duplicates (default True)
        
    Returns:
        Dict with:
            - stored_count: int number of events successfully stored
            - filtered_count: int number of events filtered by confidence
            - duplicate_count: int number of duplicate events skipped
            - failed_count: int number of events that failed to store
            - stored_ids: list of stored event IDs
    """
    stored_count = 0
    filtered_count = 0
    duplicate_count = 0
    failed_count = 0
    stored_ids: list[str] = []
    
    for event in events:
        result = store_learning_event(conn, event, deduplicate)
        
        if result['stored']:
            stored_count += 1
            stored_ids.append(result['event_id'])
        else:
            reason = result.get('reason', '')
            if 'confidence' in reason:
                filtered_count += 1
            elif 'duplicate' in reason:
                duplicate_count += 1
            else:
                failed_count += 1
    
    return {
        'stored_count': stored_count,
        'filtered_count': filtered_count,
        'duplicate_count': duplicate_count,
        'failed_count': failed_count,
        'stored_ids': stored_ids
    }


def get_learning_events_by_project(
    conn: sqlite3.Connection,
    project_id: str,
    event_type: EventType | None = None,
    min_confidence: float | None = None,
    limit: int | None = None
) -> list[LearningEvent]:
    """Retrieve learning events from database with optional filtering.
    
    Args:
        conn: Database connection
        project_id: Project identifier
        event_type: Optional filter by event type
        min_confidence: Optional minimum confidence threshold
        limit: Optional limit on number of results
        
    Returns:
        List of LearningEvent instances
    """
    query = """
        SELECT id, project_id, event_type, source, timestamp, 
               content_json, skills_json, confidence
        FROM learning_events
        WHERE project_id = ?
    """
    params: list[Any] = [project_id]
    
    if event_type:
        query += " AND event_type = ?"
        params.append(event_type.value)
    
    if min_confidence is not None:
        query += " AND confidence >= ?"
        params.append(min_confidence)
    
    query += " ORDER BY timestamp DESC"
    
    if limit:
        query += " LIMIT ?"
        params.append(limit)
    
    rows = conn.execute(query, params).fetchall()
    
    events: list[LearningEvent] = []
    for row in rows:
        try:
            content = json.loads(row['content_json'])
            skills = json.loads(row['skills_json'])
            timestamp = datetime.fromisoformat(row['timestamp'])
            
            event = LearningEvent(
                id=row['id'],
                project_id=row['project_id'],
                event_type=EventType(row['event_type']),
                timestamp=timestamp,
                content=content,
                skills=skills,
                confidence=row['confidence'],
                source=EventSource(row['source'])
            )
            events.append(event)
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            # Skip malformed events
            continue
    
    return events
