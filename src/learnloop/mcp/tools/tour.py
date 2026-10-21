"""Project tour MCP tool."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from sqlite3 import Connection
from typing import Any

from mcp.server.fastmcp import FastMCP

from learnloop.services import tour_service

Db = Callable[[], AbstractContextManager[Connection]]


def register(mcp: FastMCP, db: Db) -> None:
    @mcp.tool()
    def get_project_tour(project_id: str) -> dict[str, Any]:
        """Plan an interactive codebase walkthrough from basic concepts to advanced components."""
        with db() as conn:
            return tour_service.get_project_tour(
                conn, project_id=project_id, max_uncovered=10, include_protocol=False
            )
