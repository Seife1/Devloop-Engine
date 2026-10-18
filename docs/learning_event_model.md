# LearningEvent Model Documentation

## Overview

The `LearningEvent` model represents automatically detected learning opportunities in the LearnLoop MCP redesign. This model is a core component of the auto-tracking system that captures learning events from AI conversations, git commits, and manual entries.

## Implementation Summary

**Task**: 2.2 Implement LearningEvent model
**Requirements**: 3.7, 23.3
**Status**: ✅ Complete

## Model Structure

### Enums

#### EventType
Represents the type of learning event:
- `IMPLEMENTATION`: Code implementation detected
- `DECISION`: Technical decision with alternatives
- `QUESTION`: Learning question or inquiry
- `EXPLANATION`: User explanation of learned concepts

#### EventSource
Represents where the event was detected:
- `CONVERSATION`: From AI assistant conversation analysis
- `COMMIT`: From git commit metadata
- `MANUAL`: Manually entered by user

### LearningEvent Dataclass

**Attributes:**
- `id` (str): Unique identifier (UUID string)
- `project_id` (str): Reference to the project (UUID string)
- `event_type` (EventType): Type of learning event
- `timestamp` (datetime): When the event occurred (UTC)
- `content` (dict): Type-specific content
- `skills` (list[str]): List of skill identifiers
- `confidence` (float): Detection confidence score (0.0 to 1.0)
- `source` (EventSource): Where the event was detected

**Features:**
- Immutable (frozen dataclass)
- Comprehensive validation in `__post_init__`
- Factory method for explicit creation

## Validation Rules

### Requirement 3.7: Confidence Score Validation
- Confidence must be between 0.0 and 1.0 inclusive
- Values outside this range raise `ValueError`
- Auto-tracker assigns confidence based on detection certainty
- Events with confidence > 0.7 are stored (per Requirement 3.8)

### Requirement 23.3: Database Schema Validation
- Learning_Event enforces confidence between 0.0 and 1.0
- Prevents corrupted data from breaking the learning loop
- Validation occurs at model creation time

### Timestamp Validation
- Timestamps cannot be in the future
- Timezone-aware timestamps preferred (UTC)
- Timezone-naive timestamps are converted to UTC for comparison

### Content Validation
- Content must be a dict (not string or other type)
- Can contain nested structures
- Type-specific fields based on event_type

### Skills Validation
- Skills must be a list (can be empty)
- Cannot be None
- Contains skill identifiers as strings

## Usage Examples

### Creating an Implementation Event

```python
from datetime import datetime, timezone
from uuid import uuid4
from learnloop.domain import LearningEvent, EventType, EventSource

event = LearningEvent.create(
    id=str(uuid4()),
    project_id=str(uuid4()),
    event_type=EventType.IMPLEMENTATION,
    timestamp=datetime.now(timezone.utc),
    content={
        "code": "def calculate(x): return x * 2",
        "language": "python",
        "file": "src/calc.py"
    },
    skills=["python.functions", "python.operators"],
    confidence=0.87,
    source=EventSource.CONVERSATION
)
```

### Creating a Decision Event

```python
event = LearningEvent.create(
    id=str(uuid4()),
    project_id=str(uuid4()),
    event_type=EventType.DECISION,
    timestamp=datetime.now(timezone.utc),
    content={
        "decision": "Use SQLite for storage",
        "alternatives": ["PostgreSQL", "MySQL"],
        "rationale": "Zero-friction setup"
    },
    skills=["database.design", "sqlite"],
    confidence=0.92,
    source=EventSource.CONVERSATION
)
```

## Test Coverage

### Unit Tests (`tests/test_learning_event.py`)
- 18 comprehensive unit tests
- Tests all validation rules
- Tests edge cases and boundary values
- Tests immutability
- Tests all enum values

### Integration Tests (`tests/test_learning_event_integration.py`)
- 7 realistic scenario tests
- Demonstrates real-world usage patterns
- Tests filtering logic (confidence thresholds)
- Tests multi-event sessions
- Tests all event sources

**Total: 25 tests, all passing ✅**

## Type Safety

- Full type hints for all attributes and methods
- Passes `mypy --strict` with no issues
- Proper handling of Optional types
- Type-safe enum usage

## Design Patterns

1. **Immutable Data**: Frozen dataclass prevents accidental mutation
2. **Factory Method**: `create()` method provides clear construction
3. **Fail-Fast Validation**: Errors raised immediately on invalid data
4. **Enum Safety**: Type-safe event types and sources
5. **Defensive Programming**: Validates all inputs in `__post_init__`

## Integration Points

### Auto-Tracker Service
The Auto-Tracker analyzes AI conversations and creates LearningEvents:
```python
def analyze_conversation(messages):
    for message in messages:
        if has_significant_code(message):
            event = LearningEvent.create(
                # ... event creation
                confidence=calculate_confidence(message),
                source=EventSource.CONVERSATION
            )
            if event.confidence > 0.7:
                store_event(event)
```

### Git Integration
Git hooks create events from commits:
```python
def process_commit(commit_data):
    event = LearningEvent.create(
        event_type=EventType.IMPLEMENTATION,
        content={"commit_sha": commit_data.sha, ...},
        confidence=1.0,  # Verified commit
        source=EventSource.COMMIT
    )
```

## Next Steps

After implementing LearningEvent:
1. Implement database schema for storing events (Task 4.1)
2. Implement Auto-Tracker service using this model (Task 6)
3. Integrate with conversation analysis (Task 6.1)
4. Add database persistence layer (Task 4.2)

## Files

- **Model**: `src/learnloop/domain/learning_event.py`
- **Unit Tests**: `tests/test_learning_event.py`
- **Integration Tests**: `tests/test_learning_event_integration.py`
- **Exports**: `src/learnloop/domain/__init__.py`
