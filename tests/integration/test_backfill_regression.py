from __future__ import annotations

import hashlib
import os
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


def _git(repo: Path, *args: str, env: dict[str, str] | None = None) -> str:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
        env=merged_env,
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
    assert snapshot_commit["kind"] == "snapshot"
    assert snapshot_commit["message"] == "learnloop: tracked files snapshot"
    assert "src/main.py" in snapshot_commit["files"]

    conn.close()


def test_backfilled_real_commit_triggers_staleness(tmp_path: Path):
    """v0.4.1 requirement: Real backfilled commits keep origin='backfill'
    (still never unexplained, never exposure) but DO count toward staleness when newer than a baseline.
    """
    repo = tmp_path / "repo_stale"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.com")

    # Initial file and commit c1
    src_dir = repo / "src"
    src_dir.mkdir()
    core_file = src_dir / "core.py"
    core_file.write_text("def run(): return 1\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(
        repo,
        "commit",
        "-m",
        "feat: initial core",
        env={"GIT_AUTHOR_DATE": "2026-03-01T10:00:00+00:00", "GIT_COMMITTER_DATE": "2026-03-01T10:00:00+00:00"},
    )
    c1_sha = _git(repo, "rev-parse", "HEAD").strip()
    c1_time = _git(repo, "log", "-1", "--format=%cI", c1_sha).strip()

    # DB setup
    db_path = tmp_path / "test_stale.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    migrate(conn, db_path)

    # Register project
    conn.execute(
        "INSERT INTO projects (id, name, repo_path, created_at) VALUES ('p1', 'Repo', ?, '2026-03-01T00:00:00+00:00')",
        (str(repo),),
    )
    # Ingest c1
    conn.execute(
        "INSERT INTO commits (sha, project_id, message, files, committed_at, status, origin, kind)"
        " VALUES (?, 'p1', 'feat: initial core', '[\"src/core.py\"]', ?, 'verified', 'hook', 'commit')",
        (c1_sha, c1_time),
    )
    conn.commit()

    # Register knowledge item
    register_knowledge_item(
        conn,
        project_id="p1",
        key="core-logic",
        title="Core Logic",
        kind="component",
        band="basic",
        summary="Core logic runner",
        files=["src/core.py"],
    )

    # Explain item at baseline c1
    exp_res = record_explanation(
        conn,
        project_id="p1",
        key="core-logic",
        learner_text="Runs core logic function.",
        score=1.0,
    )
    assert exp_res["status"] == "explained"
    assert exp_res["baseline_commit"] == c1_sha

    # Verify not stale
    assert list_stale_items(conn, "p1")["count"] == 0

    # Wait or make newer commit in git
    core_file.write_text("def run(): return 2  # updated\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(
        repo,
        "commit",
        "-m",
        "feat: update core logic",
        env={"GIT_AUTHOR_DATE": "2026-03-01T11:00:00+00:00", "GIT_COMMITTER_DATE": "2026-03-01T11:00:00+00:00"},
    )
    c2_sha = _git(repo, "rev-parse", "HEAD").strip()
    assert c2_sha != c1_sha

    # Run backfill to ingest git commits
    ret = cmd_backfill(repo, limit=10)
    assert ret == 0

    # Ingest queue
    ingest(conn, Settings(db_path=db_path), "p1", repo)

    # Verify c2 properties: origin='backfill', kind='commit'
    c2_row = conn.execute("SELECT * FROM commits WHERE sha=?", (c2_sha,)).fetchone()
    assert c2_row is not None
    assert c2_row["origin"] == "backfill"
    assert c2_row["kind"] == "commit"

    # CRITICAL: Verify item IS stale now because newer real commit c2 touched src/core.py!
    stale_res = list_stale_items(conn, "p1")
    assert stale_res["count"] == 1
    assert stale_res["stale_items"][0]["key"] == "core-logic"
    changing_shas = [c["sha"] for c in stale_res["stale_items"][0]["changing_commits"]]
    assert c2_sha in changing_shas

    # Verify origin='backfill' commits never appear as unexplained in reconcile
    from learnloop.services.reconcile_service import reconcile
    rec = reconcile(conn, "p1")
    unexplained_shas = [u["sha"] for u in rec["unexplained"]]
    assert c2_sha not in unexplained_shas

    conn.close()


def test_one_snapshot_per_project_replaces_previous(tmp_path: Path):
    """v0.4.1 requirement: One snapshot per project: a new backfill replaces
    the previous snapshot row, not adds another.
    """
    repo = tmp_path / "repo_snap"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", "Test User")
    _git(repo, "config", "user.email", "test@example.com")

    # Initial file and commit c1
    f1 = repo / "f1.txt"
    f1.write_text("file 1\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "feat: c1")
    c1_sha = _git(repo, "rev-parse", "HEAD").strip()

    # DB setup
    db_path = tmp_path / "test_snap.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    migrate(conn, db_path)

    conn.execute(
        "INSERT INTO projects (id, name, repo_path, created_at) VALUES ('p1', 'Repo', ?, '2026-03-01T00:00:00+00:00')",
        (str(repo),),
    )
    conn.commit()

    # Backfill at c1
    assert cmd_backfill(repo, limit=10) == 0
    ingest(conn, Settings(db_path=db_path), "p1", repo)

    # Verify exactly 1 snapshot row
    snap_rows_1 = conn.execute(
        "SELECT sha, kind FROM commits WHERE project_id='p1' AND kind='snapshot'"
    ).fetchall()
    assert len(snap_rows_1) == 1
    s1_sha = snap_rows_1[0]["sha"]
    expected_s1 = hashlib.sha1(f"learnloop:backfill:snapshot:{c1_sha}".encode()).hexdigest()
    assert s1_sha == expected_s1

    # Now make commit c2 with a new file
    f2 = repo / "f2.txt"
    f2.write_text("file 2\n", encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", "feat: c2")
    c2_sha = _git(repo, "rev-parse", "HEAD").strip()
    assert c2_sha != c1_sha

    # Backfill at c2
    assert cmd_backfill(repo, limit=10) == 0
    ingest(conn, Settings(db_path=db_path), "p1", repo)

    # Verify STILL exactly 1 snapshot row, and it replaced s1 with s2
    snap_rows_2 = conn.execute(
        "SELECT sha, files, kind FROM commits WHERE project_id='p1' AND kind='snapshot'"
    ).fetchall()
    assert len(snap_rows_2) == 1
    s2_sha = snap_rows_2[0]["sha"]
    expected_s2 = hashlib.sha1(f"learnloop:backfill:snapshot:{c2_sha}".encode()).hexdigest()
    assert s2_sha == expected_s2
    assert s2_sha != s1_sha
    assert "f2.txt" in snap_rows_2[0]["files"]

    # Verify old s1 row is completely gone
    assert conn.execute("SELECT COUNT(*) FROM commits WHERE sha=?", (s1_sha,)).fetchone()[0] == 0

    conn.close()
