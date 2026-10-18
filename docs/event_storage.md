# Learning Event Storage Module

## Overview

The `event_storage` module provides functionality for storing learning events in the database with automatic filtering and deduplication. This implements **Requirement 3.8** of the MCP-Native LearnLoop Plugin Redesign specification.

## Features

- **Confidence Filtering**: Only stores events with confidence scores above 0.7 threshold
- **Content-Based Deduplication**: Prevents storing duplicate events within a 24-hour window
- **Batch Operations**: Supports storing multiple events efficiently
- **Flexible Retrieval**: Query events by project, type, confidence, and more

## Usage

### Importing

```python
from learnloop.capture.event_storage import (
    CONFIDENCE_THRESHOLD,
    store_learning_event,
    store_learning_events,
    get_learning_events_by_project,
)
from learnloop.domain.learning_event import LearningEvent, EventType, EventSource
```

### Storing a Single Event

```python
import sqlite3
from datetime import datetime, timezone
from uuid import uuid4

# Create a learning event
event = LearningEvent(
    id=str(uuid4()),
    project_id="my-project",
    event_type=EventType.IMPLEMENTATION,
    timestamp=datetime.now(timezone.utc),
    content={"code": "def hello(): print('world')", "language": "python"},
    skills=["python"],
    confidence=0.85,
    source=EventSource.CONVERSATION
)

# Store it
conn = sqlite3.connect("database.db")
result = store_learning_event(conn, event)

if result['stored']:
    print(f"Event stored with ID: {result['event_id']}")
else:
    print(f"Event not stored: {result['reason']}")
```

### Storing Multiple Events

```python
events = [event1, event2, event3]
result = store_learning_events(conn, events)

print(f"Stored: {result['stored_count']}")
print(f"Filtered (low confidence): {result['filtered_count']}")
print(f"Duplicates skipped: {result['duplicate_count']}")
```

### Retrieving Events

```python
# Get all events for a project
events = get_learning_events_by_project(conn, "my-project")

# Filter by event type
impl_events = get_learning_events_by_project(
    conn,
    "my-project",
    event_type=EventType.IMPLEMENTATION
)

# Filter by minimum confidence
high_conf = get_learning_events_by_project(
    conn,
    "my-project",
    min_confidence=0.8
)

# Limit results
recent = get_learning_events_by_project(
    conn,
    "my-project",
    limit=10
)
```

## API Reference

### Constants

#### `CONFIDENCE_THRESHOLD`

The minimum confidence score (0.7) required for an event to be stored. Events at or below this threshold are filtered out.

### Functions

#### `store_learning_event(conn, event, deduplicate=True)`

Store a single learning event in the database.

**Parameters:**
- `conn` (sqlite3.Connection): Database connection
- `event` (LearningEvent): Event to store
- `deduplicate` (bool, optional): Whether to check for duplicates (default: True)

**Returns:**
- `dict`: Result dictionary with:
  - `stored` (bool): Whether event was stored
  - `event_id` (str): Event ID if stored
  - `reason` (str): Explanation if not stored

**Filtering Behavior:**
- Events with confidence ≤ 0.7 are not stored
- Duplicate events (same content, type, within 24h) are not stored

#### `store_learning_events(conn, events, deduplicate=True)`

Store multiple learning events in batch.

**Parameters:**
- `conn` (sqlite3.Connection): Database connection
- `events` (list[LearningEvent]): Events to store
- `deduplicate` (bool, optional): Whether to check for duplicates (default: True)

**Returns:**
- `dict`: Summary with:
  - `stored_count` (int): Number of events stored
  - `filtered_count` (int): Number filtered by confidence
  - `duplicate_count` (int): Number of duplicates skipped
  - `failed_count` (int): Number that failed to store
  - `stored_ids` (list[str]): IDs of stored events

#### `get_learning_events_by_project(conn, project_id, event_type=None, min_confidence=None, limit=None)`

Retrieve learning events from the database.

**Parameters:**
- `conn` (sqlite3.Connection): Database connection
- `project_id` (str): Project identifier
- `event_type` (EventType, optional): Filter by event type
- `min_confidence` (float, optional): Minimum confidence threshold
- `limit` (int, optional): Maximum number of results

**Returns:**
- `list[LearningEvent]`: List of matching events, ordered by timestamp descending

## Deduplication Logic

Events are considered duplicates if they meet all criteria:

1. **Same project**: Both events belong to the same project
2. **Same type**: Both events have the same event_type
3. **Same content**: Content hash matches exactly
4. **Recent timing**: Both events within 24-hour window

This prevents the same learning opportunity from being recorded multiple times while still allowing:
- Same content in different projects
- Same content with different event types
- Same content after 24 hours has passed

## Design Decisions

### Why 0.7 Confidence Threshold?

The threshold of 0.7 (>70% confidence) balances:
- **Quality**: Filters out low-confidence noise
- **Coverage**: Captures most significant learning events
- **Flexibility**: Not so strict as to miss valuable events

Based on testing, events above 0.7 confidence typically represent:
- Complex code implementations (cyclomatic complexity > 0.3)
- Meaningful architectural decisions
- Substantive technical questions

### Why 24-Hour Deduplication Window?

A 24-hour window provides:
- **Short-term protection**: Prevents immediate duplicates from conversation analysis
- **Long-term flexibility**: Allows revisiting topics after a day
- **Performance**: Keeps deduplication queries efficient

## Testing

The module includes comprehensive tests covering:
- Confidence filtering at boundary conditions
- Deduplication with same and different content
- Batch storage with mixed results
- Retrieval with various filters
- Edge cases (empty skills, complex content, etc.)

Run tests with:
```bash
python -m pytest tests/capture/test_event_storage.py -v
```

## Requirements Implemented

This module implements:

- **Requirement 3.8**: Store significant learning events
  - Filter by confidence threshold (>0.7)
  - Deduplicate based on content similarity
  - Store in learning_events database table

- **Requirement 23.3**: Confidence validation (0.0-1.0)

## Example

See `examples/event_storage_example.py` for a complete working example demonstrating all features.

## Related Modules

- `learnloop.domain.learning_event`: LearningEvent model and validation
- `learnloop.capture.complexity`: Complexity score calculation
- `learnloop.capture.skill_mapper`: Skill detection from code
