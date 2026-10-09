from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from sqlite3 import Connection
from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from learnloop.mcp.schemas import QuestionResult, QuizQuestion, SkillId
from learnloop.services import lesson_service, quiz_service

Db = Callable[[], AbstractContextManager[Connection]]


def register(mcp: FastMCP, db: Db) -> None:
    @mcp.tool()
    def get_teaching_context(project_id: str | None = None, skill: SkillId | None = None) -> dict[str, Any]:
        """Start a lesson. Returns the learner's top gap (or the skill you name), the real commits and
        files that exercised it, the AI's stated reasons, design decisions, the learner's known
        mistakes, a difficulty `level`, and step-by-step teaching `instructions` you MUST follow."""
        with db() as conn:
            return lesson_service.get_teaching_context(conn, project_id, skill)

    @mcp.tool()
    def create_quiz(
        skill: SkillId,
        questions: Annotated[list[QuizQuestion], Field(min_length=1, max_length=6)],
        project_id: str | None = None,
    ) -> dict[str, Any]:
        """Store a quiz (questions, reference answers, rubric) BEFORE asking the learner anything.
        Returns quiz_id. Do not reveal reference answers until the learner has answered."""
        with db() as conn:
            return quiz_service.create_quiz(conn, skill, [q.model_dump() for q in questions], project_id)

    @mcp.tool()
    def record_quiz_result(
        quiz_id: str,
        results: Annotated[list[QuestionResult], Field(min_length=1, max_length=6)],
    ) -> dict[str, Any]:
        """Record how the LEARNER did: one result per question, with their answer pasted verbatim and
        your rubric-based score (0-1). Updates mastery once per quiz. A quiz can be recorded only once."""
        with db() as conn:
            return quiz_service.record_quiz_result(conn, quiz_id, [r.model_dump() for r in results])
