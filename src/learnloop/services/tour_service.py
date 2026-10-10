"""Project tour service. Generates bounded evidence bundle for guiding tour sessions."""

from __future__ import annotations

import fnmatch
import re
import sqlite3
from typing import Any

from learnloop.services.capture_service import require_project
from learnloop.services.knowledge_service import get_all_known_paths
from learnloop.services.profile_service import get_learner_profile

TOUR_PROTOCOL = """\
Project Tour Protocol:
1. Read real project files in your IDE to ground your explanations.
2. Walk bands in strict order: Basic first (what the project does, entry point, folder purposes, \
request/data flow in plain words), then Intermediate, then Advanced.
3. Teach at most 5 items per turn/call.
4. Call register_knowledge_item for each concept you teach, citing real project files.
5. Adapt language: use simple analogies and short sentences for school/beginner levels.
6. Never skip the learner's questions; answer thoroughly before moving on.
7. Offer a 2-minute pause between bands.
8. Park off-topic questions for later without needing any special tool.\
"""

ENTRY_POINT_PATTERNS = [
    "main.*",
    "app.*",
    "index.*",
    "server.*",
    "manage.py",
    "cmd/*/main.go",
    "cmd/**/main.go",
    "package.json",
    "pyproject.toml",
    "go.mod",
    "Cargo.toml",
    "Dockerfile",
    "docker-compose*",
]

MANIFEST_PATTERNS = [
    "package.json",
    "pyproject.toml",
    "go.mod",
    "Cargo.toml",
    "requirements*.txt",
    "Gemfile",
    "pom.xml",
    "build.gradle*",
    "composer.json",
    "Dockerfile",
    "docker-compose*",
]


def _matches_any(path: str, patterns: list[str]) -> bool:
    basename = path.rsplit("/", 1)[-1]
    for pat in patterns:
        if fnmatch.fnmatch(path, pat) or fnmatch.fnmatch(basename, pat):
            return True
        if "/" in pat and re.match(fnmatch.translate(pat), path):
            return True
    return False


def get_project_tour(conn: sqlite3.Connection, project_id: str) -> dict[str, Any]:
    """Generate bounded project tour bundle (<8 KB)."""
    require_project(conn, project_id)
    profile = get_learner_profile(conn)

    known_paths = sorted(get_all_known_paths(conn, project_id))

    # Top-level directories with file counts
    top_dirs: dict[str, int] = {}
    for p in known_paths:
        parts = p.split("/")
        top = parts[0] if len(parts) > 1 else "."
        top_dirs[top] = top_dirs.get(top, 0) + 1

    # Candidates and manifests
    entry_candidates: list[str] = [p for p in known_paths if _matches_any(p, ENTRY_POINT_PATTERNS)][:20]
    manifests: list[str] = [p for p in known_paths if _matches_any(p, MANIFEST_PATTERNS)][:20]

    # Existing items by band
    items_rows = conn.execute(
        "SELECT id, key, title, band, status FROM knowledge_items WHERE project_id=?", (project_id,)
    ).fetchall()

    items_by_band: dict[str, list[dict[str, str]]] = {
        "basic": [],
        "intermediate": [],
        "advanced": [],
    }
    covered_paths: set[str] = set()

    for r in items_rows:
        band = r["band"]
        if band in items_by_band:
            items_by_band[band].append({"key": r["key"], "title": r["title"], "status": r["status"]})

    file_rows = conn.execute(
        "SELECT f.path FROM item_files f JOIN knowledge_items k ON k.id=f.item_id WHERE k.project_id=?",
        (project_id,),
    ).fetchall()
    for f in file_rows:
        covered_paths.add(f["path"])

    # Uncovered files (capped at 40)
    uncovered = [p for p in known_paths if p not in covered_paths]
    uncovered_sample = uncovered[:40]
    uncovered_truncated = len(uncovered) > 40

    return {
        "project_id": project_id,
        "learner_profile": profile,
        "top_level_dirs": top_dirs,
        "entry_point_candidates": entry_candidates,
        "manifest_files": manifests,
        "items_by_band": items_by_band,
        "uncovered_files": uncovered_sample,
        "uncovered_truncated": uncovered_truncated,
        "uncovered_total": len(uncovered),
        "protocol": TOUR_PROTOCOL,
    }
