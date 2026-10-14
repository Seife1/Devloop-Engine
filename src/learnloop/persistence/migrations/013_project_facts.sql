-- Migration 013: Sourced Did You Know project facts
CREATE TABLE project_facts (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  topic TEXT NOT NULL,
  fact TEXT NOT NULL,
  source_url TEXT NOT NULL,
  source_title TEXT NOT NULL,
  retrieved_at TEXT NOT NULL,
  technology TEXT,
  fact_hash TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE (project_id, source_url, fact_hash)
);

CREATE INDEX idx_project_facts_project ON project_facts(project_id);
CREATE INDEX idx_project_facts_retrieved ON project_facts(project_id, retrieved_at);
