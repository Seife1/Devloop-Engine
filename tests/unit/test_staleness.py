from __future__ import annotations

from learnloop.domain.staleness import compute_item_staleness, find_changing_commits_for_item


def test_find_changing_commits_strictly_greater():
    item_files = ["src/auth.py"]
    baseline_at = "2026-03-01T12:00:00Z"
    commits = [
        {
            "sha": "c1",
            "message": "fix auth",
            "committed_at": "2026-03-01T12:05:00Z",
            "files": ["src/auth.py", "tests/test_auth.py"],
        },
        {
            "sha": "c0",
            "message": "old commit",
            "committed_at": "2026-03-01T11:59:00Z",
            "files": ["src/auth.py"],
        },
    ]

    changing = find_changing_commits_for_item(item_files, baseline_at, commits)
    assert len(changing) == 1
    assert changing[0]["sha"] == "c1"
    assert changing[0]["matched_files"] == ["src/auth.py"]


def test_tie_timestamp_not_stale():
    item_files = ["src/auth.py"]
    baseline_at = "2026-03-01T12:00:00Z"
    commits = [
        {
            "sha": "c1",
            "message": "same timestamp commit",
            "committed_at": "2026-03-01T12:00:00Z",
            "files": ["src/auth.py"],
        }
    ]

    changing = find_changing_commits_for_item(item_files, baseline_at, commits)
    assert len(changing) == 0


def test_unrelated_files_not_stale():
    item_files = ["src/auth.py"]
    baseline_at = "2026-03-01T12:00:00Z"
    commits = [
        {
            "sha": "c2",
            "message": "touch readme only",
            "committed_at": "2026-03-01T12:10:00Z",
            "files": ["README.md"],
        }
    ]

    changing = find_changing_commits_for_item(item_files, baseline_at, commits)
    assert len(changing) == 0


def test_missing_baseline_not_stale():
    item_files = ["src/auth.py"]
    commits = [
        {
            "sha": "c1",
            "message": "change auth",
            "committed_at": "2026-03-01T12:10:00Z",
            "files": ["src/auth.py"],
        }
    ]
    assert find_changing_commits_for_item(item_files, None, commits) == []


def test_status_filtering_in_compute_item_staleness():
    item_files = ["src/auth.py"]
    baseline_commit = "c0"
    baseline_at = "2026-03-01T12:00:00Z"
    commits = [
        {
            "sha": "c1",
            "message": "change auth",
            "committed_at": "2026-03-01T12:10:00Z",
            "files": ["src/auth.py"],
        }
    ]

    # 'unexplained' status is not considered stale (it was never mastered)
    assert (
        compute_item_staleness(
            status="unexplained",
            item_files=item_files,
            baseline_commit=baseline_commit,
            baseline_committed_at=baseline_at,
            commits=commits,
        )
        is None
    )

    # 'explained' is checked
    res = compute_item_staleness(
        status="explained",
        item_files=item_files,
        baseline_commit=baseline_commit,
        baseline_committed_at=baseline_at,
        commits=commits,
    )
    assert res is not None
    assert res["baseline_commit"] == "c0"
    assert len(res["changing_commits"]) == 1

    # 'shaky' is checked
    res_shaky = compute_item_staleness(
        status="shaky",
        item_files=item_files,
        baseline_commit=baseline_commit,
        baseline_committed_at=baseline_at,
        commits=commits,
    )
    assert res_shaky is not None


def test_changing_commits_cap_and_order():
    item_files = ["src/core.py"]
    baseline_at = "2026-03-01T10:00:00Z"
    commits = [
        {
            "sha": f"c{i}",
            "message": f"msg {i}",
            "committed_at": f"2026-03-01T10:0{i}:00Z",
            "files": ["src/core.py"],
        }
        for i in range(1, 10)
    ]

    changing = find_changing_commits_for_item(item_files, baseline_at, commits, max_commits=5)
    assert len(changing) == 5
    # Should be ordered descending by committed_at (c9 down to c5)
    assert [c["sha"] for c in changing] == ["c9", "c8", "c7", "c6", "c5"]
