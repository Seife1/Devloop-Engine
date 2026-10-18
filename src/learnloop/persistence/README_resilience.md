# Database Resilience Layer

This module provides production-ready error handling for SQLite database operations in LearnLoop.

## Features

### 1. Retry Logic with Exponential Backoff (Requirement 24.1)

Automatically retries database connections when the database is locked, with exponentially increasing delays:

```python
from learnloop.persistence import get_resilient_connection, db

# Connect with automatic retry
conn, mgr = get_resilient_connection("path/to/database.db")

# Connection will retry up to 3 times with exponential backoff:
# - First retry after 0.1s
# - Second retry after 0.2s
# - Third retry after 0.4s
```

### 2. Fallback to In-Memory Database (Requirement 24.2)

If connection fails after all retries, automatically falls back to an in-memory temporary database:

```python
conn, mgr = get_resilient_connection("path/to/locked_database.db")

if mgr.is_temporary:
    print("Warning: Using temporary in-memory database")
    # All data will be lost when connection closes
    # Queue write operations for later persistence
```

### 3. Corruption Detection (Requirement 24.4)

Automatically checks database integrity using `PRAGMA integrity_check`:

```python
from learnloop.persistence import DatabaseResilience

resilience = DatabaseResilience()
conn = resilience.connect_with_retry(db_path, db.connect)

# Corruption is detected automatically during connection
# If corrupted, falls back to in-memory database
```

### 4. Write Operation Queuing (Requirement 24.3)

When using temporary database, queue write operations for later persistence:

```python
conn, mgr = get_resilient_connection(db_path)

if mgr.is_temporary:
    # Queue writes instead of executing directly
    mgr.queue_write("execute", "INSERT INTO projects (id, name) VALUES (?, ?)", (1, "MyProject"))
    mgr.queue_write("execute", "UPDATE projects SET name = ? WHERE id = ?", ("NewName", 1))
    
    print(f"Queued {mgr.get_queue_size()} operations")
    
    # Later, when connection is restored:
    persistent_conn = db.connect(db_path)
    mgr.is_temporary = False
    flushed = mgr.flush_queue(persistent_conn)
    print(f"Flushed {flushed} operations to persistent database")
else:
    # Execute directly on persistent database
    conn.execute("INSERT INTO projects (id, name) VALUES (?, ?)", (1, "MyProject"))
    conn.commit()
```

## Usage Examples

### Basic Usage with Context Manager

```python
from learnloop.persistence import DatabaseResilience, db

resilience = DatabaseResilience()

with resilience.resilient_connection(db_path, db.connect) as (conn, mgr):
    if mgr.is_temporary:
        # Queue operations for temporary database
        mgr.queue_write("execute", "INSERT INTO table VALUES (?)", (value,))
    else:
        # Execute directly on persistent database
        conn.execute("INSERT INTO table VALUES (?)", (value,))
        conn.commit()
```

### Custom Retry Configuration

```python
from learnloop.persistence import DatabaseResilience

# Customize retry behavior
resilience = DatabaseResilience(
    max_retries=5,           # Try 5 times instead of 3
    initial_backoff=0.5,     # Start with 500ms delay
    backoff_multiplier=3.0,  # Triple delay each time
)

conn = resilience.connect_with_retry(db_path, db.connect)
```

### Manual Queue Management

```python
conn, mgr = get_resilient_connection(db_path)

if mgr.is_temporary:
    # Queue some operations
    mgr.queue_write("execute", "CREATE TABLE test (id INTEGER)")
    mgr.queue_write("execute", "INSERT INTO test VALUES (1)")
    
    # Clear queue if needed
    mgr.clear_queue()
    
    # Or inspect queue
    print(f"Queue has {mgr.get_queue_size()} operations")
```

## Error Handling

The resilience layer handles these error scenarios:

1. **Locked Database** (`sqlite3.OperationalError: database is locked`)
   - Retries with exponential backoff
   - Falls back to in-memory if all retries fail

2. **Disk I/O Errors** (`sqlite3.DatabaseError`)
   - Immediately falls back to in-memory database
   - Logs error details for debugging

3. **Permission Errors** (`OSError: permission denied`)
   - Falls back to in-memory database
   - User can later restore access and flush queued operations

4. **Database Corruption**
   - Detected during connection via `PRAGMA integrity_check`
   - Falls back to in-memory database
   - Logs corruption details

## Best Practices

1. **Check `is_temporary` flag**: Always check if you're using a temporary database before executing writes

2. **Queue writes for temporary database**: Don't execute writes directly on temporary databases if you need to persist them later

3. **Monitor queue size**: Keep an eye on queued operations to avoid memory issues

4. **Flush regularly**: When connection is restored, flush queued operations promptly

5. **Handle flush failures**: The `flush_queue()` method returns the number of successful operations - check for partial failures

## Integration with Existing Code

The resilience layer wraps the existing `db.connect()` function:

```python
# Old code (no resilience)
from learnloop.persistence import db
conn = db.connect(db_path)

# New code (with resilience)
from learnloop.persistence import get_resilient_connection
conn, mgr = get_resilient_connection(db_path)

# Check if temporary
if mgr.is_temporary:
    print("Warning: Using temporary database")
```

## Logging

The resilience layer logs all operations:

- `DEBUG`: Connection attempts, integrity checks
- `INFO`: Successful connections, fallback creation, queue operations
- `WARNING`: Retry attempts, queue warnings
- `ERROR`: Connection failures, corruption detection, flush failures

Enable logging to monitor resilience behavior:

```python
import logging
logging.basicConfig(level=logging.INFO)
```
