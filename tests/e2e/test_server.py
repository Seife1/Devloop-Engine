"""Drive the real FastMCP server the way an IDE agent would."""

import json
import subprocess

from learnloop.server import build_server


async def call(server, name, args):
    result = await server.call_tool(name, args)
    content = result[0] if isinstance(result, tuple) else result
    return json.loads(content[0].text)


async def test_tools_are_registered(settings):
    names = {t.name for t in await build_server(settings).list_tools()}
    assert {
        "start_project",
        "start_skill_session",
        "ingest_queue",
        "find_gaps",
        "get_skill_map",
        "submit_attempt",
        "flag_misunderstanding",
        "log_decision",
        "list_skills",
    } <= names


async def test_full_loop_with_real_git_hook_path(settings, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    run = lambda *a: subprocess.run(["git", "-C", str(repo), *a], check=True, capture_output=True)  # noqa: E731
    run("init", "-q")
    run("config", "user.email", "t@t")
    run("config", "user.name", "t")
    server = build_server(settings)

    project = await call(server, "start_project", {"name": "demo", "repo_path": str(repo)})
    await call(
        server,
        "start_skill_session",
        {
            "project_id": project["id"],
            "skills": ["python.testing.mocking"],
            "summary": "mock requests in tests",
            "rationale": "avoid network",
        },
    )

    (repo / "test_a.py").write_text("def test_x(): pass\n")
    (repo / ".env").write_text("SECRET=1\n")
    run("add", ".")
    run("commit", "-qm", "add tests")  # noqa: E702
    from learnloop.cli import cmd_record_commit

    assert cmd_record_commit(repo) == 0  # what the hook runs

    result = await call(server, "ingest_queue", {"project_id": project["id"]})
    assert result["ingested"] == 1 and result["commits_verified"] == 1

    gaps = await call(server, "find_gaps", {"project_id": project["id"]})
    assert gaps["gaps"][0]["skill"] == "python.testing.mocking"
    assert gaps["gaps"][0]["status"] == "untested"

    queued = json.dumps([p.name for p in (repo / ".learn" / "queue").glob("*")])
    assert ".env" not in queued


async def test_hook_never_fails_outside_a_repo(tmp_path):
    from learnloop.cli import cmd_record_commit

    assert cmd_record_commit(tmp_path) == 0


async def test_teaching_tools_and_prompt_registered(settings):
    server = build_server(settings)
    names = {t.name for t in await server.list_tools()}
    assert {"get_teaching_context", "create_quiz", "record_quiz_result"} <= names
    prompts = {p.name for p in await server.list_prompts()}
    assert "teach-me" in prompts


async def test_teach_me_prompt_embeds_protocol(settings):
    server = build_server(settings)
    result = await server.get_prompt("teach-me", {"project_id": "p1"})
    text = result.messages[0].content.text
    assert "get_teaching_context(project_id='p1')" in text and "WAIT" in text


async def test_lesson_over_the_protocol(settings, tmp_path):
    server = build_server(settings)
    project = await call(server, "start_project", {"name": "d", "repo_path": str(tmp_path)})
    ctx = await call(server, "get_teaching_context", {"project_id": project["id"]})
    assert ctx["skill"] is None
    quiz = await call(
        server,
        "create_quiz",
        {
            "skill": "python",
            "questions": [
                {"kind": "explain", "prompt": "why?", "reference_answer": "because", "rubric": ["a"]}
            ],
        },
    )
    out = await call(
        server,
        "record_quiz_result",
        {
            "quiz_id": quiz["quiz_id"],
            "results": [{"ordinal": 1, "learner_answer": "because it is", "score": 0.5}],
        },
    )
    assert out["attempts"] == 1 and out["confidence"] == "low"
