"""Knowledge item and explanation tools."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from sqlite3 import Connection
from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from learnloop.mcp.schemas import (
    FilePath,
    ItemBand,
    ItemKey,
    ItemKind,
    ItemStatus,
    ItemSummary,
    ItemTitle,
    LearnerAudience,
    Limit,
    Score,
    SelfRating,
)
from learnloop.services import knowledge_service, readiness_service

Db = Callable[[], AbstractContextManager[Connection]]


def register(mcp: FastMCP, db: Db) -> None:
    import os

    @mcp.tool()
    def register_knowledge_item(
        project_id: str,
        key: ItemKey,
        title: ItemTitle,
        kind: ItemKind,
        band: ItemBand,
        files: Annotated[list[FilePath], Field(min_length=1, max_length=12)],
        summary: ItemSummary,
        tags: Annotated[list[Annotated[str, Field(min_length=1, max_length=40)]], Field(max_length=5)]
        | None = None,
    ) -> dict[str, Any]:
        """Register or update a project knowledge item (component, decision, concept, or bug-fix)."""
        with db() as conn:
            return knowledge_service.register_knowledge_item(
                conn,
                project_id=project_id,
                key=key,
                title=title,
                kind=kind,
                band=band,
                files=files,
                summary=summary,
                tags=tags,
            )

    @mcp.tool()
    def record_explanation(
        project_id: str,
        key: ItemKey,
        learner_text: Annotated[str, Field(min_length=1, max_length=4000)],
        score: Score,
        audience: LearnerAudience | None = None,
        depth: Annotated[int, Field(ge=1, le=5)] | None = None,
        explanation_id: int | None = None,
        self_rating: SelfRating | None = None,
    ) -> dict[str, Any]:
        """Record the learner's explain-back for a knowledge item and rubric score (0.0-1.0)."""
        with db() as conn:
            return knowledge_service.record_explanation(
                conn,
                project_id=project_id,
                key=key,
                learner_text=learner_text,
                score=score,
                audience=audience,
                depth=depth,
                explanation_id=explanation_id,
                self_rating=self_rating,
            )

    @mcp.tool()
    def list_items(
        project_id: str,
        band: ItemBand | None = None,
        status: ItemStatus | None = None,
        stale_only: bool = False,
        detailed: bool = False,
        limit: Limit = 30,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        """List project knowledge items with optional filters. Compact by default (set detailed=True for files/commits)."""
        with db() as conn:
            if stale_only:
                return knowledge_service.list_stale_items(conn, project_id=project_id)
            return knowledge_service.list_items(
                conn,
                project_id=project_id,
                band=band,
                status=status,
                limit=limit,
                cursor=cursor,
                detailed=detailed,
            )

    if os.environ.get("LEARNLOOP_LEGACY_TOOLS") == "1":
        @mcp.tool()
        def list_stale_items(project_id: str) -> dict[str, Any]:
            """DEPRECATED legacy tool. Use list_items(stale_only=True) instead."""
            with db() as conn:
                return knowledge_service.list_stale_items(conn, project_id=project_id)

    @mcp.tool()
    def get_project_readiness(project_id: str | None = None) -> dict[str, Any]:
        """Get count-based readiness metrics for a project (explained, stale, due, and band counts)."""
        with db() as conn:
            return readiness_service.get_project_readiness(conn, project_id=project_id)
    
    @mcp.tool()
    def generate_explanation_prompt(
        project_id: str,
        key: ItemKey,
        max_context_lines: Annotated[int, Field(ge=10, le=100)] = 50,
    ) -> dict[str, Any]:
        """Generate depth-appropriate explain-back questions (2-4) and code context for a knowledge item."""
        with db() as conn:
            return knowledge_service.generate_item_explanation_prompt(
                conn,
                project_id=project_id,
                key=key,
                max_context_lines=max_context_lines,
            )
