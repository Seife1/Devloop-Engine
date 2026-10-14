"""Service for scanning and querying project technologies."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import Any

from learnloop.capture.techscan import scan_technologies


def refresh_technologies(conn: sqlite3.Connection, project_id: str) -> dict[str, Any]:
    """Scan the repository for dependencies and refresh project_technologies table."""
    row = conn.execute(
        "SELECT id, repo_path FROM projects WHERE id = ?",
        (project_id,),
    ).fetchone()
    if not row:
        raise ValueError(f"Project not found: {project_id}")

    repo_path = row["repo_path"] if isinstance(row, sqlite3.Row) else row[1]
    detected = scan_technologies(repo_path)

    now = datetime.now(UTC).isoformat()
    conn.execute("DELETE FROM project_technologies WHERE project_id = ?", (project_id,))
    conn.executemany(
        "INSERT OR REPLACE INTO project_technologies "
        "(project_id, ecosystem, name, version_spec, source_file, detected_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        [
            (project_id, t["ecosystem"], t["name"], t["version_spec"], t["source_file"], now)
            for t in detected
        ],
    )
    conn.commit()

    return {
        "project_id": project_id,
        "count": len(detected),
        "technologies": detected,
    }


def list_technologies(conn: sqlite3.Connection, project_id: str) -> list[dict[str, Any]]:
    """List detected technologies for a project grouped by ecosystem."""
    rows = conn.execute(
        "SELECT ecosystem, name, version_spec, source_file, detected_at "
        "FROM project_technologies WHERE project_id = ? "
        "ORDER BY ecosystem ASC, name ASC",
        (project_id,),
    ).fetchall()

    return [
        {
            "ecosystem": r["ecosystem"] if isinstance(r, sqlite3.Row) else r[0],
            "name": r["name"] if isinstance(r, sqlite3.Row) else r[1],
            "version_spec": r["version_spec"] if isinstance(r, sqlite3.Row) else r[2],
            "source_file": r["source_file"] if isinstance(r, sqlite3.Row) else r[3],
            "detected_at": r["detected_at"] if isinstance(r, sqlite3.Row) else r[4],
        }
        for r in rows
    ]
