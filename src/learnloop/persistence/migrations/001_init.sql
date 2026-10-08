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

-- INTENT: what the agent SAYS it is doing (never counts as exposure by itself)
CREATE TABLE intents (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id),
  summary TEXT NOT NULL,
  rationale TEXT NOT NULL,
  commit_sha TEXT,                       -- optional explicit link
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','verified','abandoned')),
  created_at TEXT NOT NULL
);
CREATE TABLE intent_skills (
  intent_id TEXT NOT NULL REFERENCES intents(id) ON DELETE CASCADE,
  skill_id TEXT NOT NULL REFERENCES skills(id),
  PRIMARY KEY (intent_id, skill_id)
);

-- OUTCOME: what the git hook says actually changed (metadata only, redacted)
CREATE TABLE commits (
  sha TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id),
  message TEXT NOT NULL,
  files TEXT NOT NULL,                   -- JSON array of paths
  committed_at TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'new' CHECK (status IN ('new','verified','unexplained'))
);

-- VERIFIED EVENT = exposure. Only created when intent and outcome agree.
CREATE TABLE events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  project_id TEXT NOT NULL REFERENCES projects(id),
  skill_id TEXT NOT NULL REFERENCES skills(id),
  commit_sha TEXT NOT NULL REFERENCES commits(sha),
  intent_id TEXT NOT NULL REFERENCES intents(id),
  created_at TEXT NOT NULL,
  UNIQUE (commit_sha, skill_id)          -- one commit exposes a skill once
);
CREATE INDEX idx_events_skill ON events(skill_id);

CREATE TABLE decisions (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id),
  intent_id TEXT REFERENCES intents(id),
  choice TEXT NOT NULL,
  alternatives TEXT NOT NULL,            -- JSON array
  tradeoffs TEXT NOT NULL,
  created_at TEXT NOT NULL
);

-- MASTERY: moves only from the learner's own attempts
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
