"""SQLite connection + forward-only migrations (PRAGMA user_version).

Losing a learner's history is the worst bug this product can have, so schema changes are
numbered SQL files applied in order and never edited after release.
"""

from __future__ import annotations

import sqlite3
from importlib import resources
from pathlib import Path

from learnloop.taxonomy.loader import load_skills


def migrate(conn: sqlite3.Connection) -> None:
    current = conn.execute("PRAGMA user_version").fetchone()[0]
    files = sorted(
        (p for p in resources.files("learnloop.persistence.migrations").iterdir() if p.name.endswith(".sql")),
        key=lambda p: p.name,
    )
    for f in files:
        version = int(f.name.split("_", 1)[0])
        if version > current:
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
    migrate(conn)
    seed_taxonomy(conn)
    return conn
