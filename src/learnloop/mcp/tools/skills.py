from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from sqlite3 import Connection
from typing import Any

from mcp.server.fastmcp import FastMCP

from learnloop.mcp.schemas import Limit, ShortText, SkillProposalId
from learnloop.services import skill_service

Db = Callable[[], AbstractContextManager[Connection]]


def register(mcp: FastMCP, db: Db) -> None:
    @mcp.tool()
    def list_skills(prefix: str = "") -> list[dict[str, str]]:
        """DEPRECATED: not used by the per-project flow.
        List valid skill ids (optionally filtered by prefix like 'python.testing')."""
        with db() as conn:
            rows = conn.execute(
                "SELECT id, name, source FROM skills WHERE id LIKE ? ORDER BY id LIMIT 100", (prefix + "%",)
            )
            return [{"id": r["id"], "name": r["name"], "source": r["source"] or "seed"} for r in rows]

    @mcp.tool()
    def propose_skill(id: SkillProposalId, name: ShortText, rationale: ShortText) -> dict[str, Any]:
        """DEPRECATED: not used by the per-project flow.
        Propose a new fine-grained skill. Id must extend an existing parent (e.g. 'python.dataclasses')."""
        with db() as conn:
            return skill_service.propose_skill(conn, id, name, rationale)

    @mcp.tool()
    def get_skill_map(project_id: str | None = None, limit: Limit = 10) -> dict[str, Any]:
        """DEPRECATED: not used by the per-project flow.
        Skills with VERIFIED exposure next to the learner's mastery, confidence and attempt
        count. Top-N by exposure; check `truncated`. Mastery of 'untested' is not zero — it is unknown."""
        with db() as conn:
            return skill_service.get_skill_map(conn, project_id, limit)

    @mcp.tool()
    def find_gaps(project_id: str | None = None, limit: Limit = 5) -> dict[str, Any]:
        """DEPRECATED: not used by the per-project flow.
        Skills the AI used a lot that the learner has not demonstrated. Highest priority first."""
        with db() as conn:
            return skill_service.find_gaps(conn, project_id, limit)

    @mcp.tool()
    def flag_misunderstanding(
        skill: str,
        pattern: ShortText,
        confidence: str = "medium",
    ) -> dict[str, Any]:
        """DEPRECATED legacy tool."""
        from learnloop.services import capture_service
        with db() as conn:
            return capture_service.flag_misunderstanding(conn, skill, pattern, confidence)
