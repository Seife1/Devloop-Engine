"""Session-start briefing service.

Delivers a calm, compact (< 3 KB) briefing at IDE session start:
- Changes since last briefing (new commits, unexplained commits, stale items)
- Due reviews (max 3 items) and plain waiting count (no overdue guilt)
- Suggested next action (deterministic: tour -> explain-stale -> review -> nothing)
- Calm protocol wording
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any

from learnloop.capture.skill_mapper import suggest_skills
from learnloop.domain import clock
from learnloop.domain.staleness import compute_item_staleness
from learnloop.services.capture_service import require_project
from learnloop.services.knowledge_service import _auto_ingest
from learnloop.services.profile_service import get_effective_profile
from learnloop.services.review_service import review_due

BRIEFING_PROTOCOL = """\
Session Briefing Protocol:
1. Calm start (~60s): present the briefing without pressure or urgency.
2. Overdue items are simply re-spaced; there is never an urgent backlog or penalty.
3. Offer ONE next action (suggested_next) and ask if the learner is ready.
4. Respect the learner's focus: allow them to say "skip" or "not now" to start coding immediately.
5. If reviewing: max 3 reviews per session, 1 question at a time, varied formats.\
"""

MAX_PAYLOAD_BYTES = 3072


def get_session_briefing(
    conn: sqlite3.Connection,
    project_id: str,
    now: datetime | None = None,
    ingest: bool = True,
) -> dict[str, Any]:
    """Generate a compact (< 3 KB) session-start briefing.

    - Ingests queue before computing if ingest=True.
    - Ignores origin='backfill' commits when counting new or unexplained commits.
    - Never outputs an "overdue" count or backlog number.
    - Updates projects.last_briefing_at to now.
    """
    if ingest:
        _auto_ingest(conn, project_id)
    project = require_project(conn, project_id)
    profile = get_effective_profile(conn, project_id)

    now_dt = now or clock.utcnow()
    now_s = clock.iso(now_dt)
    last_briefing_at = project["last_briefing_at"]

    # 1. New commits since last briefing (ignoring backfill)
    if last_briefing_at:
        new_commits_row = conn.execute(
            "SELECT COUNT(*) FROM commits WHERE project_id=? AND (origin IS NULL OR origin != 'backfill') "
            "AND kind = 'commit' AND committed_at > ?",
            (project_id, last_briefing_at),
        ).fetchone()
        new_commits_count = int(new_commits_row[0]) if new_commits_row else 0
    else:
        new_commits_row = conn.execute(
            "SELECT COUNT(*) FROM commits WHERE project_id=? AND (origin IS NULL OR origin != 'backfill') "
            "AND kind = 'commit'",
            (project_id,),
        ).fetchone()
        new_commits_count = int(new_commits_row[0]) if new_commits_row else 0

    # 2. Unexplained commits (ignoring backfill)
    unexplained_rows = conn.execute(
        "SELECT sha, message, files FROM commits WHERE project_id=? AND status='unexplained'"
        " AND (origin IS NULL OR origin != 'backfill') AND kind = 'commit' ORDER BY committed_at DESC",
        (project_id,),
    ).fetchall()
    unexplained_count = len(unexplained_rows)
    unexplained_suggestions = [
        {
            "sha": r["sha"][:7],
            "message": r["message"][:60],
            "suggested_skills": suggest_skills(conn, json.loads(r["files"]))[:3],
        }
        for r in unexplained_rows[:3]
    ]

    # 3. Knowledge items & staleness
    item_rows = conn.execute(
        "SELECT id, key, title, status, depth, baseline_commit, baseline_committed_at"
        " FROM knowledge_items WHERE project_id=? ORDER BY created_at ASC",
        (project_id,),
    ).fetchall()
    total_items = len(item_rows)

    # Pre-fetch commits for staleness check (exclude synthetic snapshot, include real backfilled commits)
    commit_rows = conn.execute(
        "SELECT sha, message, committed_at, files FROM commits WHERE project_id=?"
        " AND kind = 'commit' ORDER BY committed_at DESC",
        (project_id,),
    ).fetchall()
    commits_data = [
        {
            "sha": c["sha"],
            "message": c["message"],
            "committed_at": c["committed_at"],
            "files": json.loads(c["files"]),
        }
        for c in commit_rows
    ]

    stale_items: list[dict[str, str]] = []
    for it in item_rows:
        file_rows = conn.execute(
            "SELECT path FROM item_files WHERE item_id=? ORDER BY path ASC",
            (it["id"],),
        ).fetchall()
        item_files = [f["path"] for f in file_rows]
        staleness = compute_item_staleness(
            status=it["status"],
            item_files=item_files,
            baseline_commit=it["baseline_commit"],
            baseline_committed_at=it["baseline_committed_at"],
            commits=commits_data,
        )
        if staleness is not None:
            stale_items.append({"key": it["key"], "title": it["title"]})

    stale_count = len(stale_items)
    top_stale = stale_items[:3]

    # 4. Due reviews (max 3 items) and waiting count
    due_res = review_due(conn, project_id, limit=3, now=now_dt, ingest=ingest)
    due_items = [{"key": it["key"], "title": it["title"]} for it in due_res["items"]]
    waiting_count = due_res["waiting"]

    # 5. Suggested next action (deterministic priority)
    if total_items == 0:
        suggested_next = "tour"
    elif stale_count > 0:
        suggested_next = "explain-stale"
    elif len(due_items) > 0:
        suggested_next = "review"
    else:
        suggested_next = "nothing"

    # Readiness counts
    unexplained_items_count = sum(1 for it in item_rows if it["status"] == "unexplained")
    shaky_items_count = sum(1 for it in item_rows if it["status"] == "shaky")
    explained_items_count = sum(1 for it in item_rows if it["status"] == "explained")

    base_headline = f"{explained_items_count} of {total_items} parts explained"
    headline_parts: list[str] = []
    if stale_count > 0:
        headline_parts.append(f"{stale_count} stale")
    if waiting_count > 0:
        headline_parts.append(f"{waiting_count} due for review")
    readiness_headline = (
        f"{base_headline} ({', '.join(headline_parts)})"
        if headline_parts
        else base_headline
    )

    readiness = {
        "headline": readiness_headline,
        "unexplained": unexplained_items_count,
        "shaky": shaky_items_count,
        "explained": explained_items_count,
        "stale": stale_count,
        "due": waiting_count,
    }

    # Update projects.last_briefing_at
    conn.execute(
        "UPDATE projects SET last_briefing_at=? WHERE id=?",
        (now_s, project_id),
    )
    conn.commit()

    briefing_payload: dict[str, Any] = {
        "project_id": project_id,
        "session_minutes": int(profile["session_minutes"]),
        "readiness": readiness,
        "changes_since_briefing": {
            "last_briefing_at": last_briefing_at,
            "new_commits": new_commits_count,
            "unexplained_commits": unexplained_count,
            "unexplained_suggestions": unexplained_suggestions,
            "stale_items_count": stale_count,
            "stale_items": top_stale,
        },
        "due": due_items,
        "waiting": waiting_count,
        "suggested_next": suggested_next,
        "protocol": BRIEFING_PROTOCOL,
    }

    # Ensure payload strictly <= MAX_PAYLOAD_BYTES (3 KB)
    encoded = json.dumps(briefing_payload).encode("utf-8")
    if len(encoded) > MAX_PAYLOAD_BYTES:
        # Emergency shrink: drop suggestions and truncate protocol if needed
        briefing_payload["changes_since_briefing"]["unexplained_suggestions"] = []
        briefing_payload["protocol"] = briefing_payload["protocol"][:200]

    return briefing_payload
