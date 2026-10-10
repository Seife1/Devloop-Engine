"""Spaced repetition review and session briefing MCP tools."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from sqlite3 import Connection
from typing import Any

from mcp.server.fastmcp import FastMCP

from learnloop.mcp.schemas import (
    ItemKey,
    LearnerAnswerText,
    ReviewLimit,
    ReviewQuestionText,
    Score,
    ShortText,
    SnoozeDays,
)
from learnloop.services import briefing_service, review_service

Db = Callable[[], AbstractContextManager[Connection]]


def register(mcp: FastMCP, db: Db) -> None:
    @mcp.tool()
    def review_due(
        project_id: ShortText,
        limit: ReviewLimit = 3,
    ) -> dict[str, Any]:
        """Fetch knowledge items due for spaced repetition review today (max 3).
        Ordered with stale items first. Waiting items are shown as a plain count.
        """
        with db() as conn:
            return review_service.review_due(conn, project_id=project_id, limit=limit)

    @mcp.tool()
    def record_review(
        project_id: ShortText,
        key: ItemKey,
        question: ReviewQuestionText,
        learner_answer: LearnerAnswerText,
        score: Score,
        review_id: int | None = None,
    ) -> dict[str, Any]:
        """Record the learner's answer to a spaced review question and reschedule using SM-2.
        Redacts free text before DB write, updates depth if score >= 0.8, and regenerates concepts.md.
        """
        with db() as conn:
            return review_service.record_review(
                conn,
                project_id=project_id,
                key=key,
                question=question,
                learner_answer=learner_answer,
                score=score,
                review_id=review_id,
            )

    @mcp.tool()
    def snooze_item(
        project_id: ShortText,
        key: ItemKey,
        days: SnoozeDays = 7,
    ) -> dict[str, Any]:
        """Snooze reviews for a knowledge item between 1 and 30 days."""
        with db() as conn:
            return review_service.snooze_item(
                conn,
                project_id=project_id,
                key=key,
                days=days,
            )

    @mcp.tool()
    def get_session_briefing(
        project_id: ShortText,
    ) -> dict[str, Any]:
        """Get a calm, compact (< 3 KB) session-start briefing showing recent changes and due reviews.
        Updates projects.last_briefing_at to record this catch-up session.
        """
        with db() as conn:
            return briefing_service.get_session_briefing(
                conn,
                project_id=project_id,
            )
