from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from learnloop.capture.techscan import (
    parse_cargo_toml,
    parse_docker_compose,
    parse_dockerfile,
    parse_go_mod,
    parse_package_json,
    parse_pyproject_toml,
    parse_requirements_txt,
    redact_credentials,
    scan_technologies,
)
from learnloop.persistence.db import migrate
from learnloop.services import capture_service, technology_service


def test_redact_credentials():
    assert redact_credentials("https://user:pass@pypi.org/simple") == "https://***@pypi.org/simple"
    assert redact_credentials("git+https://token@github.com/org/repo.git") == "git+https://***@github.com/org/repo.git"
    assert redact_credentials("http://user:secret@example.com/foo") == "http://***@example.com/foo"
    assert redact_credentials("https://example.com/normal") == "https://example.com/normal"
    assert redact_credentials("plain_text") == "plain_text"


def test_parse_requirements_txt_clean_and_adversarial():
    sample = """
    # This is a comment
    requests>=2.28.0,<3.0
    pytest
    fastapi[all]==0.100.0 ; python_version >= '3.8'
    django >= 4.0 # inline comment

    # Option lines to ignore
    -r requirements-base.txt
    -e .
    -i https://pypi.org/simple
    --index-url https://user:secret1@pypi.example.com/simple
    --extra-index-url https://user:secret2@pypi.example.com/simple
    --find-links /local/wheels

    # Direct reference
    custom-tool @ https://user:secret3@github.com/org/custom-tool.git@v1.0

    # Raw URL line without package name (should be dropped)
    https://user:secret4@github.com/bad/url.git
    """
    results = parse_requirements_txt(sample, "requirements.txt")
    names = {r["name"]: r for r in results}

    assert "requests" in names
    assert names["requests"]["version_spec"] == ">=2.28.0,<3.0"
    assert names["requests"]["ecosystem"] == "python"

    assert "pytest" in names
    assert names["pytest"]["version_spec"] is None

    assert "fastapi" in names
    assert names["fastapi"]["version_spec"] == "==0.100.0"

    assert "django" in names
    assert names["django"]["version_spec"] == ">= 4.0"

    assert "custom-tool" in names
    assert names["custom-tool"]["version_spec"] is None

    # Verify no option lines or credentials leaked
    for r in results:
        assert not r["name"].startswith("-")
        assert "secret" not in (r["version_spec"] or "")
        assert "secret" not in r["name"]
        assert "http" not in r["name"]


def test_parse_pyproject_toml():
    sample = """
    [project]
    name = "myapp"
    dependencies = [
        "flask>=2.0.0",
        "httpx~=0.24.0",
    ]

    [project.optional-dependencies]
    dev = [
        "pytest>=7.0",
        "ruff>=0.1",
    ]

    [build-system]
    requires = ["hatchling>=1.0"]
    """
    results = parse_pyproject_toml(sample, "pyproject.toml")
    names = {r["name"] for r in results}
    assert "flask" in names
    assert "httpx" in names
    assert "pytest" in names
    assert "ruff" in names
    assert "hatchling" in names


def test_parse_package_json():
    sample = """{
        "name": "frontend",
        "dependencies": {
            "react": "^18.2.0",
            "next": "14.0.0",
            "@types/react": "^18.2.0"
        },
        "devDependencies": {
            "typescript": "^5.0.0",
            "private-pkg": "git+https://user:token123@github.com/org/repo.git"
        }
    }"""
    results = parse_package_json(sample, "package.json")
    names = {r["name"]: r for r in results}

    assert "react" in names
    assert names["react"]["version_spec"] == "^18.2.0"
    assert names["react"]["ecosystem"] == "npm"

    assert "@types/react" in names
    assert "typescript" in names
    assert "token123" not in names["private-pkg"]["version_spec"]
    assert "git+https://***@github.com/org/repo.git" in names["private-pkg"]["version_spec"]


def test_parse_go_mod():
    sample = """
    module example.com/my/server

    go 1.21

    require (
        github.com/gin-gonic/gin v1.9.1
        golang.org/x/crypto v0.14.0 // indirect
    )

    require rsc.io/quote v1.5.2
    """
    results = parse_go_mod(sample, "go.mod")
    names = {r["name"]: r for r in results}

    assert "github.com/gin-gonic/gin" in names
    assert names["github.com/gin-gonic/gin"]["version_spec"] == "v1.9.1"
    assert names["github.com/gin-gonic/gin"]["ecosystem"] == "go"

    assert "golang.org/x/crypto" in names
    assert names["golang.org/x/crypto"]["version_spec"] == "v0.14.0"

    assert "rsc.io/quote" in names
    assert names["rsc.io/quote"]["version_spec"] == "v1.5.2"


def test_parse_cargo_toml():
    sample = """
    [package]
    name = "rust_app"
    version = "0.1.0"

    [dependencies]
    serde = "1.0.190"
    tokio = { version = "1.32", features = ["full"] }
    secret-crate = { git = "https://user:token456@github.com/secret/crate.git" }

    [dev-dependencies]
    tempfile = "3.8"
    """
    results = parse_cargo_toml(sample, "Cargo.toml")
    names = {r["name"]: r for r in results}

    assert "serde" in names
    assert names["serde"]["version_spec"] == "1.0.190"
    assert names["serde"]["ecosystem"] == "cargo"

    assert "tokio" in names
    assert names["tokio"]["version_spec"] == "1.32"

    assert "secret-crate" in names
    assert "token456" not in (names["secret-crate"]["version_spec"] or "")

    assert "tempfile" in names


def test_parse_dockerfile_and_compose():
    df = """
    FROM python:3.11-slim as builder
    WORKDIR /app
    FROM node:18-alpine
    WORKDIR /frontend
    FROM scratch
    """
    df_results = parse_dockerfile(df, "Dockerfile")
    df_names = {r["name"]: r for r in df_results}
    assert "python" in df_names
    assert df_names["python"]["version_spec"] == "3.11-slim"
    assert "node" in df_names
    assert df_names["node"]["version_spec"] == "18-alpine"
    assert "scratch" in df_names

    compose = """
    version: '3.8'
    services:
      db:
        image: postgres:15-alpine
      cache:
        image: redis:7
    """
    compose_results = parse_docker_compose(compose, "docker-compose.yml")
    c_names = {r["name"]: r for r in compose_results}
    assert "postgres" in c_names
    assert c_names["postgres"]["version_spec"] == "15-alpine"
    assert "redis" in c_names


def test_malformed_manifest_files_are_non_fatal(tmp_path: Path):
    repo = tmp_path / "repo_malformed"
    repo.mkdir()

    # Broken TOML, broken JSON
    (repo / "pyproject.toml").write_text("this is [broken toml", encoding="utf-8")
    (repo / "package.json").write_text("{broken json", encoding="utf-8")
    # Valid requirements.txt
    (repo / "requirements.txt").write_text("pytest==8.0.0\n", encoding="utf-8")

    results = scan_technologies(repo)
    assert len(results) == 1
    assert results[0]["name"] == "pytest"
    assert results[0]["version_spec"] == "==8.0.0"


def test_oversized_manifest_file_is_skipped(tmp_path: Path):
    repo = tmp_path / "repo_oversized"
    repo.mkdir()

    # 205 KB requirements.txt
    oversized = "pytest==8.0.0\n" * 15000
    assert len(oversized.encode("utf-8")) > 200 * 1024
    (repo / "requirements.txt").write_text(oversized, encoding="utf-8")

    results = scan_technologies(repo)
    assert len(results) == 0


def test_vendored_directories_skipped(tmp_path: Path):
    repo = tmp_path / "repo_vendored"
    repo.mkdir()

    # Valid in root
    (repo / "requirements.txt").write_text("root-pkg==1.0\n", encoding="utf-8")

    # Inside node_modules
    nm = repo / "node_modules" / "sub"
    nm.mkdir(parents=True)
    (nm / "package.json").write_text('{"dependencies": {"inner-npm": "1.0"}}', encoding="utf-8")

    # Inside venv
    venv = repo / "venv" / "sub"
    venv.mkdir(parents=True)
    (venv / "requirements.txt").write_text("venv-pkg==1.0\n", encoding="utf-8")

    # Inside .git
    git = repo / ".git" / "hooks"
    git.mkdir(parents=True)
    (git / "requirements.txt").write_text("git-pkg==1.0\n", encoding="utf-8")

    results = scan_technologies(repo)
    names = {r["name"] for r in results}
    assert "root-pkg" in names
    assert "inner-npm" not in names
    assert "venv-pkg" not in names
    assert "git-pkg" not in names


def test_directory_depth_limit(tmp_path: Path):
    repo = tmp_path / "repo_depth"
    repo.mkdir()

    # Depth 0 (root)
    (repo / "requirements.txt").write_text("depth0-pkg==1.0\n", encoding="utf-8")

    # Depth 1
    d1 = repo / "backend"
    d1.mkdir()
    (d1 / "requirements.txt").write_text("depth1-pkg==1.0\n", encoding="utf-8")

    # Depth 2
    d2 = d1 / "services"
    d2.mkdir()
    (d2 / "requirements.txt").write_text("depth2-pkg==1.0\n", encoding="utf-8")

    # Depth 3 (exceeds MAX_DEPTH 2)
    d3 = d2 / "subservice"
    d3.mkdir()
    (d3 / "requirements.txt").write_text("depth3-pkg==1.0\n", encoding="utf-8")

    results = scan_technologies(repo)
    names = {r["name"] for r in results}
    assert "depth0-pkg" in names
    assert "depth1-pkg" in names
    assert "depth2-pkg" in names
    assert "depth3-pkg" not in names


def test_symlink_escape_refused(tmp_path: Path):
    outside = tmp_path / "outside_dir"
    outside.mkdir()
    (outside / "requirements.txt").write_text("outside-pkg==1.0\n", encoding="utf-8")

    repo = tmp_path / "repo_sym_target"
    repo.mkdir()
    sym_link = repo / "sym_outside"

    try:
        os.symlink(outside, sym_link, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks not supported in environment")

    results = scan_technologies(repo)
    names = {r["name"] for r in results}
    assert "outside-pkg" not in names


def test_technology_service_refresh_and_list(tmp_path: Path):
    db_path = tmp_path / "tech_test.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    migrate(conn, db_path)

    repo = tmp_path / "my_project_repo"
    repo.mkdir()
    (repo / "requirements.txt").write_text("requests==2.31.0\nflask>=2.0\n", encoding="utf-8")
    (repo / "package.json").write_text('{"dependencies": {"lodash": "^4.17.21"}}', encoding="utf-8")

    p = capture_service.start_project(conn, "Tech Project", str(repo))
    pid = p["id"]

    # Refresh technologies
    res = technology_service.refresh_technologies(conn, pid)
    assert res["project_id"] == pid
    assert res["count"] == 3

    # List technologies
    listed = technology_service.list_technologies(conn, pid)
    assert len(listed) == 3
    eco_names = {(t["ecosystem"], t["name"]) for t in listed}
    assert ("python", "requests") in eco_names
    assert ("python", "flask") in eco_names
    assert ("npm", "lodash") in eco_names

    # Idempotent re-run
    res2 = technology_service.refresh_technologies(conn, pid)
    assert res2["count"] == 3

    conn.close()


def test_dashboard_renders_technologies_and_escapes_xss(tmp_path: Path):
    import http.client
    import threading

    from learnloop.dashboard.server import DashboardHandler, DashboardServer

    db_path = tmp_path / "dash_tech.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    migrate(conn, db_path)

    repo = tmp_path / "dash_repo"
    repo.mkdir()
    p = capture_service.start_project(conn, "Dash Tech Project", str(repo))
    pid = p["id"]

    # Insert technologies including an XSS string
    conn.execute(
        "INSERT INTO project_technologies (project_id, ecosystem, name, version_spec, source_file, detected_at)"
        " VALUES (?, 'python', '<script>alert(1)</script>', '>=1.0', 'requirements.txt', '2026-03-01T00:00:00Z')",
        (pid,),
    )
    conn.execute(
        "INSERT INTO project_technologies (project_id, ecosystem, name, version_spec, source_file, detected_at)"
        " VALUES (?, 'npm', 'react', '^18.0.0', 'package.json', '2026-03-01T00:00:00Z')",
        (pid,),
    )
    conn.commit()
    conn.close()

    server = DashboardServer(("127.0.0.1", 0), DashboardHandler)
    port = server.server_address[1]
    DashboardHandler.server_port = port
    DashboardHandler.db_path = db_path

    st = threading.Thread(target=server.serve_forever, daemon=True)
    st.start()

    try:
        http_conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        http_conn.request("GET", f"/p/{pid}/", headers={"Host": f"127.0.0.1:{port}"})
        resp = http_conn.getresponse()
        assert resp.status == 200
        body = resp.read().decode("utf-8")
        http_conn.close()

        # Technologies panel present
        assert "Technologies &amp; References" in body or "Technologies & References" in body
        assert "react" in body
        assert "[package.json]" in body

        # XSS injection properly escaped
        assert "<script>alert(1)</script>" not in body
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in body
    finally:
        server.shutdown()
        server.server_close()


def test_cli_techscan_runs_cleanly(tmp_path: Path, capsys):
    from learnloop.cli import cmd_techscan
    from learnloop.config import Settings

    repo = tmp_path / "cli_repo"
    repo.mkdir()
    (repo / "requirements.txt").write_text("fastapi==0.100.0\n", encoding="utf-8")

    db_path = tmp_path / "cli_tech.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    migrate(conn, db_path)
    conn.close()

    # Monkeypatch settings db_path
    orig_load = Settings.load
    try:
        Settings.load = lambda: Settings(db_path=db_path)
        code = cmd_techscan(repo)
        assert code == 0
        captured = capsys.readouterr()
        assert "fastapi" in captured.out
        assert "PYTHON" in captured.out
    finally:
        Settings.load = orig_load


def test_techscan_junction_directory_skipped(tmp_path: Path):
    if sys.platform != "win32":
        pytest.skip("Windows NTFS junctions are only supported on Windows")

    outside = tmp_path / "outside_junc_tech"
    outside.mkdir()
    (outside / "requirements.txt").write_text("junction-pkg==1.0\n", encoding="utf-8")

    repo = tmp_path / "repo_junc_tech"
    repo.mkdir()
    link_junc = repo / "junc_dir"

    cmd = ["cmd.exe", "/c", "mklink", "/J", str(link_junc), str(outside)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        pytest.skip(f"mklink /J creation failed: {proc.stderr or proc.stdout}")

    try:
        results = scan_technologies(repo)
        names = {r["name"] for r in results}
        assert "junction-pkg" not in names
    finally:
        subprocess.run(["cmd.exe", "/c", "rmdir", str(link_junc)], capture_output=True)

