"""Learner profile MCP tools."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from sqlite3 import Connection
from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from learnloop.mcp.schemas import LearnerAudience, LearnerGoal, LearnerProfileLevel
from learnloop.services import profile_service

Db = Callable[[], AbstractContextManager[Connection]]


def register(mcp: FastMCP, db: Db) -> None:
    @mcp.tool()
    def set_learner_profile(
        level: LearnerProfileLevel | None = None,
        goal: LearnerGoal | None = None,
        session_minutes: Annotated[int, Field(ge=3, le=30)] | None = None,
        audience: LearnerAudience | None = None,
        project_id: str | None = None,
    ) -> dict[str, Any]:
        """Configure learner profile preferences (level, goal, session minutes, target audience).
        If project_id is provided, overrides profile for that project; otherwise updates global profile."""
        with db() as conn:
            return profile_service.set_learner_profile(
                conn,
                level=level,
                goal=goal,
                session_minutes=session_minutes,
                audience=audience,
                project_id=project_id,
            )
