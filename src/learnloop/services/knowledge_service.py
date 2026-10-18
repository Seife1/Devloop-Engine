"""Knowledge items and explanation tracking service."""

from __future__ import annotations

import difflib
import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from learnloop.capture.redaction import redact
from learnloop.domain import clock
from learnloop.domain.depth import start_depth
from learnloop.domain.errors import NotFoundError, ValidationError
from learnloop.domain.path_utils import normalise_path
from learnloop.domain.staleness import compute_item_staleness
from learnloop.journal.concept_log import regenerate_concept_log
from learnloop.services.capture_service import require_project
from learnloop.services.profile_service import get_effective_profile
from learnloop.services.explanation_service import (
    calculate_explanation_depth,
    generate_quality_feedback,
)

VALID_KINDS = {"component", "decision", "concept", "bug-fix"}
VALID_BANDS = {"basic", "intermediate", "advanced"}
VALID_STATUSES = {"unexplained", "shaky", "explained"}


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


def _auto_ingest(conn: sqlite3.Connection, project_id: str) -> None:
    """Ingest queued commits before reading or updating baseline/staleness."""
    row = conn.execute("SELECT repo_path FROM projects WHERE id=?", (project_id,)).fetchone()
    if row:
        from learnloop.capture import queue
        from learnloop.config import Settings

        settings = Settings.load()
        queue.ingest(conn, settings, project_id, Path(row["repo_path"]))


def get_all_known_paths(conn: sqlite3.Connection, project_id: str) -> set[str]:
    """Retrieve union of all paths appearing in commits for this project (any origin)."""
    rows = conn.execute("SELECT files FROM commits WHERE project_id=?", (project_id,)).fetchall()
    known: set[str] = set()
    for r in rows:
        try:
            paths = json.loads(r["files"])
            if isinstance(paths, list):
                for p in paths:
                    if isinstance(p, str):
                        known.add(p)
        except Exception:  # noqa: BLE001
            continue
    return known


def register_knowledge_item(
    conn: sqlite3.Connection,
    project_id: str,
    key: str,
    title: str,
    kind: str,
    band: str,
    files: list[str],
    summary: str,
    tags: list[str] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Register or update a knowledge item for the project.

    Idempotent on (project_id, key). Redacts free text, validates files against known project paths.
    """
    project = require_project(conn, project_id)

    key_clean = key.strip()
    if not key_clean:
        raise ValidationError("Key cannot be empty.")

    kind_clean = kind.strip().lower()
    if kind_clean not in VALID_KINDS:
        raise ValidationError(f"Invalid kind {kind!r}. Expected one of: {sorted(VALID_KINDS)}")

    band_clean = band.strip().lower()
    if band_clean not in VALID_BANDS:
        raise ValidationError(f"Invalid band {band!r}. Expected one of: {sorted(VALID_BANDS)}")

    if not files or not (1 <= len(files) <= 12):
        raise ValidationError(f"Files list must contain between 1 and 12 paths, got {len(files)}.")

    cleaned_tags = [redact(t.strip()) for t in (tags or []) if t.strip()]
    if len(cleaned_tags) > 5:
        raise ValidationError("At most 5 tags allowed per item.")

    if len(summary.strip()) > 600:
        raise ValidationError(f"Summary exceeds 600 characters ({len(summary.strip())} chars).")

    # Normalise paths
    norm_files: list[str] = list(dict.fromkeys(normalise_path(f) for f in files))

    # Verify paths exist in project's known commits
    known_paths = get_all_known_paths(conn, project_id)
    missing = [p for p in norm_files if p not in known_paths]
    if missing:
        candidates: dict[str, list[str]] = {
            m: difflib.get_close_matches(m, sorted(known_paths), n=8) for m in missing
        }
        raise ValidationError(
            f"File(s) {missing} not found in project commits. Closest known paths: {candidates}"
        )

    # Redact free text
    title_redacted = redact(title.strip())
    summary_redacted = redact(summary.strip())

    now_s = clock.iso(now or clock.utcnow())

    existing = conn.execute(
        "SELECT * FROM knowledge_items WHERE project_id=? AND key=?", (project_id, key_clean)
    ).fetchone()

    if existing:
        item_id = existing["id"]
        conn.execute(
            "UPDATE knowledge_items SET title=?, kind=?, band=?, summary=?, updated_at=?"
            " WHERE id=?",
            (title_redacted, kind_clean, band_clean, summary_redacted, now_s, item_id),
        )
        conn.execute("DELETE FROM item_files WHERE item_id=?", (item_id,))
        conn.execute("DELETE FROM item_tags WHERE item_id=?", (item_id,))
        status = existing["status"]
        depth = existing["depth"]
        created = False
    else:
        profile = get_effective_profile(conn, project_id)
        item_id = _new_id()
        depth = start_depth(profile["level"])
        status = "unexplained"
        conn.execute(
            "INSERT INTO knowledge_items (id, project_id, key, title, kind, band, summary, status,"
            " depth, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                item_id,
                project_id,
                key_clean,
                title_redacted,
                kind_clean,
                band_clean,
                summary_redacted,
                status,
                depth,
                now_s,
                now_s,
            ),
        )
        created = True

    conn.executemany(
        "INSERT INTO item_files (item_id, path) VALUES (?,?)",
        [(item_id, p) for p in norm_files],
    )
    if cleaned_tags:
        conn.executemany(
            "INSERT INTO item_tags (item_id, tag) VALUES (?,?)",
            [(item_id, t) for t in dict.fromkeys(cleaned_tags)],
        )

    conn.commit()

    written = regenerate_concept_log(conn, project_id, project["repo_path"])

    return {
        "id": item_id,
        "project_id": project_id,
        "key": key_clean,
        "title": title_redacted,
        "kind": kind_clean,
        "band": band_clean,
        "status": status,
        "depth": depth,
        "files": norm_files,
        "tags": cleaned_tags,
        "summary": summary_redacted,
        "created": created,
        "concept_log_written": written,
    }


def record_explanation(
    conn: sqlite3.Connection,
    project_id: str,
    key: str,
    learner_text: str,
    score: float,
    audience: str | None = None,
    depth: int | None = None,
    explanation_id: int | None = None,
    self_rating: int | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Grade and record learner explain-back.

    Auto-ingests queue first so baseline commit matches reality.
    Redacts text, validates non-empty learner_text, updates status & depth, and updates baseline commit.
    """
    _auto_ingest(conn, project_id)
    project = require_project(conn, project_id)

    cleaned_text = learner_text.strip()
    if not cleaned_text:
        raise ValidationError("learner_text cannot be empty.")

    if not (0.0 <= score <= 1.0):
        raise ValidationError(f"Score must be between 0.0 and 1.0, got {score}")

    if self_rating is not None and not (1 <= self_rating <= 5):
        raise ValidationError(f"self_rating must be between 1 and 5, got {self_rating}")

    item = conn.execute(
        "SELECT * FROM knowledge_items WHERE project_id=? AND key=?", (project_id, key.strip())
    ).fetchone()
    if not item:
        raise NotFoundError(f"Knowledge item with key {key!r} not found in project {project_id!r}.")

    item_id = item["id"]

    # Check idempotency if explanation_id passed
    if explanation_id is not None:
        existing_exp = conn.execute(
            "SELECT * FROM explanations WHERE id=?", (explanation_id,)
        ).fetchone()
        if existing_exp:
            exp_rating = (
                existing_exp["self_rating"]
                if "self_rating" in existing_exp.keys()
                else None
            )
            return {
                "explanation_id": existing_exp["id"],
                "item_id": item_id,
                "key": item["key"],
                "score": existing_exp["score"],
                "self_rating": exp_rating,
                "status": item["status"],
                "depth": item["depth"],
                "created": False,
                "concept_log_written": True,
            }

    profile = get_effective_profile(conn, project_id)
    now_s = clock.iso(now or clock.utcnow())
    redacted_text = redact(cleaned_text)
    
    # Calculate explanation depth score (0.0-1.0) based on text analysis
    # Requirements: 10.3, 10.4
    explanation_depth_score = calculate_explanation_depth(cleaned_text)
    
    # Generate quality feedback if depth is low
    # Requirement: 10.7
    quality_feedback = generate_quality_feedback(explanation_depth_score, self_rating)

    # Determine status & depth transitions
    new_status = "explained" if score >= 0.8 else "shaky"
    curr_depth = int(item["depth"])
    target_depth = depth if depth is not None else curr_depth
    if target_depth < 1 or target_depth > 5:
        raise ValidationError(f"Depth {target_depth} out of range (1..5).")
    new_depth = max(curr_depth, target_depth)

    # Find newest ingested git commit for project (exclude synthetic snapshot)
    newest_commit = conn.execute(
        "SELECT sha, committed_at FROM commits WHERE project_id=?"
        " AND kind = 'commit'"
        " ORDER BY committed_at DESC, sha DESC LIMIT 1",
        (project_id,),
    ).fetchone()

    baseline_commit = newest_commit["sha"] if newest_commit else None
    baseline_committed_at = newest_commit["committed_at"] if newest_commit else None

    # Insert explanation
    chosen_audience = audience.strip().lower() if audience else profile["audience"]
    if explanation_id is not None:
        conn.execute(
            "INSERT INTO explanations "
            "(id, item_id, audience, depth, learner_text, score, self_rating, created_at)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (
                explanation_id,
                item_id,
                chosen_audience,
                new_depth,
                redacted_text,
                score,
                self_rating,
                now_s,
            ),
        )
        rec_exp_id = explanation_id
    else:
        cur = conn.execute(
            "INSERT INTO explanations "
            "(item_id, audience, depth, learner_text, score, self_rating, created_at)"
            " VALUES (?,?,?,?,?,?,?)",
            (
                item_id,
                chosen_audience,
                new_depth,
                redacted_text,
                score,
                self_rating,
                now_s,
            ),
        )
        rec_exp_id = int(cur.lastrowid or 0)

    # Update knowledge item
    conn.execute(
        "UPDATE knowledge_items SET status=?, depth=?, baseline_commit=?, baseline_committed_at=?,"
        " updated_at=? WHERE id=?",
        (new_status, new_depth, baseline_commit, baseline_committed_at, now_s, item_id),
    )

    # Initialize review schedule if item_reviews table exists
    try:
        from learnloop.domain.scheduling import initial_schedule

        rev_exists = conn.execute("SELECT 1 FROM item_reviews WHERE item_id=?", (item_id,)).fetchone()
        if not rev_exists:
            init_st = initial_schedule(now=now, is_stale=False)
            conn.execute(
                "INSERT INTO item_reviews (item_id, interval_days, ease, reps, due_at, last_reviewed_at)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (
                    item_id,
                    init_st.interval_days,
                    init_st.ease,
                    init_st.reps,
                    init_st.due_at,
                    init_st.last_reviewed_at,
                ),
            )
    except sqlite3.OperationalError:
        pass

    conn.commit()

    written = regenerate_concept_log(conn, project_id, project["repo_path"])

    result = {
        "explanation_id": rec_exp_id,
        "item_id": item_id,
        "key": item["key"],
        "status": new_status,
        "depth": new_depth,
        "score": score,
        "self_rating": self_rating,
        "baseline_commit": baseline_commit,
        "baseline_committed_at": baseline_committed_at,
        "created": True,
        "concept_log_written": written,
        "explanation_depth_score": explanation_depth_score,  # Requirement: 10.4
    }
    
    # Add quality feedback if needed (Requirement: 10.7)
    if quality_feedback["needs_improvement"]:
        result["quality_feedback"] = quality_feedback
    
    return result


def list_items(
    conn: sqlite3.Connection,
    project_id: str,
    band: str | None = None,
    status: str | None = None,
    limit: int = 30,
    cursor: str | None = None,
) -> dict[str, Any]:
    """List knowledge items for a project, bounded summary <= 160 chars."""
    require_project(conn, project_id)
    clamped_limit = min(max(1, limit), 30)

    query = "SELECT * FROM knowledge_items WHERE project_id=?"
    params: list[Any] = [project_id]

    if band:
        query += " AND band=?"
        params.append(band.strip().lower())
    if status:
        query += " AND status=?"
        params.append(status.strip().lower())
    if cursor:
        query += " AND key > ?"
        params.append(cursor.strip())

    query += " ORDER BY key ASC LIMIT ?"
    params.append(clamped_limit + 1)

    rows = conn.execute(query, params).fetchall()
    has_more = len(rows) > clamped_limit
    selected_rows = rows[:clamped_limit]

    items: list[dict[str, Any]] = []
    for r in selected_rows:
        item_id = r["id"]
        files = [
            f["path"]
            for f in conn.execute(
                "SELECT path FROM item_files WHERE item_id=? ORDER BY path ASC", (item_id,)
            ).fetchall()
        ]
        tags = [
            t["tag"]
            for t in conn.execute(
                "SELECT tag FROM item_tags WHERE item_id=? ORDER BY tag ASC", (item_id,)
            ).fetchall()
        ]
        summary_short = r["summary"][:160]
        latest_exp = conn.execute(
            "SELECT self_rating FROM explanations WHERE item_id=? ORDER BY created_at DESC, id DESC LIMIT 1",
            (item_id,),
        ).fetchone()
        self_rating = (
            latest_exp["self_rating"]
            if latest_exp and "self_rating" in latest_exp.keys()
            else None
        )
        items.append(
            {
                "id": item_id,
                "key": r["key"],
                "title": r["title"],
                "kind": r["kind"],
                "band": r["band"],
                "status": r["status"],
                "depth": r["depth"],
                "summary": summary_short,
                "files": files,
                "tags": tags,
                "self_rating": self_rating,
                "baseline_commit": r["baseline_commit"],
                "baseline_committed_at": r["baseline_committed_at"],
            }
        )

    next_cursor = selected_rows[-1]["key"] if has_more and selected_rows else None

    return {
        "items": items,
        "next_cursor": next_cursor,
        "count": len(items),
    }


def list_stale_items(
    conn: sqlite3.Connection,
    project_id: str,
    ingest: bool = True,
) -> dict[str, Any]:
    """Find and return all stale knowledge items for the project.

    Auto-ingests queue first if ingest=True so findings reflect current git state.
    """
    if ingest:
        _auto_ingest(conn, project_id)
    require_project(conn, project_id)

    items = conn.execute(
        "SELECT * FROM knowledge_items WHERE project_id=? AND status IN ('explained', 'shaky')",
        (project_id,),
    ).fetchall()

    commit_rows = conn.execute(
        "SELECT sha, message, committed_at, files FROM commits WHERE project_id=?"
        " AND kind = 'commit' ORDER BY committed_at DESC",
        (project_id,),
    ).fetchall()

    commits: list[dict[str, Any]] = []
    for c in commit_rows:
        try:
            flist = json.loads(c["files"])
        except Exception:  # noqa: BLE001
            flist = []
        commits.append(
            {
                "sha": c["sha"],
                "message": c["message"],
                "committed_at": c["committed_at"],
                "files": flist,
            }
        )

    stale_items: list[dict[str, Any]] = []
    for item in items:
        item_files = [
            f["path"]
            for f in conn.execute(
                "SELECT path FROM item_files WHERE item_id=? ORDER BY path ASC", (item["id"],)
            ).fetchall()
        ]
        staleness_info = compute_item_staleness(
            status=item["status"],
            item_files=item_files,
            baseline_commit=item["baseline_commit"],
            baseline_committed_at=item["baseline_committed_at"],
            commits=commits,
        )
        if staleness_info:
            stale_items.append(
                {
                    "key": item["key"],
                    "title": item["title"],
                    "files": item_files,
                    "baseline_commit": staleness_info["baseline_commit"],
                    "baseline_committed_at": staleness_info["baseline_committed_at"],
                    "changing_commits": staleness_info["changing_commits"],
                }
            )

    return {
        "stale_items": stale_items,
        "count": len(stale_items),
    }


def generate_item_explanation_prompt(
    conn: sqlite3.Connection,
    project_id: str,
    key: str,
    max_context_lines: int = 50,
) -> dict[str, Any]:
    """Generate explanation prompt for a knowledge item.
    
    Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8
    
    Args:
        conn: Database connection
        project_id: Project ID
        key: Knowledge item key
        max_context_lines: Maximum lines of code context to include (default 50)
        
    Returns:
        dict with prompt text, questions, and metadata
        
    Raises:
        NotFoundError: If knowledge item not found
    """
    from learnloop.services.explanation_service import generate_explanation_prompt
    
    require_project(conn, project_id)
    
    # Fetch the knowledge item
    item = conn.execute(
        "SELECT * FROM knowledge_items WHERE project_id=? AND key=?",
        (project_id, key.strip()),
    ).fetchone()
    
    if not item:
        raise NotFoundError(f"Knowledge item with key {key!r} not found in project {project_id!r}.")
    
    # Fetch tracked files from item_files table
    files_rows = conn.execute(
        "SELECT path FROM item_files WHERE item_id=? ORDER BY path",
        (item["id"],)
    ).fetchall()
    files = [row["path"] for row in files_rows]
    
    # Try to extract code context from tracked files
    # Requirement: 8.2 - Extract code snippets from exposure files (max 50 lines)
    code_context = None
    if files:
        try:
            # Get the first file's content as context
            first_file = Path(files[0])
            if first_file.exists() and first_file.is_file():
                with open(first_file, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    # Limit to max_context_lines
                    if len(lines) > max_context_lines:
                        code_context = ''.join(lines[:max_context_lines])
                    else:
                        code_context = ''.join(lines)
        except (OSError, IOError):
            # If file read fails, continue without context
            pass
    
    # Generate the prompt
    # Requirements: 8.3, 8.4, 8.5, 8.6, 8.7, 8.8
    prompt_data = generate_explanation_prompt(
        item_key=item["key"],
        item_title=item["title"],
        item_kind=item["kind"],
        item_band=item["band"],
        tracked_files=files,
        code_context=code_context,
        max_context_lines=max_context_lines,
    )
    
    return prompt_data
