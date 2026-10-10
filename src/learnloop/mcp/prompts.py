from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from learnloop.services.briefing_service import BRIEFING_PROTOCOL
from learnloop.services.lesson_service import TEACHING_PROTOCOL
from learnloop.services.review_service import REVIEW_PROTOCOL
from learnloop.services.tour_service import TOUR_PROTOCOL

INTERVIEW_PROTOCOL = """\
Mock Interview Protocol:
1. Adopt the interviewer persona matching the learner profile audience (tech-lead, recruiter, classmate).
2. Ask ONE technical interview question at a time about this project's components, decisions, or trade-offs.
3. Wait for the learner's own response before following up or evaluating.
4. Drill deeper with realistic follow-up questions: edge cases, failure modes, scalability, alternatives.
5. Grade each answer objectively against a clear rubric (0.0 to 1.0).
6. Record each outcome using record_review(
   project_id=..., key=..., question=..., learner_answer=..., score=...
).
7. Conclude after 3 to 5 questions with concise, actionable feedback.\
"""


def register(mcp: FastMCP) -> None:
    @mcp.prompt(name="teach-me", description="Teach me my biggest gap, using my own project's code")
    def teach_me(project_id: str = "", skill: str = "") -> str:
        args = []
        if project_id:
            args.append(f"project_id={project_id!r}")
        if skill:
            args.append(f"skill={skill!r}")
        call = f"get_teaching_context({', '.join(args)})"
        return (
            f"Run a LearnLoop lesson. First call {call}, then follow its `instructions` exactly.\n\n"
            f"{TEACHING_PROTOCOL}"
        )

    @mcp.prompt(name="tour", description="Start an interactive tour of the project from basics to advanced")
    def tour(project_id: str = "") -> str:
        call = f"get_project_tour(project_id={project_id!r})" if project_id else "get_project_tour()"
        return (
            f"Run an interactive project tour. First call {call}, then follow its `protocol` exactly.\n\n"
            f"{TOUR_PROTOCOL}"
        )

    @mcp.prompt(name="catch-up", description="Deliver a quick session-start briefing on what changed")
    def catch_up(project_id: str = "") -> str:
        call = f"get_session_briefing(project_id={project_id!r})" if project_id else "get_session_briefing()"
        return (
            f"Run a LearnLoop session catch-up briefing. First call {call},\n"
            f"then follow its `protocol` exactly.\n\n"
            f"{BRIEFING_PROTOCOL}"
        )

    @mcp.prompt(name="review", description="Run today's spaced repetition review of knowledge items")
    def review(project_id: str = "") -> str:
        call = f"review_due(project_id={project_id!r})" if project_id else "review_due()"
        return (
            f"Run a LearnLoop spaced review session. First call {call}, then follow its `protocol` exactly.\n"
            f"For each item reviewed, record the score and explanation using record_review(...).\n\n"
            f"{REVIEW_PROTOCOL}"
        )

    @mcp.prompt(name="interview", description="Mock technical interview based on project knowledge items")
    def interview(project_id: str = "") -> str:
        args = f"project_id={project_id!r}" if project_id else ""
        return (
            f"Conduct a mock technical interview based on project knowledge items.\n"
            f"First call get_learner_profile() and review_due({args}) or list_knowledge_items({args}).\n\n"
            f"{INTERVIEW_PROTOCOL}"
        )
