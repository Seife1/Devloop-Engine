from __future__ import annotations

import json
import subprocess
from pathlib import Path

from learnloop.capture import queue
from learnloop.cli import cmd_backfill
from learnloop.config import Settings
from learnloop.persistence.db import connect
from learnloop.services import knowledge_service, reconcile_service


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True
    ).stdout


def test_backfill_and_ingest_isolation(tmp_path: Path):
    # 1. Initialize a real git repo
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", "Tester")
    _git(repo, "config", "user.email", "tester@example.com")

    # Commit 1: old file
    (repo / "old_file.py").write_text("x = 1\n")
    _git(repo, "add", "old_file.py")
    _git(repo, "commit", "-m", "commit 1: old file")

    # Commit 2: recent file
    (repo / "recent_file.py").write_text("y = 2\n")
    _git(repo, "add", "recent_file.py")
    _git(repo, "commit", "-m", "commit 2: recent file")

    # 2. Run backfill with limit=1 (so commit 1 is not in the last 1 commit log, but will be in tracked snapshot!)
    ret = cmd_backfill(repo, limit=1)
    assert ret == 0

    # Verify queue files were written
    qdir = repo / ".learn" / "queue"
    q_files = list(qdir.glob("*.json"))
    assert len(q_files) == 2  # 1 commit + 1 snapshot

    # Verify each has origin == 'backfill'
    for qf in q_files:
        data = json.loads(qf.read_text("utf-8"))
        assert data["origin"] == "backfill"

    # Also create an old-format queue file without "origin" field
    old_q = {
        "sha": "old_sha123",
        "message": "old commit message",
        "files": ["legacy.py"],
        "committed_at": "2026-01-01T00:00:00Z",
    }
    (qdir / "old_sha123.json").write_text(json.dumps(old_q), encoding="utf-8")

    # 3. Setup database and ingest
    db_path = tmp_path / "test.db"
    conn = connect(db_path)
    conn.execute(
        "INSERT INTO projects (id, name, repo_path, created_at) VALUES ('p1', 'Repo', ?, '2026-01-01T00:00:00Z')",
        (str(repo.resolve()),),
    )
    conn.commit()

    settings = Settings(db_path=db_path)
    stats = queue.ingest(conn, settings, "p1", repo)
    assert stats["ingested"] == 3

    # Check origin defaults in DB: legacy should be 'hook', backfilled should be 'backfill'
    legacy_row = conn.execute("SELECT origin FROM commits WHERE sha='old_sha123'").fetchone()
    assert legacy_row["origin"] == "hook"

    # Check reconcile: backfilled commits must NEVER appear in unexplained
    rec = reconcile_service.reconcile(conn, "p1")
    unexplained_shas = [u["sha"] for u in rec["unexplained"]]
    assert "old_sha123" in unexplained_shas
    # None of the backfilled commits appear in unexplained!
    for qf in q_files:
        assert qf.stem not in unexplained_shas

    # Verify exposure is 0 (events table has 0 rows)
    assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0

    # Verify that old_file.py (from snapshot) is known and can be registered as an item!
    item = knowledge_service.register_knowledge_item(
        conn=conn,
        project_id="p1",
        key="old.component",
        title="Old Component",
        kind="component",
        band="basic",
        files=["old_file.py"],
        summary="Old component from tracked snapshot.",
    )
    assert item["created"] is True
    assert item["files"] == ["old_file.py"]

    conn.close()
