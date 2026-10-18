"""Unit tests for database resilience layer.

Tests retry logic, fallback to in-memory database, corruption detection,
and write operation queuing.
"""

from __future__ import annotations

import sqlite3
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from learnloop.persistence.db_resilience import DatabaseResilience, WriteOperation


class TestDatabaseResilience:
    """Test suite for DatabaseResilience class."""
    
    def test_successful_connection_first_attempt(self):
        """Test successful connection on first attempt."""
        resilience = DatabaseResilience()
        
        def mock_connect(path: Path | str) -> sqlite3.Connection:
            conn = sqlite3.connect(":memory:")
            conn.row_factory = sqlite3.Row
            return conn
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            conn = resilience.connect_with_retry(db_path, mock_connect)
            
            assert conn is not None
            assert not resilience.is_temporary
            assert resilience.get_queue_size() == 0
            conn.close()
    
    def test_retry_on_locked_database(self):
        """Test retry logic when database is locked (Requirement 24.1)."""
        resilience = DatabaseResilience(
            max_retries=3,
            initial_backoff=0.01,  # Fast for testing
            backoff_multiplier=2.0,
        )
        
        attempt_count = 0
        
        def mock_connect(path: Path | str) -> sqlite3.Connection:
            nonlocal attempt_count
            attempt_count += 1
            
            if attempt_count < 3:
                # Fail first two attempts
                raise sqlite3.OperationalError("database is locked")
            
            # Succeed on third attempt
            conn = sqlite3.connect(":memory:")
            conn.row_factory = sqlite3.Row
            return conn
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            start_time = time.time()
            conn = resilience.connect_with_retry(db_path, mock_connect)
            elapsed = time.time() - start_time
            
            assert attempt_count == 3
            assert conn is not None
            assert not resilience.is_temporary
            # Should have waited: 0.01 + 0.02 = 0.03 seconds minimum
            assert elapsed >= 0.03
            conn.close()
    
    def test_fallback_to_in_memory_after_retries(self):
        """Test fallback to in-memory database after retry exhaustion (Requirement 24.2)."""
        resilience = DatabaseResilience(
            max_retries=3,
            initial_backoff=0.01,
        )
        
        def mock_connect(path: Path | str) -> sqlite3.Connection:
            if str(path) == ":memory:":
                # Allow in-memory connection for fallback
                conn = sqlite3.connect(":memory:")
                conn.row_factory = sqlite3.Row
                return conn
            # Always fail for file-based connections
            raise sqlite3.OperationalError("database is locked")
        
        with tempfile.TemporaryDirectory() as tmpdir, \
             patch("learnloop.persistence.db.migrate"), \
             patch("learnloop.persistence.db.seed_taxonomy"):
            
            db_path = Path(tmpdir) / "test.db"
            conn = resilience.connect_with_retry(db_path, mock_connect)
            
            assert conn is not None
            assert resilience.is_temporary
            assert resilience.get_queue_size() == 0
            conn.close()
    
    def test_corruption_detection(self):
        """Test database corruption detection (Requirement 24.4)."""
        resilience = DatabaseResilience()
        
        # Create a mock connection that reports corruption
        conn = Mock(spec=sqlite3.Connection)
        execute_result = Mock()
        execute_result.fetchone.return_value = ("corruption detected",)
        conn.execute.return_value = execute_result
        
        result = resilience._check_integrity(conn)
        
        assert result is False
    
    def test_corruption_triggers_fallback(self):
        """Test that corruption detection triggers fallback to in-memory database."""
        resilience = DatabaseResilience(max_retries=1)
        
        def mock_connect(path: Path | str) -> sqlite3.Connection:
            if str(path) == ":memory:":
                conn = sqlite3.connect(":memory:")
                conn.row_factory = sqlite3.Row
                return conn
            
            # Return a connection that will fail integrity check
            conn = Mock(spec=sqlite3.Connection)
            execute_result = Mock()
            execute_result.fetchone.return_value = ("corruption detected",)
            conn.execute.return_value = execute_result
            conn.close = Mock()
            return conn
        
        with tempfile.TemporaryDirectory() as tmpdir, \
             patch("learnloop.persistence.db.migrate"), \
             patch("learnloop.persistence.db.seed_taxonomy"):
            
            db_path = Path(tmpdir) / "test.db"
            conn = resilience.connect_with_retry(db_path, mock_connect)
            
            assert resilience.is_temporary
            conn.close()
    
    def test_write_operation_queuing(self):
        """Test queuing write operations for temporary database (Requirement 24.3)."""
        resilience = DatabaseResilience()
        resilience.is_temporary = True
        
        # Queue some operations
        resilience.queue_write("execute", "INSERT INTO test VALUES (?)", (1,))
        resilience.queue_write("executemany", "INSERT INTO test VALUES (?)", [(2,), (3,)])
        resilience.queue_write("executescript", "CREATE TABLE test2 (id INTEGER)")
        
        assert resilience.get_queue_size() == 3
        
        # Verify operations are queued correctly
        ops = resilience.write_queue
        assert ops[0].operation == "execute"
        assert ops[0].sql == "INSERT INTO test VALUES (?)"
        assert ops[0].parameters == (1,)
        
        assert ops[1].operation == "executemany"
        assert ops[1].parameters == [(2,), (3,)]
        
        assert ops[2].operation == "executescript"
    
    def test_flush_queue_to_persistent_database(self):
        """Test flushing queued operations to persistent database."""
        resilience = DatabaseResilience()
        resilience.is_temporary = True
        
        # Queue operations
        resilience.queue_write("execute", "CREATE TABLE test (id INTEGER, value TEXT)", None)
        resilience.queue_write("execute", "INSERT INTO test VALUES (?, ?)", (1, "a"))
        resilience.queue_write("execute", "INSERT INTO test VALUES (?, ?)", (2, "b"))
        
        # Create persistent database
        conn = sqlite3.connect(":memory:")
        resilience.is_temporary = False
        
        # Flush queue
        flushed = resilience.flush_queue(conn)
        
        assert flushed == 3
        assert resilience.get_queue_size() == 0
        
        # Verify data was written
        cursor = conn.execute("SELECT * FROM test ORDER BY id")
        rows = cursor.fetchall()
        assert len(rows) == 2
        assert rows[0] == (1, "a")
        assert rows[1] == (2, "b")
        
        conn.close()
    
    def test_cannot_flush_to_temporary_database(self):
        """Test that flushing to temporary database raises error."""
        resilience = DatabaseResilience()
        resilience.is_temporary = True
        resilience.queue_write("execute", "INSERT INTO test VALUES (?)", (1,))
        
        conn = sqlite3.connect(":memory:")
        
        with pytest.raises(ValueError, match="Cannot flush queue to temporary"):
            resilience.flush_queue(conn)
        
        conn.close()
    
    def test_clear_queue(self):
        """Test clearing queued operations."""
        resilience = DatabaseResilience()
        resilience.is_temporary = True
        
        resilience.queue_write("execute", "INSERT INTO test VALUES (?)", (1,))
        resilience.queue_write("execute", "INSERT INTO test VALUES (?)", (2,))
        
        assert resilience.get_queue_size() == 2
        
        resilience.clear_queue()
        
        assert resilience.get_queue_size() == 0
    
    def test_exponential_backoff_timing(self):
        """Test that exponential backoff delays increase correctly."""
        resilience = DatabaseResilience(
            max_retries=3,
            initial_backoff=0.01,
            backoff_multiplier=2.0,
        )
        
        attempt_count = 0
        
        def mock_connect(path: Path | str) -> sqlite3.Connection:
            nonlocal attempt_count
            attempt_count += 1
            
            if attempt_count <= 3:
                raise sqlite3.OperationalError("database is locked")
            
            # Should not reach here in this test
            return sqlite3.connect(":memory:")
        
        with tempfile.TemporaryDirectory() as tmpdir, \
             patch("learnloop.persistence.db.migrate"), \
             patch("learnloop.persistence.db.seed_taxonomy"):
            
            db_path = Path(tmpdir) / "test.db"
            start_time = time.time()
            conn = resilience.connect_with_retry(db_path, mock_connect)
            elapsed = time.time() - start_time
            
            # Expected delays: 0.01 + 0.02 = 0.03 seconds
            assert elapsed >= 0.03
            # Should have fallen back to in-memory
            assert resilience.is_temporary
            conn.close()
    
    def test_resilient_connection_context_manager(self):
        """Test resilient_connection context manager."""
        resilience = DatabaseResilience()
        
        def mock_connect(path: Path | str) -> sqlite3.Connection:
            conn = sqlite3.connect(":memory:")
            conn.row_factory = sqlite3.Row
            return conn
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            
            with resilience.resilient_connection(db_path, mock_connect) as (conn, mgr):
                assert conn is not None
                assert mgr is resilience
                assert not mgr.is_temporary
                
                # Can use connection within context
                conn.execute("CREATE TABLE test (id INTEGER)")
    
    def test_queue_operations_in_context_manager(self):
        """Test queuing operations when using temporary database in context manager."""
        resilience = DatabaseResilience(max_retries=1)
        
        def mock_connect(path: Path | str) -> sqlite3.Connection:
            if str(path) == ":memory:":
                conn = sqlite3.connect(":memory:")
                conn.row_factory = sqlite3.Row
                return conn
            raise sqlite3.OperationalError("database is locked")
        
        with tempfile.TemporaryDirectory() as tmpdir, \
             patch("learnloop.persistence.db.migrate"), \
             patch("learnloop.persistence.db.seed_taxonomy"):
            
            db_path = Path(tmpdir) / "test.db"
            
            with resilience.resilient_connection(db_path, mock_connect) as (conn, mgr):
                assert mgr.is_temporary
                
                # Queue operations instead of executing directly
                mgr.queue_write("execute", "INSERT INTO test VALUES (?)", (1,))
                mgr.queue_write("execute", "INSERT INTO test VALUES (?)", (2,))
                
                assert mgr.get_queue_size() == 2
    
    def test_integrity_check_with_ok_database(self):
        """Test integrity check passes with healthy database."""
        resilience = DatabaseResilience()
        conn = sqlite3.connect(":memory:")
        
        result = resilience._check_integrity(conn)
        
        assert result is True
        conn.close()
    
    def test_write_operation_dataclass(self):
        """Test WriteOperation dataclass."""
        op = WriteOperation(
            operation="execute",
            sql="INSERT INTO test VALUES (?)",
            parameters=(1,),
        )
        
        assert op.operation == "execute"
        assert op.sql == "INSERT INTO test VALUES (?)"
        assert op.parameters == (1,)
        assert op.timestamp > 0
    
    def test_queue_warning_on_non_temporary_database(self, caplog):
        """Test warning when queuing on non-temporary database."""
        resilience = DatabaseResilience()
        resilience.is_temporary = False
        
        with caplog.at_level("WARNING"):
            resilience.queue_write("execute", "INSERT INTO test VALUES (?)", (1,))
        
        assert "non-temporary database" in caplog.text
    
    def test_failed_flush_operation_continues(self):
        """Test that flush continues even if some operations fail."""
        resilience = DatabaseResilience()
        resilience.is_temporary = True
        
        # Queue operations, second one will fail
        resilience.queue_write("execute", "CREATE TABLE test (id INTEGER)", None)
        resilience.queue_write("execute", "INSERT INTO nonexistent VALUES (?)", (1,))
        resilience.queue_write("execute", "INSERT INTO test VALUES (?)", (1,))
        
        conn = sqlite3.connect(":memory:")
        resilience.is_temporary = False
        
        # Flush should handle the error and continue
        flushed = resilience.flush_queue(conn)
        
        # Two operations should succeed (create table and last insert)
        assert flushed == 2
        
        conn.close()
    
    def test_database_error_triggers_fallback(self):
        """Test that DatabaseError triggers fallback."""
        resilience = DatabaseResilience(max_retries=1)
        
        def mock_connect(path: Path | str) -> sqlite3.Connection:
            if str(path) == ":memory:":
                conn = sqlite3.connect(":memory:")
                conn.row_factory = sqlite3.Row
                return conn
            raise sqlite3.DatabaseError("disk I/O error")
        
        with tempfile.TemporaryDirectory() as tmpdir, \
             patch("learnloop.persistence.db.migrate"), \
             patch("learnloop.persistence.db.seed_taxonomy"):
            
            db_path = Path(tmpdir) / "test.db"
            conn = resilience.connect_with_retry(db_path, mock_connect)
            
            assert resilience.is_temporary
            conn.close()
    
    def test_os_error_triggers_fallback(self):
        """Test that OSError triggers fallback."""
        resilience = DatabaseResilience(max_retries=1)
        
        def mock_connect(path: Path | str) -> sqlite3.Connection:
            if str(path) == ":memory:":
                conn = sqlite3.connect(":memory:")
                conn.row_factory = sqlite3.Row
                return conn
            raise OSError("permission denied")
        
        with tempfile.TemporaryDirectory() as tmpdir, \
             patch("learnloop.persistence.db.migrate"), \
             patch("learnloop.persistence.db.seed_taxonomy"):
            
            db_path = Path(tmpdir) / "test.db"
            conn = resilience.connect_with_retry(db_path, mock_connect)
            
            assert resilience.is_temporary
            conn.close()


class TestGetResilientConnection:
    """Test global convenience function."""
    
    def test_get_resilient_connection_with_default_connect(self):
        """Test get_resilient_connection with default connect function."""
        from learnloop.persistence.db_resilience import get_resilient_connection
        
        with tempfile.TemporaryDirectory() as tmpdir, \
             patch("learnloop.persistence.db.connect") as mock_connect:
            
            mock_conn = Mock(spec=sqlite3.Connection)
            mock_conn.execute.return_value = Mock(fetchone=lambda: ("ok",))
            mock_connect.return_value = mock_conn
            
            db_path = Path(tmpdir) / "test.db"
            conn, mgr = get_resilient_connection(db_path)
            
            assert conn is mock_conn
            assert isinstance(mgr, DatabaseResilience)
            mock_connect.assert_called_once()
    
    def test_get_resilient_connection_with_custom_connect(self):
        """Test get_resilient_connection with custom connect function."""
        from learnloop.persistence.db_resilience import get_resilient_connection
        
        def custom_connect(path: Path | str) -> sqlite3.Connection:
            conn = sqlite3.connect(":memory:")
            conn.row_factory = sqlite3.Row
            return conn
        
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            conn, mgr = get_resilient_connection(db_path, custom_connect)
            
            assert conn is not None
            assert isinstance(mgr, DatabaseResilience)
            conn.close()
