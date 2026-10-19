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

QUIZZES_V2 = """
CREATE TABLE quizzes (
  id TEXT PRIMARY KEY,
  skill_id TEXT NOT NULL REFERENCES skills(id),
  project_id TEXT REFERENCES projects(id),
  level TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','recorded')),
  created_at TEXT NOT NULL
);
CREATE TABLE quiz_questions (
  quiz_id TEXT NOT NULL REFERENCES quizzes(id) ON DELETE CASCADE,
  ordinal INTEGER NOT NULL,
  kind TEXT NOT NULL,
  prompt TEXT NOT NULL,
  reference_answer TEXT NOT NULL,
  rubric TEXT NOT NULL,
  PRIMARY KEY (quiz_id, ordinal)
);
CREATE TABLE quiz_answers (
  quiz_id TEXT NOT NULL,
  ordinal INTEGER NOT NULL,
  learner_answer TEXT NOT NULL,
  score REAL NOT NULL CHECK (score BETWEEN 0 AND 1),
  hints_used INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  PRIMARY KEY (quiz_id, ordinal),
  FOREIGN KEY (quiz_id, ordinal) REFERENCES quiz_questions(quiz_id, ordinal)
);
ALTER TABLE attempts ADD COLUMN quiz_id TEXT REFERENCES quizzes(id);
"""


def _build_v2_database(conn: sqlite3.Connection) -> None:
    conn.executescript(INIT_V1)
    conn.executescript(QUIZZES_V2)
    conn.execute("PRAGMA user_version=2")
    conn.commit()


def test_migration_from_v2_to_latest_preserves_all_data(tmp_path: Path):
    db_path = tmp_path / "v2_migration.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")

    _build_v2_database(conn)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 2

    # Populate rows in EVERY table (13 tables)
    conn.execute(
        "INSERT INTO projects (id, name, repo_path, created_at) VALUES (?, ?, ?, ?)",
        ("p1", "LearnLoop Project", "/workspace/repo", "2026-03-01T10:00:00Z"),
    )
    conn.execute(
        "INSERT INTO skills (id, name, parent_id) VALUES (?, ?, ?)",
        ("python.testing", "Python Testing", None),
    )
    conn.execute(
        "INSERT INTO skills (id, name, parent_id) VALUES (?, ?, ?)",
        ("python.testing.mocking", "Mocking", "python.testing"),
    )
    conn.execute(
        "INSERT INTO intents (id, project_id, summary, rationale, commit_sha, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        ("i1", "p1", "Add unit tests", "Ensure regression coverage", None, "open", "2026-03-01T10:01:00Z"),
    )
    conn.execute(
        "INSERT INTO intent_skills (intent_id, skill_id) VALUES (?, ?)",
        ("i1", "python.testing"),
    )
    conn.execute(
        "INSERT INTO commits (sha, project_id, message, files, committed_at, status) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("c1", "p1", "test: add unit tests", '["tests/test_x.py"]', "2026-03-01T10:02:00Z", "verified"),
    )
    conn.execute(
        "INSERT INTO events (id, project_id, skill_id, commit_sha, intent_id, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (1, "p1", "python.testing", "c1", "i1", "2026-03-01T10:03:00Z"),
    )
    conn.execute(
        "INSERT INTO decisions (id, project_id, intent_id, choice, alternatives, tradeoffs, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            "d1",
            "p1",
            "i1",
            "pytest framework",
            '["unittest", "nose"]',
            "pytest has cleaner fixtures",
            "2026-03-01T10:04:00Z",
        ),
    )
    conn.execute(
        "INSERT INTO attempts (id, skill_id, raw_score, hints_used, created_at, quiz_id) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (1, "python.testing", 0.85, 1, "2026-03-01T10:05:00Z", None),
    )
    conn.execute(
        "INSERT INTO skill_mastery (skill_id, mastery, attempts, updated_at) VALUES (?, ?, ?, ?)",
        ("python.testing", 0.65, 1, "2026-03-01T10:06:00Z"),
    )
    conn.execute(
        "INSERT INTO mistakes (id, skill_id, pattern, count, confidence, last_seen) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (1, "python.testing", "forgot assert statement", 2, "medium", "2026-03-01T10:07:00Z"),
    )
    conn.execute(
        "INSERT INTO quizzes (id, skill_id, project_id, level, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("q1", "python.testing", "p1", "intermediate", "open", "2026-03-01T10:08:00Z"),
    )
    conn.execute(
        "INSERT INTO quiz_questions (quiz_id, ordinal, kind, prompt, reference_answer, rubric) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("q1", 1, "explain", "Explain mock return_value", "Sets return value", '["mock", "return"]'),
    )
    conn.execute(
        "INSERT INTO quiz_answers (quiz_id, ordinal, learner_answer, score, hints_used, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        ("q1", 1, "return_value specifies what the mock returns when called", 1.0, 0, "2026-03-01T10:09:00Z"),
    )
    conn.commit()

    # List of all 13 v2 tables
    v2_tables = [
        "projects",
        "skills",
        "intents",
        "intent_skills",
        "commits",
        "events",
        "decisions",
        "attempts",
        "skill_mastery",
        "mistakes",
        "quizzes",
        "quiz_questions",
        "quiz_answers",
    ]

    # Verify every table has at least one row before migration
    for tbl in v2_tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        assert count > 0, f"Table {tbl} had no rows before migration"

    # Run migrations to latest version
    migrate(conn, db_path)

    # Assert latest user_version (14 for v0.5.3 + MCP-native redesign)
    new_version = conn.execute("PRAGMA user_version").fetchone()[0]
    assert new_version == 14

    # 1. Assert no row is lost or altered
    assert conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0] == 1
    proj = conn.execute("SELECT * FROM projects WHERE id='p1'").fetchone()
    assert proj["name"] == "LearnLoop Project"
    assert proj["repo_path"] == "/workspace/repo"
    assert proj["created_at"] == "2026-03-01T10:00:00Z"

    assert conn.execute("SELECT COUNT(*) FROM skills").fetchone()[0] == 2
    sk = conn.execute("SELECT * FROM skills WHERE id='python.testing'").fetchone()
    assert sk["name"] == "Python Testing"
    assert sk["parent_id"] is None

    assert conn.execute("SELECT COUNT(*) FROM intents").fetchone()[0] == 1
    intent = conn.execute("SELECT * FROM intents WHERE id='i1'").fetchone()
    assert intent["summary"] == "Add unit tests"
    assert intent["rationale"] == "Ensure regression coverage"
    assert intent["status"] == "open"

    assert conn.execute("SELECT COUNT(*) FROM intent_skills").fetchone()[0] == 1
    isk = conn.execute("SELECT * FROM intent_skills WHERE intent_id='i1'").fetchone()
    assert isk["skill_id"] == "python.testing"

    assert conn.execute("SELECT COUNT(*) FROM commits").fetchone()[0] == 1
    cm = conn.execute("SELECT * FROM commits WHERE sha='c1'").fetchone()
    assert cm["message"] == "test: add unit tests"
    assert cm["status"] == "verified"
    assert cm["origin"] == "hook"
    assert cm["kind"] == "commit"

    assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1
    ev = conn.execute("SELECT * FROM events WHERE id=1").fetchone()
    assert ev["skill_id"] == "python.testing"
    assert ev["commit_sha"] == "c1"

    assert conn.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] == 1
    dec = conn.execute("SELECT * FROM decisions WHERE id='d1'").fetchone()
    assert dec["choice"] == "pytest framework"

    assert conn.execute("SELECT COUNT(*) FROM attempts").fetchone()[0] == 1
    att = conn.execute("SELECT * FROM attempts WHERE id=1").fetchone()
    assert att["raw_score"] == 0.85
    assert att["hints_used"] == 1

    assert conn.execute("SELECT COUNT(*) FROM skill_mastery").fetchone()[0] == 1
    sm = conn.execute("SELECT * FROM skill_mastery WHERE skill_id='python.testing'").fetchone()
    assert sm["mastery"] == 0.65

    assert conn.execute("SELECT COUNT(*) FROM mistakes").fetchone()[0] == 1
    mis = conn.execute("SELECT * FROM mistakes WHERE id=1").fetchone()
    assert mis["pattern"] == "forgot assert statement"
    assert mis["count"] == 2

    assert conn.execute("SELECT COUNT(*) FROM quizzes").fetchone()[0] == 1
    qz = conn.execute("SELECT * FROM quizzes WHERE id='q1'").fetchone()
    assert qz["skill_id"] == "python.testing"
    assert qz["level"] == "intermediate"

    assert conn.execute("SELECT COUNT(*) FROM quiz_questions").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM quiz_answers").fetchone()[0] == 1

    # 2. Assert old quiz_questions have grounding='unspecified' and source_file is None
    qq = conn.execute("SELECT * FROM quiz_questions WHERE quiz_id='q1' AND ordinal=1").fetchone()
    assert qq["prompt"] == "Explain mock return_value"
    assert qq["reference_answer"] == "Sets return value"
    assert qq["grounding"] == "unspecified"
    assert qq["source_file"] is None

    # 3. Assert old skills have source='seed' and proposed_at is None and rationale is None
    sk1 = conn.execute("SELECT * FROM skills WHERE id='python.testing'").fetchone()
    assert sk1["source"] == "seed"
    assert sk1["proposed_at"] is None
    assert sk1["rationale"] is None

    sk2 = conn.execute("SELECT * FROM skills WHERE id='python.testing.mocking'").fetchone()
    assert sk2["source"] == "seed"
    assert sk2["proposed_at"] is None
    assert sk2["rationale"] is None

    # 4. Check new table intent_files exists
    assert conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='intent_files'"
    ).fetchone() is not None

    # 5. Check migration 007 tables exist and learner_profile has default row
    for tbl in ("learner_profile", "knowledge_items", "item_files", "item_tags", "explanations"):
        assert conn.execute(
            f"SELECT name FROM sqlite_master WHERE type='table' AND name='{tbl}'"
        ).fetchone() is not None
    prof = conn.execute("SELECT * FROM learner_profile WHERE id=1").fetchone()
    assert prof is not None
    assert prof["level"] == "beginner"

    # 6. Check migration 009 kind column and snapshot index
    assert "kind" in cm.keys()
    assert conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_commits_project_snapshot'"
    ).fetchone() is not None

    conn.close()


def test_migration_005_to_006(tmp_path: Path):
    db_path = tmp_path / "v5_to_v6.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")

    _build_v2_database(conn)
    # Apply 003, 004, 005 manually
    conn.execute(
        "CREATE TABLE intent_files (intent_id TEXT NOT NULL REFERENCES intents(id) ON DELETE CASCADE, path TEXT NOT NULL, touched INTEGER, PRIMARY KEY (intent_id, path));"
    )
    conn.execute("ALTER TABLE quiz_questions ADD COLUMN source_file TEXT;")
    conn.execute(
        "ALTER TABLE quiz_questions ADD COLUMN grounding TEXT NOT NULL DEFAULT 'unspecified' CHECK (grounding IN ('project','generic','unspecified'));"
    )
    conn.execute("ALTER TABLE skills ADD COLUMN source TEXT NOT NULL DEFAULT 'seed' CHECK (source IN ('seed','proposed'));")
    conn.execute("ALTER TABLE skills ADD COLUMN proposed_at TEXT;")
    conn.execute("ALTER TABLE skills ADD COLUMN rationale TEXT;")
    conn.execute("PRAGMA user_version=5")
    conn.commit()

    conn.execute(
        "INSERT INTO projects (id, name, repo_path, created_at) VALUES ('p1', 'P1', '/repo', '2026-01-01T00:00:00Z')"
    )
    conn.execute(
        "INSERT INTO commits (sha, project_id, message, files, committed_at, status) VALUES ('c1', 'p1', 'msg', '[]', '2026-01-01T00:00:00Z', 'verified')"
    )
    conn.commit()

    # Apply migration 006 (migrate will also apply 007-014)
    migrate(conn, db_path)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 14

    row = conn.execute("SELECT origin FROM commits WHERE sha='c1'").fetchone()
    assert row["origin"] == "hook"

    # Insert commit with origin backfill
    conn.execute(
        "INSERT INTO commits (sha, project_id, message, files, committed_at, status, origin) VALUES ('c2', 'p1', 'backfill msg', '[]', '2026-01-01T00:00:00Z', 'new', 'backfill')"
    )
    conn.commit()
    assert conn.execute("SELECT origin FROM commits WHERE sha='c2'").fetchone()[0] == "backfill"
    conn.close()


def test_migration_006_to_007(tmp_path: Path):
    db_path = tmp_path / "v6_to_v7.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")

    _build_v2_database(conn)
    conn.execute(
        "CREATE TABLE intent_files (intent_id TEXT NOT NULL REFERENCES intents(id) ON DELETE CASCADE, path TEXT NOT NULL, touched INTEGER, PRIMARY KEY (intent_id, path));"
    )
    conn.execute("ALTER TABLE quiz_questions ADD COLUMN source_file TEXT;")
    conn.execute(
        "ALTER TABLE quiz_questions ADD COLUMN grounding TEXT NOT NULL DEFAULT 'unspecified' CHECK (grounding IN ('project','generic','unspecified'));"
    )
    conn.execute("ALTER TABLE skills ADD COLUMN source TEXT NOT NULL DEFAULT 'seed' CHECK (source IN ('seed','proposed'));")
    conn.execute("ALTER TABLE skills ADD COLUMN proposed_at TEXT;")
    conn.execute("ALTER TABLE skills ADD COLUMN rationale TEXT;")
    conn.execute("ALTER TABLE commits ADD COLUMN origin TEXT NOT NULL DEFAULT 'hook' CHECK (origin IN ('hook','backfill'));")
    conn.execute("PRAGMA user_version=6")
    conn.commit()

    migrate(conn, db_path)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 14

    # Verify learner_profile initialized
    prof = conn.execute("SELECT * FROM learner_profile WHERE id=1").fetchone()
    assert prof["level"] == "beginner"
    assert prof["goal"] == "both"
    assert prof["session_minutes"] == 5
    assert prof["audience"] == "self"

    # Verify tables work
    conn.execute(
        "INSERT INTO projects (id, name, repo_path, created_at) VALUES ('p1', 'P1', '/repo', '2026-01-01T00:00:00Z')"
    )
    conn.execute(
        "INSERT INTO knowledge_items (id, project_id, key, title, kind, band, summary, status, depth, created_at, updated_at)"
        " VALUES ('k1', 'p1', 'core', 'Core Title', 'component', 'basic', 'Summary', 'unexplained', 1, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')"
    )
    conn.execute("INSERT INTO item_files (item_id, path) VALUES ('k1', 'src/main.py')")
    conn.execute("INSERT INTO item_tags (item_id, tag) VALUES ('k1', 'core')")
    conn.execute(
        "INSERT INTO explanations (id, item_id, audience, depth, learner_text, score, created_at)"
        " VALUES (1, 'k1', 'self', 1, 'Learner explanation', 0.9, '2026-01-01T00:00:00Z')"
    )
    conn.commit()

    assert conn.execute("SELECT COUNT(*) FROM knowledge_items").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM item_files").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM item_tags").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM explanations").fetchone()[0] == 1
    conn.close()


def test_migration_007_to_008(tmp_path: Path):
    db_path = tmp_path / "v7_to_v8.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")

    _build_v2_database(conn)
    conn.execute(
        "CREATE TABLE intent_files (intent_id TEXT NOT NULL REFERENCES intents(id) ON DELETE CASCADE, path TEXT NOT NULL, touched INTEGER, PRIMARY KEY (intent_id, path));"
    )
    conn.execute("ALTER TABLE quiz_questions ADD COLUMN source_file TEXT;")
    conn.execute(
        "ALTER TABLE quiz_questions ADD COLUMN grounding TEXT NOT NULL DEFAULT 'unspecified' CHECK (grounding IN ('project','generic','unspecified'));"
    )
    conn.execute("ALTER TABLE skills ADD COLUMN source TEXT NOT NULL DEFAULT 'seed' CHECK (source IN ('seed','proposed'));")
    conn.execute("ALTER TABLE skills ADD COLUMN proposed_at TEXT;")
    conn.execute("ALTER TABLE skills ADD COLUMN rationale TEXT;")
    conn.execute("ALTER TABLE commits ADD COLUMN origin TEXT NOT NULL DEFAULT 'hook' CHECK (origin IN ('hook','backfill'));")

    # 007 tables
    conn.execute("""
    CREATE TABLE learner_profile (
      id INTEGER PRIMARY KEY CHECK (id = 1),
      level TEXT NOT NULL DEFAULT 'beginner' CHECK (level IN ('school', 'beginner', 'junior', 'mid', 'senior')),
      goal TEXT NOT NULL DEFAULT 'both' CHECK (goal IN ('learn', 'interview', 'both')),
      session_minutes INTEGER NOT NULL DEFAULT 5 CHECK (session_minutes BETWEEN 3 AND 30),
      audience TEXT NOT NULL DEFAULT 'self' CHECK (audience IN ('self', 'classmate', 'recruiter', 'tech-lead')),
      updated_at TEXT NOT NULL
    );
    """)
    conn.execute(
        "INSERT INTO learner_profile (id, level, goal, session_minutes, audience, updated_at)"
        " VALUES (1, 'beginner', 'both', 5, 'self', '2026-01-01T00:00:00Z')"
    )
    conn.execute("""
    CREATE TABLE knowledge_items (
      id TEXT PRIMARY KEY,
      project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
      key TEXT NOT NULL,
      title TEXT NOT NULL,
      kind TEXT NOT NULL CHECK (kind IN ('component', 'decision', 'concept', 'bug-fix')),
      band TEXT NOT NULL CHECK (band IN ('basic', 'intermediate', 'advanced')),
      summary TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'unexplained' CHECK (status IN ('unexplained', 'shaky', 'explained')),
      depth INTEGER NOT NULL DEFAULT 1 CHECK (depth BETWEEN 1 AND 5),
      baseline_commit TEXT NULL REFERENCES commits(sha),
      baseline_committed_at TEXT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      UNIQUE (project_id, key)
    );
    """)
    conn.execute("""
    CREATE TABLE item_files (
      item_id TEXT NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE,
      path TEXT NOT NULL,
      PRIMARY KEY (item_id, path)
    );
    """)
    conn.execute("""
    CREATE TABLE item_tags (
      item_id TEXT NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE,
      tag TEXT NOT NULL,
      PRIMARY KEY (item_id, tag)
    );
    """)
    conn.execute("""
    CREATE TABLE explanations (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      item_id TEXT NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE,
      audience TEXT NOT NULL CHECK (audience IN ('self', 'classmate', 'recruiter', 'tech-lead')),
      depth INTEGER NOT NULL CHECK (depth BETWEEN 1 AND 5),
      learner_text TEXT NOT NULL,
      score REAL NOT NULL CHECK (score BETWEEN 0.0 AND 1.0),
      created_at TEXT NOT NULL
    );
    """)
    conn.execute("PRAGMA user_version=7")
    conn.commit()

    conn.execute(
        "INSERT INTO projects (id, name, repo_path, created_at) VALUES ('p1', 'P1', '/repo', '2026-01-01T00:00:00Z')"
    )
    conn.execute(
        "INSERT INTO knowledge_items (id, project_id, key, title, kind, band, summary, status, depth, created_at, updated_at)"
        " VALUES ('k1', 'p1', 'core', 'Core Title', 'component', 'basic', 'Summary', 'unexplained', 1, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')"
    )
    conn.commit()

    migrate(conn, db_path)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 14

    # Verify last_briefing_at column exists
    p = conn.execute("SELECT * FROM projects WHERE id='p1'").fetchone()
    assert "last_briefing_at" in p.keys()
    assert p["last_briefing_at"] is None

    # Test item_reviews insertion
    conn.execute(
        "INSERT INTO item_reviews (item_id, interval_days, ease, reps, due_at, last_reviewed_at)"
        " VALUES ('k1', 1, 2.3, 0, '2026-01-02T00:00:00Z', '2026-01-01T00:00:00Z')"
    )
    # Test item_questions insertion
    conn.execute(
        "INSERT INTO item_questions (item_id, question, depth, created_at)"
        " VALUES ('k1', 'Why did you choose this architecture?', 1, '2026-01-01T00:00:00Z')"
    )
    conn.commit()

    rev = conn.execute("SELECT * FROM item_reviews WHERE item_id='k1'").fetchone()
    assert rev["interval_days"] == 1
    assert rev["ease"] == 2.3
    assert rev["reps"] == 0

    q = conn.execute("SELECT * FROM item_questions WHERE item_id='k1'").fetchone()
    assert q["question"] == "Why did you choose this architecture?"
    assert q["depth"] == 1

    conn.close()


def test_migration_008_to_009(tmp_path: Path):
    db_path = tmp_path / "v8_to_v9.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")

    _build_v2_database(conn)
    # Apply 003, 004, 005, 006
    conn.execute(
        "CREATE TABLE intent_files (intent_id TEXT NOT NULL REFERENCES intents(id) ON DELETE CASCADE, path TEXT NOT NULL, touched INTEGER, PRIMARY KEY (intent_id, path));"
    )
    conn.execute("ALTER TABLE quiz_questions ADD COLUMN source_file TEXT;")
    conn.execute(
        "ALTER TABLE quiz_questions ADD COLUMN grounding TEXT NOT NULL DEFAULT 'unspecified' CHECK (grounding IN ('project','generic','unspecified'));"
    )
    conn.execute("ALTER TABLE skills ADD COLUMN source TEXT NOT NULL DEFAULT 'seed' CHECK (source IN ('seed','proposed'));")
    conn.execute("ALTER TABLE skills ADD COLUMN proposed_at TEXT;")
    conn.execute("ALTER TABLE skills ADD COLUMN rationale TEXT;")
    conn.execute("ALTER TABLE commits ADD COLUMN origin TEXT NOT NULL DEFAULT 'hook' CHECK (origin IN ('hook','backfill'));")

    # Apply 007
    conn.execute("""
    CREATE TABLE learner_profile (
      id INTEGER PRIMARY KEY CHECK (id = 1),
      level TEXT NOT NULL DEFAULT 'beginner' CHECK (level IN ('school', 'beginner', 'junior', 'mid', 'senior')),
      goal TEXT NOT NULL DEFAULT 'both' CHECK (goal IN ('learn', 'interview', 'both')),
      session_minutes INTEGER NOT NULL DEFAULT 5 CHECK (session_minutes BETWEEN 3 AND 30),
      audience TEXT NOT NULL DEFAULT 'self' CHECK (audience IN ('self', 'classmate', 'recruiter', 'tech-lead')),
      updated_at TEXT NOT NULL
    );
    """)
    conn.execute("""
    CREATE TABLE knowledge_items (
      id TEXT PRIMARY KEY,
      project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
      key TEXT NOT NULL,
      title TEXT NOT NULL,
      kind TEXT NOT NULL CHECK (kind IN ('component', 'decision', 'concept', 'bug-fix')),
      band TEXT NOT NULL CHECK (band IN ('basic', 'intermediate', 'advanced')),
      summary TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'unexplained' CHECK (status IN ('unexplained', 'shaky', 'explained')),
      depth INTEGER NOT NULL DEFAULT 1 CHECK (depth BETWEEN 1 AND 5),
      baseline_commit TEXT NULL REFERENCES commits(sha),
      baseline_committed_at TEXT NULL,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      UNIQUE (project_id, key)
    );
    """)
    conn.execute("""
    CREATE TABLE item_files (
      item_id TEXT NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE,
      path TEXT NOT NULL,
      PRIMARY KEY (item_id, path)
    );
    """)
    conn.execute("""
    CREATE TABLE item_tags (
      item_id TEXT NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE,
      tag TEXT NOT NULL,
      PRIMARY KEY (item_id, tag)
    );
    """)
    conn.execute("""
    CREATE TABLE explanations (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      item_id TEXT NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE,
      audience TEXT NOT NULL CHECK (audience IN ('self', 'classmate', 'recruiter', 'tech-lead')),
      depth INTEGER NOT NULL CHECK (depth BETWEEN 1 AND 5),
      learner_text TEXT NOT NULL,
      score REAL NOT NULL CHECK (score BETWEEN 0.0 AND 1.0),
      created_at TEXT NOT NULL
    );
    """)

    # Apply 008
    conn.execute("""
    CREATE TABLE item_reviews (
      item_id TEXT PRIMARY KEY REFERENCES knowledge_items(id) ON DELETE CASCADE,
      interval_days INTEGER NOT NULL DEFAULT 1 CHECK (interval_days >= 1),
      ease REAL NOT NULL DEFAULT 2.3 CHECK (ease BETWEEN 1.3 AND 3.0),
      reps INTEGER NOT NULL DEFAULT 0 CHECK (reps >= 0),
      due_at TEXT NOT NULL,
      snoozed_until TEXT NULL,
      last_reviewed_at TEXT NULL
    );
    """)
    conn.execute("""
    CREATE TABLE item_questions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      item_id TEXT NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE,
      question TEXT NOT NULL,
      depth INTEGER NOT NULL CHECK (depth BETWEEN 1 AND 5),
      created_at TEXT NOT NULL
    );
    """)
    conn.execute("ALTER TABLE projects ADD COLUMN last_briefing_at TEXT NULL;")
    conn.execute("PRAGMA user_version=8")
    conn.commit()

    # Populate rows in EVERY table (all 21 v8 tables)
    conn.execute(
        "INSERT INTO projects (id, name, repo_path, created_at, last_briefing_at)"
        " VALUES ('p1', 'P1', '/repo', '2026-03-01T00:00:00Z', NULL)"
    )
    conn.execute(
        "INSERT INTO skills (id, name, parent_id, source, proposed_at, rationale)"
        " VALUES ('python.testing', 'Testing', NULL, 'seed', NULL, NULL)"
    )
    conn.execute(
        "INSERT INTO intents (id, project_id, summary, rationale, commit_sha, status, created_at)"
        " VALUES ('i1', 'p1', 'Intent summary', 'Rationale', NULL, 'open', '2026-03-01T00:00:00Z')"
    )
    conn.execute("INSERT INTO intent_skills (intent_id, skill_id) VALUES ('i1', 'python.testing')")
    conn.execute(
        "INSERT INTO commits (sha, project_id, message, files, committed_at, status, origin)"
        " VALUES ('c1', 'p1', 'initial commit', '[\"src/main.py\"]', '2026-03-01T00:00:00Z', 'verified', 'hook')"
    )
    conn.execute(
        "INSERT INTO events (id, project_id, skill_id, commit_sha, intent_id, created_at)"
        " VALUES (1, 'p1', 'python.testing', 'c1', 'i1', '2026-03-01T00:00:00Z')"
    )
    conn.execute(
        "INSERT INTO decisions (id, project_id, intent_id, choice, alternatives, tradeoffs, created_at)"
        " VALUES ('d1', 'p1', 'i1', 'choice', '[]', 'tradeoffs', '2026-03-01T00:00:00Z')"
    )
    conn.execute(
        "INSERT INTO attempts (id, skill_id, raw_score, hints_used, created_at, quiz_id)"
        " VALUES (1, 'python.testing', 1.0, 0, '2026-03-01T00:00:00Z', NULL)"
    )
    conn.execute(
        "INSERT INTO skill_mastery (skill_id, mastery, attempts, updated_at)"
        " VALUES ('python.testing', 1.0, 1, '2026-03-01T00:00:00Z')"
    )
    conn.execute(
        "INSERT INTO mistakes (id, skill_id, pattern, count, confidence, last_seen)"
        " VALUES (1, 'python.testing', 'pattern', 1, 'medium', '2026-03-01T00:00:00Z')"
    )
    conn.execute(
        "INSERT INTO quizzes (id, skill_id, project_id, level, status, created_at)"
        " VALUES ('q1', 'python.testing', 'p1', 'intermediate', 'open', '2026-03-01T00:00:00Z')"
    )
    conn.execute(
        "INSERT INTO quiz_questions (quiz_id, ordinal, kind, prompt, reference_answer, rubric, source_file, grounding)"
        " VALUES ('q1', 1, 'explain', 'prompt', 'ref', '[]', NULL, 'unspecified')"
    )
    conn.execute(
        "INSERT INTO quiz_answers (quiz_id, ordinal, learner_answer, score, hints_used, created_at)"
        " VALUES ('q1', 1, 'answer', 1.0, 0, '2026-03-01T00:00:00Z')"
    )
    conn.execute("INSERT INTO intent_files (intent_id, path, touched) VALUES ('i1', 'src/main.py', 1)")
    conn.execute(
        "INSERT INTO learner_profile (id, level, goal, session_minutes, audience, updated_at)"
        " VALUES (1, 'beginner', 'both', 5, 'self', '2026-03-01T00:00:00Z')"
    )
    conn.execute(
        "INSERT INTO knowledge_items (id, project_id, key, title, kind, band, summary, status, depth, baseline_commit, baseline_committed_at, created_at, updated_at)"
        " VALUES ('k1', 'p1', 'core', 'Core', 'component', 'basic', 'Summary', 'explained', 1, 'c1', '2026-03-01T00:00:00Z', '2026-03-01T00:00:00Z', '2026-03-01T00:00:00Z')"
    )
    conn.execute("INSERT INTO item_files (item_id, path) VALUES ('k1', 'src/main.py')")
    conn.execute("INSERT INTO item_tags (item_id, tag) VALUES ('k1', 'core')")
    conn.execute(
        "INSERT INTO explanations (id, item_id, audience, depth, learner_text, score, created_at)"
        " VALUES (1, 'k1', 'self', 1, 'Learner explanation', 1.0, '2026-03-01T00:00:00Z')"
    )
    conn.execute(
        "INSERT INTO item_reviews (item_id, interval_days, ease, reps, due_at, snoozed_until, last_reviewed_at)"
        " VALUES ('k1', 1, 2.3, 0, '2026-03-02T00:00:00Z', NULL, '2026-03-01T00:00:00Z')"
    )
    conn.execute(
        "INSERT INTO item_questions (id, item_id, question, depth, created_at)"
        " VALUES (1, 'k1', 'Question?', 1, '2026-03-01T00:00:00Z')"
    )
    conn.commit()

    all_21_tables = [
        "projects",
        "skills",
        "intents",
        "intent_skills",
        "commits",
        "events",
        "decisions",
        "attempts",
        "skill_mastery",
        "mistakes",
        "quizzes",
        "quiz_questions",
        "quiz_answers",
        "intent_files",
        "learner_profile",
        "knowledge_items",
        "item_files",
        "item_tags",
        "explanations",
        "item_reviews",
        "item_questions",
    ]
    for tbl in all_21_tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        assert count > 0, f"Table {tbl} had no rows in v8 DB"

    # Migrate v8 -> v9
    migrate(conn, db_path)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 14

    # Verify all 21 tables still have rows
    for tbl in all_21_tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        assert count > 0, f"Table {tbl} lost data during v8->v9 migration"

    # Verify commits.kind defaults to 'commit'
    c1 = conn.execute("SELECT * FROM commits WHERE sha='c1'").fetchone()
    assert c1["kind"] == "commit"

    # Test inserting a snapshot commit
    conn.execute(
        "INSERT INTO commits (sha, project_id, message, files, committed_at, status, origin, kind)"
        " VALUES ('snap1', 'p1', 'snapshot 1', '[]', '2026-03-01T00:00:00Z', 'new', 'backfill', 'snapshot')"
    )
    conn.commit()
    snap = conn.execute("SELECT * FROM commits WHERE sha='snap1'").fetchone()
    assert snap["kind"] == "snapshot"

    # Test inserting a second snapshot commit for same project triggers unique constraint
    import pytest
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO commits (sha, project_id, message, files, committed_at, status, origin, kind)"
            " VALUES ('snap2', 'p1', 'snapshot 2', '[]', '2026-03-01T00:00:00Z', 'new', 'backfill', 'snapshot')"
        )

    # Test CHECK constraint on kind
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO commits (sha, project_id, message, files, committed_at, status, origin, kind)"
            " VALUES ('c_invalid', 'p1', 'invalid kind', '[]', '2026-03-01T00:00:00Z', 'new', 'hook', 'invalid_kind')"
        )

    conn.close()


def test_migration_009_to_010_cleans_legacy_snapshots(tmp_path: Path):
    db_path = tmp_path / "v9_to_v10.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")

    _build_v2_database(conn)
    conn.execute("CREATE TABLE intent_files (intent_id TEXT NOT NULL REFERENCES intents(id) ON DELETE CASCADE, path TEXT NOT NULL, touched INTEGER, PRIMARY KEY (intent_id, path));")
    conn.execute("ALTER TABLE quiz_questions ADD COLUMN source_file TEXT;")
    conn.execute("ALTER TABLE quiz_questions ADD COLUMN grounding TEXT NOT NULL DEFAULT 'unspecified' CHECK (grounding IN ('project','generic','unspecified'));")
    conn.execute("ALTER TABLE skills ADD COLUMN source TEXT NOT NULL DEFAULT 'seed' CHECK (source IN ('seed','proposed'));")
    conn.execute("ALTER TABLE skills ADD COLUMN proposed_at TEXT;")
    conn.execute("ALTER TABLE skills ADD COLUMN rationale TEXT;")
    conn.execute("ALTER TABLE commits ADD COLUMN origin TEXT NOT NULL DEFAULT 'hook' CHECK (origin IN ('hook','backfill'));")
    conn.execute("CREATE TABLE learner_profile (id INTEGER PRIMARY KEY CHECK (id = 1), level TEXT NOT NULL CHECK (level IN ('school', 'beginner', 'junior', 'mid', 'senior')), goal TEXT NOT NULL CHECK (goal IN ('learn', 'interview', 'both')), session_minutes INTEGER NOT NULL CHECK (session_minutes >= 3 AND session_minutes <= 30), audience TEXT NOT NULL CHECK (audience IN ('self', 'classmate', 'recruiter', 'tech-lead')), updated_at TEXT NOT NULL);")
    conn.execute("CREATE TABLE knowledge_items (id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE, key TEXT NOT NULL, title TEXT NOT NULL, kind TEXT NOT NULL CHECK (kind IN ('component', 'decision', 'concept', 'bug-fix')), band TEXT NOT NULL CHECK (band IN ('basic', 'intermediate', 'advanced')), summary TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'unexplained' CHECK (status IN ('unexplained', 'shaky', 'explained')), depth INTEGER NOT NULL DEFAULT 1 CHECK (depth >= 1 AND depth <= 5), baseline_commit TEXT REFERENCES commits(sha) ON DELETE SET NULL, baseline_committed_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, UNIQUE (project_id, key));")
    conn.execute("CREATE TABLE item_files (item_id TEXT NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE, path TEXT NOT NULL, PRIMARY KEY (item_id, path));")
    conn.execute("CREATE TABLE item_tags (item_id TEXT NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE, tag TEXT NOT NULL, PRIMARY KEY (item_id, tag));")
    conn.execute("CREATE TABLE explanations (id INTEGER PRIMARY KEY AUTOINCREMENT, item_id TEXT NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE, audience TEXT NOT NULL CHECK (audience IN ('self', 'classmate', 'recruiter', 'tech-lead')), depth INTEGER NOT NULL CHECK (depth >= 1 AND depth <= 5), learner_text TEXT NOT NULL, score REAL NOT NULL CHECK (score >= 0.0 AND score <= 1.0), created_at TEXT NOT NULL);")
    conn.execute("ALTER TABLE projects ADD COLUMN last_briefing_at TEXT;")
    conn.execute("CREATE TABLE item_reviews (item_id TEXT PRIMARY KEY REFERENCES knowledge_items(id) ON DELETE CASCADE, interval_days INTEGER NOT NULL CHECK (interval_days >= 1), ease REAL NOT NULL CHECK (ease >= 1.3), reps INTEGER NOT NULL CHECK (reps >= 0), due_at TEXT NOT NULL, snoozed_until TEXT, last_reviewed_at TEXT);")
    conn.execute("CREATE TABLE item_questions (id INTEGER PRIMARY KEY AUTOINCREMENT, item_id TEXT NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE, question TEXT NOT NULL, format TEXT NOT NULL CHECK (format IN ('explain', 'predict', 'spot-the-bug', 'defend', 'what-if')), created_at TEXT NOT NULL);")
    conn.execute("ALTER TABLE commits ADD COLUMN kind TEXT NOT NULL DEFAULT 'commit' CHECK (kind IN ('commit','snapshot'));")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_commits_project_snapshot ON commits(project_id) WHERE kind = 'snapshot';")
    conn.execute("PRAGMA user_version=9")
    conn.commit()

    # Populate project p1 with 2 legacy snapshots (kind='commit', origin='hook')
    # and reference the older snapshot with an event and a knowledge item
    conn.execute("INSERT INTO projects (id, name, repo_path, created_at) VALUES ('p1', 'P1', '/repo1', '2026-03-01T00:00:00Z')")
    conn.execute("INSERT INTO skills (id, name) VALUES ('s1', 'Skill 1')")
    conn.execute("INSERT INTO intents (id, project_id, summary, rationale, created_at) VALUES ('i1', 'p1', 's', 'r', '2026-03-01T00:00:00Z')")
    conn.execute("INSERT INTO commits (sha, project_id, message, files, committed_at, status, origin, kind) VALUES ('old_snap', 'p1', 'learnloop: tracked files snapshot', '[]', '2026-03-01T00:00:00Z', 'verified', 'hook', 'commit')")
    conn.execute("INSERT INTO commits (sha, project_id, message, files, committed_at, status, origin, kind) VALUES ('new_snap', 'p1', 'learnloop: tracked files snapshot', '[]', '2026-03-02T00:00:00Z', 'new', 'hook', 'commit')")
    conn.execute("INSERT INTO commits (sha, project_id, message, files, committed_at, status, origin, kind) VALUES ('real_c', 'p1', 'feat: work', '[]', '2026-03-03T00:00:00Z', 'verified', 'hook', 'commit')")
    conn.execute("INSERT INTO events (project_id, skill_id, commit_sha, intent_id, created_at) VALUES ('p1', 's1', 'old_snap', 'i1', '2026-03-01T00:00:00Z')")
    conn.execute("INSERT INTO knowledge_items (id, project_id, key, title, kind, band, summary, status, depth, baseline_commit, created_at, updated_at) VALUES ('k1', 'p1', 'k1', 'K1', 'component', 'basic', 'sum', 'explained', 1, 'old_snap', '2026-03-01T00:00:00Z', '2026-03-01T00:00:00Z')")
    conn.commit()

    # Migrate to v10+
    migrate(conn, db_path)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 14

    # Check foreign keys pass
    fk_errors = conn.execute("PRAGMA foreign_key_check").fetchall()
    assert len(fk_errors) == 0

    # Old snapshot was deleted!
    assert conn.execute("SELECT 1 FROM commits WHERE sha='old_snap'").fetchone() is None

    # New snapshot was kept, updated to kind='snapshot', origin='backfill'
    ns = conn.execute("SELECT * FROM commits WHERE sha='new_snap'").fetchone()
    assert ns["kind"] == "snapshot"
    assert ns["origin"] == "backfill"

    # Event and knowledge item now reference new_snap
    ev = conn.execute("SELECT * FROM events WHERE intent_id='i1'").fetchone()
    assert ev["commit_sha"] == "new_snap"

    ki = conn.execute("SELECT * FROM knowledge_items WHERE id='k1'").fetchone()
    assert ki["baseline_commit"] == "new_snap"

    # Real commit was untouched
    rc = conn.execute("SELECT * FROM commits WHERE sha='real_c'").fetchone()
    assert rc["kind"] == "commit"
    assert rc["origin"] == "hook"
    conn.close()


def test_migration_010_to_011_project_scoping_and_ratings(tmp_path: Path):
    db_path = tmp_path / "v10_to_v11.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")

    _build_v2_database(conn)
    conn.execute("CREATE TABLE intent_files (intent_id TEXT NOT NULL REFERENCES intents(id) ON DELETE CASCADE, path TEXT NOT NULL, touched INTEGER, PRIMARY KEY (intent_id, path));")
    conn.execute("ALTER TABLE quiz_questions ADD COLUMN source_file TEXT;")
    conn.execute("ALTER TABLE quiz_questions ADD COLUMN grounding TEXT NOT NULL DEFAULT 'unspecified' CHECK (grounding IN ('project','generic','unspecified'));")
    conn.execute("ALTER TABLE skills ADD COLUMN source TEXT NOT NULL DEFAULT 'seed' CHECK (source IN ('seed','proposed'));")
    conn.execute("ALTER TABLE skills ADD COLUMN proposed_at TEXT;")
    conn.execute("ALTER TABLE skills ADD COLUMN rationale TEXT;")
    conn.execute("ALTER TABLE commits ADD COLUMN origin TEXT NOT NULL DEFAULT 'hook' CHECK (origin IN ('hook','backfill'));")
    conn.execute("CREATE TABLE learner_profile (id INTEGER PRIMARY KEY CHECK (id = 1), level TEXT NOT NULL CHECK (level IN ('school', 'beginner', 'junior', 'mid', 'senior')), goal TEXT NOT NULL CHECK (goal IN ('learn', 'interview', 'both')), session_minutes INTEGER NOT NULL CHECK (session_minutes >= 3 AND session_minutes <= 30), audience TEXT NOT NULL CHECK (audience IN ('self', 'classmate', 'recruiter', 'tech-lead')), updated_at TEXT NOT NULL);")
    conn.execute("CREATE TABLE knowledge_items (id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE, key TEXT NOT NULL, title TEXT NOT NULL, kind TEXT NOT NULL CHECK (kind IN ('component', 'decision', 'concept', 'bug-fix')), band TEXT NOT NULL CHECK (band IN ('basic', 'intermediate', 'advanced')), summary TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'unexplained' CHECK (status IN ('unexplained', 'shaky', 'explained')), depth INTEGER NOT NULL DEFAULT 1 CHECK (depth >= 1 AND depth <= 5), baseline_commit TEXT REFERENCES commits(sha) ON DELETE SET NULL, baseline_committed_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, UNIQUE (project_id, key));")
    conn.execute("CREATE TABLE item_files (item_id TEXT NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE, path TEXT NOT NULL, PRIMARY KEY (item_id, path));")
    conn.execute("CREATE TABLE item_tags (item_id TEXT NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE, tag TEXT NOT NULL, PRIMARY KEY (item_id, tag));")
    conn.execute("CREATE TABLE explanations (id INTEGER PRIMARY KEY AUTOINCREMENT, item_id TEXT NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE, audience TEXT NOT NULL CHECK (audience IN ('self', 'classmate', 'recruiter', 'tech-lead')), depth INTEGER NOT NULL CHECK (depth >= 1 AND depth <= 5), learner_text TEXT NOT NULL, score REAL NOT NULL CHECK (score >= 0.0 AND score <= 1.0), created_at TEXT NOT NULL);")
    conn.execute("ALTER TABLE projects ADD COLUMN last_briefing_at TEXT;")
    conn.execute("CREATE TABLE item_reviews (item_id TEXT PRIMARY KEY REFERENCES knowledge_items(id) ON DELETE CASCADE, interval_days INTEGER NOT NULL CHECK (interval_days >= 1), ease REAL NOT NULL CHECK (ease >= 1.3), reps INTEGER NOT NULL CHECK (reps >= 0), due_at TEXT NOT NULL, snoozed_until TEXT, last_reviewed_at TEXT);")
    conn.execute("CREATE TABLE item_questions (id INTEGER PRIMARY KEY AUTOINCREMENT, item_id TEXT NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE, question TEXT NOT NULL, format TEXT NOT NULL CHECK (format IN ('explain', 'predict', 'spot-the-bug', 'defend', 'what-if')), created_at TEXT NOT NULL);")
    conn.execute("ALTER TABLE commits ADD COLUMN kind TEXT NOT NULL DEFAULT 'commit' CHECK (kind IN ('commit','snapshot'));")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_commits_project_snapshot ON commits(project_id) WHERE kind = 'snapshot';")
    conn.execute("PRAGMA user_version=10")
    conn.commit()

    conn.execute("INSERT INTO projects (id, name, repo_path, created_at) VALUES ('p1', 'P1', '/repo1', '2026-03-01T00:00:00Z')")
    conn.execute("INSERT INTO knowledge_items (id, project_id, key, title, kind, band, summary, status, depth, created_at, updated_at) VALUES ('k1', 'p1', 'k1', 'K1', 'component', 'basic', 'sum', 'explained', 1, '2026-03-01T00:00:00Z', '2026-03-01T00:00:00Z')")
    conn.execute("INSERT INTO explanations (id, item_id, audience, depth, learner_text, score, created_at) VALUES (1, 'k1', 'self', 1, 'text', 1.0, '2026-03-01T00:00:00Z')")
    conn.commit()

    migrate(conn, db_path)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 14

    # Verify project_profile table exists and works
    conn.execute(
        "INSERT INTO project_profile (project_id, level, goal, audience, session_minutes, updated_at)"
        " VALUES ('p1', 'senior', 'interview', 'tech-lead', 10, '2026-03-01T00:00:00Z')"
    )
    pp = conn.execute("SELECT * FROM project_profile WHERE project_id='p1'").fetchone()
    assert pp["level"] == "senior"

    # Verify explanations.self_rating works
    exp1 = conn.execute("SELECT * FROM explanations WHERE id=1").fetchone()
    assert "self_rating" in exp1.keys()
    assert exp1["self_rating"] is None

    conn.execute(
        "INSERT INTO explanations (item_id, audience, depth, learner_text, score, self_rating, created_at)"
        " VALUES ('k1', 'self', 1, 'new text', 0.9, 4, '2026-03-02T00:00:00Z')"
    )
    conn.commit()

    import pytest
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO explanations (item_id, audience, depth, learner_text, score, self_rating, created_at)"
            " VALUES ('k1', 'self', 1, 'bad rating', 0.9, 6, '2026-03-02T00:00:00Z')"
        )

    conn.close()


def test_migration_011_to_012_project_technologies(tmp_path: Path):
    db_path = tmp_path / "v11_to_v12.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")

    _build_v2_database(conn)
    conn.execute("CREATE TABLE intent_files (intent_id TEXT NOT NULL REFERENCES intents(id) ON DELETE CASCADE, path TEXT NOT NULL, touched INTEGER, PRIMARY KEY (intent_id, path));")
    conn.execute("ALTER TABLE quiz_questions ADD COLUMN source_file TEXT;")
    conn.execute("ALTER TABLE quiz_questions ADD COLUMN grounding TEXT NOT NULL DEFAULT 'unspecified' CHECK (grounding IN ('project','generic','unspecified'));")
    conn.execute("ALTER TABLE skills ADD COLUMN source TEXT NOT NULL DEFAULT 'seed' CHECK (source IN ('seed','proposed'));")
    conn.execute("ALTER TABLE skills ADD COLUMN proposed_at TEXT;")
    conn.execute("ALTER TABLE skills ADD COLUMN rationale TEXT;")
    conn.execute("ALTER TABLE commits ADD COLUMN origin TEXT NOT NULL DEFAULT 'hook' CHECK (origin IN ('hook','backfill'));")
    conn.execute("CREATE TABLE learner_profile (id INTEGER PRIMARY KEY CHECK (id = 1), level TEXT NOT NULL CHECK (level IN ('school', 'beginner', 'junior', 'mid', 'senior')), goal TEXT NOT NULL CHECK (goal IN ('learn', 'interview', 'both')), session_minutes INTEGER NOT NULL CHECK (session_minutes >= 3 AND session_minutes <= 30), audience TEXT NOT NULL CHECK (audience IN ('self', 'classmate', 'recruiter', 'tech-lead')), updated_at TEXT NOT NULL);")
    conn.execute("CREATE TABLE knowledge_items (id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE, key TEXT NOT NULL, title TEXT NOT NULL, kind TEXT NOT NULL CHECK (kind IN ('component', 'decision', 'concept', 'bug-fix')), band TEXT NOT NULL CHECK (band IN ('basic', 'intermediate', 'advanced')), summary TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'unexplained' CHECK (status IN ('unexplained', 'shaky', 'explained')), depth INTEGER NOT NULL DEFAULT 1 CHECK (depth >= 1 AND depth <= 5), baseline_commit TEXT REFERENCES commits(sha) ON DELETE SET NULL, baseline_committed_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, UNIQUE (project_id, key));")
    conn.execute("CREATE TABLE item_files (item_id TEXT NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE, path TEXT NOT NULL, PRIMARY KEY (item_id, path));")
    conn.execute("CREATE TABLE item_tags (item_id TEXT NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE, tag TEXT NOT NULL, PRIMARY KEY (item_id, tag));")
    conn.execute("CREATE TABLE explanations (id INTEGER PRIMARY KEY AUTOINCREMENT, item_id TEXT NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE, audience TEXT NOT NULL CHECK (audience IN ('self', 'classmate', 'recruiter', 'tech-lead')), depth INTEGER NOT NULL CHECK (depth >= 1 AND depth <= 5), learner_text TEXT NOT NULL, score REAL NOT NULL CHECK (score >= 0.0 AND score <= 1.0), self_rating INTEGER NULL CHECK (self_rating BETWEEN 1 AND 5), created_at TEXT NOT NULL);")
    conn.execute("ALTER TABLE projects ADD COLUMN last_briefing_at TEXT;")
    conn.execute("CREATE TABLE item_reviews (item_id TEXT PRIMARY KEY REFERENCES knowledge_items(id) ON DELETE CASCADE, interval_days INTEGER NOT NULL CHECK (interval_days >= 1), ease REAL NOT NULL CHECK (ease >= 1.3), reps INTEGER NOT NULL CHECK (reps >= 0), due_at TEXT NOT NULL, snoozed_until TEXT, last_reviewed_at TEXT);")
    conn.execute("CREATE TABLE item_questions (id INTEGER PRIMARY KEY AUTOINCREMENT, item_id TEXT NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE, question TEXT NOT NULL, format TEXT NOT NULL CHECK (format IN ('explain', 'predict', 'spot-the-bug', 'defend', 'what-if')), created_at TEXT NOT NULL);")
    conn.execute("ALTER TABLE commits ADD COLUMN kind TEXT NOT NULL DEFAULT 'commit' CHECK (kind IN ('commit','snapshot'));")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_commits_project_snapshot ON commits(project_id) WHERE kind = 'snapshot';")
    conn.execute("CREATE TABLE project_profile (project_id TEXT PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE, level TEXT NULL, goal TEXT NULL, session_minutes INTEGER NULL, audience TEXT NULL, updated_at TEXT NOT NULL);")
    conn.execute("PRAGMA user_version=11")
    conn.commit()

    conn.execute("INSERT INTO projects (id, name, repo_path, created_at) VALUES ('p1', 'P1', '/repo1', '2026-03-01T00:00:00Z')")
    conn.commit()

    migrate(conn, db_path)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 14

    # Verify project_technologies table exists and works
    conn.execute(
        "INSERT INTO project_technologies (project_id, ecosystem, name, version_spec, source_file, detected_at)"
        " VALUES ('p1', 'python', 'fastapi', '>=0.100.0', 'pyproject.toml', '2026-03-01T00:00:00Z')"
    )
    tech = conn.execute("SELECT * FROM project_technologies WHERE project_id='p1'").fetchone()
    assert tech["ecosystem"] == "python"
    assert tech["name"] == "fastapi"
    assert tech["version_spec"] == ">=0.100.0"

    # Verify foreign key cascade delete
    conn.execute("DELETE FROM projects WHERE id='p1'")
    conn.commit()
    assert conn.execute("SELECT COUNT(*) FROM project_technologies").fetchone()[0] == 0

    conn.close()


def test_migration_012_to_013_project_facts(tmp_path: Path):
    db_path = tmp_path / "v12_to_v13.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")

    _build_v2_database(conn)
    conn.execute("CREATE TABLE intent_files (intent_id TEXT NOT NULL REFERENCES intents(id) ON DELETE CASCADE, path TEXT NOT NULL, touched INTEGER, PRIMARY KEY (intent_id, path));")
    conn.execute("ALTER TABLE quiz_questions ADD COLUMN source_file TEXT;")
    conn.execute("ALTER TABLE quiz_questions ADD COLUMN grounding TEXT NOT NULL DEFAULT 'unspecified' CHECK (grounding IN ('project','generic','unspecified'));")
    conn.execute("ALTER TABLE skills ADD COLUMN source TEXT NOT NULL DEFAULT 'seed' CHECK (source IN ('seed','proposed'));")
    conn.execute("ALTER TABLE skills ADD COLUMN proposed_at TEXT;")
    conn.execute("ALTER TABLE skills ADD COLUMN rationale TEXT;")
    conn.execute("ALTER TABLE commits ADD COLUMN origin TEXT NOT NULL DEFAULT 'hook' CHECK (origin IN ('hook','backfill'));")
    conn.execute("CREATE TABLE learner_profile (id INTEGER PRIMARY KEY CHECK (id = 1), level TEXT NOT NULL CHECK (level IN ('school', 'beginner', 'junior', 'mid', 'senior')), goal TEXT NOT NULL CHECK (goal IN ('learn', 'interview', 'both')), session_minutes INTEGER NOT NULL CHECK (session_minutes >= 3 AND session_minutes <= 30), audience TEXT NOT NULL CHECK (audience IN ('self', 'classmate', 'recruiter', 'tech-lead')), updated_at TEXT NOT NULL);")
    conn.execute("CREATE TABLE knowledge_items (id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE, key TEXT NOT NULL, title TEXT NOT NULL, kind TEXT NOT NULL CHECK (kind IN ('component', 'decision', 'concept', 'bug-fix')), band TEXT NOT NULL CHECK (band IN ('basic', 'intermediate', 'advanced')), summary TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'unexplained' CHECK (status IN ('unexplained', 'shaky', 'explained')), depth INTEGER NOT NULL DEFAULT 1 CHECK (depth >= 1 AND depth <= 5), baseline_commit TEXT REFERENCES commits(sha) ON DELETE SET NULL, baseline_committed_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, UNIQUE (project_id, key));")
    conn.execute("CREATE TABLE item_files (item_id TEXT NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE, path TEXT NOT NULL, PRIMARY KEY (item_id, path));")
    conn.execute("CREATE TABLE item_tags (item_id TEXT NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE, tag TEXT NOT NULL, PRIMARY KEY (item_id, tag));")
    conn.execute("CREATE TABLE explanations (id INTEGER PRIMARY KEY AUTOINCREMENT, item_id TEXT NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE, audience TEXT NOT NULL CHECK (audience IN ('self', 'classmate', 'recruiter', 'tech-lead')), depth INTEGER NOT NULL CHECK (depth >= 1 AND depth <= 5), learner_text TEXT NOT NULL, score REAL NOT NULL CHECK (score >= 0.0 AND score <= 1.0), self_rating INTEGER NULL CHECK (self_rating BETWEEN 1 AND 5), created_at TEXT NOT NULL);")
    conn.execute("ALTER TABLE projects ADD COLUMN last_briefing_at TEXT;")
    conn.execute("CREATE TABLE item_reviews (item_id TEXT PRIMARY KEY REFERENCES knowledge_items(id) ON DELETE CASCADE, interval_days INTEGER NOT NULL CHECK (interval_days >= 1), ease REAL NOT NULL CHECK (ease >= 1.3), reps INTEGER NOT NULL CHECK (reps >= 0), due_at TEXT NOT NULL, snoozed_until TEXT, last_reviewed_at TEXT);")
    conn.execute("CREATE TABLE item_questions (id INTEGER PRIMARY KEY AUTOINCREMENT, item_id TEXT NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE, question TEXT NOT NULL, format TEXT NOT NULL CHECK (format IN ('explain', 'predict', 'spot-the-bug', 'defend', 'what-if')), created_at TEXT NOT NULL);")
    conn.execute("ALTER TABLE commits ADD COLUMN kind TEXT NOT NULL DEFAULT 'commit' CHECK (kind IN ('commit','snapshot'));")
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_commits_project_snapshot ON commits(project_id) WHERE kind = 'snapshot';")
    conn.execute("CREATE TABLE project_profile (project_id TEXT PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE, level TEXT NULL, goal TEXT NULL, session_minutes INTEGER NULL, audience TEXT NULL, updated_at TEXT NOT NULL);")
    conn.execute("CREATE TABLE project_technologies (id INTEGER PRIMARY KEY AUTOINCREMENT, project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE, ecosystem TEXT NOT NULL CHECK (ecosystem IN ('python', 'npm', 'go', 'cargo', 'docker')), name TEXT NOT NULL, version_spec TEXT, source_file TEXT NOT NULL, detected_at TEXT NOT NULL, UNIQUE (project_id, ecosystem, name));")
    conn.execute("CREATE INDEX idx_project_technologies_proj ON project_technologies(project_id);")
    conn.execute("PRAGMA user_version=12")
    conn.commit()

    conn.execute("INSERT INTO projects (id, name, repo_path, created_at) VALUES ('p1', 'P1', '/repo1', '2026-03-01T00:00:00Z')")
    conn.commit()

    migrate(conn, db_path)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == 14

    # Verify project_facts table exists and works
    conn.execute(
        "INSERT INTO project_facts (id, project_id, topic, fact, source_url, source_title, retrieved_at, technology, fact_hash, created_at)"
        " VALUES ('f1', 'p1', 'Testing', 'Pytest rocks', 'https://docs.pytest.org/en/stable/', 'Pytest Docs', '2026-03-01T00:00:00Z', 'pytest', 'abc123hash', '2026-03-01T00:00:00Z')"
    )
    fact = conn.execute("SELECT * FROM project_facts WHERE id='f1'").fetchone()
    assert fact["topic"] == "Testing"
    assert fact["fact"] == "Pytest rocks"
    assert fact["source_url"] == "https://docs.pytest.org/en/stable/"
    assert fact["technology"] == "pytest"

    # Verify UNIQUE(project_id, source_url, fact_hash) constraint
    import pytest
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO project_facts (id, project_id, topic, fact, source_url, source_title, retrieved_at, technology, fact_hash, created_at)"
            " VALUES ('f2', 'p1', 'Testing', 'Pytest rocks duplicate', 'https://docs.pytest.org/en/stable/', 'Pytest Docs', '2026-03-01T00:00:00Z', 'pytest', 'abc123hash', '2026-03-01T00:00:00Z')"
        )

    # Verify foreign key cascade delete
    conn.execute("DELETE FROM projects WHERE id='p1'")
    conn.commit()
    assert conn.execute("SELECT COUNT(*) FROM project_facts").fetchone()[0] == 0

    conn.close()
