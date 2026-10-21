"""Unit tests for domain-clustered MCP tools."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from learnloop.config import Settings
from learnloop.persistence.db import connect
from learnloop.server import build_server


@pytest.fixture
def test_env(tmp_path: Path):
    db_path = tmp_path / "test.db"
    settings = Settings(db_path=db_path)
    server = build_server(settings)
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()
    (repo / "main.py").write_text("print('hello')\n")
    return server, settings, repo


@pytest.mark.asyncio
async def test_clustered_tools_registered(test_env):
    server, settings, repo = test_env
    tools = await server.list_tools()
    tool_names = {t.name for t in tools}
    assert "track_intent" in tool_names
    assert "manage_reviews" in tool_names
    assert "manage_knowledge" in tool_names
    assert "explore_project" in tool_names


@pytest.mark.asyncio
async def test_track_intent_and_auto_project_resolution(test_env):
    server, settings, repo = test_env

    # 1. Init project
    res_init = await server.call_tool(
        "track_intent",
        {"action": "init_project", "name": "cluster_test", "repo_path": str(repo.resolve())},
    )
    assert res_init is not None

    # 2. Start session WITHOUT project_id (auto-resolved!)
    res_intent = await server.call_tool(
        "track_intent",
        {
            "action": "start_session",
            "summary": "Build cluster tools",
            "files": ["main.py"],
        },
    )
    assert res_intent is not None

    # 3. Log decision WITHOUT project_id (auto-resolved!)
    res_decision = await server.call_tool(
        "track_intent",
        {
            "action": "log_decision",
            "choice": "Domain clustering",
            "alternatives": ["Individual tools"],
            "tradeoffs": "Fewer tools vs slightly wider arguments",
        },
    )
    assert res_decision is not None


@pytest.mark.asyncio
async def test_manage_knowledge_and_reviews_workflow(test_env):
    server, settings, repo = test_env

    # Setup project and commit
    conn = connect(settings.db_path)
    conn.execute(
        "INSERT INTO projects (id, name, repo_path, created_at) VALUES ('p1', 'Repo', ?, '2026-01-01T00:00:00Z')",
        (str(repo.resolve()),),
    )
    conn.execute(
        "INSERT INTO commits (sha, project_id, message, files, committed_at, status, origin)"
        " VALUES ('c1', 'p1', 'init', '[\"main.py\"]', '2026-01-01T00:00:00Z', 'verified', 'hook')"
    )
    conn.commit()
    conn.close()

    # 1. Register knowledge item
    res_reg = await server.call_tool(
        "manage_knowledge",
        {
            "action": "register",
            "key": "app.core",
            "title": "Application Core",
            "kind": "component",
            "band": "basic",
            "files": ["main.py"],
            "summary": "Main entry point of the app",
        },
    )
    assert res_reg is not None

    # 2. List items (compact by default)
    res_list = await server.call_tool("manage_knowledge", {"action": "list"})
    assert res_list is not None

    # 3. Get readiness
    res_ready = await server.call_tool("manage_knowledge", {"action": "readiness"})
    assert res_ready is not None

    # 4. Reviews - session briefing
    res_briefing = await server.call_tool("manage_reviews", {"action": "briefing"})
    assert res_briefing is not None

    # 5. Explore project - tour
    res_tour = await server.call_tool("explore_project", {"action": "tour"})
    assert res_tour is not None
