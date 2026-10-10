-- Migration 010: Clean legacy snapshots
-- 1. Deduplicate events before re-pointing to avoid (commit_sha, skill_id) collisions
DELETE FROM events
WHERE commit_sha IN (
    SELECT c_old.sha FROM commits c_old
    WHERE c_old.message = 'learnloop: tracked files snapshot'
      AND c_old.sha != (
          SELECT c_new.sha FROM commits c_new
          WHERE c_new.project_id = events.project_id
            AND c_new.message = 'learnloop: tracked files snapshot'
          ORDER BY c_new.committed_at DESC, c_new.sha DESC LIMIT 1
      )
)
AND skill_id IN (
    SELECT e2.skill_id FROM events e2
    WHERE e2.commit_sha = (
        SELECT c_new.sha FROM commits c_new
        WHERE c_new.project_id = events.project_id
          AND c_new.message = 'learnloop: tracked files snapshot'
        ORDER BY c_new.committed_at DESC, c_new.sha DESC LIMIT 1
    )
);

-- 2. Re-point events referencing older snapshots to newest snapshot for that project
UPDATE events
SET commit_sha = (
    SELECT c_new.sha FROM commits c_new
    WHERE c_new.project_id = events.project_id
      AND c_new.message = 'learnloop: tracked files snapshot'
    ORDER BY c_new.committed_at DESC, c_new.sha DESC LIMIT 1
)
WHERE commit_sha IN (
    SELECT c_old.sha FROM commits c_old
    WHERE c_old.message = 'learnloop: tracked files snapshot'
);

-- 3. Re-point knowledge_items referencing older snapshots to newest snapshot for that project
UPDATE knowledge_items
SET baseline_commit = (
    SELECT c_new.sha FROM commits c_new
    WHERE c_new.project_id = knowledge_items.project_id
      AND c_new.message = 'learnloop: tracked files snapshot'
    ORDER BY c_new.committed_at DESC, c_new.sha DESC LIMIT 1
)
WHERE baseline_commit IN (
    SELECT c_old.sha FROM commits c_old
    WHERE c_old.message = 'learnloop: tracked files snapshot'
);

-- 4. Delete older snapshot rows that are not the newest for that project
DELETE FROM commits
WHERE message = 'learnloop: tracked files snapshot'
  AND sha NOT IN (
      SELECT c_new.sha FROM (
          SELECT sha, project_id,
                 ROW_NUMBER() OVER (PARTITION BY project_id ORDER BY committed_at DESC, sha DESC) as rn
          FROM commits
          WHERE message = 'learnloop: tracked files snapshot'
      ) c_new
      WHERE c_new.rn = 1
  );

-- 5. Set kept newest snapshot row's kind='snapshot' and origin='backfill'
UPDATE commits
SET kind = 'snapshot', origin = 'backfill'
WHERE message = 'learnloop: tracked files snapshot';
