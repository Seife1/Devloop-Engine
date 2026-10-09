ALTER TABLE quiz_questions ADD COLUMN source_file TEXT;
ALTER TABLE quiz_questions ADD COLUMN grounding TEXT NOT NULL DEFAULT 'unspecified' CHECK (grounding IN ('project','generic','unspecified'));
