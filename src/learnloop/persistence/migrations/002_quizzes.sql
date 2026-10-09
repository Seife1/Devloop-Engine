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
  rubric TEXT NOT NULL,                  -- JSON array of required points
  PRIMARY KEY (quiz_id, ordinal)
);
-- Audit trail: a score is only accepted together with the learner's own answer text.
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
