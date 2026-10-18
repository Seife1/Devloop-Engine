"""Async database operations for MCP-native LearnLoop using aiosqlite.

This module provides an async database layer with connection pooling, CRUD operations
for all domain models, and transaction support for the MCP server integration.

Requirements:
- 1.6: Load existing project context
- 27.2: Database operations must be efficient
- 24.1-24.3: Error handling with retry logic and resilience
"""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator, Optional
from uuid import UUID, uuid4

import aiosqlite

from learnloop.domain.errors import ValidationError
from learnloop.domain.models import (
    DepthBand,
    ExposureRecord,
    IntentRecord,
    IntentStatus,
    KnowledgeItem,
    ReviewSchedule,
    create_initial_review_schedule,
)
from learnloop.domain.project_context import ProjectContext, Technology

log = logging.getLogger(__name__)


class AsyncDatabase:
    """Async SQLite database with connection pooling and CRUD operations.
    
    This class provides async database operations for all LearnLoop models with:
    - Connection pooling for efficient resource usage
    - Proper parameter binding to prevent SQL injection
    - Transaction support with context managers
    - Error handling with exponential backoff retry
    - CRUD operations for ProjectContext, IntentRecord, ExposureRecord, KnowledgeItem, ReviewSchedule
    
    Requirements:
    - 1.6: Load existing project context
    - 27.2: Efficient database operations
    - 24.1: Retry with exponential backoff on locked database
    """
    
    def __init__(self, db_path: Path, pool_size: int = 5):
        """Initialize async database with connection pool.
        
        Args:
            db_path: Path to SQLite database file
            pool_size: Maximum number of connections in pool (default 5)
        """
        self.db_path = Path(db_path)
        self.pool_size = pool_size
        self._connection_semaphore = asyncio.Semaphore(pool_size)
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize database schema and run migrations.
        
        This method is idempotent and can be called multiple times safely.
        """
        if self._initialized:
            return
        
        # Ensure parent directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Run migrations synchronously on initialization
        from learnloop.persistence.db import migrate, seed_taxonomy
        import sqlite3
        
        conn = sqlite3.connect(self.db_path, timeout=10)
        try:
            conn.execute("PRAGMA foreign_keys=ON")
            conn.execute("PRAGMA journal_mode=WAL")
            migrate(conn, self.db_path)
            seed_taxonomy(conn)
            conn.commit()
        finally:
            conn.close()
        
        self._initialized = True
        log.info(f"Initialized async database at {self.db_path}")
    
    @asynccontextmanager
    async def _get_connection(self) -> AsyncIterator[aiosqlite.Connection]:
        """Get a connection from the pool with proper resource management.
        
        Yields:
            Async database connection
        """
        async with self._connection_semaphore:
            conn = await aiosqlite.connect(
                self.db_path,
                timeout=10.0,
                isolation_level=None  # Autocommit mode by default
            )
            conn.row_factory = aiosqlite.Row
            
            try:
                await conn.execute("PRAGMA foreign_keys=ON")
                yield conn
            finally:
                await conn.close()
    
    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[aiosqlite.Connection]:
        """Context manager for database transactions.
        
        Provides automatic commit on success and rollback on exception.
        
        Example:
            async with db.transaction() as conn:
                await conn.execute("INSERT INTO ...")
                await conn.execute("UPDATE ...")
                # Commits automatically on exit
        
        Yields:
            Async database connection in transaction mode
        """
        async with self._get_connection() as conn:
            await conn.execute("BEGIN")
            try:
                yield conn
                await conn.commit()
            except Exception:
                await conn.rollback()
                raise
    
    async def _retry_on_locked(self, operation, max_retries: int = 3):
        """Retry operation with exponential backoff on database locked error.
        
        Requirement 24.1: Retry with exponential backoff up to 3 attempts
        
        Args:
            operation: Async callable to execute
            max_retries: Maximum number of retry attempts
        
        Returns:
            Result of operation
        
        Raises:
            Exception: If all retries exhausted
        """
        for attempt in range(max_retries):
            try:
                return await operation()
            except aiosqlite.OperationalError as e:
                if "database is locked" in str(e) and attempt < max_retries - 1:
                    wait_time = 0.1 * (2 ** attempt)  # Exponential backoff
                    log.warning(f"Database locked, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                else:
                    raise
    
    # ============================================================================
    # ProjectContext CRUD Operations
    # ============================================================================
    
    async def create_project(
        self,
        name: str,
        repo_path: Path,
        git_root: Optional[Path] = None,
        technologies: Optional[list[Technology]] = None,
    ) -> ProjectContext:
        """Create a new project record.
        
        Args:
            name: Project name
            repo_path: Absolute path to repository
            git_root: Git repository root path (if different from repo_path)
            technologies: List of detected technologies
        
        Returns:
            Created ProjectContext
        
        Raises:
            ValidationError: If validation fails
        """
        project = ProjectContext.create_new(name, repo_path, git_root, technologies or [])
        
        async def _create():
            async with self._get_connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO projects (id, name, repo_path, git_root, readiness_level, last_accessed, total_commits, explained_commits, knowledge_items_count, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(project.id),
                        project.name,
                        str(project.repo_path),
                        str(project.git_root) if project.git_root else None,
                        project.readiness_level,
                        project.last_accessed.isoformat(),
                        project.total_commits,
                        project.explained_commits,
                        project.knowledge_items_count,
                        datetime.now(timezone.utc).isoformat(),
                    )
                )
                
                # Store technologies
                if project.technologies:
                    await conn.executemany(
                        """
                        INSERT INTO technologies (id, project_id, name, version, category, detected_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        [
                            (str(uuid4()), str(project.id), tech.name, tech.version, tech.category, datetime.now(timezone.utc).isoformat())
                            for tech in project.technologies
                        ]
                    )
                
                await conn.commit()
        
        await self._retry_on_locked(_create)
        log.info(f"Created project {project.id}: {project.name}")
        return project
    
    async def get_project_by_path(self, repo_path: Path) -> Optional[ProjectContext]:
        """Find project by repository path.
        
        Requirement 1.6: Load existing project context
        
        Args:
            repo_path: Repository path to search
        
        Returns:
            ProjectContext if found, None otherwise
        """
        async def _get():
            async with self._get_connection() as conn:
                cursor = await conn.execute(
                    """
                    SELECT id, name, repo_path, git_root, readiness_level, last_accessed,
                           total_commits, explained_commits, knowledge_items_count
                    FROM projects
                    WHERE repo_path = ?
                    """,
                    (str(repo_path),)
                )
                row = await cursor.fetchone()
                
                if not row:
                    return None
                
                # Fetch technologies
                tech_cursor = await conn.execute(
                    "SELECT name, version, category FROM technologies WHERE project_id = ?",
                    (row["id"],)
                )
                tech_rows = await tech_cursor.fetchall()
                technologies = [
                    Technology(name=t["name"], version=t["version"], category=t["category"])
                    for t in tech_rows
                ]
                
                return ProjectContext(
                    id=UUID(row["id"]),
                    name=row["name"],
                    repo_path=Path(row["repo_path"]),
                    technologies=technologies,
                    readiness_level=row["readiness_level"],
                    is_new=False,
                    last_accessed=datetime.fromisoformat(row["last_accessed"]),
                    git_root=Path(row["git_root"]) if row["git_root"] else None,
                    total_commits=row["total_commits"],
                    explained_commits=row["explained_commits"],
                    knowledge_items_count=row["knowledge_items_count"],
                )
        
        return await self._retry_on_locked(_get)
    
    async def get_project_by_id(self, project_id: UUID) -> Optional[ProjectContext]:
        """Find project by ID.
        
        Args:
            project_id: Project UUID
        
        Returns:
            ProjectContext if found, None otherwise
        """
        async def _get():
            async with self._get_connection() as conn:
                cursor = await conn.execute(
                    """
                    SELECT id, name, repo_path, git_root, readiness_level, last_accessed,
                           total_commits, explained_commits, knowledge_items_count
                    FROM projects
                    WHERE id = ?
                    """,
                    (str(project_id),)
                )
                row = await cursor.fetchone()
                
                if not row:
                    return None
                
                # Fetch technologies
                tech_cursor = await conn.execute(
                    "SELECT name, version, category FROM technologies WHERE project_id = ?",
                    (row["id"],)
                )
                tech_rows = await tech_cursor.fetchall()
                technologies = [
                    Technology(name=t["name"], version=t["version"], category=t["category"])
                    for t in tech_rows
                ]
                
                return ProjectContext(
                    id=UUID(row["id"]),
                    name=row["name"],
                    repo_path=Path(row["repo_path"]),
                    technologies=technologies,
                    readiness_level=row["readiness_level"],
                    is_new=False,
                    last_accessed=datetime.fromisoformat(row["last_accessed"]),
                    git_root=Path(row["git_root"]) if row["git_root"] else None,
                    total_commits=row["total_commits"],
                    explained_commits=row["explained_commits"],
                    knowledge_items_count=row["knowledge_items_count"],
                )
        
        return await self._retry_on_locked(_get)
    
    async def update_project_metrics(
        self,
        project_id: UUID,
        total_commits: Optional[int] = None,
        explained_commits: Optional[int] = None,
        knowledge_items_count: Optional[int] = None,
    ) -> None:
        """Update project metrics.
        
        Args:
            project_id: Project UUID
            total_commits: New total commit count (if provided)
            explained_commits: New explained commit count (if provided)
            knowledge_items_count: New knowledge items count (if provided)
        """
        updates = []
        params = []
        
        if total_commits is not None:
            updates.append("total_commits = ?")
            params.append(total_commits)
        
        if explained_commits is not None:
            updates.append("explained_commits = ?")
            params.append(explained_commits)
        
        if knowledge_items_count is not None:
            updates.append("knowledge_items_count = ?")
            params.append(knowledge_items_count)
        
        if not updates:
            return
        
        params.append(str(project_id))
        
        async def _update():
            async with self._get_connection() as conn:
                await conn.execute(
                    f"UPDATE projects SET {', '.join(updates)} WHERE id = ?",
                    params
                )
                await conn.commit()
        
        await self._retry_on_locked(_update)
    
    async def update_project_readiness_level(self, project_id: UUID, level: int) -> None:
        """Update project readiness level.
        
        Args:
            project_id: Project UUID
            level: New readiness level (1-4)
        
        Raises:
            ValueError: If level is invalid
        """
        if not 1 <= level <= 4:
            raise ValueError(f"readiness_level must be between 1 and 4, got {level}")
        
        async def _update():
            async with self._get_connection() as conn:
                await conn.execute(
                    "UPDATE projects SET readiness_level = ? WHERE id = ?",
                    (level, str(project_id))
                )
                await conn.commit()
        
        await self._retry_on_locked(_update)
    
    async def update_project_last_accessed(self, project_id: UUID) -> None:
        """Update project last accessed timestamp to current time.
        
        Args:
            project_id: Project UUID
        """
        async def _update():
            async with self._get_connection() as conn:
                await conn.execute(
                    "UPDATE projects SET last_accessed = ? WHERE id = ?",
                    (datetime.now(timezone.utc).isoformat(), str(project_id))
                )
                await conn.commit()
        
        await self._retry_on_locked(_update)
    
    # ============================================================================
    # IntentRecord CRUD Operations
    # ============================================================================
    
    async def create_intent(
        self,
        session_id: str,
        project_id: UUID,
        intent_description: str,
        files: list[str],
        skills: list[str],
    ) -> IntentRecord:
        """Create a new intent record.
        
        Args:
            session_id: Session identifier
            project_id: Project UUID
            intent_description: Description of learning intent
            files: List of file paths
            skills: List of skill identifiers
        
        Returns:
            Created IntentRecord
        
        Raises:
            ValidationError: If validation fails
        """
        now = datetime.now(timezone.utc)
        intent = IntentRecord(
            id=str(uuid4()),
            session_id=session_id,
            project_id=str(project_id),
            intent_description=intent_description,
            files=files,
            skills=skills,
            created_at=now,
            status=IntentStatus.OPEN,
        )
        
        async def _create():
            async with self._get_connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO intent_records (id, session_id, project_id, intent_description, files_json, skills_json, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        intent.id,
                        intent.session_id,
                        intent.project_id,
                        intent.intent_description,
                        json.dumps(intent.files),
                        json.dumps(intent.skills),
                        intent.status.value,
                        intent.created_at.isoformat(),
                    )
                )
                await conn.commit()
        
        await self._retry_on_locked(_create)
        log.info(f"Created intent {intent.id} for project {project_id}")
        return intent
    
    async def get_open_intents(self, project_id: UUID) -> list[IntentRecord]:
        """Fetch all open intents for a project.
        
        Args:
            project_id: Project UUID
        
        Returns:
            List of open IntentRecords
        """
        async def _get():
            async with self._get_connection() as conn:
                cursor = await conn.execute(
                    """
                    SELECT id, session_id, project_id, intent_description, files_json, skills_json,
                           status, matched_commit_sha, created_at, closed_at
                    FROM intent_records
                    WHERE project_id = ? AND status = 'open'
                    ORDER BY created_at DESC
                    """,
                    (str(project_id),)
                )
                rows = await cursor.fetchall()
                
                intents = []
                for row in rows:
                    intents.append(IntentRecord(
                        id=row["id"],
                        session_id=row["session_id"],
                        project_id=row["project_id"],
                        intent_description=row["intent_description"],
                        files=json.loads(row["files_json"]),
                        skills=json.loads(row["skills_json"]),
                        created_at=datetime.fromisoformat(row["created_at"]),
                        status=IntentStatus(row["status"]),
                        matched_commit_sha=row["matched_commit_sha"],
                        closed_at=datetime.fromisoformat(row["closed_at"]) if row["closed_at"] else None,
                    ))
                
                return intents
        
        return await self._retry_on_locked(_get)
    
    async def close_intent(
        self,
        intent_id: str,
        status: IntentStatus,
        matched_commit_sha: Optional[str] = None,
    ) -> None:
        """Close an intent by updating status.
        
        Args:
            intent_id: Intent ID
            status: New status (MATCHED or ABANDONED)
            matched_commit_sha: Commit SHA if status is MATCHED
        
        Raises:
            ValidationError: If status is MATCHED but commit_sha is None
        """
        if status == IntentStatus.MATCHED and matched_commit_sha is None:
            raise ValidationError("matched_commit_sha required when status is MATCHED")
        
        if status == IntentStatus.OPEN:
            raise ValidationError("Cannot close intent with OPEN status")
        
        now = datetime.now(timezone.utc)
        
        async def _update():
            async with self._get_connection() as conn:
                await conn.execute(
                    """
                    UPDATE intent_records
                    SET status = ?, matched_commit_sha = ?, closed_at = ?
                    WHERE id = ?
                    """,
                    (status.value, matched_commit_sha, now.isoformat(), intent_id)
                )
                await conn.commit()
        
        await self._retry_on_locked(_update)
        log.info(f"Closed intent {intent_id} with status {status.value}")
    
    # ============================================================================
    # ExposureRecord CRUD Operations
    # ============================================================================
    
    async def create_exposure(
        self,
        project_id: UUID,
        intent_id: str,
        commit_sha: str,
        skills: list[str],
        files: list[str],
    ) -> ExposureRecord:
        """Create a new exposure record.
        
        Args:
            project_id: Project UUID
            intent_id: Intent ID
            commit_sha: Git commit SHA (40 hex characters)
            skills: List of skill identifiers
            files: List of file paths
        
        Returns:
            Created ExposureRecord
        
        Raises:
            ValidationError: If validation fails
        """
        now = datetime.now(timezone.utc)
        exposure = ExposureRecord(
            id=str(uuid4()),
            project_id=str(project_id),
            intent_id=intent_id,
            commit_sha=commit_sha,
            skills=skills,
            files=files,
            verified_at=now,
        )
        
        async def _create():
            async with self._get_connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO exposure_records (id, project_id, intent_id, commit_sha, skills_json, files_json, verified_at, explanation_recorded, explanation_depth)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        exposure.id,
                        exposure.project_id,
                        exposure.intent_id,
                        exposure.commit_sha,
                        json.dumps(exposure.skills),
                        json.dumps(exposure.files),
                        exposure.verified_at.isoformat(),
                        1 if exposure.explanation_recorded else 0,
                        exposure.explanation_depth,
                    )
                )
                await conn.commit()
        
        await self._retry_on_locked(_create)
        log.info(f"Created exposure {exposure.id} for intent {intent_id}")
        return exposure
    
    async def update_exposure_explanation(
        self,
        exposure_id: str,
        explanation_depth: float,
    ) -> None:
        """Update exposure with explanation data.
        
        Args:
            exposure_id: Exposure ID
            explanation_depth: Depth score (0.0-1.0)
        
        Raises:
            ValidationError: If depth is out of range
        """
        if not 0.0 <= explanation_depth <= 1.0:
            raise ValidationError(f"explanation_depth must be 0.0-1.0, got {explanation_depth}")
        
        async def _update():
            async with self._get_connection() as conn:
                await conn.execute(
                    """
                    UPDATE exposure_records
                    SET explanation_recorded = 1, explanation_depth = ?
                    WHERE id = ?
                    """,
                    (explanation_depth, exposure_id)
                )
                await conn.commit()
        
        await self._retry_on_locked(_update)
    
    async def get_exposures_without_explanation(self, project_id: UUID, limit: int = 10) -> list[ExposureRecord]:
        """Fetch exposure records without recorded explanations.
        
        Args:
            project_id: Project UUID
            limit: Maximum number of records to return
        
        Returns:
            List of ExposureRecords without explanations
        """
        async def _get():
            async with self._get_connection() as conn:
                cursor = await conn.execute(
                    """
                    SELECT id, project_id, intent_id, commit_sha, skills_json, files_json,
                           verified_at, explanation_recorded, explanation_depth
                    FROM exposure_records
                    WHERE project_id = ? AND explanation_recorded = 0
                    ORDER BY verified_at DESC
                    LIMIT ?
                    """,
                    (str(project_id), limit)
                )
                rows = await cursor.fetchall()
                
                exposures = []
                for row in rows:
                    exposures.append(ExposureRecord(
                        id=row["id"],
                        project_id=row["project_id"],
                        intent_id=row["intent_id"],
                        commit_sha=row["commit_sha"],
                        skills=json.loads(row["skills_json"]),
                        files=json.loads(row["files_json"]),
                        verified_at=datetime.fromisoformat(row["verified_at"]),
                        explanation_recorded=bool(row["explanation_recorded"]),
                        explanation_depth=row["explanation_depth"],
                    ))
                
                return exposures
        
        return await self._retry_on_locked(_get)
    
    # ============================================================================
    # KnowledgeItem CRUD Operations
    # ============================================================================
    
    async def create_knowledge_item(
        self,
        project_id: UUID,
        key: str,
        title: str,
        summary: str,
        tracked_files: list[str],
        depth_band: DepthBand,
        self_rating: Optional[float] = None,
    ) -> KnowledgeItem:
        """Create a new knowledge item.
        
        Args:
            project_id: Project UUID
            key: Unique key within project
            title: Item title (<100 chars)
            summary: Item summary (<500 chars)
            tracked_files: List of tracked file paths
            depth_band: Complexity classification
            self_rating: User self-rating (1.0-5.0)
        
        Returns:
            Created KnowledgeItem
        
        Raises:
            ValidationError: If validation fails
        """
        now = datetime.now(timezone.utc)
        item = KnowledgeItem(
            id=str(uuid4()),
            project_id=str(project_id),
            key=key,
            title=title,
            summary=summary,
            tracked_files=tracked_files,
            depth_band=depth_band,
            created_at=now,
            self_rating=self_rating,
        )
        
        async def _create():
            async with self._get_connection() as conn:
                # Check key uniqueness
                cursor = await conn.execute(
                    "SELECT id FROM knowledge_items WHERE project_id = ? AND key = ?",
                    (str(project_id), key)
                )
                if await cursor.fetchone():
                    raise ValidationError(f"Knowledge item key '{key}' already exists in project")
                
                # Insert into knowledge_items table (using old schema columns)
                await conn.execute(
                    """
                    INSERT INTO knowledge_items (id, project_id, key, title, summary, kind, band, status, depth, created_at, updated_at, self_rating, is_stale, stale_since, last_explained_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item.id,
                        item.project_id,
                        item.key,
                        item.title,
                        item.summary,
                        'concept',  # Default kind
                        item.depth_band.value,
                        'unexplained',  # Default status
                        1,  # Default depth
                        item.created_at.isoformat(),
                        item.created_at.isoformat(),
                        item.self_rating,
                        1 if item.is_stale else 0,
                        item.stale_since.isoformat() if item.stale_since else None,
                        item.last_explained_at.isoformat() if item.last_explained_at else None,
                    )
                )
                
                # Insert tracked files into item_files table
                if tracked_files:
                    await conn.executemany(
                        "INSERT INTO item_files (item_id, path) VALUES (?, ?)",
                        [(item.id, path) for path in tracked_files]
                    )
                
                await conn.commit()
        
        await self._retry_on_locked(_create)
        log.info(f"Created knowledge item {item.id}: {item.key}")
        return item
    
    async def get_knowledge_item_by_key(self, project_id: UUID, key: str) -> Optional[KnowledgeItem]:
        """Find knowledge item by key.
        
        Args:
            project_id: Project UUID
            key: Item key
        
        Returns:
            KnowledgeItem if found, None otherwise
        """
        async def _get():
            async with self._get_connection() as conn:
                cursor = await conn.execute(
                    """
                    SELECT id, project_id, key, title, summary, band, created_at,
                           last_explained_at, self_rating, is_stale, stale_since
                    FROM knowledge_items
                    WHERE project_id = ? AND key = ?
                    """,
                    (str(project_id), key)
                )
                row = await cursor.fetchone()
                
                if not row:
                    return None
                
                # Fetch tracked files
                files_cursor = await conn.execute(
                    "SELECT path FROM item_files WHERE item_id = ?",
                    (row["id"],)
                )
                files_rows = await files_cursor.fetchall()
                tracked_files = [f["path"] for f in files_rows]
                
                return KnowledgeItem(
                    id=row["id"],
                    project_id=row["project_id"],
                    key=row["key"],
                    title=row["title"],
                    summary=row["summary"],
                    tracked_files=tracked_files,
                    depth_band=DepthBand(row["band"]),
                    created_at=datetime.fromisoformat(row["created_at"]),
                    last_explained_at=datetime.fromisoformat(row["last_explained_at"]) if row["last_explained_at"] else None,
                    self_rating=row["self_rating"],
                    is_stale=bool(row["is_stale"]),
                    stale_since=datetime.fromisoformat(row["stale_since"]) if row["stale_since"] else None,
                )
        
        return await self._retry_on_locked(_get)
    
    async def list_knowledge_items(self, project_id: UUID) -> list[KnowledgeItem]:
        """List all knowledge items for a project.
        
        Args:
            project_id: Project UUID
        
        Returns:
            List of KnowledgeItems
        """
        async def _get():
            async with self._get_connection() as conn:
                cursor = await conn.execute(
                    """
                    SELECT id, project_id, key, title, summary, band, created_at,
                           last_explained_at, self_rating, is_stale, stale_since
                    FROM knowledge_items
                    WHERE project_id = ?
                    ORDER BY created_at DESC
                    """,
                    (str(project_id),)
                )
                rows = await cursor.fetchall()
                
                items = []
                for row in rows:
                    # Fetch tracked files for each item
                    files_cursor = await conn.execute(
                        "SELECT path FROM item_files WHERE item_id = ?",
                        (row["id"],)
                    )
                    files_rows = await files_cursor.fetchall()
                    tracked_files = [f["path"] for f in files_rows]
                    
                    items.append(KnowledgeItem(
                        id=row["id"],
                        project_id=row["project_id"],
                        key=row["key"],
                        title=row["title"],
                        summary=row["summary"],
                        tracked_files=tracked_files,
                        depth_band=DepthBand(row["band"]),
                        created_at=datetime.fromisoformat(row["created_at"]),
                        last_explained_at=datetime.fromisoformat(row["last_explained_at"]) if row["last_explained_at"] else None,
                        self_rating=row["self_rating"],
                        is_stale=bool(row["is_stale"]),
                        stale_since=datetime.fromisoformat(row["stale_since"]) if row["stale_since"] else None,
                    ))
                
                return items
        
        return await self._retry_on_locked(_get)
    
    async def update_knowledge_item_staleness(
        self,
        item_id: str,
        is_stale: bool,
        stale_since: Optional[datetime] = None,
    ) -> None:
        """Update knowledge item staleness status.
        
        Args:
            item_id: Knowledge item ID
            is_stale: Staleness flag
            stale_since: Timestamp when item became stale
        """
        async def _update():
            async with self._get_connection() as conn:
                await conn.execute(
                    """
                    UPDATE knowledge_items
                    SET is_stale = ?, stale_since = ?
                    WHERE id = ?
                    """,
                    (
                        1 if is_stale else 0,
                        stale_since.isoformat() if stale_since else None,
                        item_id
                    )
                )
                await conn.commit()
        
        await self._retry_on_locked(_update)
    
    # ============================================================================
    # ReviewSchedule CRUD Operations
    # ============================================================================
    
    async def create_review_schedule(self, item_id: str) -> ReviewSchedule:
        """Create initial review schedule for a knowledge item.
        
        Args:
            item_id: Knowledge item ID
        
        Returns:
            Created ReviewSchedule with initial SM-2 parameters
        """
        schedule = create_initial_review_schedule(item_id)
        
        async def _create():
            async with self._get_connection() as conn:
                await conn.execute(
                    """
                    INSERT INTO review_schedules (id, item_id, interval, easiness, repetitions, success_streak, due_at, snoozed_until, last_reviewed_at, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        schedule.id,
                        schedule.item_id,
                        schedule.interval,
                        schedule.easiness,
                        schedule.repetitions,
                        schedule.success_streak,
                        schedule.due_at.isoformat(),
                        schedule.snoozed_until.isoformat() if schedule.snoozed_until else None,
                        schedule.last_reviewed_at.isoformat() if schedule.last_reviewed_at else None,
                        datetime.now(timezone.utc).isoformat(),
                    )
                )
                await conn.commit()
        
        await self._retry_on_locked(_create)
        log.info(f"Created review schedule for item {item_id}")
        return schedule
    
    async def get_review_schedule(self, item_id: str) -> Optional[ReviewSchedule]:
        """Get review schedule for a knowledge item.
        
        Args:
            item_id: Knowledge item ID
        
        Returns:
            ReviewSchedule if found, None otherwise
        """
        async def _get():
            async with self._get_connection() as conn:
                cursor = await conn.execute(
                    """
                    SELECT id, item_id, interval, easiness, repetitions, success_streak,
                           due_at, snoozed_until, last_reviewed_at
                    FROM review_schedules
                    WHERE item_id = ?
                    """,
                    (item_id,)
                )
                row = await cursor.fetchone()
                
                if not row:
                    return None
                
                return ReviewSchedule(
                    id=row["id"],
                    item_id=row["item_id"],
                    interval=row["interval"],
                    easiness=row["easiness"],
                    repetitions=row["repetitions"],
                    due_at=datetime.fromisoformat(row["due_at"]),
                    snoozed_until=datetime.fromisoformat(row["snoozed_until"]) if row["snoozed_until"] else None,
                    last_reviewed_at=datetime.fromisoformat(row["last_reviewed_at"]) if row["last_reviewed_at"] else None,
                    success_streak=row["success_streak"],
                )
        
        return await self._retry_on_locked(_get)
    
    async def update_review_schedule(self, schedule: ReviewSchedule) -> None:
        """Update review schedule after review completion.
        
        Args:
            schedule: ReviewSchedule with updated values
        """
        async def _update():
            async with self._get_connection() as conn:
                await conn.execute(
                    """
                    UPDATE review_schedules
                    SET interval = ?, easiness = ?, repetitions = ?, success_streak = ?,
                        due_at = ?, last_reviewed_at = ?
                    WHERE id = ?
                    """,
                    (
                        schedule.interval,
                        schedule.easiness,
                        schedule.repetitions,
                        schedule.success_streak,
                        schedule.due_at.isoformat(),
                        schedule.last_reviewed_at.isoformat() if schedule.last_reviewed_at else None,
                        schedule.id,
                    )
                )
                await conn.commit()
        
        await self._retry_on_locked(_update)
    
    async def get_due_reviews(
        self,
        project_id: UUID,
        limit: Optional[int] = None,
    ) -> list[tuple[KnowledgeItem, ReviewSchedule]]:
        """Fetch knowledge items due for review.
        
        Args:
            project_id: Project UUID
            limit: Maximum number of reviews to return
        
        Returns:
            List of (KnowledgeItem, ReviewSchedule) tuples
        """
        now = datetime.now(timezone.utc).isoformat()
        
        async def _get():
            async with self._get_connection() as conn:
                query = """
                    SELECT 
                        ki.id, ki.project_id, ki.key, ki.title, ki.summary, ki.band,
                        ki.created_at, ki.last_explained_at, ki.self_rating, 
                        ki.is_stale, ki.stale_since,
                        rs.id as schedule_id, rs.item_id, rs.interval, rs.easiness, 
                        rs.repetitions, rs.success_streak, rs.due_at, rs.snoozed_until, 
                        rs.last_reviewed_at
                    FROM knowledge_items ki
                    JOIN review_schedules rs ON ki.id = rs.item_id
                    WHERE ki.project_id = ?
                      AND rs.due_at <= ?
                      AND (rs.snoozed_until IS NULL OR rs.snoozed_until <= ?)
                    ORDER BY rs.due_at ASC
                """
                
                params = [str(project_id), now, now]
                
                if limit is not None:
                    query += " LIMIT ?"
                    params.append(limit)
                
                cursor = await conn.execute(query, params)
                rows = await cursor.fetchall()
                
                results = []
                for row in rows:
                    # Fetch tracked files for each item
                    files_cursor = await conn.execute(
                        "SELECT path FROM item_files WHERE item_id = ?",
                        (row["id"],)
                    )
                    files_rows = await files_cursor.fetchall()
                    tracked_files = [f["path"] for f in files_rows]
                    
                    item = KnowledgeItem(
                        id=row["id"],
                        project_id=row["project_id"],
                        key=row["key"],
                        title=row["title"],
                        summary=row["summary"],
                        tracked_files=tracked_files,
                        depth_band=DepthBand(row["band"]),
                        created_at=datetime.fromisoformat(row["created_at"]),
                        last_explained_at=datetime.fromisoformat(row["last_explained_at"]) if row["last_explained_at"] else None,
                        self_rating=row["self_rating"],
                        is_stale=bool(row["is_stale"]),
                        stale_since=datetime.fromisoformat(row["stale_since"]) if row["stale_since"] else None,
                    )
                    
                    schedule = ReviewSchedule(
                        id=row["schedule_id"],
                        item_id=row["item_id"],
                        interval=row["interval"],
                        easiness=row["easiness"],
                        repetitions=row["repetitions"],
                        due_at=datetime.fromisoformat(row["due_at"]),
                        snoozed_until=datetime.fromisoformat(row["snoozed_until"]) if row["snoozed_until"] else None,
                        last_reviewed_at=datetime.fromisoformat(row["last_reviewed_at"]) if row["last_reviewed_at"] else None,
                        success_streak=row["success_streak"],
                    )
                    
                    results.append((item, schedule))
                
                return results
        
        return await self._retry_on_locked(_get)
    
    async def snooze_review(self, schedule_id: str, days: int) -> None:
        """Snooze a review for specified number of days.
        
        Args:
            schedule_id: Review schedule ID
            days: Number of days to snooze
        """
        from datetime import timedelta
        
        snooze_until = datetime.now(timezone.utc) + timedelta(days=days)
        
        async def _update():
            async with self._get_connection() as conn:
                await conn.execute(
                    "UPDATE review_schedules SET snoozed_until = ? WHERE id = ?",
                    (snooze_until.isoformat(), schedule_id)
                )
                await conn.commit()
        
        await self._retry_on_locked(_update)
