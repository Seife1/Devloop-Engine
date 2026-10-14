-- Migration 012: Deterministic project technologies
CREATE TABLE project_technologies (
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  ecosystem TEXT NOT NULL,
  name TEXT NOT NULL,
  version_spec TEXT,
  source_file TEXT NOT NULL,
  detected_at TEXT NOT NULL,
  PRIMARY KEY (project_id, ecosystem, name)
);

CREATE INDEX idx_project_technologies_proj ON project_technologies(project_id);
