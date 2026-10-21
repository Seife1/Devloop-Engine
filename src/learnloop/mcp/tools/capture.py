"""Intent + outcome tools. Thin: validate -> one service call -> shape result."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from pathlib import Path
from sqlite3 import Connection
from typing import Annotated, Any, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from learnloop.capture import queue
from learnloop.config import Settings
from learnloop.mcp.schemas import FilePath, LongText, ShortText, SkillId
from learnloop.services import capture_service, reconcile_service

Db = Callable[[], AbstractContextManager[Connection]]


def register(mcp: FastMCP, db: Db, settings: Settings) -> None:
    @mcp.tool()
    def start_project(name: ShortText, repo_path: ShortText) -> dict[str, Any]:
        """Register the workspace project (idempotent per repo_path). Returns project ID."""
        with db() as conn:
            return capture_service.start_project(conn, name, repo_path)

    @mcp.tool()
    def start_skill_session(
        project_id: str,
        summary: LongText,
        files: Annotated[list[FilePath], Field(max_length=50)] | None = None,
        rationale: LongText | None = None,
        skills: Annotated[list[SkillId], Field(min_length=0, max_length=8)] = [],  # noqa: B006
        intent_id: str | None = None,
        commit_sha: str | None = None,
    ) -> dict[str, Any]:
        """Declare what you plan to build before coding, or explain a commit. Matched with git commits."""
        with db() as conn:
            result = capture_service.start_skill_session(
                conn, project_id, skills, summary, rationale or "", intent_id, commit_sha, files
            )
            if commit_sha:
                reconcile_service.reconcile(conn, project_id, settings.abandon_days)
            return result

    @mcp.tool()
    def log_decision(
        project_id: str,
        choice: ShortText,
        alternatives: Annotated[list[ShortText], Field(max_length=6)],
        tradeoffs: LongText,
        intent_id: str | None = None,
    ) -> dict[str, Any]:
        """Record an architectural or design decision with alternatives and trade-offs."""
        with db() as conn:
            return capture_service.log_decision(conn, project_id, choice, alternatives, tradeoffs, intent_id)

    @mcp.tool()
    def ingest_queue(project_id: str) -> dict[str, Any]:
        """Ingest queued git commits and reconcile them with declared learning intents."""
        with db() as conn:
            project = capture_service.require_project(conn, project_id)
            stats = queue.ingest(conn, settings, project_id, Path(project["repo_path"]))
            return {**stats, **reconcile_service.reconcile(conn, project_id, settings.abandon_days)}
