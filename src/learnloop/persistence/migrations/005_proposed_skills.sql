ALTER TABLE skills ADD COLUMN source TEXT NOT NULL DEFAULT 'seed' CHECK (source IN ('seed','proposed'));
ALTER TABLE skills ADD COLUMN proposed_at TEXT;
ALTER TABLE skills ADD COLUMN rationale TEXT;
