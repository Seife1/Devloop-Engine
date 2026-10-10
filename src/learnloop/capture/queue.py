"""Write (hook side) and ingest (server side) of the commit queue at <repo>/.learn/queue/.

The hook never talks to the server: the server is pull-based and may not be running.
Queue files are metadata only (sha, message, file paths), redacted, and idempotent by sha.
"""

from __future__ import annotations

import json
import logging
import os
import sqlite3
from pathlib import Path

from learnloop.capture.redaction import is_ignored, redact
from learnloop.config import Settings
from learnloop.domain import clock

log = logging.getLogger(__name__)
MAX_FILES_PER_COMMIT = 500
MAX_FILES_BACKFILL = 5000


def queue_dir(repo: Path) -> Path:
    return repo / ".learn" / "queue"


def write_queue_entry(
    repo: Path,
    sha: str,
    message: str,
    files: list[str],
    committed_at: str,
    origin: str = "hook",
    kind: str = "commit",
    max_files: int = MAX_FILES_PER_COMMIT,
) -> Path:
    """Hook side / backfill side. Redacts first, writes atomically."""
    clean_kind = kind if kind in ("commit", "snapshot") else "commit"
    entry = {
        "sha": sha,
        "message": redact(message)[:500],
        "files": [f for f in files if not is_ignored(f)][:max_files],
        "committed_at": committed_at,
        "origin": origin,
        "kind": clean_kind,
    }
    d = queue_dir(repo)
    d.mkdir(parents=True, exist_ok=True)
    final = d / f"{sha}.json"
    tmp = d / f".{sha}.tmp"
    tmp.write_text(json.dumps(entry), encoding="utf-8")
    os.replace(tmp, final)
    return final


def ingest(conn: sqlite3.Connection, settings: Settings, project_id: str, repo: Path) -> dict[str, int]:
    """Server side. Redacts again, dedupes by sha, quarantines bad files instead of crashing."""
    stats = {"ingested": 0, "duplicates": 0, "rejected": 0}
    d = queue_dir(repo)
    if not d.is_dir():
        return stats
    for path in sorted(d.glob("*.json"))[: settings.max_queue_files]:
        try:
            if path.stat().st_size > settings.max_queue_file_bytes:
                raise ValueError("queue file too large")
            e = json.loads(path.read_text("utf-8"))
            sha, committed_at = str(e["sha"]), clock.iso(clock.parse(e["committed_at"]))
            files = [f for f in e["files"] if isinstance(f, str) and not is_ignored(f)]
            origin = str(e.get("origin", "hook"))
            if origin not in ("hook", "backfill"):
                origin = "hook"
            kind = str(e.get("kind", "commit"))
            if kind not in ("commit", "snapshot"):
                kind = "commit"

            # One snapshot per project: new snapshot replaces previous snapshot row
            verb = "REPLACE" if kind == "snapshot" else "IGNORE"
            if kind == "snapshot":
                conn.execute("DELETE FROM commits WHERE project_id=? AND kind='snapshot'", (project_id,))
            cur = conn.execute(
                f"INSERT OR {verb} INTO commits "
                "(sha, project_id, message, files, committed_at, origin, kind) "
                "VALUES (?,?,?,?,?,?,?)",
                (
                    sha,
                    project_id,
                    redact(str(e["message"]))[:500],
                    json.dumps(files),
                    committed_at,
                    origin,
                    kind,
                ),
            )

            stats["ingested" if cur.rowcount else "duplicates"] += 1
            conn.commit()
            path.unlink()
        except Exception as exc:  # noqa: BLE001 - one bad file must not block the rest
            log.warning("rejecting queue file %s: %s", path.name, exc)
            path.rename(path.with_suffix(".failed"))
            stats["rejected"] += 1
    return stats
