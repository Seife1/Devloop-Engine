from __future__ import annotations

import json
from pathlib import Path

import pytest

from learnloop.domain.errors import ValidationError
from learnloop.persistence.db import connect
from learnloop.services import knowledge_service


def test_register_knowledge_item_validations_and_redaction(tmp_path: Path):
    db_path = tmp_path / "test.db"
    conn = connect(db_path)

    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()

    conn.execute(
        "INSERT INTO projects (id, name, repo_path, created_at) VALUES ('p1', 'Repo', ?, '2026-01-01T00:00:00Z')",
        (str(repo_dir.resolve()),),
    )
    # Seed known commit with specific files
    known_files = ["src/auth.py", "src/user.py", "tests/test_auth.py"]
    conn.execute(
        "INSERT INTO commits (sha, project_id, message, files, committed_at, status, origin)"
        " VALUES ('c1', 'p1', 'init', ?, '2026-01-01T00:00:00Z', 'verified', 'hook')",
        (json.dumps(known_files),),
    )
    conn.commit()

    # 1. Reject unknown paths with difflib candidate suggestions
    with pytest.raises(ValidationError) as exc:
        knowledge_service.register_knowledge_item(
            conn=conn,
            project_id="p1",
            key="auth.mod",
            title="Auth",
            kind="component",
            band="basic",
            files=["src/aut.py"],  # typo
            summary="Auth module",
        )
    assert "src/auth.py" in str(exc.value)

    # 2. Reject absolute paths and parent traversal
    with pytest.raises(ValidationError):
        knowledge_service.register_knowledge_item(
            conn=conn,
            project_id="p1",
            key="bad.path1",
            title="Bad",
            kind="component",
            band="basic",
            files=["/src/auth.py"],
            summary="Bad path",
        )
    with pytest.raises(ValidationError):
        knowledge_service.register_knowledge_item(
            conn=conn,
            project_id="p1",
            key="bad.path2",
            title="Bad",
            kind="component",
            band="basic",
            files=["../auth.py"],
            summary="Bad path",
        )

    # 3. Reject empty files or > 12 files
    with pytest.raises(ValidationError):
        knowledge_service.register_knowledge_item(
            conn=conn,
            project_id="p1",
            key="empty.files",
            title="Bad",
            kind="component",
            band="basic",
            files=[],
            summary="Bad",
        )

    # 4. Redaction test: fake secrets in title, summary, and tags
    secret_key = "sk-live-999999999999999999999999999999"
    item = knowledge_service.register_knowledge_item(
        conn=conn,
        project_id="p1",
        key="auth.service",
        title=f"Auth Service with key {secret_key}",
        kind="component",
        band="basic",
        files=["src/auth.py"],
        summary=f"Uses token {secret_key} for login",
        tags=["auth", f"tag-{secret_key}"],
    )
    assert item["created"] is True
    assert secret_key not in item["title"]
    assert secret_key not in item["summary"]
    for t in item["tags"]:
        assert secret_key not in t

    # Check directly in the database
    db_row = conn.execute("SELECT * FROM knowledge_items WHERE id=?", (item["id"],)).fetchone()
    assert secret_key not in db_row["title"]
    assert secret_key not in db_row["summary"]
    assert "[REDACTED]" in db_row["summary"]

    tag_rows = conn.execute("SELECT tag FROM item_tags WHERE item_id=?", (item["id"],)).fetchall()
    for tr in tag_rows:
        assert secret_key not in tr["tag"]

    # 5. Idempotent upsert
    item_updated = knowledge_service.register_knowledge_item(
        conn=conn,
        project_id="p1",
        key="auth.service",
        title="Updated Auth Service",
        kind="component",
        band="intermediate",
        files=["src/auth.py", "src/user.py"],
        summary="Updated summary without secrets",
        tags=["auth", "users"],
    )
    assert item_updated["created"] is False
    assert item_updated["id"] == item["id"]
    assert item_updated["band"] == "intermediate"
    assert len(item_updated["files"]) == 2

    conn.close()


def test_record_explanation_and_staleness_auto_ingest(tmp_path: Path):
    db_path = tmp_path / "test.db"
    conn = connect(db_path)

    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()
    q_dir = repo_dir / ".learn" / "queue"
    q_dir.mkdir(parents=True)

    conn.execute(
        "INSERT INTO projects (id, name, repo_path, created_at) VALUES ('p1', 'Repo', ?, '2026-01-01T00:00:00Z')",
        (str(repo_dir.resolve()),),
    )
    conn.execute(
        "INSERT INTO commits (sha, project_id, message, files, committed_at, status, origin)"
        " VALUES ('c1', 'p1', 'commit 1', '[\"src/core.py\"]', '2026-01-01T10:00:00Z', 'verified', 'hook')"
    )
    conn.commit()

    # Register knowledge item
    knowledge_service.register_knowledge_item(
        conn=conn,
        project_id="p1",
        key="core.sys",
        title="Core System",
        kind="component",
        band="basic",
        files=["src/core.py"],
        summary="Core logic",
    )

    # 1. Rejects empty learner_text
    with pytest.raises(ValidationError):
        knowledge_service.record_explanation(
            conn=conn,
            project_id="p1",
            key="core.sys",
            learner_text="   ",
            score=0.9,
        )

    # 2. Add a new commit to the queue (un-ingested), then call record_explanation
    # Amendment 5 test: record_explanation must auto-ingest the queue,
    # so baseline_commit is 'c2' (current HEAD), NOT the old 'c1'!
    q_entry = {
        "sha": "c2",
        "message": "commit 2: modify core",
        "files": ["src/core.py"],
        "committed_at": "2026-01-01T11:00:00Z",
        "origin": "hook",
    }
    (q_dir / "c2.json").write_text(json.dumps(q_entry), encoding="utf-8")

    secret_in_exp = "sk-live-555555555555555555555555555555"
    exp = knowledge_service.record_explanation(
        conn=conn,
        project_id="p1",
        key="core.sys",
        learner_text=f"I modified the core system using secret {secret_in_exp}",
        score=0.9,
        depth=2,
    )
    assert exp["created"] is True
    assert exp["status"] == "explained"
    assert exp["depth"] == 2
    # Baseline commit must be c2 because of auto-ingest!
    assert exp["baseline_commit"] == "c2"

    # Verify secret redacted in explanations table
    exp_db = conn.execute("SELECT learner_text FROM explanations WHERE id=?", (exp["explanation_id"],)).fetchone()
    assert secret_in_exp not in exp_db["learner_text"]
    assert "[REDACTED]" in exp_db["learner_text"]

    # At this point, no newer commits exist, so list_stale_items must be empty
    stale = knowledge_service.list_stale_items(conn, "p1")
    assert stale["count"] == 0

    # 3. Add commit c3 touching src/core.py to queue (un-ingested)
    q_entry_3 = {
        "sha": "c3",
        "message": "commit 3: update core again",
        "files": ["src/core.py"],
        "committed_at": "2026-01-01T12:00:00Z",
        "origin": "hook",
    }
    (q_dir / "c3.json").write_text(json.dumps(q_entry_3), encoding="utf-8")

    # Call list_stale_items: it must auto-ingest c3 and detect that core.sys is now stale!
    stale_after = knowledge_service.list_stale_items(conn, "p1")
    assert stale_after["count"] == 1
    assert stale_after["stale_items"][0]["key"] == "core.sys"
    assert stale_after["stale_items"][0]["baseline_commit"] == "c2"
    assert len(stale_after["stale_items"][0]["changing_commits"]) == 1
    assert stale_after["stale_items"][0]["changing_commits"][0]["sha"] == "c3"

    conn.close()


def test_list_items_filtering_and_pagination(tmp_path: Path):
    db_path = tmp_path / "test.db"
    conn = connect(db_path)

    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()

    conn.execute(
        "INSERT INTO projects (id, name, repo_path, created_at) VALUES ('p1', 'Repo', ?, '2026-01-01T00:00:00Z')",
        (str(repo_dir.resolve()),),
    )
    conn.execute(
        "INSERT INTO commits (sha, project_id, message, files, committed_at, status, origin)"
        " VALUES ('c1', 'p1', 'init', '[\"a.py\", \"b.py\", \"c.py\"]', '2026-01-01T00:00:00Z', 'verified', 'hook')"
    )
    conn.commit()

    # Register 3 items across different bands
    for key, band, f in [("item1", "basic", "a.py"), ("item2", "intermediate", "b.py"), ("item3", "basic", "c.py")]:
        knowledge_service.register_knowledge_item(
            conn=conn,
            project_id="p1",
            key=key,
            title=f"Title {key}",
            kind="concept",
            band=band,
            files=[f],
            summary="A" * 200,  # long summary to check 160-char truncation
        )

    # 1. Filter by band
    basic_items = knowledge_service.list_items(conn, "p1", band="basic")
    assert basic_items["count"] == 2
    for it in basic_items["items"]:
        assert it["band"] == "basic"
        assert len(it["summary"]) <= 160

    # 2. Pagination with limit and cursor
    page1 = knowledge_service.list_items(conn, "p1", limit=2)
    assert page1["count"] == 2
    assert page1["next_cursor"] == "item2"

    page2 = knowledge_service.list_items(conn, "p1", limit=2, cursor=page1["next_cursor"])
    assert page2["count"] == 1
    assert page2["items"][0]["key"] == "item3"
    assert page2["next_cursor"] is None

    conn.close()
