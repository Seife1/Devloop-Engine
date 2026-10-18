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


DID_YOU_KNOW_PROTOCOL = """\
Did You Know Fact Protocol:
Trigger: Whenever the user updates the project, scales up, introduces a new technology/library,
refactors, or makes an architectural decision, proactively uncover and record a captivating,
verified insight to spark curiosity and delight ("Aha!" moment).

Focus Areas (Choose what best matches the moment):
1. Living Evolution & Modern Upgrades: Breaking specification changes, modern migrations, and
   deprecations vs new standards (e.g., SSE transport deprecated in favor of Streamable HTTP in MCP).
2. Origin Stories & Computing History: The creator behind the language/tool, why it was built,
   fascinating historical circumstances, or serendipitous accidents (e.g., Guido van Rossum creating
   Python during Christmas 1989 because he was bored; Richard Hipp creating SQLite on a US Navy
   destroyer so damage-control software wouldn't crash when Oracle network sockets failed).
3. Pop Culture, Media & Lore Crossovers: Real-world hacker lore, seminal articles, iconic movies
   (Mr. Robot, WarGames, The Matrix), anime (Ghost in the Shell, Lain), or literature (The Cuckoo's
   Egg, Cryptonomicon) connected to the technical domain (cybersecurity, cryptography, systems, AI).
4. Developer Context Match: Welcoming historical sparks for new languages/beginners, deep
   architectural insights for complex refactors.

Verification & Recording Rules:
1. Identify the relevant technology, architectural concept, or cultural domain in the project.
2. Using your OWN web tools, retrieve and verify an official documentation page, RFC, historical
   archive, or authoritative source.
3. Formulate the insight in your own engaging words (maximum 300 characters). Never invent or guess URLs.
4. Call add_did_you_know(
     project_id=...,
     topic=...,
     fact=...,
     source_url=...,
     source_title=...,
     retrieved_at=...,
     technology=...
   ).
   The source_url must strictly use HTTPS with a valid domain host (no userinfo,
   not localhost or IP literals).\
"""



def register(mcp: FastMCP) -> None:
    @mcp.prompt(
        name="teach-me",
        description="DEPRECATED: not used by per-project flow. Use tour, review, or interview instead.",
    )
    def teach_me(project_id: str = "", skill: str = "") -> str:
        args = []
        if project_id:
            args.append(f"project_id={project_id!r}")
        if skill:
            args.append(f"skill={skill!r}")
        call = f"get_teaching_context({', '.join(args)})"
        return (
            f"DEPRECATED: Prefer tour, review, or mock-interview for per-project confidence.\n"
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

    @mcp.prompt(
        name="did-you-know",
        description="Discover and record a captivating, verified insight (modern specs, origin lore, pop-culture/media crossovers)",
    )
    def did_you_know(project_id: str = "") -> str:
        call = f"refresh_technologies(project_id={project_id!r})" if project_id else "refresh_technologies()"
        return (
            f"Discover and record an engaging, verified insight (living evolution, origin lore, or cultural crossovers).\n"
            f"First check project technologies with {call} or list_items().\n\n"
            f"{DID_YOU_KNOW_PROTOCOL}"
        )
