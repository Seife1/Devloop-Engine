from __future__ import annotations

import json
from pathlib import Path

from learnloop.persistence.db import connect
from learnloop.services.tour_service import TOUR_PROTOCOL, get_project_tour


def test_tour_bundle_bounds_with_5000_files(tmp_path: Path):
    db_path = tmp_path / "tour.db"
    conn = connect(db_path)

    conn.execute(
        "INSERT INTO projects (id, name, repo_path, created_at) VALUES ('p1', 'Big Project', '/repo', '2026-01-01T00:00:00Z')"
    )

    # Generate 5,000 distinct file paths across several directories
    files_5000 = [f"src/sub{i % 20}/module_{i}.py" for i in range(4980)]
    files_5000.extend(
        [
            "main.py",
            "app.py",
            "pyproject.toml",
            "package.json",
            "Dockerfile",
            "docker-compose.yml",
            "server.go",
            "cmd/app/main.go",
            "manage.py",
            "index.ts",
            "Cargo.toml",
            "go.mod",
        ]
    )

    conn.execute(
        "INSERT INTO commits (sha, project_id, message, files, committed_at, status, origin)"
        " VALUES ('c1', 'p1', 'initial 5000 files', ?, '2026-01-01T00:00:00Z', 'verified', 'hook')",
        (json.dumps(files_5000),),
    )

    # Insert a few existing knowledge items
    conn.execute(
        "INSERT INTO knowledge_items (id, project_id, key, title, kind, band, summary, status, depth, created_at, updated_at)"
        " VALUES ('k1', 'p1', 'entry', 'Entry Point', 'component', 'basic', 'Summary', 'explained', 1, '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')"
    )
    conn.execute("INSERT INTO item_files (item_id, path) VALUES ('k1', 'main.py')")
    conn.commit()

    bundle = get_project_tour(conn, "p1")

    # Serialize to JSON to measure payload size
    bundle_json = json.dumps(bundle)
    bundle_size_bytes = len(bundle_json.encode("utf-8"))

    # Must stay strictly under 8 KB (8192 bytes)
    assert bundle_size_bytes < 8192, f"Tour bundle size {bundle_size_bytes} >= 8192 bytes"

    # Verify structural contents
    assert bundle["project_id"] == "p1"
    assert "src" in bundle["top_level_dirs"]
    assert bundle["top_level_dirs"]["src"] == 4980
    assert len(bundle["uncovered_files"]) == 40
    assert bundle["uncovered_truncated"] is True
    assert bundle["uncovered_total"] > 4000
    assert "main.py" in bundle["entry_point_candidates"]
    assert "pyproject.toml" in bundle["manifest_files"]
    assert len(bundle["items_by_band"]["basic"]) == 1
    assert bundle["protocol"] == TOUR_PROTOCOL
    conn.close()
