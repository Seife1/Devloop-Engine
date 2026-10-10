-- Migration 011: Per-project profile overrides and self-rating on explanations
ALTER TABLE explanations ADD COLUMN self_rating INTEGER NULL CHECK (self_rating BETWEEN 1 AND 5);

CREATE TABLE project_profile (
  project_id TEXT PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
  level TEXT NULL CHECK (level IS NULL OR level IN ('school', 'beginner', 'junior', 'mid', 'senior')),
  goal TEXT NULL CHECK (goal IS NULL OR goal IN ('learn', 'interview', 'both')),
  session_minutes INTEGER NULL CHECK (session_minutes IS NULL OR session_minutes BETWEEN 3 AND 30),
  audience TEXT NULL CHECK (audience IS NULL OR audience IN ('self', 'classmate', 'recruiter', 'tech-lead')),
  updated_at TEXT NOT NULL
);
