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
from learnloop.mcp.schemas import LongText, ShortText, SkillId
from learnloop.services import capture_service, reconcile_service

Db = Callable[[], AbstractContextManager[Connection]]


def register(mcp: FastMCP, db: Db, settings: Settings) -> None:
    @mcp.tool()
    def start_project(name: ShortText, repo_path: ShortText) -> dict[str, Any]:
        """Register the project you are working in (idempotent per repo_path). Returns project id."""
        with db() as conn:
            return capture_service.start_project(conn, name, repo_path)

    @mcp.tool()
    def start_skill_session(
        project_id: str,
        skills: Annotated[list[SkillId], Field(min_length=1, max_length=8)],
        summary: LongText,
        rationale: LongText,
        intent_id: str | None = None,
        commit_sha: str | None = None,
    ) -> dict[str, Any]:
        """Declare what you are about to build and which skills it exercises (INTENT only).
        Does not count as learning exposure until a matching git commit verifies it.
        Pass a stable intent_id so retries are idempotent; pass commit_sha to explain an
        already-made 'unexplained' commit."""
        with db() as conn:
            result = capture_service.start_skill_session(
                conn, project_id, skills, summary, rationale, intent_id, commit_sha
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
        """Record a meaningful design choice, the alternatives rejected, and the trade-offs."""
        with db() as conn:
            return capture_service.log_decision(conn, project_id, choice, alternatives, tradeoffs, intent_id)

    @mcp.tool()
    def flag_misunderstanding(
        skill: SkillId,
        pattern: ShortText,
        confidence: Literal["low", "medium", "high"] = "medium",
    ) -> dict[str, Any]:
        """Flag a recurring mistake the LEARNER made (not the AI), e.g. 'patches the defining
        module instead of the importing module'. Only flag what you actually observed."""
        with db() as conn:
            return capture_service.flag_misunderstanding(conn, skill, pattern, confidence)

    @mcp.tool()
    def ingest_queue(project_id: str) -> dict[str, Any]:
        """Ingest queued git commits (written by the post-commit hook), then reconcile them
        with declared intents. Returns commits still unexplained, with suggested skills —
        explain each via start_skill_session(commit_sha=...)."""
        with db() as conn:
            project = capture_service.require_project(conn, project_id)
            stats = queue.ingest(conn, settings, project_id, Path(project["repo_path"]))
            return {**stats, **reconcile_service.reconcile(conn, project_id, settings.abandon_days)}
