CREATE TABLE item_reviews (
  item_id TEXT PRIMARY KEY REFERENCES knowledge_items(id) ON DELETE CASCADE,
  interval_days INTEGER NOT NULL DEFAULT 1 CHECK (interval_days >= 1),
  ease REAL NOT NULL DEFAULT 2.3 CHECK (ease BETWEEN 1.3 AND 3.0),
  reps INTEGER NOT NULL DEFAULT 0 CHECK (reps >= 0),
  due_at TEXT NOT NULL,
  snoozed_until TEXT NULL,
  last_reviewed_at TEXT NULL
);

CREATE TABLE item_questions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  item_id TEXT NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE,
  question TEXT NOT NULL,
  depth INTEGER NOT NULL CHECK (depth BETWEEN 1 AND 5),
  created_at TEXT NOT NULL
);

ALTER TABLE projects ADD COLUMN last_briefing_at TEXT NULL;
