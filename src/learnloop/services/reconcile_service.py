"""Reconciliation: join INTENT (agent) with OUTCOME (git). Exposure exists only where both agree.

intent + commit  -> verified, exposure counted
intent only      -> stays open, abandoned after N days, no exposure
commit only      -> 'unexplained', no exposure until the agent explains it
"""

from __future__ import annotations

import json
import math
import sqlite3
from datetime import datetime, timedelta
from typing import Any

from learnloop.capture.skill_mapper import suggest_skills
from learnloop.domain import clock


def calculate_file_overlap(intent_files: list[str], commit_files: list[str]) -> float:
    """Calculate file overlap score between intent and commit.
    
    Requirements: 36.1, 36.2
    
    Args:
        intent_files: List of files declared in the intent
        commit_files: List of files modified in the commit
        
    Returns:
        Float between 0.0 and 1.0 representing the overlap score,
        normalized by the intent file list size
    """
    if not intent_files:
        return 0.0
    
    intent_set = set(intent_files)
    commit_set = set(commit_files)
    
    # Count files present in both intent and commit
    overlap_count = len(intent_set & commit_set)
    
    # Normalize by intent file list size
    overlap_score = overlap_count / len(intent_files)
    
    return overlap_score


def calculate_time_decay(time_delta: timedelta) -> float:
    """Calculate time decay score using exponential decay.
    
    Requirements: 36.3
    
    Uses exponential decay with 24-hour half-life. The score represents
    how recent the commit is relative to the intent creation time.
    
    Args:
        time_delta: Time difference between commit and intent creation
        
    Returns:
        Float between 0.0 and 1.0, where 1.0 is immediate and decreases
        exponentially with a 24-hour half-life
    """
    # Handle negative time deltas (commit before intent)
    if time_delta.total_seconds() < 0:
        return 0.0
    
    # Convert to hours
    hours = time_delta.total_seconds() / 3600.0
    
    # Exponential decay with 24-hour half-life
    # Formula: 2^(-hours/half_life)
    half_life_hours = 24.0
    decay_score = math.pow(2, -hours / half_life_hours)
    
    return decay_score


def _verify(
    conn: sqlite3.Connection,
    project_id: str,
    sha: str,
    intents: list[sqlite3.Row],
    now: str,
    commit_files: list[str],
) -> int:
    commit_file_set = set(commit_files)
    warnings = 0
    for intent in intents:
        conn.execute("UPDATE intents SET status='verified', commit_sha=? WHERE id=?", (sha, intent["id"]))
        for r in conn.execute(
            "SELECT skill_id FROM intent_skills WHERE intent_id=?", (intent["id"],)
        ).fetchall():
            conn.execute(
                "INSERT OR IGNORE INTO events (project_id, skill_id, commit_sha, intent_id, created_at)"
                " VALUES (?,?,?,?,?)",
                (project_id, r["skill_id"], sha, intent["id"], now),
            )
        declared_rows = conn.execute(
            "SELECT path FROM intent_files WHERE intent_id=?", (intent["id"],)
        ).fetchall()
        if declared_rows:
            touched_any = False
            for d in declared_rows:
                p = d["path"]
                is_touched = 1 if p in commit_file_set else 0
                if is_touched:
                    touched_any = True
                conn.execute(
                    "UPDATE intent_files SET touched=? WHERE intent_id=? AND path=?",
                    (is_touched, intent["id"], p),
                )
            if not touched_any:
                warnings += 1
    conn.execute("UPDATE commits SET status='verified' WHERE sha=?", (sha,))
    return warnings


def reconcile_intents(
    conn: sqlite3.Connection,
    project_id: str,
    match_threshold: float = 0.6,
    file_overlap_weight: float = 0.7,
    time_proximity_weight: float = 0.3,
    abandon_days: int = 14,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Match open intents with commits using file overlap and time proximity scoring.
    
    Requirements: 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 7.10, 36.1-36.6
    
    Algorithm:
    1. Load unprocessed queue entries
    2. Load open intent_records for the project
    3. For each commit, calculate match scores with all open intents
    4. Match score = (file_overlap * 0.7) + (time_proximity * 0.3)
    5. If match score >= threshold (0.6), create exposure_record
    6. Mark unmatched commits as unexplained
    7. Abandon intents older than 14 days
    
    Args:
        conn: Database connection
        project_id: Project identifier
        match_threshold: Minimum score for intent-commit matching (default 0.6)
        file_overlap_weight: Weight for file overlap in scoring (default 0.7)
        time_proximity_weight: Weight for time proximity in scoring (default 0.3)
        abandon_days: Days before abandoning open intents (default 14)
        now: Current timestamp (defaults to utcnow)
        
    Returns:
        Dictionary with:
        - matched: Number of intents matched with commits
        - abandoned: Number of intents abandoned
        - unexplained: Number of commits without matching intents
        - processed_commits: Total commits processed
    """
    import uuid
    
    now_dt = now or clock.utcnow()
    now_s = clock.iso(now_dt)
    
    matched_count = 0
    abandoned_count = 0
    unexplained_count = 0
    processed_commits = 0
    
    # Step 1: Load unprocessed queue entries
    queue_entries = conn.execute(
        """SELECT qe.*, c.message, c.files, c.committed_at
           FROM queue_entries qe
           JOIN commits c ON qe.commit_sha = c.sha
           WHERE qe.project_id = ? AND qe.processed = 0
           ORDER BY c.committed_at""",
        (project_id,),
    ).fetchall()
    
    # Step 2: Load open intent_records
    open_intents = conn.execute(
        """SELECT id, intent_description, files_json, skills_json, created_at
           FROM intent_records
           WHERE project_id = ? AND status = 'open'""",
        (project_id,),
    ).fetchall()
    
    # Convert to list for manipulation
    open_intents_list = list(open_intents)
    
    # Step 3: Match commits with intents
    for commit_entry in queue_entries:
        commit_sha = commit_entry["commit_sha"]
        commit_files = json.loads(commit_entry["files"])
        commit_time = datetime.fromisoformat(commit_entry["committed_at"])
        
        best_match = None
        best_score = 0.0
        
        # Find best matching intent
        for intent in open_intents_list:
            intent_created = datetime.fromisoformat(intent["created_at"])
            
            # Intent must be created before commit
            if intent_created > commit_time:
                continue
            
            # Calculate match score
            intent_files = json.loads(intent["files_json"])
            file_overlap = calculate_file_overlap(intent_files, commit_files)
            time_delta = commit_time - intent_created
            time_score = calculate_time_decay(time_delta)
            
            score = (file_overlap * file_overlap_weight) + (time_score * time_proximity_weight)
            
            if score >= match_threshold and score > best_score:
                best_match = intent
                best_score = score
        
        if best_match is not None:
            # Create exposure_record
            exposure_id = str(uuid.uuid4())
            conn.execute(
                """INSERT INTO exposure_records 
                   (id, project_id, intent_id, commit_sha, skills_json, files_json, verified_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    exposure_id,
                    project_id,
                    best_match["id"],
                    commit_sha,
                    best_match["skills_json"],
                    commit_entry["files"],
                    now_s,
                ),
            )
            
            # Update intent_record status to matched
            conn.execute(
                """UPDATE intent_records 
                   SET status = 'matched', matched_commit_sha = ?, closed_at = ?
                   WHERE id = ?""",
                (commit_sha, now_s, best_match["id"]),
            )
            
            # Remove from open intents list to prevent duplicate matching
            open_intents_list.remove(best_match)
            matched_count += 1
        else:
            # Mark commit as unexplained (if not already)
            conn.execute(
                "UPDATE commits SET status = 'unexplained' WHERE sha = ?",
                (commit_sha,),
            )
            unexplained_count += 1
        
        # Mark queue entry as processed
        conn.execute(
            "UPDATE queue_entries SET processed = 1, processed_at = ? WHERE id = ?",
            (now_s, commit_entry["id"]),
        )
        processed_commits += 1
    
    # Step 4: Abandon stale intents
    cutoff = clock.iso(now_dt - timedelta(days=abandon_days))
    abandoned_count = conn.execute(
        """UPDATE intent_records 
           SET status = 'abandoned', closed_at = ?
           WHERE project_id = ? AND status = 'open' AND created_at < ?""",
        (now_s, project_id, cutoff),
    ).rowcount
    
    conn.commit()
    
    return {
        "matched": matched_count,
        "abandoned": abandoned_count,
        "unexplained": unexplained_count,
        "processed_commits": processed_commits,
    }


def reconcile(
    conn: sqlite3.Connection, project_id: str, abandon_days: int = 14, now: datetime | None = None
) -> dict[str, Any]:
    now_dt = now or clock.utcnow()
    now_s = clock.iso(now_dt)
    verified = 0
    warnings = 0
    commits = conn.execute(
        "SELECT * FROM commits WHERE project_id=? AND status IN ('new','unexplained')"
        " AND origin != 'backfill' ORDER BY committed_at",
        (project_id,),
    ).fetchall()
    for c in commits:
        commit_files = json.loads(c["files"])
        # 1) explicit link: intent declared this commit_sha
        intents = conn.execute(
            "SELECT * FROM intents WHERE project_id=? AND status='open' AND commit_sha=?",
            (project_id, c["sha"]),
        ).fetchall()
        # 2) otherwise, open unlinked intents declared before the commit (only for new commits)
        if not intents and c["status"] == "new":
            intents = conn.execute(
                "SELECT * FROM intents WHERE project_id=? AND status='open'"
                " AND commit_sha IS NULL AND created_at <= ?",
                (project_id, c["committed_at"]),
            ).fetchall()
        if intents:
            warnings += _verify(conn, project_id, c["sha"], intents, now_s, commit_files)
            verified += 1
        elif c["status"] == "new":
            conn.execute("UPDATE commits SET status='unexplained' WHERE sha=?", (c["sha"],))

    cutoff = clock.iso(now_dt - timedelta(days=abandon_days))
    abandoned = conn.execute(
        "UPDATE intents SET status='abandoned' WHERE project_id=? AND status='open' AND created_at < ?",
        (project_id, cutoff),
    ).rowcount
    conn.commit()

    unexplained = [
        {
            "sha": r["sha"],
            "message": r["message"],
            "suggested_skills": suggest_skills(conn, json.loads(r["files"])),
        }
        for r in conn.execute(
            "SELECT * FROM commits WHERE project_id=? AND status='unexplained'"
            " AND origin != 'backfill' ORDER BY committed_at",
            (project_id,),
        )
    ]
    return {
        "commits_verified": verified,
        "intents_abandoned": abandoned,
        "unexplained": unexplained,
        "warnings": warnings,
    }
