from __future__ import annotations

import hashlib
import sqlite3
import subprocess
from pathlib import Path

from learnloop.capture.queue import ingest
from learnloop.cli import cmd_backfill
from learnloop.config import Settings
from learnloop.persistence.db import migrate
from learnloop.services.knowledge_service import (
    list_stale_items,
    record_explanation,
    register_knowledge_item,
)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def test_backfill_regression_item_not_stale_and_baseline_unchanged(tmp_path: Path):
    """Phase A regression test:
    Explain an item, run backfill (twice), assert the item is NOT stale and the baseline commit is unchanged.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.com")

    # Create file and commit
    src_dir = repo / "src"
    src_dir.mkdir()
    main_file = src_dir / "main.py"
    main_file.write_text("print('hello world')\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "feat: initial commit")
    c1_sha = _git(repo, "rev-parse", "HEAD").strip()
    commit_time = _git(repo, "log", "-1", "--format=%cI", c1_sha).strip()

    # Set up DB
    db_path = tmp_path / "test_learnloop.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    migrate(conn, db_path)

    # Register project
    conn.execute(
        "INSERT INTO projects (id, name, repo_path, created_at) VALUES ('p1', 'Repo', ?, '2026-03-01T00:00:00+00:00')",
        (str(repo),),
    )
    # Record initial commit in DB
    conn.execute(
        "INSERT INTO commits (sha, project_id, message, files, committed_at, status, origin)"
        " VALUES (?, 'p1', 'feat: initial commit', '[\"src/main.py\"]', ?, 'verified', 'hook')",
        (c1_sha, commit_time),
    )
    conn.commit()

    # Register knowledge item
    register_knowledge_item(
        conn,
        project_id="p1",
        key="main-module",
        title="Main Module",
        kind="component",
        band="basic",
        summary="Entrypoint of application",
        files=["src/main.py"],
    )

    # Explain the item
    exp_res = record_explanation(
        conn,
        project_id="p1",
        key="main-module",
        learner_text="This is the main entry point that prints hello world.",
        score=1.0,
    )
    assert exp_res["status"] == "explained"
    assert exp_res["baseline_commit"] == c1_sha

    # Verify not stale initially
    stale_initial = list_stale_items(conn, "p1")
    assert stale_initial["count"] == 0

    # Run backfill first time
    ret1 = cmd_backfill(repo, limit=10)
    assert ret1 == 0

    # Ingest queued entries
    ingest(conn, Settings(db_path=db_path), "p1", repo)

    # Verify item is NOT stale after 1st backfill and baseline commit is unchanged
    stale_after_1 = list_stale_items(conn, "p1")
    assert stale_after_1["count"] == 0

    item_row_1 = conn.execute(
        "SELECT baseline_commit FROM knowledge_items WHERE project_id='p1' AND key='main-module'"
    ).fetchone()
    assert item_row_1["baseline_commit"] == c1_sha

    # Run backfill second time (idempotency)
    ret2 = cmd_backfill(repo, limit=10)
    assert ret2 == 0

    ingest(conn, Settings(db_path=db_path), "p1", repo)

    # Verify item is STILL NOT stale after 2nd backfill and baseline commit is unchanged
    stale_after_2 = list_stale_items(conn, "p1")
    assert stale_after_2["count"] == 0

    item_row_2 = conn.execute(
        "SELECT baseline_commit FROM knowledge_items WHERE project_id='p1' AND key='main-module'"
    ).fetchone()
    assert item_row_2["baseline_commit"] == c1_sha

    # Verify how the backfill snapshot is stored:
    # 1. Deterministic SHA based on head_sha
    expected_snapshot_sha = hashlib.sha1(f"learnloop:backfill:snapshot:{c1_sha}".encode()).hexdigest()
    snapshot_commit = conn.execute(
        "SELECT * FROM commits WHERE sha=?", (expected_snapshot_sha,)
    ).fetchone()
    assert snapshot_commit is not None
    assert snapshot_commit["origin"] == "backfill"
    assert snapshot_commit["message"] == "learnloop: tracked files snapshot"
    assert "src/main.py" in snapshot_commit["files"]

    conn.close()
