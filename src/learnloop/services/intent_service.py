"""Intent tracking service for MCP-native redesign.

This service handles intent creation and management using the new intent_records schema.
Requirements: 4.1-4.6
"""

from __future__ import annotations

import logging
from uuid import UUID

from learnloop.domain.errors import ValidationError
from learnloop.domain.models import IntentRecord
from learnloop.persistence.async_db import AsyncDatabase

log = logging.getLogger(__name__)


async def create_intent(
    db: AsyncDatabase,
    session_id: str,
    project_id: UUID,
    intent_description: str,
    files: list[str],
    skills: list[str] | None = None,
) -> IntentRecord:
    """Create a new intent record for skill session tracking.
    
    Creates an IntentRecord with OPEN status for tracking learning intentions.
    Validates input parameters and ensures data integrity.
    
    Args:
        db: Async database instance
        session_id: MCP session identifier
        project_id: Project UUID
        intent_description: Description of what will be implemented
        files: List of file paths to be modified (required, non-empty)
        skills: Optional list of skill identifiers
    
    Returns:
        Created IntentRecord with OPEN status
    
    Raises:
        ValidationError: If validation fails (empty files, invalid params)
    
    Requirements:
        - 4.1: Create IntentRecord when user calls start_skill_session
        - 4.2: Capture intent description, file list, and skills
        - 4.3: Mark with status "open" upon creation
        - 4.4: Store session_id and timestamp
        - 4.5: Allow multiple open intents per project
        - 4.6: Respond in under 50ms (async operation, non-blocking)
    """
    # Validate inputs (Requirement 4.1, 4.2)
    if not intent_description or not intent_description.strip():
        raise ValidationError("intent_description must not be empty")
    
    if not files or len(files) == 0:
        raise ValidationError("files list must not be empty (Requirement 4.2)")
    
    if len(files) > 50:
        raise ValidationError("files list cannot exceed 50 items")
    
    # Normalize skills list
    skills_list = skills or []
    
    # Create intent using async database layer
    # This creates record with OPEN status (Requirement 4.3)
    # Stores session_id and timestamp (Requirement 4.4)
    intent = await db.create_intent(
        session_id=session_id,
        project_id=project_id,
        intent_description=intent_description,
        files=files,
        skills=skills_list,
    )
    
    log.info(
        f"Created intent {intent.id} for project {project_id}, "
        f"session {session_id}, tracking {len(files)} files"
    )
    
    return intent


async def get_open_intents(
    db: AsyncDatabase,
    project_id: UUID,
) -> list[IntentRecord]:
    """Fetch all open intents for a project.
    
    Args:
        db: Async database instance
        project_id: Project UUID
    
    Returns:
        List of open IntentRecords ordered by creation time (newest first)
    
    Requirements:
        - 7.2: Load all open Intent_Records for the project
        - Filter by project_id
        - Return ordered by created_at
    """
    intents = await db.get_open_intents(project_id)
    log.debug(f"Retrieved {len(intents)} open intents for project {project_id}")
    return intents


async def close_intent(
    db: AsyncDatabase,
    intent_id: str,
    status: str,
    commit_sha: str | None = None,
) -> None:
    """Close an intent with final status.
    
    Args:
        db: Async database instance
        intent_id: Intent record ID
        status: Final status ('matched' or 'abandoned')
        commit_sha: Commit SHA if status is 'matched'
    
    Raises:
        ValidationError: If status is invalid or matched without commit_sha
    """
    if status not in ('matched', 'abandoned'):
        raise ValidationError(f"Invalid intent status: {status}")
    
    if status == 'matched' and not commit_sha:
        raise ValidationError("matched status requires commit_sha")
    
    await db.close_intent(intent_id, status, commit_sha)
    log.info(f"Closed intent {intent_id} with status {status}")
