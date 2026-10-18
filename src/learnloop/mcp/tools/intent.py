"""MCP-native intent tracking tools.

These tools use the new intent_records schema with session tracking.
Requirements: 4.1-4.6, 7.1
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from contextlib import AbstractContextManager
from sqlite3 import Connection
from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from learnloop.config import Settings
from learnloop.mcp.schemas import FilePath, LongText, SkillId
from learnloop.services import capture_service

Db = Callable[[], AbstractContextManager[Connection]]


def _generate_session_id() -> str:
    """Generate a session ID for tracking intents.
    
    In a full MCP implementation, this would come from the MCP context.
    For now, we generate a stable session ID per process.
    """
    # TODO: Extract actual session ID from MCP context when available
    return uuid.uuid4().hex[:16]


def register(mcp: FastMCP, db: Db, settings: Settings) -> None:
    """Register MCP-native intent tracking tools."""
    
    # Session ID is generated once per server instance
    # In production, this should come from MCP session context
    _session_id = _generate_session_id()
    
    @mcp.tool()
    def start_skill_session_v2(
        project_id: str,
        intent_description: LongText,
        files: Annotated[list[FilePath], Field(min_length=1, max_length=50)],
        skills: Annotated[list[SkillId], Field(min_length=0, max_length=8)] = [],  # noqa: B006
        intent_id: str | None = None,
    ) -> dict[str, Any]:
        """Declare what you are about to build (MCP-native version with session tracking).
        
        Creates an intent record that tracks your learning goals before implementation.
        The intent will be matched with git commits to create verified exposure records.
        
        Args:
            project_id: Project identifier
            intent_description: What you plan to implement (1-2000 chars)
            files: List of files you'll be working on (1-50 files)
            skills: Optional skill identifiers being practiced (0-8 skills)
            intent_id: Optional ID for idempotency (auto-generated if not provided)
        
        Returns:
            Dict with intent_id, created (bool), and status
        
        Requirements:
            - 4.1: Tool handler for intent creation
            - 4.2: Validate input parameters (intent, files, skills)
            - 4.3: Create IntentRecord with OPEN status
            - 4.4: Store session_id and timestamp
            - 4.5: Allow multiple open intents per project
            - 4.6: Return success response in under 50ms
        """
        with db() as conn:
            return capture_service.start_skill_session_v2(
                conn=conn,
                project_id=project_id,
                session_id=_session_id,
                intent_description=intent_description,
                files=files,
                skills=skills,
                intent_id=intent_id,
            )
