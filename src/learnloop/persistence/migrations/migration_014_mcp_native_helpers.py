"""Python migration helpers for 014_mcp_native_redesign.

These helpers safely add columns to existing tables, checking if they already exist.
SQLite doesn't support IF NOT EXISTS for ALTER TABLE ADD COLUMN, so we use PRAGMA checks.
"""

import logging
import sqlite3

log = logging.getLogger(__name__)


def safe_add_column(
    conn: sqlite3.Connection,
    table: str,
    column: str,
    column_def: str
) -> bool:
    """Safely add a column to a table if it doesn't already exist.
    
    Args:
        conn: Database connection
        table: Table name
        column: Column name to add
        column_def: Full column definition (e.g., "TEXT NULL")
    
    Returns:
        True if column was added, False if it already existed
    """
    # Check if column exists
    cursor = conn.execute(f"PRAGMA table_info({table})")
    columns = {row[1] for row in cursor.fetchall()}
    
    if column in columns:
        log.debug(f"Column {table}.{column} already exists, skipping")
        return False
    
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_def}")
        log.info(f"Added column {table}.{column}")
        return True
    except sqlite3.OperationalError as e:
        log.warning(f"Failed to add column {table}.{column}: {e}")
        return False


def migrate_knowledge_items(conn: sqlite3.Connection) -> None:
    """Add MCP-native columns to knowledge_items table.
    
    The knowledge_items table was created in migration 007 with a different structure.
    We extend it here for the MCP-native redesign.
    """
    # Check if knowledge_items table exists
    cursor = conn.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='knowledge_items'
    """)
    if not cursor.fetchone():
        log.info("knowledge_items table doesn't exist yet, skipping column additions")
        return
    
    # Add new columns for MCP-native features
    safe_add_column(
        conn, "knowledge_items", "self_rating",
        "REAL NULL CHECK (self_rating IS NULL OR (self_rating BETWEEN 1.0 AND 5.0))"
    )
    safe_add_column(
        conn, "knowledge_items", "is_stale",
        "INTEGER NOT NULL DEFAULT 0 CHECK (is_stale IN (0, 1))"
    )
    safe_add_column(
        conn, "knowledge_items", "stale_since",
        "TEXT NULL"
    )
    safe_add_column(
        conn, "knowledge_items", "stale_commit_sha",
        "TEXT NULL REFERENCES commits(sha)"
    )
    safe_add_column(
        conn, "knowledge_items", "last_explained_at",
        "TEXT NULL"
    )
    
    conn.commit()
    
    # Create staleness index if is_stale column was added
    try:
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_knowledge_items_stale 
            ON knowledge_items(project_id, is_stale)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_knowledge_items_staleness
            ON knowledge_items(project_id, is_stale, stale_since)
        """)
        conn.commit()
        log.info("Created staleness indexes on knowledge_items")
    except sqlite3.OperationalError as e:
        log.warning(f"Failed to create staleness indexes: {e}")


def migrate_projects(conn: sqlite3.Connection) -> None:
    """Add MCP-native columns to projects table."""
    safe_add_column(conn, "projects", "git_root", "TEXT NULL")
    safe_add_column(
        conn, "projects", "total_commits",
        "INTEGER NOT NULL DEFAULT 0 CHECK (total_commits >= 0)"
    )
    safe_add_column(
        conn, "projects", "explained_commits",
        "INTEGER NOT NULL DEFAULT 0 CHECK (explained_commits >= 0)"
    )
    safe_add_column(
        conn, "projects", "knowledge_items_count",
        "INTEGER NOT NULL DEFAULT 0 CHECK (knowledge_items_count >= 0)"
    )
    safe_add_column(
        conn, "projects", "readiness_level",
        "INTEGER NOT NULL DEFAULT 1 CHECK (readiness_level BETWEEN 1 AND 4)"
    )
    safe_add_column(
        conn, "projects", "last_accessed",
        "TEXT NOT NULL DEFAULT (datetime('now'))"
    )
    
    conn.commit()


def migrate_explanations(conn: sqlite3.Connection) -> None:
    """Add explanation_depth column to explanations table if it exists."""
    # Check if explanations table exists
    cursor = conn.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='explanations'
    """)
    if not cursor.fetchone():
        log.info("explanations table doesn't exist yet, skipping")
        return
    
    safe_add_column(
        conn, "explanations", "explanation_depth",
        "REAL NULL CHECK (explanation_depth IS NULL OR (explanation_depth BETWEEN 0.0 AND 1.0))"
    )
    safe_add_column(
        conn, "explanations", "item_id_ref",
        "TEXT NULL REFERENCES knowledge_items(id) ON DELETE SET NULL"
    )
    
    conn.commit()


def migrate_commits(conn: sqlite3.Connection) -> None:
    """Add origin column to commits table."""
    safe_add_column(
        conn, "commits", "origin",
        "TEXT NULL DEFAULT 'unexplained' CHECK (origin IS NULL OR origin IN ('matched', 'unexplained', 'manual'))"
    )
    
    conn.commit()


def apply_python_migrations(conn: sqlite3.Connection) -> None:
    """Apply all Python-based schema migrations for migration 014.
    
    This function should be called after the SQL migration is applied.
    """
    log.info("Applying Python migrations for 014_mcp_native_redesign")
    
    try:
        migrate_projects(conn)
        migrate_knowledge_items(conn)
        migrate_explanations(conn)
        migrate_commits(conn)
        log.info("Python migrations completed successfully")
    except Exception as e:
        log.error(f"Python migration failed: {e}")
        raise
