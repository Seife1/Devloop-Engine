ALTER TABLE commits ADD COLUMN kind TEXT NOT NULL DEFAULT 'commit' CHECK (kind IN ('commit','snapshot'));
CREATE UNIQUE INDEX IF NOT EXISTS idx_commits_project_snapshot ON commits(project_id) WHERE kind = 'snapshot';
