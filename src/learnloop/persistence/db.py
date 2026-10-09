"""SQLite connection + forward-only migrations (PRAGMA user_version).

Losing a learner's history is the worst bug this product can have, so schema changes are
numbered SQL files applied in order and never edited after release.
"""

from __future__ import annotations

import logging
import shutil
import sqlite3
from importlib import resources
from pathlib import Path

from learnloop.taxonomy.loader import load_skills

log = logging.getLogger(__name__)


def _backup_if_needed(path: Path, current_version: int) -> None:
    """Copy the DB file before applying migrations. One backup per source version."""
    if current_version == 0:
        return
    backup = path.parent / f"{path.name}.bak-v{current_version}"
    if backup.exists():
        return
    try:
        shutil.copy2(path, backup)
        log.info("backed up %s -> %s", path.name, backup.name)
    except OSError as exc:
        log.warning("could not back up database: %s", exc)


def migrate(conn: sqlite3.Connection, path: Path | None = None) -> None:
    current: int = conn.execute("PRAGMA user_version").fetchone()[0]
    files = sorted(
        (p for p in resources.files("learnloop.persistence.migrations").iterdir() if p.name.endswith(".sql")),
        key=lambda p: p.name,
    )
    pending = [f for f in files if int(f.name.split("_", 1)[0]) > current]
    if pending and path is not None:
        _backup_if_needed(path, current)
    for f in pending:
        version = int(f.name.split("_", 1)[0])
        conn.executescript(f.read_text("utf-8"))
        conn.execute(f"PRAGMA user_version={version}")
        conn.commit()


def seed_taxonomy(conn: sqlite3.Connection) -> None:
    conn.executemany(
        "INSERT OR IGNORE INTO skills (id, name, parent_id) VALUES (:id, :name, :parent_id)",
        sorted(load_skills(), key=lambda s: str(s["id"]).count(".")),  # parents first
    )
    conn.commit()


def connect(path: Path | str) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA journal_mode=WAL")
    migrate(conn, path)
    seed_taxonomy(conn)
    return conn
