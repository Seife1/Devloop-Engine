from __future__ import annotations

import json
from pathlib import Path

import pytest

from learnloop.dashboard.server import (
    count_queue_commits,
    extract_project_description,
    get_required_migration_version,
    is_reparse_point_or_link,
    list_safe_learn_docs,
    read_safe_learn_doc,
)


def test_get_required_migration_version():
    ver = get_required_migration_version()
    assert isinstance(ver, int)
    assert ver >= 14


def test_is_reparse_point_or_link(tmp_path: Path):
    regular_file = tmp_path / "regular.txt"
    regular_file.write_text("hello", encoding="utf-8")
    assert not is_reparse_point_or_link(regular_file)


def test_count_queue_commits(tmp_path: Path):
    repo = tmp_path / "test_repo"
    repo.mkdir()
    assert count_queue_commits(repo) == 0

    learn = repo / ".learn"
    learn.mkdir()
    q = learn / "queue"
    q.mkdir()

    (q / "c1.json").write_text("{}", encoding="utf-8")
    (q / "c2.json").write_text("{}", encoding="utf-8")
    assert count_queue_commits(repo) == 2


def test_list_and_read_safe_learn_docs(tmp_path: Path):
    repo = tmp_path / "test_repo"
    repo.mkdir()
    learn = repo / ".learn"
    learn.mkdir()

    (learn / "guide.md").write_text("# My Guide\nContent here", encoding="utf-8")
    (learn / "notes.md").write_text("# Notes", encoding="utf-8")
    (learn / "secret.txt").write_text("not markdown", encoding="utf-8")

    docs = list_safe_learn_docs(repo)
    assert docs == ["guide.md", "notes.md"]

    content = read_safe_learn_doc(repo, "guide.md")
    assert content is not None
    assert "# My Guide" in content

    # Non-existent doc
    assert read_safe_learn_doc(repo, "nonexistent.md") is None


def test_extract_project_description_pyproject(tmp_path: Path):
    repo = tmp_path / "py_repo"
    repo.mkdir()
    pyproj = repo / "pyproject.toml"
    pyproj.write_text('[project]\nname = "demo"\ndescription = "A demo project"\n', encoding="utf-8")

    desc = extract_project_description(repo)
    assert desc == "A demo project"


def test_extract_project_description_package_json(tmp_path: Path):
    repo = tmp_path / "node_repo"
    repo.mkdir()
    pkg = repo / "package.json"
    pkg.write_text(json.dumps({"name": "demo-node", "description": "Node test pkg"}), encoding="utf-8")

    desc = extract_project_description(repo)
    assert desc == "Node test pkg"


def test_extract_project_description_empty():
    assert extract_project_description(None) == ""
