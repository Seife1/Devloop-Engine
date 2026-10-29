"""Safe filesystem and dashboard utilities for LearnLoop.

This module provides verified, secure helper utilities for inspecting repository
artifacts (.learn/ queue commits, markdown documents, project descriptions)
and running the unified LearnLoop dashboard.
"""

from __future__ import annotations

import importlib.resources
import json
import os
import stat
import sys
from pathlib import Path

MAX_DOC_SIZE_BYTES = 500 * 1024


def get_required_migration_version() -> int:
    """Return the highest numbered migration file available in the package."""
    files = sorted(
        (
            p
            for p in importlib.resources.files("learnloop.persistence.migrations").iterdir()
            if p.name.endswith(".sql")
        ),
        key=lambda p: p.name,
    )
    if not files:
        return 0
    return max(int(f.name.split("_", 1)[0]) for f in files)


def is_reparse_point_or_link(path: Path | str) -> bool:
    """Return True if path is a symlink, Windows junction, or reparse point."""
    try:
        p = Path(path)
        if p.is_symlink() or os.path.islink(p):
            return True
        st = p.lstat()
        reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        attrs = getattr(st, "st_file_attributes", 0)
        if bool(attrs & reparse_flag):
            return True
        return False
    except (OSError, ValueError):
        return True


def _resolve_safe_learn_path(repo_path: Path | str) -> Path | None:
    """Resolve storage path: either <repo>/.learn if it exists, or isolated user storage."""
    try:
        from learnloop.config import get_workspace_storage_dir

        repo = Path(repo_path).resolve()
        legacy_path = repo / ".learn"
        if legacy_path.is_dir() and not is_reparse_point_or_link(legacy_path):
            if legacy_path.resolve() == repo / ".learn":
                return legacy_path

        user_storage = get_workspace_storage_dir(repo).resolve()
        if user_storage.is_dir() and not is_reparse_point_or_link(user_storage):
            return user_storage
        return None
    except Exception:
        return None


def count_queue_commits(repo_path: Path | str) -> int:
    """Safely count waiting commit entries in workspace queue (directory listing only)."""
    try:
        learn_path = _resolve_safe_learn_path(repo_path)
        if not learn_path:
            return 0
        q_path = learn_path / "queue"
        if not q_path.is_dir() or is_reparse_point_or_link(q_path):
            return 0
        if q_path.resolve() != learn_path.resolve() / "queue":
            return 0
        return sum(
            1 for p in q_path.iterdir() if p.is_file() and not is_reparse_point_or_link(p)
        )
    except Exception:
        return 0


def list_safe_learn_docs(repo_path: Path | str) -> list[str]:
    """Safely list .md documentation files in workspace learning directory."""
    try:
        learn_path = _resolve_safe_learn_path(repo_path)
        if not learn_path:
            return []
        docs = []
        for p in learn_path.iterdir():
            if p.is_file() and not is_reparse_point_or_link(p) and p.name.endswith(".md"):
                if p.resolve().parent != learn_path.resolve():
                    continue
                if p.stat().st_size <= MAX_DOC_SIZE_BYTES:
                    docs.append(p.name)
        return sorted(docs)
    except Exception:
        return []


def extract_project_description(repo_path: Path | str | None) -> str:
    """Extract a one-line project description from pyproject.toml or package.json."""
    if not repo_path:
        return ""
    try:
        repo = Path(repo_path).resolve()
        pyproj = repo / "pyproject.toml"
        if pyproj.is_file() and not is_reparse_point_or_link(pyproj):
            try:
                import tomllib

                data = tomllib.loads(pyproj.read_text(encoding="utf-8"))
                desc = data.get("project", {}).get("description")
                if not desc:
                    desc = data.get("tool", {}).get("poetry", {}).get("description")
                if desc and isinstance(desc, str):
                    return desc.strip()
            except Exception:
                pass

        pkg_json = repo / "package.json"
        if pkg_json.is_file() and not is_reparse_point_or_link(pkg_json):
            try:
                data = json.loads(pkg_json.read_text(encoding="utf-8"))
                desc = data.get("description")
                if desc and isinstance(desc, str):
                    return desc.strip()
            except Exception:
                pass
    except Exception:
        pass
    return ""


def read_safe_learn_doc(repo_path: Path | str, doc_name: str) -> str | None:
    """Safely read a markdown doc directly within workspace learning directory."""
    try:
        learn_path = _resolve_safe_learn_path(repo_path)
        if not learn_path:
            return None

        clean_name = doc_name if doc_name.endswith(".md") else f"{doc_name}.md"
        target = learn_path / clean_name
        if is_reparse_point_or_link(target):
            return None
        resolved = target.resolve()
        learn_resolved = learn_path.resolve()
        if resolved.parent != learn_resolved:
            return None
        if not resolved.is_file() or is_reparse_point_or_link(resolved):
            return None
        if resolved.stat().st_size > MAX_DOC_SIZE_BYTES:
            return None
        return resolved.read_text("utf-8")
    except Exception:
        return None


def run_dashboard_server(port: int = 8765, db_path: Path | None = None) -> int:
    """Run the modern unified LearnLoop dashboard via FastAPI and Uvicorn."""
    try:
        import uvicorn
        from learnloop.http_server import app

        sys.stdout.write(f"LearnLoop dashboard running at http://127.0.0.1:{port}/\n")
        sys.stdout.flush()
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
        return 0
    except Exception as exc:
        sys.stderr.write(f"Failed to start dashboard server: {exc}\n")
        return 1
