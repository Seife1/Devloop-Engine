"""Database resilience layer with retry, fallback, and corruption detection.

This module provides error handling for database operations including:
- Exponential backoff retry for locked databases
- Fallback to in-memory database on connection failure
- Corruption detection with PRAGMA integrity_check
- Write operation queuing for temporary databases
"""

from __future__ import annotations

import logging
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator

log = logging.getLogger(__name__)


@dataclass
class WriteOperation:
    """Represents a queued write operation for later persistence."""
    
    operation: str  # 'execute', 'executemany', or 'executescript'
    sql: str
    parameters: tuple[Any, ...] | list[dict[str, Any]] | None = None
    timestamp: float = field(default_factory=time.time)


class DatabaseResilience:
    """Manages database connection with retry logic, fallback, and corruption detection."""
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_backoff: float = 0.1,
        backoff_multiplier: float = 2.0,
    ):
        """Initialize resilience manager.
        
        Args:
            max_retries: Maximum number of retry attempts for locked database
            initial_backoff: Initial backoff delay in seconds
            backoff_multiplier: Multiplier for exponential backoff
        """
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self.backoff_multiplier = backoff_multiplier
        self.is_temporary = False
        self.write_queue: list[WriteOperation] = []
        self._temp_connection: sqlite3.Connection | None = None
    
    def connect_with_retry(
        self,
        path: Path | str,
        connect_fn: Callable[[Path | str], sqlite3.Connection],
    ) -> sqlite3.Connection:
        """Connect to database with exponential backoff retry.
        
        Implements Requirement 24.1: Retry connection with exponential backoff up to 3 attempts.
        
        Args:
            path: Path to database file
            connect_fn: Function to establish connection (e.g., db.connect)
        
        Returns:
            Database connection (may be in-memory fallback)
        
        Raises:
            sqlite3.Error: If connection fails after all retries and fallback fails
        """
        path = Path(path)
        last_error: Exception | None = None
        
        for attempt in range(self.max_retries):
            try:
                log.debug(f"Attempting database connection (attempt {attempt + 1}/{self.max_retries})")
                conn = connect_fn(path)
                
                # Check for corruption on successful connection
                if not self._check_integrity(conn):
                    log.error(f"Database corruption detected at {path}")
                    conn.close()
                    raise sqlite3.DatabaseError("Database corruption detected")
                
                log.info(f"Database connection established: {path}")
                self.is_temporary = False
                return conn
                
            except sqlite3.OperationalError as e:
                last_error = e
                if "locked" in str(e).lower() or "busy" in str(e).lower():
                    backoff = self.initial_backoff * (self.backoff_multiplier ** attempt)
                    log.warning(
                        f"Database locked (attempt {attempt + 1}/{self.max_retries}), "
                        f"retrying in {backoff:.2f}s: {e}"
                    )
                    if attempt < self.max_retries - 1:
                        time.sleep(backoff)
                        continue
                else:
                    log.error(f"Database connection failed: {e}")
                    break
            
            except (sqlite3.DatabaseError, OSError) as e:
                last_error = e
                log.error(f"Database error on attempt {attempt + 1}: {e}")
                break
        
        # All retries failed, fall back to in-memory database
        log.warning(
            f"Failed to connect to {path} after {self.max_retries} attempts. "
            f"Falling back to in-memory database. Last error: {last_error}"
        )
        return self._create_fallback_database(connect_fn)
    
    def _check_integrity(self, conn: sqlite3.Connection) -> bool:
        """Check database integrity using PRAGMA integrity_check.
        
        Implements Requirement 24.4: Detect corruption with PRAGMA integrity_check.
        
        Args:
            conn: Database connection to check
        
        Returns:
            True if database is OK, False if corruption detected
        """
        try:
            result = conn.execute("PRAGMA integrity_check").fetchone()
            if result and result[0] == "ok":
                log.debug("Database integrity check: OK")
                return True
            else:
                log.error(f"Database integrity check failed: {result}")
                return False
        except sqlite3.Error as e:
            log.error(f"Failed to run integrity check: {e}")
            return False
    
    def _create_fallback_database(
        self,
        connect_fn: Callable[[Path | str], sqlite3.Connection],
    ) -> sqlite3.Connection:
        """Create in-memory fallback database.
        
        Implements Requirement 24.2: Create in-memory temporary database on connection failure.
        
        Args:
            connect_fn: Function to establish connection with migrations
        
        Returns:
            In-memory database connection with schema applied
        """
        log.info("Creating in-memory fallback database")
        self.is_temporary = True
        self.write_queue.clear()
        
        try:
            # Use :memory: path to create in-memory database
            # The connect_fn will apply migrations
            conn = sqlite3.connect(":memory:", timeout=10)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA journal_mode=MEMORY")
            
            # Apply migrations manually for in-memory database
            from learnloop.persistence.db import migrate, seed_taxonomy
            migrate(conn, path=None)
            seed_taxonomy(conn)
            
            log.info("In-memory fallback database ready")
            self._temp_connection = conn
            return conn
            
        except sqlite3.Error as e:
            log.critical(f"Failed to create in-memory fallback database: {e}")
            raise
    
    def queue_write(
        self,
        operation: str,
        sql: str,
        parameters: tuple[Any, ...] | list[dict[str, Any]] | None = None,
    ) -> None:
        """Queue a write operation for later persistence.
        
        Implements Requirement 24.3: Queue write operations when using temporary database.
        
        Args:
            operation: Type of operation ('execute', 'executemany', 'executescript')
            sql: SQL statement
            parameters: Parameters for the SQL statement
        """
        if not self.is_temporary:
            log.warning("Queuing write operation on non-temporary database")
            return
        
        op = WriteOperation(
            operation=operation,
            sql=sql,
            parameters=parameters,
        )
        self.write_queue.append(op)
        log.debug(f"Queued write operation: {operation} (queue size: {len(self.write_queue)})")
    
    def flush_queue(self, conn: sqlite3.Connection) -> int:
        """Flush queued write operations to a persistent database.
        
        Args:
            conn: Target database connection (must be persistent, not in-memory)
        
        Returns:
            Number of operations successfully flushed
        
        Raises:
            ValueError: If attempting to flush to an in-memory database
        """
        if self.is_temporary:
            raise ValueError("Cannot flush queue to temporary in-memory database")
        
        if not self.write_queue:
            log.debug("No queued write operations to flush")
            return 0
        
        flushed = 0
        failed = 0
        
        log.info(f"Flushing {len(self.write_queue)} queued write operations")
        
        for op in self.write_queue:
            try:
                if op.operation == "execute":
                    conn.execute(op.sql, op.parameters or ())
                elif op.operation == "executemany":
                    conn.executemany(op.sql, op.parameters or [])
                elif op.operation == "executescript":
                    conn.executescript(op.sql)
                else:
                    log.error(f"Unknown operation type: {op.operation}")
                    failed += 1
                    continue
                
                flushed += 1
                
            except sqlite3.Error as e:
                log.error(f"Failed to flush operation: {e}")
                failed += 1
        
        try:
            conn.commit()
            log.info(f"Successfully flushed {flushed} operations ({failed} failed)")
            self.write_queue.clear()
        except sqlite3.Error as e:
            log.error(f"Failed to commit flushed operations: {e}")
            raise
        
        return flushed
    
    def get_queue_size(self) -> int:
        """Get the number of queued write operations.
        
        Returns:
            Number of queued operations
        """
        return len(self.write_queue)
    
    def clear_queue(self) -> None:
        """Clear all queued write operations without flushing."""
        count = len(self.write_queue)
        self.write_queue.clear()
        log.info(f"Cleared {count} queued write operations")
    
    @contextmanager
    def resilient_connection(
        self,
        path: Path | str,
        connect_fn: Callable[[Path | str], sqlite3.Connection],
    ) -> Iterator[tuple[sqlite3.Connection, 'DatabaseResilience']]:
        """Context manager for resilient database connection.
        
        Provides a database connection with automatic retry and fallback,
        along with the resilience manager for queue operations.
        
        Args:
            path: Path to database file
            connect_fn: Function to establish connection
        
        Yields:
            Tuple of (connection, resilience_manager)
        
        Example:
            >>> resilience = DatabaseResilience()
            >>> with resilience.resilient_connection(db_path, db.connect) as (conn, mgr):
            ...     if mgr.is_temporary:
            ...         mgr.queue_write('execute', 'INSERT INTO ...', (value,))
            ...     else:
            ...         conn.execute('INSERT INTO ...', (value,))
        """
        conn = self.connect_with_retry(path, connect_fn)
        try:
            yield conn, self
        finally:
            if conn and not self.is_temporary:
                conn.close()
            # Keep in-memory connection alive for the session


# Global instance for convenience
_global_resilience = DatabaseResilience()


def get_resilient_connection(
    path: Path | str,
    connect_fn: Callable[[Path | str], sqlite3.Connection] | None = None,
) -> tuple[sqlite3.Connection, DatabaseResilience]:
    """Get a resilient database connection using the global resilience manager.
    
    This is a convenience function that uses a global DatabaseResilience instance.
    For more control, create your own DatabaseResilience instance.
    
    Args:
        path: Path to database file
        connect_fn: Function to establish connection (defaults to learnloop.persistence.db.connect)
    
    Returns:
        Tuple of (connection, resilience_manager)
    
    Example:
        >>> from learnloop.persistence import db_resilience
        >>> conn, mgr = db_resilience.get_resilient_connection(db_path)
        >>> if mgr.is_temporary:
        ...     print("Warning: Using temporary in-memory database")
    """
    if connect_fn is None:
        from learnloop.persistence.db import connect
        connect_fn = connect
    
    return _global_resilience.connect_with_retry(path, connect_fn), _global_resilience
