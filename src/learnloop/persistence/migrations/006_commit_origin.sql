ALTER TABLE commits ADD COLUMN origin TEXT NOT NULL DEFAULT 'hook' CHECK (origin IN ('hook','backfill'));
