"""Did You Know facts MCP tool."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from sqlite3 import Connection
from typing import Any

from mcp.server.fastmcp import FastMCP

from learnloop.services import fact_service

Db = Callable[[], AbstractContextManager[Connection]]


def register(mcp: FastMCP, db: Db) -> None:
    @mcp.tool()
    def add_did_you_know(
        project_id: str,
        topic: str,
        fact: str,
        source_url: str,
        source_title: str,
        retrieved_at: str,
        technology: str | None = None,
    ) -> dict[str, Any]:
        """Record a captivating, verified insight connected to a project technology, architecture, or history.

        Trigger whenever the user adds/updates technology, scales the project, or makes key technical decisions.
        Uncovers living spec evolution (e.g. deprecations/upgrades), creator origin stories & computing lore,
        or pop-culture/historical media crossovers (movies, anime, books, real-world lore) to create an "Aha!" moment.

        Protocol requirement: You MUST fetch and read the source using your own web tools BEFORE
        calling this tool. Write the fact in your own engaging words (max 300 chars). The source_url
        must be HTTPS with a valid domain host (no userinfo, not localhost or IP literals).
        """
        with db() as conn:
            return fact_service.add_did_you_know(
                conn,
                project_id=project_id,
                topic=topic,
                fact=fact,
                source_url=source_url,
                source_title=source_title,
                retrieved_at=retrieved_at,
                technology=technology,
            )
