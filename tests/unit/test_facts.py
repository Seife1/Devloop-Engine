from __future__ import annotations

import http.client
import sqlite3
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from mcp.server.fastmcp import FastMCP

from learnloop.dashboard.server import DashboardHandler, DashboardServer
from learnloop.domain.errors import NotFoundError, ValidationError
from learnloop.mcp.tools import facts as facts_tool
from learnloop.persistence.db import migrate
from learnloop.services import capture_service, fact_service


@pytest.fixture
def db_conn(tmp_path: Path):
    db_path = tmp_path / "facts_test.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    migrate(conn, db_path)
    yield conn, db_path
    conn.close()


@pytest.fixture
def project(db_conn, tmp_path: Path):
    conn, _ = db_conn
    repo_path = tmp_path / "fact_repo"
    repo_path.mkdir(parents=True, exist_ok=True)
    proj = capture_service.start_project(conn, "Fact Project", str(repo_path))
    return proj


def test_validate_source_url_success():
    valid_urls = [
        "https://docs.python.org/3/library/sqlite3.html",
        "https://pytest.org/en/latest/",
        "https://sub.domain.co.uk/path?q=1&b=2#section",
        "https://github.com/astral-sh/uv",
    ]
    for url in valid_urls:
        assert fact_service.validate_source_url(url) == url


def test_validate_source_url_rejections():
    # Scheme rejections
    for bad in ["http://example.com", "ftp://example.com", "javascript:alert(1)", "file:///etc/passwd"]:
        with pytest.raises(ValidationError, match="https"):
            fact_service.validate_source_url(bad)

    # Missing hostname / empty
    for bad in ["", "   ", "https://", "https:///path"]:
        with pytest.raises(ValidationError):
            fact_service.validate_source_url(bad)

    # Userinfo / credentials in URL
    for bad in ["https://user:pass@example.com", "https://user@example.com"]:
        with pytest.raises(ValidationError, match="userinfo"):
            fact_service.validate_source_url(bad)

    # Localhost / loopback
    for bad in ["https://localhost", "https://localhost/doc", "https://127.0.0.1", "https://0.0.0.0", "https://[::1]"]:
        with pytest.raises(ValidationError, match="not allowed|IP address literal"):
            fact_service.validate_source_url(bad)

    # IP address literals (IPv4 and IPv6)
    for bad in ["https://10.0.0.1/test", "https://192.168.1.1/", "https://172.16.0.1/", "https://8.8.8.8/"]:
        with pytest.raises(ValidationError, match="domain name, not an IP address"):
            fact_service.validate_source_url(bad)

    # Invalid characters
    for bad in ["https://example.com/<script>", 'https://example.com/"test"', "https://example.com/ space"]:
        with pytest.raises(ValidationError, match="invalid characters"):
            fact_service.validate_source_url(bad)

    # Incomplete or invalid domain names
    for bad in ["https://local/", "https://domain./"]:
        with pytest.raises(ValidationError, match="valid domain"):
            fact_service.validate_source_url(bad)

    # Overly long URL (> 500 chars)
    long_url = "https://example.com/" + "a" * 500
    with pytest.raises(ValidationError, match="between 1 and 500 characters"):
        fact_service.validate_source_url(long_url)


def test_validate_retrieved_at():
    # Valid ISO timestamps
    now_iso = datetime.now(UTC).isoformat()
    assert fact_service.validate_retrieved_at(now_iso).startswith("202")
    assert fact_service.validate_retrieved_at("2026-03-01T12:00:00Z") == "2026-03-01T12:00:00+00:00"
    assert fact_service.validate_retrieved_at("2026-03-01T12:00:00+00:00") == "2026-03-01T12:00:00+00:00"

    # Invalid timestamps
    with pytest.raises(ValidationError, match="provided"):
        fact_service.validate_retrieved_at("")

    with pytest.raises(ValidationError, match="valid ISO 8601"):
        fact_service.validate_retrieved_at("yesterday")

    with pytest.raises(ValidationError, match="valid ISO 8601"):
        fact_service.validate_retrieved_at("2026-99-99")

    # Future timestamps (> 5 min ahead)
    future = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    with pytest.raises(ValidationError, match="future"):
        fact_service.validate_retrieved_at(future)

    with pytest.raises(ValidationError, match="future"):
        fact_service.validate_retrieved_at("2099-01-01T00:00:00Z")


def test_add_did_you_know_success_and_list(db_conn, project):
    conn, _ = db_conn
    pid = project["id"]

    res = fact_service.add_did_you_know(
        conn,
        project_id=pid,
        topic="SQLite Concurrency",
        fact="SQLite WAL mode allows multiple concurrent readers alongside a single active writer without lock contention.",
        source_url="https://sqlite.org/wal.html",
        source_title="SQLite WAL Documentation",
        retrieved_at="2026-03-01T10:00:00Z",
        technology="sqlite3",
    )

    assert res["created"] is True
    assert res["topic"] == "SQLite Concurrency"
    assert res["technology"] == "sqlite3"
    assert res["source_url"] == "https://sqlite.org/wal.html"
    assert len(res["id"]) == 12

    # Query back via list_facts
    facts = fact_service.list_facts(conn, pid, limit=5)
    assert len(facts) == 1
    assert facts[0]["id"] == res["id"]
    assert facts[0]["topic"] == "SQLite Concurrency"


def test_add_did_you_know_validations(db_conn, project):
    conn, _ = db_conn
    pid = project["id"]

    # Unknown project
    with pytest.raises(NotFoundError):
        fact_service.add_did_you_know(
            conn,
            project_id="nonexistent-proj",
            topic="Topic",
            fact="Fact text",
            source_url="https://example.com/doc",
            source_title="Doc",
            retrieved_at="2026-03-01T10:00:00Z",
        )

    # Topic bounds
    with pytest.raises(ValidationError, match="topic"):
        fact_service.add_did_you_know(
            conn,
            project_id=pid,
            topic="",
            fact="Fact text",
            source_url="https://example.com/doc",
            source_title="Doc",
            retrieved_at="2026-03-01T10:00:00Z",
        )
    with pytest.raises(ValidationError, match="topic"):
        fact_service.add_did_you_know(
            conn,
            project_id=pid,
            topic="x" * 81,
            fact="Fact text",
            source_url="https://example.com/doc",
            source_title="Doc",
            retrieved_at="2026-03-01T10:00:00Z",
        )

    # Fact bounds
    with pytest.raises(ValidationError, match="fact"):
        fact_service.add_did_you_know(
            conn,
            project_id=pid,
            topic="Topic",
            fact="",
            source_url="https://example.com/doc",
            source_title="Doc",
            retrieved_at="2026-03-01T10:00:00Z",
        )
    with pytest.raises(ValidationError, match="fact"):
        fact_service.add_did_you_know(
            conn,
            project_id=pid,
            topic="Topic",
            fact="x" * 301,
            source_url="https://example.com/doc",
            source_title="Doc",
            retrieved_at="2026-03-01T10:00:00Z",
        )

    # Title bounds
    with pytest.raises(ValidationError, match="source_title"):
        fact_service.add_did_you_know(
            conn,
            project_id=pid,
            topic="Topic",
            fact="Fact text",
            source_url="https://example.com/doc",
            source_title="",
            retrieved_at="2026-03-01T10:00:00Z",
        )
    with pytest.raises(ValidationError, match="source_title"):
        fact_service.add_did_you_know(
            conn,
            project_id=pid,
            topic="Topic",
            fact="Fact text",
            source_url="https://example.com/doc",
            source_title="x" * 201,
            retrieved_at="2026-03-01T10:00:00Z",
        )


def test_add_did_you_know_daily_rate_limit(db_conn, project):
    conn, _ = db_conn
    pid = project["id"]

    for i in range(10):
        res = fact_service.add_did_you_know(
            conn,
            project_id=pid,
            topic=f"Topic {i}",
            fact=f"Distinct fact number {i} with sufficient length to be distinct and valid.",
            source_url=f"https://example.com/doc/{i}",
            source_title=f"Doc {i}",
            retrieved_at="2026-03-01T10:00:00Z",
        )
        assert res["created"] is True

    # 11th fact on same day raises ValidationError
    with pytest.raises(ValidationError, match="Daily limit of 10 facts reached"):
        fact_service.add_did_you_know(
            conn,
            project_id=pid,
            topic="Topic 10",
            fact="Eleventh fact should be blocked by rate limit check.",
            source_url="https://example.com/doc/10",
            source_title="Doc 10",
            retrieved_at="2026-03-01T10:00:00Z",
        )


def test_add_did_you_know_idempotency(db_conn, project):
    conn, _ = db_conn
    pid = project["id"]

    # First call creates the fact
    res1 = fact_service.add_did_you_know(
        conn,
        project_id=pid,
        topic="FastMCP Lifespan",
        fact="FastMCP supports async context managers for server lifespan startup and shutdown hooks.",
        source_url="https://modelcontextprotocol.io/docs/concepts/architecture",
        source_title="MCP Architecture",
        retrieved_at="2026-03-01T10:00:00Z",
        technology="fastmcp",
    )
    assert res1["created"] is True

    # Second call with same normalized fact and source_url returns created: False
    res2 = fact_service.add_did_you_know(
        conn,
        project_id=pid,
        topic="FastMCP Lifespan Modified Topic",
        fact="  FastMCP  supports   async context managers for server lifespan startup and shutdown hooks.  ",
        source_url="https://modelcontextprotocol.io/docs/concepts/architecture",
        source_title="MCP Architecture",
        retrieved_at="2026-03-01T12:00:00Z",
    )
    assert res2["created"] is False
    assert res2["id"] == res1["id"]

    # Even if 5 facts were created, re-submitting an existing fact does not trigger rate limit error
    # Let's add 4 more facts so total count = 5
    for i in range(4):
        fact_service.add_did_you_know(
            conn,
            project_id=pid,
            topic=f"Extra {i}",
            fact=f"Unique extra fact {i} for rate limit test.",
            source_url=f"https://example.com/extra/{i}",
            source_title=f"Extra Title {i}",
            retrieved_at="2026-03-01T10:00:00Z",
        )

    # Re-submitting the first fact still returns created: False and does not raise rate limit error
    res3 = fact_service.add_did_you_know(
        conn,
        project_id=pid,
        topic="FastMCP Lifespan",
        fact="FastMCP supports async context managers for server lifespan startup and shutdown hooks.",
        source_url="https://modelcontextprotocol.io/docs/concepts/architecture",
        source_title="MCP Architecture",
        retrieved_at="2026-03-01T10:00:00Z",
    )
    assert res3["created"] is False
    assert res3["id"] == res1["id"]


def test_add_did_you_know_credential_redaction(db_conn, project):
    conn, _ = db_conn
    pid = project["id"]

    # Plant credentials in topic, fact, and title
    aws_secret = "AKIAIOSFODNN7EXAMPLE"
    topic_with_secret = f"AWS Auth {aws_secret}"
    fact_with_secret = f"Configure your environment with AWS key {aws_secret} to enable secure access."
    title_with_secret = f"AWS Docs {aws_secret}"

    res = fact_service.add_did_you_know(
        conn,
        project_id=pid,
        topic=topic_with_secret,
        fact=fact_with_secret,
        source_url="https://docs.aws.amazon.com/general/latest/gr/aws-sec-cred-types.html",
        source_title=title_with_secret,
        retrieved_at="2026-03-01T10:00:00Z",
    )

    assert aws_secret not in res["topic"]
    assert "[REDACTED]" in res["topic"]
    assert aws_secret not in res["fact"]
    assert "[REDACTED]" in res["fact"]
    assert aws_secret not in res["source_title"]
    assert "[REDACTED]" in res["source_title"]

    # Verify persisted row in SQLite is also redacted
    persisted = conn.execute("SELECT * FROM project_facts WHERE id = ?", (res["id"],)).fetchone()
    assert aws_secret not in persisted["topic"]
    assert aws_secret not in persisted["fact"]
    assert aws_secret not in persisted["source_title"]


def test_mcp_tool_registration(db_conn, project):
    conn, _ = db_conn

    from contextlib import contextmanager

    @contextmanager
    def db_ctx():
        yield conn

    mcp = FastMCP("test-mcp")
    facts_tool.register(mcp, db_ctx)

    # Verify tool is registered in mcp
    tools = {t.name: t for t in mcp._tool_manager.list_tools()}
    assert "add_did_you_know" in tools


def test_dashboard_facts_rendering_and_xss_escaping(tmp_path: Path):
    db_path = tmp_path / "dashboard_facts.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    migrate(conn, db_path)

    repo_dir = tmp_path / "repo_dash"
    repo_dir.mkdir(parents=True, exist_ok=True)
    proj = capture_service.start_project(conn, "Dashboard Facts Project", str(repo_dir))
    pid = proj["id"]

    # Add fact with adversarial HTML tags
    fact_service.add_did_you_know(
        conn,
        project_id=pid,
        topic="<script>alert('topic_xss')</script>",
        fact="<img src=x onerror=alert('fact_xss')> Pytest uses AST rewriting for assertions.",
        source_url="https://docs.pytest.org/en/stable/how-to/writing_plugins.html?query=test&a=1#sec",
        source_title="<b>Pytest Plugin Docs</b>",
        retrieved_at="2026-03-01T10:00:00Z",
        technology="<script>pytest</script>",
    )
    conn.close()

    # Start dashboard server on port 0
    server = DashboardServer(("127.0.0.1", 0), DashboardHandler)
    port = server.server_address[1]
    DashboardHandler.server_port = port
    DashboardHandler.db_path = db_path

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    try:
        http_conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        http_conn.request("GET", f"/p/{pid}/", headers={"Host": f"127.0.0.1:{port}"})
        resp = http_conn.getresponse()
        assert resp.status == 200
        html_body = resp.read().decode("utf-8")
        http_conn.close()

        # 1. Panel header is present
        assert "💡 Did You Know?" in html_body

        # 2. Mandatory agent-reported badge is present
        assert '<span class="badge badge-agent-reported">Agent-reported: check the source</span>' in html_body

        # 3. Clickable HTTPS link with target="_blank" and rel="noopener noreferrer"
        assert 'target="_blank"' in html_body
        assert 'rel="noopener noreferrer"' in html_body
        assert 'href="https://docs.pytest.org/en/stable/how-to/writing_plugins.html?query=test&amp;a=1#sec"' in html_body

        # 4. Retrieval date is present
        assert "(Retrieved: 2026-03-01)" in html_body

        # 5. XSS escaping: NO raw script or img tags in HTML
        assert "<script>alert('topic_xss')</script>" not in html_body
        assert "&lt;script&gt;alert(&#x27;topic_xss&#x27;)&lt;/script&gt;" in html_body

        assert "<img src=x onerror=alert('fact_xss')>" not in html_body
        assert "&lt;img src=x onerror=alert(&#x27;fact_xss&#x27;)&gt;" in html_body

        assert "<b>Pytest Plugin Docs</b>" not in html_body
        assert "&lt;b&gt;Pytest Plugin Docs&lt;/b&gt;" in html_body

        assert "<script>pytest</script>" not in html_body
        assert "&lt;script&gt;pytest&lt;/script&gt;" in html_body
    finally:
        server.shutdown()
        server.server_close()
