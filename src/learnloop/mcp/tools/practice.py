from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from sqlite3 import Connection
from typing import Any

from mcp.server.fastmcp import FastMCP

from learnloop.mcp.schemas import Score, SkillId
from learnloop.services import practice_service

Db = Callable[[], AbstractContextManager[Connection]]


def register(mcp: FastMCP, db: Db) -> None:
    @mcp.tool()
    def submit_attempt(skill: SkillId, score: Score, hints_used: int = 0) -> dict[str, Any]:
        """Record the LEARNER's graded attempt (0.0-1.0) on a skill. Only the learner's own
        answers belong here — never score work the AI did. Updates mastery and returns
        mastery with attempt count and confidence."""
        with db() as conn:
            return practice_service.submit_attempt(conn, skill, score, max(0, hints_used))
