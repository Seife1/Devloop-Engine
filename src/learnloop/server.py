from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from mcp.server.fastmcp import FastMCP

from learnloop.config import Settings
from learnloop.mcp import prompts
from learnloop.mcp.tools import capture, practice, skills, teaching
from learnloop.persistence.db import connect


def build_server(settings: Settings | None = None) -> FastMCP:
    settings = settings or Settings.load()

    @contextmanager
    def db() -> Iterator[sqlite3.Connection]:
        conn = connect(settings.db_path)
        try:
            yield conn
        finally:
            conn.close()

    mcp = FastMCP("learnloop")
    capture.register(mcp, db, settings)
    skills.register(mcp, db)
    practice.register(mcp, db)
    teaching.register(mcp, db)
    prompts.register(mcp)
    return mcp
