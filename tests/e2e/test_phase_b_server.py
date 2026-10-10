from __future__ import annotations

import asyncio
import json
import subprocess
from io import StringIO
from pathlib import Path
from unittest.mock import patch

from learnloop.cli import cmd_backfill, cmd_briefing, cmd_init, cmd_record_commit, cmd_review
from learnloop.server import build_server


async def call(server, name, args):
    result = await server.call_tool(name, args)
    content = result[0] if isinstance(result, tuple) else result
    return json.loads(content[0].text)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout


async def test_phase_b_e2e_full_workflow(settings, tmp_path, monkeypatch):
    monkeypatch.setenv("LEARNLOOP_DB", str(settings.db_path))
    repo = tmp_path / "phase-b-repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", "Developer")
    _git(repo, "config", "user.email", "dev@example.com")

    # Initial commit
    src_dir = repo / "src"
    src_dir.mkdir()
    (src_dir / "worker.py").write_text("class Worker:\n    def process(self): pass\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "feat: initial worker implementation")

    # 1. Init & Backfill
    assert cmd_init(repo) == 0
    assert cmd_record_commit(repo) == 0
    assert cmd_backfill(repo, limit=10) == 0

    server = build_server(settings)

    # 2. Register project and ingest
    proj = await call(server, "start_project", {"name": "Phase B Project", "repo_path": str(repo)})
    pid = proj["id"]
    await call(server, "ingest_queue", {"project_id": pid})

    # 3. Register knowledge item
    await call(
        server,
        "register_knowledge_item",
        {
            "project_id": pid,
            "key": "queue.worker",
            "title": "Queue Worker",
            "kind": "component",
            "band": "basic",
            "files": ["src/worker.py"],
            "summary": "Background task consumer",
        },
    )

    # 4. Explain the item
    exp_res = await call(
        server,
        "record_explanation",
        {
            "project_id": pid,
            "key": "queue.worker",
            "learner_text": "Queue Worker processes tasks asynchronously from the work queue.",
            "score": 0.9,
        },
    )
    assert exp_res["status"] == "explained"
    assert exp_res["depth"] == 1

    # 5. Briefing before any modification
    briefing_1 = await call(server, "get_session_briefing", {"project_id": pid})
    assert briefing_1["changes_since_briefing"]["stale_items_count"] == 0
    # Payload cap
    assert len(json.dumps(briefing_1).encode("utf-8")) <= 3072

    # 6. Sleep to ensure timestamp progression, then make a commit modifying worker.py
    await asyncio.sleep(1.1)
    (src_dir / "worker.py").write_text("class Worker:\n    def process(self): return True\n")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "feat: update worker logic")
    assert cmd_record_commit(repo) == 0

    # 7. Briefing after change: detects staleness and suggests 'explain-stale'
    briefing_2 = await call(server, "get_session_briefing", {"project_id": pid})
    assert briefing_2["changes_since_briefing"]["stale_items_count"] == 1
    assert briefing_2["suggested_next"] == "explain-stale"
    assert len(json.dumps(briefing_2).encode("utf-8")) <= 3072

    # 8. review_due: stale item is due immediately and jumps to front
    due_res = await call(server, "review_due", {"project_id": pid, "limit": 3})
    assert len(due_res["items"]) == 1
    assert due_res["items"][0]["key"] == "queue.worker"
    assert due_res["items"][0]["is_stale"] is True

    # 9. record_review: answers review with planted fake secret to test redaction
    fake_secret = "ghp_123456789012345678901234567890123456"
    rev_res = await call(
        server,
        "record_review",
        {
            "project_id": pid,
            "key": "queue.worker",
            "question": f"How do you authenticate token {fake_secret} in worker?",
            "learner_answer": f"Worker uses bearer auth with secret {fake_secret}.",
            "score": 0.9,
        },
    )
    assert rev_res["created"] is True
    assert rev_res["depth"] == 2  # Bumps depth from 1 to 2
    assert rev_res["status"] == "explained"
    assert rev_res["concept_log_written"] is True

    # 10. snooze_item: test snoozing
    snooze_res = await call(server, "snooze_item", {"project_id": pid, "key": "queue.worker", "days": 7})
    assert snooze_res["days"] == 7

    # 11. Prompts registration check
    p_catchup = await server.get_prompt("catch-up", {"project_id": pid})
    assert "get_session_briefing" in p_catchup.messages[0].content.text

    p_review = await server.get_prompt("review", {"project_id": pid})
    assert "review_due" in p_review.messages[0].content.text

    p_interview = await server.get_prompt("interview", {"project_id": pid})
    assert "record_review" in p_interview.messages[0].content.text

    # 12. CLI subcommands test
    with patch("sys.stdout", new_callable=StringIO) as mock_out:
        rc_briefing = cmd_briefing(repo)
        assert rc_briefing == 0
        out_text = mock_out.getvalue()
        assert "LearnLoop Session Briefing:" in out_text
        assert "Suggested next action:" in out_text

    with patch("sys.stdout", new_callable=StringIO) as mock_out:
        rc_review = cmd_review(repo)
        assert rc_review == 0
