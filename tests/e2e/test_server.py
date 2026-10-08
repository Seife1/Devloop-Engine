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
