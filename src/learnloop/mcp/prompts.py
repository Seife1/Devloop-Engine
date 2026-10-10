from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from learnloop.services.lesson_service import TEACHING_PROTOCOL
from learnloop.services.tour_service import TOUR_PROTOCOL


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
