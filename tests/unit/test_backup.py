from __future__ import annotations

import sqlite3
from pathlib import Path

from learnloop.persistence.db import migrate

INIT_V1 = """
CREATE TABLE projects (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  repo_path TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL
);
CREATE TABLE skills (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  parent_id TEXT REFERENCES skills(id)
);
CREATE TABLE intents (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id),
  summary TEXT NOT NULL,
  rationale TEXT NOT NULL,
  commit_sha TEXT,
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','verified','abandoned')),
  created_at TEXT NOT NULL
);
CREATE TABLE intent_skills (
  intent_id TEXT NOT NULL REFERENCES intents(id) ON DELETE CASCADE,
  skill_id TEXT NOT NULL REFERENCES skills(id),
  PRIMARY KEY (intent_id, skill_id)
);
CREATE TABLE commits (
  sha TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id),
  message TEXT NOT NULL,
  files TEXT NOT NULL,
  committed_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new','verified','unexplained'))
);
CREATE TABLE events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL REFERENCES projects(id),
  skill_id TEXT NOT NULL REFERENCES skills(id),
  commit_sha TEXT NOT NULL REFERENCES commits(sha),
  intent_id TEXT NOT NULL REFERENCES intents(id),
  created_at TEXT NOT NULL,
  UNIQUE (commit_sha, skill_id)
);
CREATE INDEX idx_events_skill ON events(skill_id);
CREATE TABLE decisions (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id),
  intent_id TEXT REFERENCES intents(id),
  choice TEXT NOT NULL,
  alternatives TEXT NOT NULL,
  tradeoffs TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE attempts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  skill_id TEXT NOT NULL REFERENCES skills(id),
  raw_score REAL NOT NULL CHECK (raw_score BETWEEN 0 AND 1),
  hints_used INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL
);
CREATE TABLE skill_mastery (
  skill_id TEXT PRIMARY KEY REFERENCES skills(id),
  mastery REAL NOT NULL,
  attempts INTEGER NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE mistakes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  skill_id TEXT NOT NULL REFERENCES skills(id),
  pattern TEXT NOT NULL,
  count INTEGER NOT NULL DEFAULT 1,
  confidence TEXT NOT NULL DEFAULT 'medium' CHECK (confidence IN ('low','medium','high')),
  last_seen TEXT NOT NULL,
  UNIQUE (skill_id, pattern)
);
"""


def test_backup_captures_wal_uncommitted_to_main_file(tmp_path: Path):
    db_path = tmp_path / "wal_test.db"
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    # Disable autocheckpoint so committed changes remain strictly in the WAL file
    conn.execute("PRAGMA wal_autocheckpoint=0")
    conn.executescript(INIT_V1)
    conn.execute("PRAGMA user_version=1")
    conn.commit()

    # Insert a project record into WAL
    conn.execute(
        "INSERT INTO projects (id, name, repo_path, created_at) VALUES (?, ?, ?, ?)",
        ("p_wal", "Wal Project", "/workspace/wal", "2026-03-01T10:00:00Z"),
    )
    conn.commit()

    wal_path = tmp_path / "wal_test.db-wal"
    assert wal_path.exists()
    assert wal_path.stat().st_size > 0

    # Migrate from version 1 to latest (version 5)
    migrate(conn, db_path)

    backup_path = tmp_path / "wal_test.db.bak-v1"
    assert backup_path.exists()

    # The backup should contain the uncheckpointed WAL row
    bck_conn = sqlite3.connect(backup_path)
    bck_conn.row_factory = sqlite3.Row
    row = bck_conn.execute("SELECT * FROM projects WHERE id='p_wal'").fetchone()
    assert row is not None
    assert row["name"] == "Wal Project"
    bck_conn.close()
    conn.close()


def test_no_backup_on_empty_db(tmp_path: Path):
    db_path = tmp_path / "fresh.db"
    conn = sqlite3.connect(db_path)
    # version is 0 (empty database)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 0

    migrate(conn, db_path)

    # Database is migrated to version 5, but no backup should have been created for v0
    backups = list(tmp_path.glob("fresh.db.bak*"))
    assert len(backups) == 0
    conn.close()


def test_backup_once_per_upgrade(tmp_path: Path):
    db_path = tmp_path / "upgrade.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(INIT_V1)
    conn.execute("PRAGMA user_version=1")
    conn.commit()

    # Single migrate run applies v2, v3, v4, v5
    migrate(conn, db_path)

    # Exactly one backup created: .bak-v1
    backups = sorted([p.name for p in tmp_path.glob("upgrade.db.bak*")])
    assert backups == ["upgrade.db.bak-v1"]

    # Re-running migrate does not create another backup
    migrate(conn, db_path)
    backups_after = sorted([p.name for p in tmp_path.glob("upgrade.db.bak*")])
    assert backups_after == ["upgrade.db.bak-v1"]
    conn.close()
