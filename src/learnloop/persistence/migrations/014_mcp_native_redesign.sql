-- Migration 014: MCP-Native LearnLoop Plugin Redesign
-- Implements schema for new architecture with ProjectContext, LearningEvent, 
-- IntentRecord, ExposureRecord, KnowledgeItem, and ReviewSchedule models
-- Requirements: 23.1-23.11, 27.1

-- NOTE: This migration is designed to work with existing LearnLoop schemas.
-- Some tables (knowledge_items, explanations) already exist from previous migrations.
-- We extend them rather than recreate them.

-- ============================================================================
-- Technologies table for detected project technologies
-- ============================================================================
CREATE TABLE IF NOT EXISTS technologies (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  name TEXT NOT NULL CHECK (name != ''),
  version TEXT NULL,
  category TEXT NULL,  -- e.g., 'language', 'framework', 'tool'
  detected_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_technologies_project ON technologies(project_id);


-- ============================================================================
-- Learning Events Table (Auto-tracking)
-- ============================================================================
CREATE TABLE IF NOT EXISTS learning_events (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  event_type TEXT NOT NULL CHECK (event_type IN ('implementation', 'decision', 'question', 'explanation')),
  source TEXT NOT NULL CHECK (source IN ('conversation', 'commit', 'manual')),
  timestamp TEXT NOT NULL,
  content_json TEXT NOT NULL,  -- JSON dict with type-specific content
  skills_json TEXT NOT NULL,   -- JSON array of skill IDs
  confidence REAL NOT NULL CHECK (confidence BETWEEN 0.0 AND 1.0),  -- Requirement 23.3
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_learning_events_project ON learning_events(project_id);
CREATE INDEX IF NOT EXISTS idx_learning_events_timestamp ON learning_events(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_learning_events_confidence ON learning_events(confidence);
CREATE INDEX IF NOT EXISTS idx_learning_events_type ON learning_events(project_id, event_type, timestamp DESC);


-- ============================================================================
-- Intent Records Table (Redesigned)
-- ============================================================================
-- New intent tracking for MCP-native workflow
CREATE TABLE IF NOT EXISTS intent_records (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  intent_description TEXT NOT NULL,
  files_json TEXT NOT NULL,  -- JSON array of file paths
  skills_json TEXT NOT NULL, -- JSON array of skill IDs
  status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'matched', 'abandoned')),
  matched_commit_sha TEXT NULL REFERENCES commits(sha),
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  closed_at TEXT NULL,
  
  -- Validation rules (Requirements 23.4, 23.5)
  CHECK (
    (status = 'matched' AND matched_commit_sha IS NOT NULL) OR
    (status != 'matched')
  ),
  CHECK (
    (status != 'open' AND closed_at IS NOT NULL) OR
    (status = 'open')
  )
);
CREATE INDEX IF NOT EXISTS idx_intent_records_project ON intent_records(project_id);
CREATE INDEX IF NOT EXISTS idx_intent_records_status ON intent_records(status);
CREATE INDEX IF NOT EXISTS idx_intent_records_session ON intent_records(session_id);
CREATE INDEX IF NOT EXISTS idx_intent_records_created ON intent_records(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_intent_records_reconciliation ON intent_records(project_id, status, created_at DESC);


-- ============================================================================
-- Exposure Records Table (Verified Learning)
-- ============================================================================
CREATE TABLE IF NOT EXISTS exposure_records (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  intent_id TEXT NOT NULL REFERENCES intent_records(id) ON DELETE CASCADE,
  commit_sha TEXT NOT NULL REFERENCES commits(sha) ON DELETE CASCADE,
  skills_json TEXT NOT NULL,  -- JSON array of skill IDs
  files_json TEXT NOT NULL,   -- JSON array of file paths
  verified_at TEXT NOT NULL DEFAULT (datetime('now')),
  explanation_recorded INTEGER NOT NULL DEFAULT 0 CHECK (explanation_recorded IN (0, 1)),
  explanation_depth REAL NULL CHECK (explanation_depth IS NULL OR (explanation_depth BETWEEN 0.0 AND 1.0)),
  
  -- Validation rules (Requirements 23.6, 23.7)
  CHECK (
    (explanation_recorded = 0) OR
    (explanation_recorded = 1 AND explanation_depth IS NOT NULL)
  ),
  
  UNIQUE (intent_id, commit_sha)  -- Each intent can match at most one commit
);
CREATE INDEX IF NOT EXISTS idx_exposure_records_project ON exposure_records(project_id);
CREATE INDEX IF NOT EXISTS idx_exposure_records_intent ON exposure_records(intent_id);
CREATE INDEX IF NOT EXISTS idx_exposure_records_commit ON exposure_records(commit_sha);
CREATE INDEX IF NOT EXISTS idx_exposure_records_verified ON exposure_records(verified_at DESC);


-- ============================================================================
-- Review Schedules Table (SM-2 Spaced Repetition)
-- ============================================================================
-- New table for MCP-native redesign spaced repetition
CREATE TABLE IF NOT EXISTS review_schedules (
  id TEXT PRIMARY KEY,
  item_id TEXT NOT NULL REFERENCES knowledge_items(id) ON DELETE CASCADE UNIQUE,
  interval INTEGER NOT NULL CHECK (interval >= 1),  -- Days (Requirement 23.10)
  easiness REAL NOT NULL CHECK (easiness BETWEEN 1.3 AND 2.5),  -- SM-2 factor (Requirements 23.9, 15.2)
  repetitions INTEGER NOT NULL DEFAULT 0 CHECK (repetitions >= 0),  -- Requirement 23.11
  success_streak INTEGER NOT NULL DEFAULT 0 CHECK (success_streak >= 0),
  due_at TEXT NOT NULL,
  snoozed_until TEXT NULL,
  last_reviewed_at TEXT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  
  -- Validation rules (Requirements 15.12, 23.10, 23.11)
  CHECK (
    (repetitions = 0) OR
    (repetitions > 0 AND last_reviewed_at IS NOT NULL)
  )
);
CREATE INDEX IF NOT EXISTS idx_review_schedules_due ON review_schedules(due_at);
CREATE INDEX IF NOT EXISTS idx_review_schedules_item ON review_schedules(item_id);
CREATE INDEX IF NOT EXISTS idx_review_schedules_due_query ON review_schedules(due_at, snoozed_until);


-- ============================================================================
-- Queue Entries Table (Commit Processing)
-- ============================================================================
CREATE TABLE IF NOT EXISTS queue_entries (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  commit_sha TEXT NOT NULL REFERENCES commits(sha) ON DELETE CASCADE,
  processed INTEGER NOT NULL DEFAULT 0 CHECK (processed IN (0, 1)),
  processed_at TEXT NULL,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  
  UNIQUE (commit_sha)  -- Idempotent processing
);
CREATE INDEX IF NOT EXISTS idx_queue_entries_project ON queue_entries(project_id);
CREATE INDEX IF NOT EXISTS idx_queue_entries_processed ON queue_entries(processed);
CREATE INDEX IF NOT EXISTS idx_queue_entries_created ON queue_entries(created_at DESC);


-- ============================================================================
-- Additional indexes for performance (Requirement 25.1-25.3)
-- ============================================================================

-- Composite index for session briefing queries
CREATE INDEX IF NOT EXISTS idx_commits_project_status ON commits(project_id, status, committed_at DESC);

-- Note: Staleness indexes on knowledge_items are created by Python migration helper
-- after ensuring the is_stale column exists


-- ============================================================================
-- Migration Metadata
-- ============================================================================
CREATE TABLE IF NOT EXISTS schema_migrations (
  version INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO schema_migrations (version, name) VALUES (14, 'mcp_native_redesign');
