from __future__ import annotations

import os
from pathlib import Path

from learnloop.journal.concept_log import (
    generate_concept_markdown,
    is_safe_to_write_concepts,
    regenerate_concept_log,
)
from learnloop.persistence.db import connect


def test_concept_log_idempotent_and_redacted(tmp_path: Path):
    db_path = tmp_path / "test.db"
    conn = connect(db_path)

    conn.execute(
        "INSERT INTO projects (id, name, repo_path, created_at) VALUES ('p1', 'Test', '/repo', '2026-01-01T00:00:00Z')"
    )
    # Fake secrets in summary and learner text
    fake_key = "sk-live-123456789012345678901234567890"
    conn.execute(
        "INSERT INTO knowledge_items (id, project_id, key, title, kind, band, summary, status, depth, created_at, updated_at)"
        " VALUES ('k1', 'p1', 'auth.service', 'Auth Service', 'component', 'basic', ?, 'explained', 2, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')",
        (f"Handles credentials with secret {fake_key}",),
    )
    conn.execute("INSERT INTO item_files (item_id, path) VALUES ('k1', 'src/auth.py')")
    conn.execute(
        "INSERT INTO explanations (id, item_id, audience, depth, learner_text, score, created_at)"
        " VALUES (1, 'k1', 'self', 2, ?, 0.9, '2026-01-01T00:00:00Z')",
        (f"I used token {fake_key} to verify",),
    )
    conn.commit()

    md1 = generate_concept_markdown(conn, "p1")
    md2 = generate_concept_markdown(conn, "p1")

    # Byte-identical output
    assert md1 == md2

    # Fake secret is redacted
    assert fake_key not in md1
    assert "[REDACTED]" in md1

    # Check structural elements
    assert "# Project Concepts" in md1
    assert "## Basic" in md1
    assert "## Intermediate" in md1
    assert "## Advanced" in md1
    assert "### Auth Service (`auth.service`)" in md1
    assert "- **Files**: `src/auth.py`" in md1
    conn.close()


def test_safe_writes_validations(tmp_path: Path):
    # 1. Nonexistent path
    nonexistent = tmp_path / "no_such_dir"
    safe, target, _ = is_safe_to_write_concepts(nonexistent)
    assert not safe
    assert target is None

    # 2. Non-repo directory (neither .git nor .learn)
    plain_dir = tmp_path / "plain_dir"
    plain_dir.mkdir()
    safe, target, _ = is_safe_to_write_concepts(plain_dir)
    assert not safe

    # 3. Valid git repo
    git_repo = tmp_path / "git_repo"
    git_repo.mkdir()
    (git_repo / ".git").mkdir()
    safe, target, _ = is_safe_to_write_concepts(git_repo)
    assert safe
    assert target == (git_repo / ".learn" / "concepts.md").resolve()

    # 4. Symlinked .learn directory
    symlink_repo = tmp_path / "symlink_repo"
    symlink_repo.mkdir()
    (symlink_repo / ".git").mkdir()
    real_target = tmp_path / "somewhere_else"
    real_target.mkdir()
    learn_link = symlink_repo / ".learn"
    try:
        os.symlink(real_target, learn_link)
        safe, target, _ = is_safe_to_write_concepts(symlink_repo)
        assert not safe
    except (OSError, NotImplementedError):
        # On Windows without developer mode symlink creation might raise OSError
        pass


def test_regenerate_concept_log_writes_atomic(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").mkdir()

    db_path = tmp_path / "test.db"
    conn = connect(db_path)
    conn.execute(
        "INSERT INTO projects (id, name, repo_path, created_at) VALUES ('p1', 'Test', ?, '2026-01-01T00:00:00Z')",
        (str(repo.resolve()),),
    )
    conn.execute(
        "INSERT INTO knowledge_items (id, project_id, key, title, kind, band, summary, status, depth, created_at, updated_at)"
        " VALUES ('k1', 'p1', 'core', 'Core Title', 'component', 'basic', 'Summary', 'unexplained', 1, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')"
    )
    conn.commit()

    written = regenerate_concept_log(conn, "p1", repo)
    assert written is True
    concepts_file = repo / ".learn" / "concepts.md"
    assert concepts_file.is_file()
    content = concepts_file.read_text("utf-8")
    assert "### Core Title (`core`)" in content
    assert "AI Illusion of Competence" in content
    conn.close()


def test_init_concept_log_day_one(tmp_path: Path):
    from learnloop.journal.concept_log import init_concept_log

    repo = tmp_path / "new_repo"
    repo.mkdir()
    (repo / ".git").mkdir()

    # First call: writes starter guide
    assert init_concept_log(repo) is True
    guide_path = repo / ".learn" / "concepts.md"
    assert guide_path.is_file()
    text = guide_path.read_text("utf-8")
    assert "AI Illusion of Competence" in text
    assert "Commit early & often" in text

    # Second call: idempotent, does not overwrite
    assert init_concept_log(repo) is True
