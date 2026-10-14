"""Project technologies MCP tool."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from sqlite3 import Connection
from typing import Any

from mcp.server.fastmcp import FastMCP

from learnloop.services import technology_service

Db = Callable[[], AbstractContextManager[Connection]]


def register(mcp: FastMCP, db: Db) -> None:
    @mcp.tool()
    def refresh_technologies(project_id: str) -> dict[str, Any]:
        """Deterministically scan repository dependencies (Python, Node, Go, Rust, Docker).

        Updates project technologies. Reads only within the project's repository up to 2 directories deep.
        Offline, no network, no LLMs.
        """
        with db() as conn:
            return technology_service.refresh_technologies(conn, project_id=project_id)
