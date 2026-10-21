"""Domain-clustered MCP tools for LearnLoop.

Groups 17 fine-grained tools into 4 cohesive functional domains:
1. track_intent: Intent declaration, decisions, commit reconciliation, project init.
2. manage_reviews: Session briefings, due reviews, SM-2 grading, and snoozing.
3. manage_knowledge: Item registration, catalog listing, readiness metrics, explain-backs.
4. explore_project: Codebase tours, tech detection, verified insights, profile settings.
"""

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
from learnloop.mcp.schemas import (
    FilePath,
    ItemBand,
    ItemKey,
    ItemKind,
    ItemStatus,
    ItemSummary,
    ItemTitle,
    LearnerAnswerText,
    LearnerAudience,
    LearnerGoal,
    LearnerProfileLevel,
    Limit,
    LongText,
    ReviewLimit,
    ReviewQuestionText,
    Score,
    SelfRating,
    ShortText,
    SkillId,
    SnoozeDays,
)
from learnloop.services import (
    briefing_service,
    capture_service,
    fact_service,
    knowledge_service,
    profile_service,
    readiness_service,
    reconcile_service,
    review_service,
    technology_service,
    tour_service,
)

Db = Callable[[], AbstractContextManager[Connection]]


def resolve_project_id(conn: Connection, project_id: str | None = None) -> str:
    """Resolve project_id from argument or newest active project."""
    if project_id and project_id.strip():
        return project_id.strip()
    try:
        row = conn.execute(
            "SELECT id FROM projects ORDER BY last_accessed DESC, created_at DESC LIMIT 1"
        ).fetchone()
        if row:
            return str(row["id"])
    except Exception:
        pass
    row = conn.execute("SELECT id FROM projects ORDER BY created_at DESC LIMIT 1").fetchone()
    if row:
        return str(row["id"])
    raise ValueError("No project registered in LearnLoop. Call track_intent with action='init_project' first.")


def register(mcp: FastMCP, db: Db, settings: Settings) -> None:
    """Register the 4 clustered domain tools."""

    @mcp.tool()
    def track_intent(
        action: Literal["start_session", "log_decision", "reconcile", "init_project"] = "start_session",
        project_id: str | None = None,
        summary: LongText | None = None,
        files: Annotated[list[FilePath], Field(max_length=50)] | None = None,
        rationale: LongText | None = None,
        skills: Annotated[list[SkillId], Field(min_length=0, max_length=8)] = [],  # noqa: B006
        choice: ShortText | None = None,
        alternatives: Annotated[list[ShortText], Field(max_length=6)] | None = None,
        tradeoffs: LongText | None = None,
        intent_id: str | None = None,
        commit_sha: str | None = None,
        name: ShortText | None = None,
        repo_path: ShortText | None = None,
    ) -> dict[str, Any]:
        """Track learning intents, decisions, commit reconciliation, and project registration.
        
        Actions:
        - 'start_session': Declare what you will build before coding (summary, files, optional rationale/skills).
        - 'log_decision': Record an architectural or design choice (choice, alternatives, tradeoffs).
        - 'reconcile': Ingest queued git commits and verify learning exposures.
        - 'init_project': First-time project setup (name, repo_path). Not needed if already initialized.
        """
        with db() as conn:
            if action == "init_project":
                if not name or not repo_path:
                    raise ValueError("name and repo_path are required for init_project.")
                return capture_service.start_project(conn, name, repo_path)

            pid = resolve_project_id(conn, project_id)

            if action == "start_session":
                if not summary:
                    raise ValueError("summary is required for start_session.")
                result = capture_service.start_skill_session(
                    conn, pid, skills, summary, rationale or "", intent_id, commit_sha, files
                )
                if commit_sha:
                    reconcile_service.reconcile(conn, pid, settings.abandon_days)
                return result

            elif action == "log_decision":
                if not choice or alternatives is None or not tradeoffs:
                    raise ValueError("choice, alternatives, and tradeoffs are required for log_decision.")
                return capture_service.log_decision(conn, pid, choice, alternatives, tradeoffs, intent_id)

            elif action == "reconcile":
                proj = capture_service.require_project(conn, pid)
                stats = queue.ingest(conn, settings, pid, Path(proj["repo_path"]))
                return {**stats, **reconcile_service.reconcile(conn, pid, settings.abandon_days)}

            raise ValueError(f"Unknown action: {action}")

    @mcp.tool()
    def manage_reviews(
        action: Literal["briefing", "due", "record", "snooze"] = "briefing",
        project_id: str | None = None,
        key: ItemKey | None = None,
        question: ReviewQuestionText | None = None,
        learner_answer: LearnerAnswerText | None = None,
        score: Score | None = None,
        days: SnoozeDays = 7,
        limit: ReviewLimit = 3,
        review_id: int | None = None,
    ) -> dict[str, Any]:
        """Manage spaced reviews, SM-2 scheduling, session briefings, and snoozing.

        Actions:
        - 'briefing': Calm session-start catch-up briefing showing changes and due items.
        - 'due': Fetch up to 3 knowledge items due for spaced review today.
        - 'record': Record learner's answer to a review question and reschedule using SM-2.
        - 'snooze': Snooze reviews for a knowledge item between 1 and 30 days.
        """
        with db() as conn:
            pid = resolve_project_id(conn, project_id)

            if action == "briefing":
                return briefing_service.get_session_briefing(conn, project_id=pid)

            elif action == "due":
                return review_service.review_due(conn, project_id=pid, limit=limit)

            elif action == "record":
                if not key or not question or not learner_answer or score is None:
                    raise ValueError("key, question, learner_answer, and score are required for record.")
                return review_service.record_review(
                    conn,
                    project_id=pid,
                    key=key,
                    question=question,
                    learner_answer=learner_answer,
                    score=score,
                    review_id=review_id,
                )

            elif action == "snooze":
                if not key:
                    raise ValueError("key is required for snooze.")
                return review_service.snooze_item(conn, project_id=pid, key=key, days=days)

            raise ValueError(f"Unknown action: {action}")

    @mcp.tool()
    def manage_knowledge(
        action: Literal["register", "list", "readiness", "prompt", "explain"] = "list",
        project_id: str | None = None,
        key: ItemKey | None = None,
        title: ItemTitle | None = None,
        kind: ItemKind | None = None,
        band: ItemBand | None = None,
        status: ItemStatus | None = None,
        summary: ItemSummary | None = None,
        files: Annotated[list[FilePath], Field(min_length=1, max_length=12)] | None = None,
        tags: Annotated[list[Annotated[str, Field(min_length=1, max_length=40)]], Field(max_length=5)] | None = None,
        stale_only: bool = False,
        detailed: bool = False,
        limit: Limit = 30,
        cursor: str | None = None,
        learner_text: Annotated[str, Field(min_length=1, max_length=4000)] | None = None,
        score: Score | None = None,
        audience: LearnerAudience | None = None,
        depth: Annotated[int, Field(ge=1, le=5)] | None = None,
        self_rating: SelfRating | None = None,
        max_context_lines: Annotated[int, Field(ge=10, le=100)] = 50,
    ) -> dict[str, Any]:
        """Manage project knowledge items, explain-backs, readiness metrics, and questions.

        Actions:
        - 'register': Register or update a knowledge item (key, title, kind, band, files, summary).
        - 'list': List project items (optional filters: band, status, stale_only, detailed).
        - 'readiness': Get count-based readiness metrics (explained, stale, due, band counts).
        - 'prompt': Generate depth-appropriate explain-back questions (2-4) and code context.
        - 'explain': Record learner's explain-back and rubric score (0.0-1.0).
        """
        with db() as conn:
            pid = resolve_project_id(conn, project_id)

            if action == "register":
                if not key or not title or not kind or not band or not files or not summary:
                    raise ValueError("key, title, kind, band, files, and summary are required for register.")
                return knowledge_service.register_knowledge_item(
                    conn,
                    project_id=pid,
                    key=key,
                    title=title,
                    kind=kind,
                    band=band,
                    files=files,
                    summary=summary,
                    tags=tags,
                )

            elif action == "list":
                if stale_only:
                    return knowledge_service.list_stale_items(conn, project_id=pid)
                return knowledge_service.list_items(
                    conn,
                    project_id=pid,
                    band=band,
                    status=status,
                    limit=limit,
                    cursor=cursor,
                    detailed=detailed,
                )

            elif action == "readiness":
                return readiness_service.get_project_readiness(conn, project_id=pid)

            elif action == "prompt":
                if not key:
                    raise ValueError("key is required for prompt.")
                return knowledge_service.generate_item_explanation_prompt(
                    conn, project_id=pid, key=key, max_context_lines=max_context_lines
                )

            elif action == "explain":
                if not key or not learner_text or score is None:
                    raise ValueError("key, learner_text, and score are required for explain.")
                return knowledge_service.record_explanation(
                    conn,
                    project_id=pid,
                    key=key,
                    learner_text=learner_text,
                    score=score,
                    audience=audience,
                    depth=depth,
                    self_rating=self_rating,
                )

            raise ValueError(f"Unknown action: {action}")

    @mcp.tool()
    def explore_project(
        action: Literal["tour", "refresh_tech", "add_fact", "set_profile"] = "tour",
        project_id: str | None = None,
        topic: str | None = None,
        fact: str | None = None,
        source_url: str | None = None,
        source_title: str | None = None,
        retrieved_at: str | None = None,
        technology: str | None = None,
        level: LearnerProfileLevel | None = None,
        goal: LearnerGoal | None = None,
        session_minutes: Annotated[int, Field(ge=3, le=30)] | None = None,
        audience: LearnerAudience | None = None,
        max_uncovered: int = 10,
    ) -> dict[str, Any]:
        """Explore codebase walkthroughs, tech stack detection, verified insights, and profile setup.

        Actions:
        - 'tour': Plan or start interactive walkthrough (top dirs, manifests, uncovered files).
        - 'refresh_tech': Scan repository dependencies (Python, Node, Go, Rust, Docker).
        - 'add_fact': Record a verified technical insight, origin history, or spec update (max 300 chars).
        - 'set_profile': Configure learner preferences (level, goal, session minutes, target audience).
        """
        with db() as conn:
            pid = resolve_project_id(conn, project_id)

            if action == "tour":
                return tour_service.get_project_tour(
                    conn, project_id=pid, max_uncovered=max_uncovered, include_protocol=False
                )

            elif action == "refresh_tech":
                return technology_service.refresh_technologies(conn, project_id=pid)

            elif action == "add_fact":
                if not topic or not fact or not source_url or not source_title or not retrieved_at:
                    raise ValueError("topic, fact, source_url, source_title, and retrieved_at are required for add_fact.")
                return fact_service.add_did_you_know(
                    conn,
                    project_id=pid,
                    topic=topic,
                    fact=fact,
                    source_url=source_url,
                    source_title=source_title,
                    retrieved_at=retrieved_at,
                    technology=technology,
                )

            elif action == "set_profile":
                return profile_service.set_learner_profile(
                    conn,
                    level=level,
                    goal=goal,
                    session_minutes=session_minutes,
                    audience=audience,
                    project_id=pid,
                )

            raise ValueError(f"Unknown action: {action}")
