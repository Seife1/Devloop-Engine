"""Staleness detection for knowledge items. Pure domain logic, no I/O.

An item is STALE when status is in ('explained', 'shaky'), has a baseline commit timestamp,
and at least one ingested commit with committed_at > baseline_committed_at touches any of the item's files.
Commits with identical timestamps (tie) are not strictly greater and thus do not trigger staleness.
"""

from __future__ import annotations

from typing import Any


def find_changing_commits_for_item(
    item_files: list[str],
    baseline_committed_at: str | None,
    commits: list[dict[str, Any]],
    max_commits: int = 5,
) -> list[dict[str, Any]]:
    """Return up to `max_commits` commits that touch any of the item's files strictly after baseline.

    Args:
        item_files: The normalised file paths associated with the knowledge item.
        baseline_committed_at: ISO timestamp of the baseline commit, or None if unestablished.
        commits: List of commit dicts with keys 'sha', 'message', 'committed_at', 'files'.
        max_commits: Maximum number of changing commits to return (default 5).

    Returns:
        List of dicts with 'sha', 'message', 'committed_at', 'matched_files', ordered newest first.
    """
    if not baseline_committed_at or not item_files:
        return []

    target_files = set(item_files)
    changing: list[dict[str, Any]] = []

    for c in commits:
        c_at = str(c.get("committed_at", ""))
        # Rule: strictly greater. Ties (equal timestamp) are not stale.
        if c_at <= baseline_committed_at:
            continue
        c_files = set(c.get("files", []))
        matched = sorted(target_files.intersection(c_files))
        if matched:
            changing.append(
                {
                    "sha": str(c.get("sha", "")),
                    "message": str(c.get("message", "")),
                    "committed_at": c_at,
                    "matched_files": matched,
                }
            )

    # Sort newest first, then tie-break by sha
    changing.sort(key=lambda x: (x["committed_at"], x["sha"]), reverse=True)
    return changing[:max_commits]


def compute_item_staleness(
    status: str,
    item_files: list[str],
    baseline_commit: str | None,
    baseline_committed_at: str | None,
    commits: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Evaluate whether a knowledge item is stale.

    Returns a dict with staleness details if stale, or None if not stale.
    """
    if status not in ("explained", "shaky"):
        return None
    if not baseline_committed_at or not baseline_commit:
        return None

    changing = find_changing_commits_for_item(
        item_files=item_files,
        baseline_committed_at=baseline_committed_at,
        commits=commits,
    )
    if not changing:
        return None

    return {
        "baseline_commit": baseline_commit,
        "baseline_committed_at": baseline_committed_at,
        "changing_commits": changing,
    }
