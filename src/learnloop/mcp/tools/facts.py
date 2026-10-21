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
        """Record a verified technical insight, origin history, or modern spec update for a project technology (max 300 chars, HTTPS source)."""
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
