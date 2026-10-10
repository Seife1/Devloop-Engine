CREATE TABLE learner_profile (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  level TEXT NOT NULL DEFAULT 'beginner' CHECK (level IN ('school','beginner','junior','mid','senior')),
  goal TEXT NOT NULL DEFAULT 'both' CHECK (goal IN ('learn','interview','both')),
  session_minutes INTEGER NOT NULL DEFAULT 5 CHECK (session_minutes BETWEEN 3 AND 30),
  audience TEXT NOT NULL DEFAULT 'self' CHECK (audience IN ('self','classmate','recruiter','tech-lead')),
  updated_at TEXT NOT NULL
);

INSERT OR IGNORE INTO learner_profile (id, level, goal, session_minutes, audience, updated_at)
VALUES (1, 'beginner', 'both', 5, 'self', '2026-01-01T00:00:00Z');

CREATE TABLE knowledge_items (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id),
  key TEXT NOT NULL,
  title TEXT NOT NULL,
  kind TEXT NOT NULL CHECK (kind IN ('component','decision','concept','bug-fix')),
  band TEXT NOT NULL CHECK (band IN ('basic','intermediate','advanced')),
  summary TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'unexplained' CHECK (status IN ('unexplained','shaky','explained')),
  depth INTEGER NOT NULL DEFAULT 1 CHECK (depth BETWEEN 1 AND 5),
  baseline_commit TEXT NULL,
  baseline_committed_at TEXT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE (project_id, key)
);

CREATE TABLE item_files (
  item_id TEXT NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE,
  path TEXT NOT NULL,
  PRIMARY KEY (item_id, path)
);

CREATE TABLE item_tags (
  item_id TEXT NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE,
  tag TEXT NOT NULL,
  PRIMARY KEY (item_id, tag)
);

CREATE TABLE explanations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id TEXT NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE,
  audience TEXT NOT NULL,
  depth INTEGER NOT NULL CHECK (depth BETWEEN 1 AND 5),
  learner_text TEXT NOT NULL,
  score REAL NOT NULL CHECK (score BETWEEN 0.0 AND 1.0),
  created_at TEXT NOT NULL
);
