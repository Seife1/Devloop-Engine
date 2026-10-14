from __future__ import annotations

import http.client
import http.server
import os
import sqlite3
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from learnloop.dashboard.server import DashboardHandler
from learnloop.persistence.db import migrate
from learnloop.services import capture_service, knowledge_service


@pytest.fixture
def dashboard_env(tmp_path: Path):
    db_path = tmp_path / "dashboard_test.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    migrate(conn, db_path)

    # Project A with XSS-planted strings
    repo_a = tmp_path / "repo_alpha"
    repo_a.mkdir(parents=True)
    learn_a = repo_a / ".learn"
    learn_a.mkdir(parents=True)
    (learn_a / "guide.md").write_text("# Alpha Guide\n\n[doc link](https://example.com/alpha)\n[bad link](javascript:alert(1))", encoding="utf-8")
    (learn_a / "oversized.md").write_text("x" * (501 * 1024), encoding="utf-8")

    # Queue commits in repo A
    q_a = learn_a / "queue"
    q_a.mkdir(parents=True)
    (q_a / "commit1.json").write_text("{}", encoding="utf-8")
    (q_a / "commit2.json").write_text("{}", encoding="utf-8")

    p_a = capture_service.start_project(conn, "<script>alert('pname_a')</script>", str(repo_a))
    id_a = p_a["id"]

    # Commit in A
    conn.execute(
        "INSERT INTO commits (sha, project_id, message, files, committed_at, status, origin, kind)"
        " VALUES ('sha_a1', ?, 'alpha commit', '[\"alpha.py\"]', '2026-03-01T00:00:00Z', 'verified', 'hook', 'commit')",
        (id_a,),
    )
    conn.commit()

    # Knowledge item in A with XSS strings
    knowledge_service.register_knowledge_item(
        conn,
        id_a,
        "key_a1",
        "<img src=x onerror=alert('title')>",
        "component",
        "basic",
        ["alpha.py"],
        "<script>alert('summary')</script>",
        tags=["<script>alert('tag')</script>"],
    )

    # Explanation in A with XSS
    knowledge_service.record_explanation(
        conn,
        id_a,
        "key_a1",
        "<script>alert('learner_text')</script>",
        score=0.9,
        self_rating=4,
    )

    # Project B (completely separate)
    repo_b = tmp_path / "repo_beta"
    repo_b.mkdir(parents=True)
    learn_b = repo_b / ".learn"
    learn_b.mkdir(parents=True)
    (learn_b / "beta_doc.md").write_text("# Beta Doc\nContent beta.", encoding="utf-8")

    p_b = capture_service.start_project(conn, "Project Beta", str(repo_b))
    id_b = p_b["id"]

    conn.execute(
        "INSERT INTO commits (sha, project_id, message, files, committed_at, status, origin, kind)"
        " VALUES ('sha_b1', ?, 'beta commit', '[\"beta.py\"]', '2026-03-01T00:00:00Z', 'verified', 'hook', 'commit')",
        (id_b,),
    )
    conn.commit()

    knowledge_service.register_knowledge_item(
        conn,
        id_b,
        "key_b1",
        "Beta Component",
        "component",
        "advanced",
        ["beta.py"],
        "Beta summary",
    )
    conn.close()

    # Start DashboardServer on port 0
    from learnloop.dashboard.server import DashboardServer

    server = DashboardServer(("127.0.0.1", 0), DashboardHandler)
    port = server.server_address[1]
    DashboardHandler.server_port = port
    DashboardHandler.db_path = db_path

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    yield {
        "port": port,
        "id_a": id_a,
        "id_b": id_b,
        "repo_a": repo_a,
        "repo_b": repo_b,
        "db_path": db_path,
    }

    server.shutdown()
    server.server_close()


def _request(
    port: int,
    method: str,
    path: str,
    headers: dict[str, str] | None = None,
    body: str | None = None,
) -> tuple[int, dict[str, str], str]:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    default_headers = {"Host": f"127.0.0.1:{port}"}
    if headers:
        default_headers.update(headers)
    conn.request(method, path, body=body, headers=default_headers)
    resp = conn.getresponse()
    status = resp.status
    resp_headers = {k: v for k, v in resp.getheaders()}
    resp_body = resp.read().decode("utf-8")
    conn.close()
    return status, resp_headers, resp_body


def test_dashboard_security_headers_on_all_routes(dashboard_env):
    port = dashboard_env["port"]
    id_a = dashboard_env["id_a"]

    routes = [
        "/",
        f"/p/{id_a}/",
        f"/p/{id_a}/items/key_a1",
        f"/p/{id_a}/concepts",
        f"/p/{id_a}/docs",
        f"/p/{id_a}/docs/guide.md",
        "/static/app.css",
    ]

    for route in routes:
        status, headers, _ = _request(port, "GET", route)
        assert status == 200, f"Route {route} failed with status {status}"
        assert "default-src 'none'" in headers.get("Content-Security-Policy", "")
        assert headers.get("X-Content-Type-Options") == "nosniff"
        assert headers.get("Referrer-Policy") == "no-referrer"
        assert headers.get("X-Frame-Options") == "DENY"
        assert headers.get("Cache-Control") == "no-store"


def test_dashboard_two_projects_stay_separate(dashboard_env):
    port = dashboard_env["port"]
    id_a = dashboard_env["id_a"]
    id_b = dashboard_env["id_b"]

    status_a, _, body_a = _request(port, "GET", f"/p/{id_a}/")
    assert status_a == 200
    assert "key_a1" in body_a
    assert "key_b1" not in body_a
    assert "Beta Component" not in body_a

    status_b, _, body_b = _request(port, "GET", f"/p/{id_b}/")
    assert status_b == 200
    assert "key_b1" in body_b
    assert "key_a1" not in body_b


def test_dashboard_xss_escaping(dashboard_env):
    port = dashboard_env["port"]
    id_a = dashboard_env["id_a"]

    # 1. Home page project name
    _, _, home_body = _request(port, "GET", "/")
    assert "<script>alert('pname_a')</script>" not in home_body
    assert "&lt;script&gt;alert(&#x27;pname_a&#x27;)&lt;/script&gt;" in home_body

    # 2. Project overview item title
    _, _, ov_body = _request(port, "GET", f"/p/{id_a}/")
    assert "<img src=x onerror=alert('title')>" not in ov_body
    assert "&lt;img src=x onerror=alert(&#x27;title&#x27;)&gt;" in ov_body

    # 3. Item detail summary, learner text, tags
    _, _, item_body = _request(port, "GET", f"/p/{id_a}/items/key_a1")
    assert "<script>alert('summary')</script>" not in item_body
    assert "<script>alert('learner_text')</script>" not in item_body
    assert "<script>alert('tag')</script>" not in item_body
    assert "&lt;script&gt;alert(&#x27;summary&#x27;)&lt;/script&gt;" in item_body
    assert "&lt;script&gt;alert(&#x27;learner_text&#x27;)&lt;/script&gt;" in item_body


def test_dashboard_strips_javascript_links(dashboard_env):
    port = dashboard_env["port"]
    id_a = dashboard_env["id_a"]

    _, _, doc_body = _request(port, "GET", f"/p/{id_a}/docs/guide.md")
    assert 'href="javascript:' not in doc_body
    assert '<a href="https://example.com/alpha"' in doc_body


def test_dashboard_bad_host_header_returns_403(dashboard_env):
    port = dashboard_env["port"]
    status, _, _ = _request(port, "GET", "/", headers={"Host": "attacker.com"})
    assert status == 403


def test_dashboard_post_returns_405(dashboard_env):
    port = dashboard_env["port"]
    status, headers, _ = _request(port, "POST", "/")
    assert status == 405
    assert "Allow" in headers
    assert "GET" in headers["Allow"]


def test_dashboard_path_traversal_returns_404(dashboard_env):
    port = dashboard_env["port"]
    id_a = dashboard_env["id_a"]

    # Traversal in doc name
    status, _, _ = _request(port, "GET", f"/p/{id_a}/docs/../../secret.md")
    assert status == 404

    # Unknown doc
    status, _, _ = _request(port, "GET", f"/p/{id_a}/docs/nonexistent.md")
    assert status == 404


def test_dashboard_symlinked_learn_returns_404(dashboard_env, tmp_path: Path):
    port = dashboard_env["port"]

    # Create a project with symlinked .learn directory
    real_learn = tmp_path / "real_learn"
    real_learn.mkdir()
    (real_learn / "sym_doc.md").write_text("# Sym Doc", encoding="utf-8")

    repo_sym = tmp_path / "repo_sym"
    repo_sym.mkdir()
    link_learn = repo_sym / ".learn"
    try:
        os.symlink(real_learn, link_learn, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks not permitted in this test environment")

    # Connect to db and create project
    conn = sqlite3.connect(dashboard_env["db_path"])
    conn.row_factory = sqlite3.Row
    p_sym = capture_service.start_project(conn, "Sym Project", str(repo_sym))
    conn.close()

    status, _, _ = _request(port, "GET", f"/p/{p_sym['id']}/docs/sym_doc.md")
    assert status == 404


def test_dashboard_unknown_and_invalid_project_id_returns_404(dashboard_env):
    port = dashboard_env["port"]

    # Invalid regex
    status, _, _ = _request(port, "GET", "/p/not-valid-id/")
    assert status == 404

    # Valid regex but unknown
    status, _, _ = _request(port, "GET", "/p/000000000000/")
    assert status == 404


def test_dashboard_oversized_markdown_returns_404(dashboard_env):
    port = dashboard_env["port"]
    id_a = dashboard_env["id_a"]

    status, _, _ = _request(port, "GET", f"/p/{id_a}/docs/oversized.md")
    assert status == 404


def test_dashboard_db_connection_is_read_only(dashboard_env):
    db_path = dashboard_env["db_path"]
    uri = db_path.resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)

    with pytest.raises(sqlite3.OperationalError, match="readonly database"):
        conn.execute("INSERT INTO projects (id, name, repo_path, created_at) VALUES ('x', 'x', 'x', 'x')")

    conn.close()


def test_dashboard_never_exposes_full_repo_path(dashboard_env):
    port = dashboard_env["port"]
    id_a = dashboard_env["id_a"]
    repo_a = str(dashboard_env["repo_a"])

    for route in ["/", f"/p/{id_a}/", f"/p/{id_a}/items/key_a1", f"/p/{id_a}/concepts", f"/p/{id_a}/docs"]:
        _, _, body = _request(port, "GET", route)
        assert repo_a not in body, f"Full repo path leaked in {route}"
        # Folder basename is allowed
        assert "repo_alpha" in body


def test_dashboard_port_busy_exits_with_error(dashboard_env, capsys):
    from learnloop.dashboard.server import run_dashboard_server

    code = run_dashboard_server(port=dashboard_env["port"], db_path=dashboard_env["db_path"])
    assert code == 1
    captured = capsys.readouterr()
    assert "already in use" in captured.err


def test_dashboard_outdated_version_prints_doctor_and_exits(tmp_path: Path, capsys):
    from learnloop.dashboard.server import run_dashboard_server

    old_db = tmp_path / "old.db"
    conn = sqlite3.connect(old_db)
    conn.execute("PRAGMA user_version=2")
    conn.close()

    code = run_dashboard_server(port=0, db_path=old_db)
    assert code == 1
    captured = capsys.readouterr()
    assert "run: learnloop doctor" in captured.err


def test_dashboard_security_headers_on_error_responses(dashboard_env):
    port = dashboard_env["port"]

    # 403 Forbidden (bad host)
    status_403, headers_403, _ = _request(port, "GET", "/", headers={"Host": "attacker.com"})
    assert status_403 == 403
    assert "default-src 'none'" in headers_403.get("Content-Security-Policy", "")
    assert headers_403.get("X-Content-Type-Options") == "nosniff"
    assert headers_403.get("X-Frame-Options") == "DENY"

    # 404 Not Found (unknown project)
    status_404, headers_404, _ = _request(port, "GET", "/p/000000000000/")
    assert status_404 == 404
    assert "default-src 'none'" in headers_404.get("Content-Security-Policy", "")
    assert headers_404.get("X-Content-Type-Options") == "nosniff"
    assert headers_404.get("X-Frame-Options") == "DENY"

    # 405 Method Not Allowed (POST)
    status_405, headers_405, _ = _request(port, "POST", "/")
    assert status_405 == 405
    assert "default-src 'none'" in headers_405.get("Content-Security-Policy", "")
    assert headers_405.get("X-Content-Type-Options") == "nosniff"
    assert headers_405.get("X-Frame-Options") == "DENY"


def test_dashboard_queue_commits_waiting_hint(dashboard_env):
    port = dashboard_env["port"]
    id_a = dashboard_env["id_a"]
    id_b = dashboard_env["id_b"]

    status_a, _, body_a = _request(port, "GET", f"/p/{id_a}/")
    assert status_a == 200
    assert "2" in body_a
    assert "commits waiting in queue to be ingested" in body_a

    status_b, _, body_b = _request(port, "GET", f"/p/{id_b}/")
    assert status_b == 200
    assert "commits waiting in queue" not in body_b


def test_dashboard_junction_reparse_point_returns_404(dashboard_env, tmp_path: Path):
    if sys.platform != "win32":
        pytest.skip("Windows NTFS junctions are only supported on Windows")

    port = dashboard_env["port"]

    real_learn = tmp_path / "real_learn_junc"
    real_learn.mkdir()
    (real_learn / "junc_doc.md").write_text("# Junction Doc", encoding="utf-8")

    repo_junc = tmp_path / "repo_junc"
    repo_junc.mkdir()
    link_learn = repo_junc / ".learn"

    # Create directory junction via mklink /J
    cmd = ["cmd.exe", "/c", "mklink", "/J", str(link_learn), str(real_learn)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        pytest.skip(f"mklink /J creation failed: {proc.stderr or proc.stdout}")

    try:
        conn = sqlite3.connect(dashboard_env["db_path"])
        conn.row_factory = sqlite3.Row
        p_junc = capture_service.start_project(conn, "Junction Project", str(repo_junc))
        conn.close()

        status, _, _ = _request(port, "GET", f"/p/{p_junc['id']}/docs/junc_doc.md")
        assert status == 404
    finally:
        # Clean up junction with rmdir so we don't delete real_learn contents
        subprocess.run(["cmd.exe", "/c", "rmdir", str(link_learn)], capture_output=True)


def test_dashboard_concurrent_mcp_write_and_dashboard_read(dashboard_env):
    port = dashboard_env["port"]
    db_path = dashboard_env["db_path"]
    id_a = dashboard_env["id_a"]

    stop_event = threading.Event()
    write_errors: list[Exception] = []
    read_errors: list[Exception] = []

    def writer_thread():
        # Open write connection like FastMCP server does
        try:
            write_conn = sqlite3.connect(db_path, timeout=10.0)
            write_conn.row_factory = sqlite3.Row
            write_conn.execute("PRAGMA journal_mode=WAL")
            write_conn.execute("PRAGMA foreign_keys=ON")

            i = 0
            while not stop_event.is_set() and i < 25:
                write_conn.execute(
                    "INSERT INTO commits (sha, project_id, message, files, committed_at, status, origin, kind)"
                    " VALUES (?, ?, ?, '[\"test.py\"]', '2026-03-01T00:00:00Z', 'verified', 'hook', 'commit')",
                    (f"sha_conc_{i}", id_a, f"concurrent commit {i}"),
                )
                write_conn.commit()
                i += 1
            write_conn.close()
        except Exception as e:
            write_errors.append(e)

    writer = threading.Thread(target=writer_thread, daemon=True)
    writer.start()

    # Issue multiple concurrent GET requests while writes happen
    for _ in range(30):
        try:
            status, _, body = _request(port, "GET", f"/p/{id_a}/")
            assert status == 200
            assert "key_a1" in body
        except Exception as e:
            read_errors.append(e)

    stop_event.set()
    writer.join(timeout=5.0)

    assert not write_errors, f"Write errors occurred during concurrent read/write: {write_errors}"
    assert not read_errors, f"Read errors occurred during concurrent read/write: {read_errors}"


