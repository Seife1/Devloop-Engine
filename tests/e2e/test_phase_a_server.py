from __future__ import annotations

import json
import subprocess
from pathlib import Path

from learnloop.cli import cmd_backfill, cmd_init, cmd_record_commit
from learnloop.server import build_server


async def call(server, name, args):
    result = await server.call_tool(name, args)
    content = result[0] if isinstance(result, tuple) else result
    return json.loads(content[0].text)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout


async def test_phase_a_e2e_full_workflow(settings, tmp_path):
    repo = tmp_path / "phase-a-repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", "Developer")
    _git(repo, "config", "user.email", "dev@example.com")

    # Initial codebase
    src_dir = repo / "src"
    src_dir.mkdir()
    (src_dir / "service.py").write_text("class Service:\n    def run(self): pass\n")
    (repo / "README.md").write_text("# Phase A Demo\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "feat: initial service implementation")

    # 1. Init .learn/
    assert cmd_init(repo) == 0
    assert (repo / ".learn" / "queue").is_dir()

    # 2. Backfill pre-existing commits and tracked snapshot
    assert cmd_backfill(repo, limit=10) == 0

    server = build_server(settings)

    # 3. Register project
    proj = await call(server, "start_project", {"name": "Phase A Project", "repo_path": str(repo)})
    pid = proj["id"]

    # 4. Ingest queue (processes backfill entries)
    ingest_res = await call(server, "ingest_queue", {"project_id": pid})
    assert ingest_res["ingested"] >= 1
    # Backfilled commits must not create exposure or appear in unexplained
    assert len(ingest_res["unexplained"]) == 0

    # 5. Set learner profile
    prof = await call(
        server,
        "set_learner_profile",
        {"level": "junior", "goal": "interview", "session_minutes": 15, "audience": "tech-lead"},
    )
    assert prof["level"] == "junior"
    assert prof["audience"] == "tech-lead"

    # 6. Tour
    tour = await call(server, "get_project_tour", {"project_id": pid})
    assert "src" in tour["top_level_dirs"]
    assert "src/service.py" in tour["uncovered_files"]

    # 7. Register knowledge item
    reg = await call(
        server,
        "register_knowledge_item",
        {
            "project_id": pid,
            "key": "core.service",
            "title": "Core Service",
            "kind": "component",
            "band": "basic",
            "files": ["src/service.py"],
            "summary": "Coordinates system actions and executes business logic",
            "tags": ["service", "core"],
        },
    )
    assert reg["created"] is True
    assert reg["concept_log_written"] is True
    concepts_file = repo / ".learn" / "concepts.md"
    assert concepts_file.is_file()
    assert "### Core Service (`core.service`)" in concepts_file.read_text("utf-8")

    # 8. Record learner explanation
    exp = await call(
        server,
        "record_explanation",
        {
            "project_id": pid,
            "key": "core.service",
            "learner_text": "The core service coordinates application logic via run().",
            "score": 0.95,
        },
    )
    assert exp["status"] == "explained"
    assert exp["baseline_commit"] is not None

    # 9. Verify not stale right now
    stale_initial = await call(server, "list_stale_items", {"project_id": pid})
    assert stale_initial["count"] == 0

    # 10. Make a new commit touching src/service.py (sleep 1.1s to ensure strictly newer git timestamp)
    import asyncio
    await asyncio.sleep(1.1)
    (src_dir / "service.py").write_text("class Service:\n    def run(self): return 42\n")
    _git(repo, "add", "src/service.py")
    _git(repo, "commit", "-m", "fix: return status 42 from service")

    # Record commit (hook side)
    assert cmd_record_commit(repo) == 0

    # 11. Call list_stale_items (auto-ingests the queue!)
    stale_after = await call(server, "list_stale_items", {"project_id": pid})
    assert stale_after["count"] == 1
    stale_item = stale_after["stale_items"][0]
    assert stale_item["key"] == "core.service"
    assert len(stale_item["changing_commits"]) == 1
    assert "return status 42" in stale_item["changing_commits"][0]["message"]
