"""Project readiness service: count-based confidence metrics without scores or percentages."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any

from learnloop.domain import clock
from learnloop.domain.errors import NotFoundError
from learnloop.domain.staleness import compute_item_staleness
from learnloop.services.capture_service import require_project
from learnloop.services.knowledge_service import _auto_ingest


def get_project_readiness(
    conn: sqlite3.Connection,
    project_id: str | None = None,
    now: datetime | None = None,
    ingest: bool = True,
) -> dict[str, Any]:
    """Calculate count-based project readiness metrics without scores or percentages.

    Resolves newest project if project_id is omitted.
    """
    if not project_id:
        row = conn.execute("SELECT id FROM projects ORDER BY created_at DESC LIMIT 1").fetchone()
        if not row:
            raise NotFoundError("No projects registered. Call start_project first.")
        project_id = str(row["id"])

    require_project(conn, project_id)
    if ingest:
        _auto_ingest(conn, project_id)

    now_dt = now or clock.utcnow()
    now_s = clock.iso(now_dt)

    items = conn.execute(
        "SELECT id, key, title, band, status, baseline_commit, baseline_committed_at "
        "FROM knowledge_items WHERE project_id=?",
        (project_id,),
    ).fetchall()

    total_items = len(items)

    by_band: dict[str, dict[str, int]] = {
        "basic": {"explained": 0, "shaky": 0, "unexplained": 0},
        "intermediate": {"explained": 0, "shaky": 0, "unexplained": 0},
        "advanced": {"explained": 0, "shaky": 0, "unexplained": 0},
    }

    for it in items:
        band = str(it["band"]).lower()
        status = str(it["status"]).lower()
        if band in by_band and status in by_band[band]:
            by_band[band][status] += 1

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

    stale_count = 0
    due_count = 0

    for it in items:
        status = str(it["status"]).lower()
        item_id = it["id"]

        if status == "explained":
            item_files = [
                f["path"]
                for f in conn.execute(
                    "SELECT path FROM item_files WHERE item_id=? ORDER BY path ASC", (item_id,)
                ).fetchall()
            ]
            staleness = compute_item_staleness(
                status=it["status"],
                item_files=item_files,
                baseline_commit=it["baseline_commit"],
                baseline_committed_at=it["baseline_committed_at"],
                commits=commits,
            )
            if staleness is not None:
                stale_count += 1

            rev_row = conn.execute(
                "SELECT due_at, snoozed_until FROM item_reviews WHERE item_id=?", (item_id,)
            ).fetchone()
            if rev_row:
                due_at = rev_row["due_at"]
                snoozed_until = rev_row["snoozed_until"]
                is_snoozed = snoozed_until is not None and snoozed_until > now_s
                if not is_snoozed and due_at is not None and due_at <= now_s:
                    due_count += 1

    explained_total = sum(by_band[b]["explained"] for b in by_band)
    base = f"{explained_total} of {total_items} parts explained"
    parts: list[str] = []
    if stale_count > 0:
        parts.append(f"{stale_count} stale")
    if due_count > 0:
        parts.append(f"{due_count} due for review")

    headline = f"{base} ({', '.join(parts)})" if parts else base

    return {
        "total_items": total_items,
        "by_band": by_band,
        "stale_count": stale_count,
        "due_count": due_count,
        "headline": headline,
    }
