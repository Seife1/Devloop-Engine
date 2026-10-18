"""Local read-only dashboard server for LearnLoop.

Threat model & properties:
1. Standard library only (http.server.ThreadingHTTPServer).
2. Bound strictly to 127.0.0.1.
3. SQLite opened in URI mode=ro (writes strictly rejected by SQLite engine).
4. Host header validated against 127.0.0.1:<port> and localhost:<port> (403 otherwise).
5. Only GET and HEAD methods accepted (405 otherwise).
6. Security headers sent on every response: CSP (no scripts), X-Content-Type-Options,
   Referrer-Policy, X-Frame-Options, Cache-Control.
7. project_id regex validation (^[a-f0-9]{12}$) on all project routes (404 otherwise).
8. Parameterized SQL queries filtered by project_id.
9. Full repo filesystem paths never exposed in HTML (only folder name).
10. Safe file reads for .learn/*.md (resolved parent check, no symlinks, max 500 KB).
"""

from __future__ import annotations

import html
import http.server
import importlib.resources
import json
import os
import re
import sqlite3
import stat
import sys
import urllib.parse
from http import HTTPStatus
from pathlib import Path
from typing import Any

from learnloop.dashboard.markdown import render_markdown
from learnloop.journal.concept_log import generate_concept_markdown
from learnloop.services import knowledge_service, readiness_service, review_service

PROJECT_ID_REGEX = re.compile(r"^[a-f0-9]{12}$")
MAX_DOC_SIZE_BYTES = 500 * 1024


def get_required_migration_version() -> int:
    """Return the highest numbered migration file available in the package."""
    files = sorted(
        (
            p
            for p in importlib.resources.files("learnloop.persistence.migrations").iterdir()
            if p.name.endswith(".sql")
        ),
        key=lambda p: p.name,
    )
    if not files:
        return 0
    return max(int(f.name.split("_", 1)[0]) for f in files)


def is_reparse_point_or_link(path: Path | str) -> bool:
    """Return True if path is a symlink, Windows junction, or reparse point."""
    try:
        p = Path(path)
        if p.is_symlink() or os.path.islink(p):
            return True
        st = p.lstat()
        reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        attrs = getattr(st, "st_file_attributes", 0)
        if bool(attrs & reparse_flag):
            return True
        return False
    except (OSError, ValueError):
        return True


def count_queue_commits(repo_path: Path | str) -> int:
    """Safely count waiting commit entries in <repo>/.learn/queue (directory listing only)."""
    try:
        repo = Path(repo_path).resolve()
        learn_path = repo / ".learn"
        if not learn_path.is_dir() or is_reparse_point_or_link(learn_path):
            return 0
        if learn_path.resolve() != repo.resolve() / ".learn":
            return 0
        q_path = learn_path / "queue"
        if not q_path.is_dir() or is_reparse_point_or_link(q_path):
            return 0
        if q_path.resolve() != repo.resolve() / ".learn" / "queue":
            return 0
        return sum(
            1 for p in q_path.iterdir() if p.is_file() and not is_reparse_point_or_link(p)
        )
    except Exception:
        return 0


def list_safe_learn_docs(repo_path: Path | str) -> list[str]:
    """Safely list .md documentation files directly in <repo>/.learn/."""
    try:
        repo = Path(repo_path).resolve()
        learn_path = repo / ".learn"
        if not learn_path.is_dir() or is_reparse_point_or_link(learn_path):
            return []
        if learn_path.resolve() != repo.resolve() / ".learn":
            return []
        docs = []
        for p in learn_path.iterdir():
            if p.is_file() and not is_reparse_point_or_link(p) and p.name.endswith(".md"):
                if p.resolve().parent != learn_path.resolve():
                    continue
                if p.stat().st_size <= MAX_DOC_SIZE_BYTES:
                    docs.append(p.name)
        return sorted(docs)
    except Exception:
        return []


def extract_project_description(repo_path: Path | str | None) -> str:
    """Extract a one-line project description from pyproject.toml or package.json."""
    if not repo_path:
        return ""
    try:
        repo = Path(repo_path).resolve()
        pyproj = repo / "pyproject.toml"
        if pyproj.is_file() and not is_reparse_point_or_link(pyproj):
            try:
                import tomllib

                data = tomllib.loads(pyproj.read_text(encoding="utf-8"))
                desc = data.get("project", {}).get("description")
                if not desc:
                    desc = data.get("tool", {}).get("poetry", {}).get("description")
                if desc and isinstance(desc, str):
                    return desc.strip()
            except Exception:
                pass

        pkg_json = repo / "package.json"
        if pkg_json.is_file() and not is_reparse_point_or_link(pkg_json):
            try:
                data = json.loads(pkg_json.read_text(encoding="utf-8"))
                desc = data.get("description")
                if desc and isinstance(desc, str):
                    return desc.strip()
            except Exception:
                pass
    except Exception:
        pass
    return ""


def read_safe_learn_doc(repo_path: Path | str, doc_name: str) -> str | None:
    """Safely read a markdown doc directly within <repo>/.learn/."""
    try:
        repo = Path(repo_path).resolve()
        learn_path = repo / ".learn"
        if not learn_path.is_dir() or is_reparse_point_or_link(learn_path):
            return None
        if learn_path.resolve() != repo.resolve() / ".learn":
            return None

        clean_name = doc_name if doc_name.endswith(".md") else f"{doc_name}.md"
        target = learn_path / clean_name
        if is_reparse_point_or_link(target):
            return None
        resolved = target.resolve()
        learn_resolved = learn_path.resolve()
        if resolved.parent != learn_resolved:
            return None
        if not resolved.is_file() or is_reparse_point_or_link(resolved):
            return None
        if resolved.stat().st_size > MAX_DOC_SIZE_BYTES:
            return None
        return resolved.read_text("utf-8")
    except Exception:
        return None


class DashboardHandler(http.server.BaseHTTPRequestHandler):
    """HTTP request handler for the read-only LearnLoop dashboard."""

    server_port: int
    db_path: Path

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress default stdout logging; write to stderr if necessary."""

    def _get_ro_conn(self) -> sqlite3.Connection:
        """Open a read-only SQLite connection per request."""
        uri = self.db_path.resolve().as_uri() + "?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _validate_host(self) -> bool:
        """Validate the Host header against 127.0.0.1 and localhost to prevent DNS rebinding."""
        host = self.headers.get("Host", "").strip().lower()
        port = self.server_port
        valid_hosts = {
            f"127.0.0.1:{port}",
            f"localhost:{port}",
            "127.0.0.1",
            "localhost",
        }
        return host in valid_hosts

    def _send_security_headers(self, content_type: str = "text/html; charset=utf-8") -> None:
        self.send_header("Content-Type", content_type)
        csp = (
            "default-src 'none'; style-src 'self'; img-src 'self'; base-uri 'none'; "
            "form-action 'none'; frame-ancestors 'none'"
        )
        self.send_header("Content-Security-Policy", csp)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cache-Control", "no-store")

    def _send_response_page(self, status: int, body: str) -> None:
        payload = body.encode("utf-8")
        self.send_response(status)
        self._send_security_headers("text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(payload)

    def _send_error_page(self, status: int, message: str) -> None:
        safe_msg = html.escape(message)
        body = self._wrap_layout(
            title=f"Error {status}",
            content=f"""
            <div class="empty-state">
              <h2 class="empty-state-title">Error {status}</h2>
              <p class="empty-state-desc">{safe_msg}</p>
              <p style="margin-top: 1rem;"><a href="/">← Return to dashboard home</a></p>
            </div>
            """,
            breadcrumbs=[("Home", "/"), (f"Error {status}", "")],
            all_projects=[],
            current_project_id=None,
        )
        self._send_response_page(status, body)

    def do_HEAD(self) -> None:
        self.do_GET()

    def do_POST(self) -> None:
        self._reject_non_get()

    def do_PUT(self) -> None:
        self._reject_non_get()

    def do_DELETE(self) -> None:
        self._reject_non_get()

    def do_PATCH(self) -> None:
        self._reject_non_get()

    def _reject_non_get(self) -> None:
        self.send_response(HTTPStatus.METHOD_NOT_ALLOWED)
        self._send_security_headers("text/plain; charset=utf-8")
        self.send_header("Allow", "GET, HEAD")
        body = b"Method Not Allowed"
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_GET(self) -> None:
        if not self._validate_host():
            self._send_error_page(HTTPStatus.FORBIDDEN, "Forbidden: Invalid Host header.")
            return

        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # Static assets
        if path == "/static/app.css":
            self._serve_css()
            return

        conn = self._get_ro_conn()
        try:
            # Fetch all projects for the switcher in the header
            all_projects = [
                {"id": r["id"], "name": r["name"], "folder": Path(r["repo_path"]).name}
                for r in conn.execute(
                    "SELECT id, name, repo_path FROM projects ORDER BY name ASC"
                ).fetchall()
            ]

            if path in ("", "/"):
                self._handle_home(conn, all_projects)
                return

            if path in ("/about", "/about-learnloop"):
                self._handle_global_about(conn, all_projects)
                return

            # Match project routes: /p/<project_id>/...
            match_proj = re.match(r"^/p/([^/]+)(/.*)?$", path)
            if not match_proj:
                self._send_error_page(HTTPStatus.NOT_FOUND, "Page not found.")
                return

            project_id = match_proj.group(1)
            sub_path = match_proj.group(2) or "/"

            if not PROJECT_ID_REGEX.match(project_id):
                self._send_error_page(HTTPStatus.NOT_FOUND, "Invalid project ID.")
                return

            proj_row = conn.execute(
                "SELECT id, name, repo_path, created_at, last_briefing_at FROM projects WHERE id=?",
                (project_id,),
            ).fetchone()
            if not proj_row:
                self._send_error_page(HTTPStatus.NOT_FOUND, "Project not found.")
                return

            project = {
                "id": proj_row["id"],
                "name": proj_row["name"],
                "folder": Path(proj_row["repo_path"]).name,
                "repo_path": proj_row["repo_path"],
                "created_at": proj_row["created_at"],
                "last_briefing_at": proj_row["last_briefing_at"],
            }

            if sub_path in ("", "/"):
                self._handle_project_overview(conn, project, all_projects)
            elif sub_path.startswith("/items/"):
                item_key = sub_path[len("/items/") :]
                self._handle_item_detail(conn, project, item_key, all_projects)
            elif sub_path == "/concepts":
                self._handle_project_concepts(conn, project, all_projects)
            elif sub_path == "/docs":
                self._handle_project_docs_index(conn, project, all_projects)
            elif sub_path.startswith("/docs/"):
                doc_name = sub_path[len("/docs/") :]
                self._handle_project_doc(conn, project, doc_name, all_projects)
            elif sub_path in ("/about", "/about-learnloop"):
                self._handle_about_learnloop(conn, project, all_projects)
            else:
                self._send_error_page(HTTPStatus.NOT_FOUND, "Page not found.")
        finally:
            conn.close()

    def _serve_css(self) -> None:
        try:
            css_data = (
                importlib.resources.files("learnloop.dashboard.static").joinpath("app.css").read_bytes()
            )
            self.send_response(HTTPStatus.OK)
            self._send_security_headers("text/css; charset=utf-8")
            self.send_header("Content-Length", str(len(css_data)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(css_data)
        except Exception:
            self._send_error_page(HTTPStatus.NOT_FOUND, "CSS not found.")

    def _wrap_layout(
        self,
        title: str,
        content: str,
        breadcrumbs: list[tuple[str, str]],
        all_projects: list[dict[str, str]],
        current_project_id: str | None = None,
    ) -> str:
        safe_title = html.escape(title)

        # Build breadcrumbs HTML
        bc_items = []
        for idx, (label, link) in enumerate(breadcrumbs):
            safe_label = html.escape(label)
            if link and idx < len(breadcrumbs) - 1:
                bc_items.append(f'<a href="{html.escape(link, quote=True)}">{safe_label}</a>')
            else:
                bc_items.append(f"<span>{safe_label}</span>")
            if idx < len(breadcrumbs) - 1:
                bc_items.append('<span class="separator">/</span>')
        bc_html = "".join(bc_items)

        # Build project switcher dropdown items
        switcher_items = []
        for p in all_projects:
            pid = p["id"]
            pname = html.escape(p["name"])
            pfolder = html.escape(p["folder"])
            is_active = pid == current_project_id
            active_cls = " active" if is_active else ""
            active_pill = '<span class="item-active-pill">Current</span>' if is_active else ""
            switcher_items.append(
                f'<a href="/p/{pid}/" class="project-dropdown-item{active_cls}" title="{pfolder}">'
                f'<div class="item-title"><span>{pname}</span>{active_pill}</div>'
                f'<span class="item-folder">{pfolder}</span>'
                f'</a>'
            )
        dropdown_html = (
            "".join(switcher_items)
            if switcher_items
            else '<div class="project-dropdown-empty">No projects registered</div>'
        )

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title} — LearnLoop</title>
  <link rel="stylesheet" href="/static/app.css">
</head>
<body>
  <header class="app-header">
    <div class="header-inner">
      <div class="brand">
        <a href="/" style="color: inherit; text-decoration: none;">LearnLoop</a>
        <span class="brand-badge">Read-Only</span>
      </div>
      <div class="project-switcher">
        <div class="project-dropdown">
          <button class="project-dropdown-trigger" type="button" aria-haspopup="true" aria-expanded="false">
            <span class="dropdown-label">Projects</span>
            <span class="dropdown-badge">{len(all_projects)}</span>
            <span class="dropdown-arrow">▾</span>
          </button>
          <div class="project-dropdown-menu">
            <div class="dropdown-menu-header">Projects ({len(all_projects)})</div>
            <div class="dropdown-menu-items">
              {dropdown_html}
            </div>
          </div>
        </div>
      </div>
    </div>
  </header>
  <main class="container">
    <nav class="breadcrumbs" aria-label="Breadcrumbs">{bc_html}</nav>
    {content}
  </main>
</body>
</html>"""

    # --- Route Handlers ---

    def _handle_home(self, conn: sqlite3.Connection, all_projects: list[dict[str, str]]) -> None:
        rows = conn.execute(
            "SELECT id, name, repo_path, created_at, last_briefing_at "
            "FROM projects ORDER BY created_at DESC"
        ).fetchall()

        if not rows:
            content = """
            <div class="section-header">
              <h1 class="section-title">Projects</h1>
              <p class="section-subtitle">Read-only overview of your active learning projects.</p>
            </div>
            <div class="empty-state">
              <h2 class="empty-state-title">No projects registered yet</h2>
              <p class="empty-state-desc">Start building in your repo and call <code>start_project</code>
              with your AI agent to see project readiness and knowledge items here.</p>
            </div>
            """
            body = self._wrap_layout("Projects", content, [("Home", "/")], all_projects)
            self._send_response_page(HTTPStatus.OK, body)
            return

        cards_html = []
        for r in rows:
            pid = str(r["id"])
            pname = html.escape(r["name"])
            pfolder = html.escape(Path(r["repo_path"]).name)

            readiness = readiness_service.get_project_readiness(conn, pid, ingest=False)
            headline = html.escape(readiness["headline"])
            stale_count = readiness["stale_count"]
            due_count = readiness["due_count"]

            queue_waiting = count_queue_commits(r["repo_path"])
            queue_html = (
                f'<div class="panel-queue-hint">📦 {queue_waiting} commits waiting in queue</div>'
                if queue_waiting > 0
                else ""
            )

            last_act_row = conn.execute(
                "SELECT committed_at FROM commits WHERE project_id=? AND kind='commit' "
                "ORDER BY committed_at DESC LIMIT 1",
                (pid,),
            ).fetchone()
            if last_act_row:
                raw_time = str(last_act_row["committed_at"])
                last_activity = html.escape(raw_time[:19].replace("T", " "))
            else:
                last_activity = "None"

            card_desc = extract_project_description(r["repo_path"])
            card_desc_html = (
                f'<div style="font-size: 0.85rem; color: var(--text-muted); margin-bottom: 0.45rem; line-height: 1.35;">{html.escape(card_desc)}</div>'
                if card_desc
                else ""
            )

            cards_html.append(f"""
            <div class="card">
              <h2 class="card-title"><a href="/p/{pid}/">{pname}</a></h2>
              {card_desc_html}
              <div class="card-meta">Folder: <code>{pfolder}</code></div>
              <div class="card-headline">{headline}</div>
              {queue_html}
              <div class="card-stats">
                <span>🔥 <strong>{stale_count}</strong> stale</span>
                <span>📅 <strong>{due_count}</strong> due</span>
                <span style="margin-left: auto; color: var(--text-muted);">Active: {last_activity}</span>
              </div>
            </div>
            """)

        content = f"""
        <div class="section-header">
          <h1 class="section-title">Projects</h1>
          <p class="section-subtitle">Select a project to explore components, decisions, and readiness.</p>
        </div>
        <div class="cards-grid">
          {''.join(cards_html)}
        </div>
        """
        body = self._wrap_layout("Projects", content, [("Home", "/")], all_projects)
        self._send_response_page(HTTPStatus.OK, body)

    def _handle_project_overview(
        self,
        conn: sqlite3.Connection,
        project: dict[str, Any],
        all_projects: list[dict[str, str]],
    ) -> None:
        pid = project["id"]
        pname = html.escape(project["name"])
        pfolder = html.escape(project["folder"])

        readiness = readiness_service.get_project_readiness(conn, pid, ingest=False)
        stale_res = knowledge_service.list_stale_items(conn, pid, ingest=False)
        due_res = review_service.review_due(conn, pid, limit=10, ingest=False)

        queue_waiting = count_queue_commits(project["repo_path"])
        queue_hint = (
            f'<div class="panel-queue-hint">📦 <strong>{queue_waiting}</strong> '
            f"commits waiting in queue to be ingested.</div>"
            if queue_waiting > 0
            else ""
        )

        # Stale panel with git diff command
        stale_html = ""
        if stale_res["stale_items"]:
            items_lines = []
            for it in stale_res["stale_items"]:
                k = html.escape(it["key"])
                title = html.escape(it["title"])
                files = " ".join(html.escape(f) for f in it["files"])
                base_c = html.escape(it["baseline_commit"] or "HEAD~1")
                diff_cmd = f"git diff {base_c}..HEAD -- {files}"
                items_lines.append(f"""
                <li style="margin-bottom: 0.75rem;">
                  <strong><a href="/p/{pid}/items/{k}">{title}</a></strong> (<code>{k}</code>)
                  <code class="diff-command-box">{diff_cmd}</code>
                </li>
                """)
            stale_html = f"""
            <div class="panel panel-stale">
              <h2 class="panel-title">🔥 Stale Items ({len(stale_res['stale_items'])})</h2>
              <p style="font-size: 0.9rem; margin-bottom: 0.5rem;">
                Files changed after explanation. Inspect the changes using:
              </p>
              <ul style="list-style-type: none; margin-left: 0;">{''.join(items_lines)}</ul>
            </div>
            """

        # Due panel with review items
        due_html = ""
        if due_res["items"]:
            due_lines = []
            for it in due_res["items"]:
                k = html.escape(it["key"])
                title = html.escape(it["title"])
                due_lines.append(
                    f'<li><strong><a href="/p/{pid}/items/{k}">{title}</a></strong> (<code>{k}</code>)</li>'
                )
            due_html = f"""
            <div class="panel panel-due">
              <h2 class="panel-title">📅 Due for Review ({due_res['waiting']})</h2>
              <ul style="margin-left: 1.25rem;">{''.join(due_lines)}</ul>
            </div>
            """

        # Fetch knowledge items for table
        items_by_band: dict[str, list[dict[str, Any]]] = {
            "basic": [],
            "intermediate": [],
            "advanced": [],
        }
        item_rows = conn.execute(
            "SELECT id, key, title, kind, band, summary, status FROM knowledge_items "
            "WHERE project_id=? ORDER BY key ASC",
            (pid,),
        ).fetchall()

        for row in item_rows:
            band = str(row["band"]).lower()
            if band in items_by_band:
                exp_row = conn.execute(
                    "SELECT score, self_rating FROM explanations "
                    "WHERE item_id=? ORDER BY created_at DESC, id DESC LIMIT 1",
                    (row["id"],),
                ).fetchone()
                items_by_band[band].append(
                    {
                        "key": row["key"],
                        "title": row["title"],
                        "kind": row["kind"],
                        "summary": row["summary"],
                        "status": row["status"],
                        "score": exp_row["score"] if exp_row else None,
                        "self_rating": exp_row["self_rating"] if exp_row else None,
                    }
                )

        bands_html = []
        band_labels = [
            ("basic", "[B] Basic", "badge-basic"),
            ("intermediate", "[I] Intermediate", "badge-intermediate"),
            ("advanced", "[A] Advanced", "badge-advanced"),
        ]

        for bkey, blabel, bcls in band_labels:
            band_items = items_by_band[bkey]
            if not band_items:
                rows_html = (
                    '<tr><td colspan="4" style="text-align: center; color: var(--text-muted); '
                    'padding: 1.5rem;">No items in this band.</td></tr>'
                )
            else:
                r_list = []
                for it in band_items:
                    k = html.escape(it["key"])
                    title = html.escape(it["title"])
                    kind = html.escape(it["kind"])
                    st = it["status"]
                    st_icon = "✓" if st == "explained" else ("⚠" if st == "shaky" else "?")
                    st_badge = f'<span class="badge badge-{st}">{st_icon} {st.capitalize()}</span>'

                    rating_disp = f"★ {it['self_rating']}/5" if it["self_rating"] is not None else "—"
                    score_disp = f"{it['score']:.1f}" if it["score"] is not None else "—"
                    eval_html = (
                        f'<span class="rating-badge">{rating_disp}</span> '
                        f'<span style="color: var(--text-muted); font-size: 0.85rem;">'
                        f"(rubric: {score_disp})</span>"
                    )

                    r_list.append(f"""
                    <tr>
                      <td>
                        <strong><a href="/p/{pid}/items/{k}">{title}</a></strong><br>
                        <code style="font-size: 0.8rem;">{k}</code>
                      </td>
                      <td>{kind}</td>
                      <td>{st_badge}</td>
                      <td>{eval_html}</td>
                    </tr>
                    """)
                rows_html = "".join(r_list)

            bands_html.append(f"""
            <section class="band-section">
              <div class="band-header">
                <span class="badge {bcls}">{blabel}</span>
                <span style="font-size: 0.9rem; color: var(--text-muted); font-weight: normal;">
                  ({len(band_items)} parts)
                </span>
              </div>
              <table class="items-table">
                <thead>
                  <tr>
                    <th>Part & Key</th>
                    <th>Kind</th>
                    <th>Status</th>
                    <th>Self-Rating & Rubric</th>
                  </tr>
                </thead>
                <tbody>{rows_html}</tbody>
              </table>
            </section>
            """)

        # Project tech stack badges for header
        tech_rows = conn.execute(
            "SELECT ecosystem, name, version_spec, source_file FROM project_technologies "
            "WHERE project_id=? ORDER BY ecosystem ASC, name ASC",
            (pid,),
        ).fetchall()

        tag_rows = conn.execute(
            "SELECT DISTINCT it.tag FROM item_tags it "
            "JOIN knowledge_items ki ON it.item_id = ki.id "
            "WHERE ki.project_id=? ORDER BY it.tag ASC",
            (pid,),
        ).fetchall()

        tech_pills: list[str] = []
        for tr in tech_rows:
            safe_name = html.escape(tr["name"])
            safe_ver = f" ({html.escape(tr['version_spec'])})" if tr["version_spec"] else ""
            safe_src = html.escape(tr["source_file"])
            tech_pills.append(
                f'<span class="badge badge-tech-item" title="Manifest: [{safe_src}]">'
                f'<strong>{safe_name}</strong>{safe_ver}</span>'
            )

        tech_stack_html = (
            f'<div class="header-metadata-row project-tech-stack">'
            f'<span class="metadata-label">Stack:</span>'
            f'<div class="metadata-pills-wrap">{"".join(tech_pills)}</div>'
            f'</div>'
            if tech_pills
            else ""
        )

        tag_badges = "".join(
            f'<span class="badge badge-tag-item">'
            f'🏷️ {html.escape(r["tag"])}</span>'
            for r in tag_rows
        )
        tags_html = (
            f'<div class="header-metadata-row project-tags-bar">'
            f'<span class="metadata-label">Tags:</span>'
            f'<div class="metadata-pills-wrap">{tag_badges}</div>'
            f'</div>'
            if tag_rows
            else ""
        )

        # Did you know facts panel (Floating Micro-Learning Companion Widget)
        fact_rows = conn.execute(
            "SELECT id, topic, fact, source_url, source_title, retrieved_at, technology "
            "FROM project_facts WHERE project_id=? "
            "ORDER BY created_at DESC, id DESC LIMIT 10",
            (pid,),
        ).fetchall()

        facts_html = ""
        if fact_rows:
            num_facts = len(fact_rows)
            radio_inputs: list[str] = []
            slide_items: list[str] = []

            for idx, fr in enumerate(fact_rows):
                safe_topic = html.escape(fr["topic"])
                safe_fact = html.escape(fr["fact"])
                safe_title = html.escape(fr["source_title"])
                safe_url = html.escape(fr["source_url"], quote=True)
                retrieved_date = fr["retrieved_at"][:10]
                escaped_tech = html.escape(fr["technology"]) if fr["technology"] else ""
                tech_badge = (
                    f'<span class="badge badge-tech-pill">{escaped_tech}</span>'
                    if fr["technology"]
                    else ""
                )

                checked = "checked" if idx == 0 else ""
                radio_inputs.append(
                    f'<input type="radio" name="fact-tab-{pid}" id="fact-tab-{pid}-{idx}" '
                    f'class="fact-radio fact-radio-{idx}" {checked}>'
                )

                prev_idx = (idx - 1) % num_facts
                next_idx = (idx + 1) % num_facts

                flip_nav = ""
                if num_facts > 1:
                    flip_nav = f"""
                    <div class="fact-card-nav">
                      <label for="fact-tab-{pid}-{prev_idx}" class="fact-nav-btn prev-btn"
                        title="Previous Insight">❮</label>
                      <span class="fact-nav-counter">{idx + 1}/{num_facts}</span>
                      <label for="fact-tab-{pid}-{next_idx}" class="fact-nav-btn next-btn"
                        title="Next Insight">❯</label>
                    </div>
                    """

                slide_items.append(f"""
                <div class="fact-slide slide-{idx}">
                  <div class="fact-slide-header">
                    <div class="fact-tag-group">
                      <span class="badge badge-topic">{safe_topic}</span>
                      {tech_badge}
                    </div>
                    {flip_nav}
                  </div>
                  <p class="fact-text">{safe_fact}</p>
                  <div class="fact-slide-footer">
                    <span class="badge badge-agent-reported">Agent-reported: check the source</span>
                    <div class="fact-source-line">
                      <span>Source: <a href="{safe_url}" target="_blank"
                        rel="noopener noreferrer">{safe_title}</a></span>
                      <span class="fact-retrieved">(Retrieved: {retrieved_date})</span>
                    </div>
                  </div>
                </div>
                """)

            radios_str = "".join(radio_inputs)
            slides_str = "".join(slide_items)

            dots_html = ""
            if num_facts > 1:
                dots_labels = "".join(
                    f'<label for="fact-tab-{pid}-{d}" class="fact-dot dot-{d}" '
                    f'title="Insight {d + 1}"></label>'
                    for d in range(num_facts)
                )
                dots_html = f'<div class="fact-dots-container">{dots_labels}</div>'

            facts_html = f"""
            <aside class="floating-insight-widget">
              <input type="checkbox" id="insight-min-toggle-{pid}" class="insight-toggle-input" checked>
              {radios_str}
              <div class="insight-card-inner">
                <div class="insight-card-topbar">
                  <span class="insight-card-title">💡 Did You Know?</span>
                  <label for="insight-min-toggle-{pid}" class="insight-min-btn"
                    title="Minimize insight card">−</label>
                </div>
                <div class="insight-slides-container">
                  {slides_str}
                </div>
                {dots_html}
              </div>
              <label for="insight-min-toggle-{pid}" class="insight-floating-pill" title="Click to view insights">
                💡 Did You Know? ({num_facts})
              </label>
            </aside>
            """

        safe_repo_path = html.escape(str(project.get("repo_path", "")))
        proj_desc = extract_project_description(project.get("repo_path"))
        desc_html = (
            f'<p class="section-desc" style="font-size: 0.95rem; color: var(--text-main); margin: 0.25rem 0 0.35rem 0; line-height: 1.45;">'
            f'{html.escape(proj_desc)}</p>'
            if proj_desc
            else ""
        )
        content = f"""
        <div class="section-header">
          <h1 class="section-title">{pname}</h1>
          {desc_html}
          <p class="section-subtitle">Folder: <code>{safe_repo_path}</code></p>
          {tech_stack_html}
          {tags_html}
        </div>
        <nav class="project-subnav">
          <a href="/p/{pid}/" class="active">Overview</a>
          <a href="/p/{pid}/concepts">Concept Log</a>
          <a href="/p/{pid}/docs">Docs</a>
          <a href="/p/{pid}/about">About LearnLoop</a>
        </nav>
        {queue_hint}
        {stale_html}
        {due_html}
        {''.join(bands_html)}
        {facts_html}
        """
        body = self._wrap_layout(
            project["name"],
            content,
            [("Home", "/"), (project["name"], f"/p/{pid}/")],
            all_projects,
            current_project_id=pid,
        )
        self._send_response_page(HTTPStatus.OK, body)

    def _handle_item_detail(
        self,
        conn: sqlite3.Connection,
        project: dict[str, Any],
        item_key: str,
        all_projects: list[dict[str, str]],
    ) -> None:
        pid = project["id"]
        row = conn.execute(
            "SELECT id, key, title, kind, band, summary, status, depth FROM knowledge_items "
            "WHERE project_id=? AND key=?",
            (pid, item_key),
        ).fetchone()

        if not row:
            self._send_error_page(HTTPStatus.NOT_FOUND, f"Item '{item_key}' not found.")
            return

        item_id = row["id"]
        title = html.escape(row["title"])
        key = html.escape(row["key"])
        kind = html.escape(row["kind"])
        band = html.escape(row["band"])
        status = row["status"]
        depth = row["depth"]
        summary = html.escape(row["summary"])

        # Files
        files = [
            r["path"]
            for r in conn.execute(
                "SELECT path FROM item_files WHERE item_id=? ORDER BY path ASC", (item_id,)
            ).fetchall()
        ]
        files_html = (
            "".join(f"<li><code>{html.escape(f)}</code></li>" for f in files)
            if files
            else "<li><em>None tracked</em></li>"
        )

        # Tags
        tags = [
            r["tag"]
            for r in conn.execute(
                "SELECT tag FROM item_tags WHERE item_id=? ORDER BY tag ASC", (item_id,)
            ).fetchall()
        ]
        tags_html = (
            " ".join(
                f'<span class="badge" style="background: var(--surface-raised);">{html.escape(t)}</span>'
                for t in tags
            )
            if tags
            else "<em>None</em>"
        )

        # Explanations history
        exp_rows = conn.execute(
            "SELECT id, audience, depth, learner_text, score, self_rating, created_at "
            "FROM explanations WHERE item_id=? ORDER BY created_at DESC, id DESC",
            (item_id,),
        ).fetchall()

        if not exp_rows:
            exps_html = (
                '<div class="empty-state">'
                '<p class="empty-state-desc">No explain-backs recorded yet for this item.</p></div>'
            )
        else:
            exp_cards = []
            for e in exp_rows:
                rating_str = (
                    f"Self-Rating: ★ {e['self_rating']}/5"
                    if e["self_rating"] is not None
                    else "Self-Rating: unrated"
                )
                score_str = f"Rubric Score: {e['score']:.1f}"
                aud_str = html.escape(e["audience"])
                created_str = html.escape(e["created_at"][:19].replace("T", " "))
                text_escaped = html.escape(e["learner_text"])

                meta_sub = f"{aud_str} • Depth {e['depth']}/5 • {created_str}"
                exp_cards.append(f"""
                <div class="explanation-card">
                  <div style="display: flex; justify-content: space-between; font-size: 0.85rem;">
                    <div><strong>{rating_str}</strong> | {score_str}</div>
                    <div style="color: var(--text-muted);">{meta_sub}</div>
                  </div>
                  <blockquote style="font-size: 0.95rem; margin-top: 0.5rem;">
                    {text_escaped}
                  </blockquote>
                </div>
                """)
            exps_html = "".join(exp_cards)

        st_icon = "✓" if status == "explained" else ("⚠" if status == "shaky" else "?")
        st_badge = f'<span class="badge badge-{status}">{st_icon} {status.capitalize()}</span>'
        band_upper = band.upper()

        content = f"""
        <div class="section-header">
          <h1 class="section-title">{title}</h1>
          <p class="section-subtitle">Key: <code>{key}</code></p>
        </div>
        <div class="detail-meta-box">
          <div class="meta-row"><span class="meta-label">Status:</span> {st_badge}</div>
          <div class="meta-row">
            <span class="meta-label">Band:</span>
            <span class="badge badge-{band}">[{band_upper}]</span>
          </div>
          <div class="meta-row"><span class="meta-label">Kind:</span> {kind}</div>
          <div class="meta-row"><span class="meta-label">Depth:</span> {depth}/5</div>
          <div class="meta-row"><span class="meta-label">Tags:</span> <div>{tags_html}</div></div>
          <div class="meta-row"><span class="meta-label">Summary:</span> <div>{summary}</div></div>
          <div class="meta-row">
            <span class="meta-label">Tracked Files:</span>
            <ul style="margin-left: 1.25rem;">{files_html}</ul>
          </div>
        </div>
        <h2 style="font-size: 1.25rem; font-weight: 700; margin-bottom: 0.75rem;">Explanations History</h2>
        {exps_html}
        """

        body = self._wrap_layout(
            f"{row['title']} ({key})",
            content,
            [("Home", "/"), (project["name"], f"/p/{pid}/"), (f"Item: {key}", "")],
            all_projects,
            current_project_id=pid,
        )
        self._send_response_page(HTTPStatus.OK, body)

    def _handle_project_concepts(
        self,
        conn: sqlite3.Connection,
        project: dict[str, Any],
        all_projects: list[dict[str, str]],
    ) -> None:
        pid = project["id"]
        raw_md = generate_concept_markdown(conn, pid)
        rendered_html = render_markdown(raw_md)

        content = f"""
        <div class="section-header">
          <h1 class="section-title">Concept Log: {html.escape(project['name'])}</h1>
          <p class="section-subtitle">
            Rendered directly from the database knowledge items and explain-backs.
          </p>
        </div>
        <nav class="project-subnav">
          <a href="/p/{pid}/">Overview</a>
          <a href="/p/{pid}/concepts" class="active">Concept Log</a>
          <a href="/p/{pid}/docs">Docs</a>
          <a href="/p/{pid}/about">About LearnLoop</a>
        </nav>
        <article class="markdown-body">
          {rendered_html}
        </article>
        """
        body = self._wrap_layout(
            f"Concepts — {project['name']}",
            content,
            [("Home", "/"), (project["name"], f"/p/{pid}/"), ("Concept Log", "")],
            all_projects,
            current_project_id=pid,
        )
        self._send_response_page(HTTPStatus.OK, body)

    def _handle_project_docs_index(
        self,
        conn: sqlite3.Connection,
        project: dict[str, Any],
        all_projects: list[dict[str, str]],
    ) -> None:
        pid = project["id"]
        doc_names = list_safe_learn_docs(project["repo_path"])

        if not doc_names:
            docs_list_html = (
                '<div class="empty-state"><p class="empty-state-desc">'
                "No markdown documents found directly in <code>.learn/</code>.</p></div>"
            )
        else:
            items = []
            for name in doc_names:
                safe_name = html.escape(name)
                items.append(
                    f'<li><strong><a href="/p/{pid}/docs/{safe_name}">{safe_name}</a></strong></li>'
                )
            docs_list_html = f'<ul style="margin-left: 1.5rem; line-height: 2;">{"".join(items)}</ul>'

        content = f"""
        <div class="section-header">
          <h1 class="section-title">Documents: {html.escape(project['name'])}</h1>
          <p class="section-subtitle">Markdown files located directly in <code>.learn/</code>.</p>
        </div>
        <nav class="project-subnav">
          <a href="/p/{pid}/">Overview</a>
          <a href="/p/{pid}/concepts">Concept Log</a>
          <a href="/p/{pid}/docs" class="active">Docs</a>
          <a href="/p/{pid}/about">About LearnLoop</a>
        </nav>
        <div class="card" style="margin-top: 1rem;">
          {docs_list_html}
        </div>
        """
        body = self._wrap_layout(
            f"Docs — {project['name']}",
            content,
            [("Home", "/"), (project["name"], f"/p/{pid}/"), ("Docs", "")],
            all_projects,
            current_project_id=pid,
        )
        self._send_response_page(HTTPStatus.OK, body)

    def _handle_project_doc(
        self,
        conn: sqlite3.Connection,
        project: dict[str, Any],
        doc_name: str,
        all_projects: list[dict[str, str]],
    ) -> None:
        pid = project["id"]
        content_text = read_safe_learn_doc(project["repo_path"], doc_name)
        if content_text is None:
            self._send_error_page(
                HTTPStatus.NOT_FOUND, f"Document '{doc_name}' not found or inaccessible."
            )
            return

        rendered_html = render_markdown(content_text)
        safe_doc_name = html.escape(doc_name)

        content = f"""
        <div class="section-header">
          <h1 class="section-title">{safe_doc_name}</h1>
          <p class="section-subtitle">Project: {html.escape(project['name'])}</p>
        </div>
        <nav class="project-subnav">
          <a href="/p/{pid}/">Overview</a>
          <a href="/p/{pid}/concepts">Concept Log</a>
          <a href="/p/{pid}/docs">Docs</a>
          <a href="/p/{pid}/about">About LearnLoop</a>
        </nav>
        <article class="markdown-body">
          {rendered_html}
        </article>
        """
        body = self._wrap_layout(
            f"{doc_name} — {project['name']}",
            content,
            [("Home", "/"), (project["name"], f"/p/{pid}/"), ("Docs", f"/p/{pid}/docs"), (doc_name, "")],
            all_projects,
            current_project_id=pid,
        )
        self._send_response_page(HTTPStatus.OK, body)

    def _handle_about_learnloop(
        self,
        conn: sqlite3.Connection,
        project: dict[str, Any],
        all_projects: list[dict[str, str]],
    ) -> None:
        pid = project["id"]
        pname = html.escape(project["name"])
        content = self._render_about_learnloop_content(pid=pid, pname=pname)
        body = self._wrap_layout(
            f"About LearnLoop — {project['name']}",
            content,
            [("Home", "/"), (project["name"], f"/p/{pid}/"), ("About LearnLoop", "")],
            all_projects,
            current_project_id=pid,
        )
        self._send_response_page(HTTPStatus.OK, body)

    def _handle_global_about(
        self,
        conn: sqlite3.Connection,
        all_projects: list[dict[str, str]],
    ) -> None:
        content = self._render_about_learnloop_content(pid=None, pname=None)
        body = self._wrap_layout(
            "About LearnLoop",
            content,
            [("Home", "/"), ("About LearnLoop", "")],
            all_projects,
            current_project_id=None,
        )
        self._send_response_page(HTTPStatus.OK, body)

    def _render_about_learnloop_content(self, pid: str | None, pname: str | None) -> str:
        if pid and pname:
            header_and_nav = f"""
            <div class="section-header">
              <h1 class="section-title">About LearnLoop</h1>
              <p class="section-subtitle">
                Project: <strong>{pname}</strong> — The AI Learning Companion that transforms AI-assisted coding into true technical mastery.
              </p>
            </div>
            <nav class="project-subnav">
              <a href="/p/{pid}/">Overview</a>
              <a href="/p/{pid}/concepts">Concept Log</a>
              <a href="/p/{pid}/docs">Docs</a>
              <a href="/p/{pid}/about" class="active">About LearnLoop</a>
            </nav>
            """
        else:
            header_and_nav = """
            <div class="section-header">
              <h1 class="section-title">About LearnLoop</h1>
              <p class="section-subtitle">
                The AI Learning Companion that transforms AI-assisted coding into true technical mastery.
              </p>
            </div>
            """

        return f"""
        {header_and_nav}
        <div class="about-hero">
          <div class="about-hero-title">💡 Why LearnLoop Exists</div>
          <p class="about-hero-desc">
            When an AI coding agent writes code that runs on the first try, reading it feels effortless.
            This creates the <strong>AI Illusion of Competence</strong>: passive recognition masquerading as genuine mastery.
            LearnLoop bridges this gap by tracking what the AI built against actual Git commits, capturing your intent,
            and prompting short, targeted explain-backs so you can defend every decision with total confidence.
          </p>
        </div>

        <section class="about-section">
          <div class="about-section-header">
            <span class="about-section-badge">Problem Statement</span>
            <h2>The "AI Illusion of Competence"</h2>
          </div>
          <div class="about-grid-3">
            <div class="about-card">
              <div class="about-card-title">🧠 Passive Reading vs. Active Recall</div>
              <div class="about-card-body">
                Cognitive psychology proves that recognizing code activates shallow familiarity rather than deep retrieval.
                Because an AI-generated solution looks obvious in hindsight, developers mistakenly believe they could build it themselves from scratch.
              </div>
            </div>
            <div class="about-card">
              <div class="about-card-title">🎙️ The Defense & Review Blindspot</div>
              <div class="about-card-body">
                In technical interviews, architecture reviews, and high-stakes production outages, the AI prompt box is absent.
                Engineers who passively commit AI-written code often struggle to articulate trade-offs, edge cases, and architectural rationale.
              </div>
            </div>
            <div class="about-card">
              <div class="about-card-title">📦 Git's Comprehension Blindness</div>
              <div class="about-card-body">
                Traditional Git history records <em>what</em> code was merged, but has zero visibility into <em>who understands it</em>.
                A commit history full of complex abstractions says nothing about whether the engineer owns the codebase.
              </div>
            </div>
          </div>
          <div class="about-quote">
            “True technical mastery isn’t having working code in a repository—it’s being able to defend every architectural decision, concurrency lock, and trade-off without the AI.”
          </div>
        </section>

        <section class="about-section">
          <div class="about-section-header">
            <span class="about-section-badge">Solution</span>
            <h2>The LearnLoop Engine</h2>
          </div>
          <div class="about-grid-3">
            <div class="about-card">
              <div class="about-card-title">🛡️ Exposure vs. Mastery</div>
              <div class="about-card-body">
                <strong>Exposure</strong> (what the AI built) is automatically verified against concrete Git commits.
                <strong>Mastery</strong> is proven through your own explain-backs and self-ratings.
              </div>
            </div>
            <div class="about-card">
              <div class="about-card-title">📍 Grounded in Real Files</div>
              <div class="about-card-body">
                Every concept in LearnLoop is anchored to physical filepaths (<code>src/...</code>) and commit SHAs—not abstract, disconnected textbook trivia.
              </div>
            </div>
            <div class="about-card">
              <div class="about-card-title">🔄 Derived Staleness Engine</div>
              <div class="about-card-body">
                When new commits touch files you previously explained, LearnLoop automatically flags them as <strong>Stale</strong>, prompting a quick refresh before mental decay sets in.
              </div>
            </div>
            <div class="about-card">
              <div class="about-card-title">📈 SM-2 Spaced Repetition</div>
              <div class="about-card-body">
                Utilizes the SuperMemo SM-2 interval algorithm to prompt review questions right when memory decay begins, converting fragile short-term insights into permanent long-term memory.
              </div>
            </div>
            <div class="about-card">
              <div class="about-card-title">☕ Calm & Non-Intrusive</div>
              <div class="about-card-body">
                Zero guilt trips, notifications, or gaming streaks. Morning briefings take ~60 seconds, and spaced reviews are pulled on demand whenever you have time.
              </div>
            </div>
            <div class="about-card">
              <div class="about-card-title">🔒 100% Local-First Privacy</div>
              <div class="about-card-body">
                All data resides in a local SQLite database (<code>~/.learnloop/learnloop.db</code>). No cloud telemetry, no code uploads, and a read-only zero-JS dashboard.
              </div>
            </div>
          </div>
        </section>

        <section class="about-section">
          <div class="about-section-header">
            <span class="about-section-badge">Reference</span>
            <h2>Complete MCP Tool Suite</h2>
          </div>
          <div class="tools-table-container">
            <table class="tools-table">
              <thead>
                <tr>
                  <th>Category</th>
                  <th>Tool Name</th>
                  <th>Description & Purpose</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>Onboarding & Tour</strong></td>
                  <td><code>get_project_tour</code></td>
                  <td>Generates an interactive, bounded architectural tour of entry points, directory structure, and core components from basic to advanced.</td>
                </tr>
                <tr>
                  <td><strong>Onboarding & Tour</strong></td>
                  <td><code>get_session_briefing</code></td>
                  <td>Delivers a 60-second morning catch-up summarizing recent commits, explain-back readiness, and the single recommended next action.</td>
                </tr>
                <tr>
                  <td><strong>Capture & Reconcile</strong></td>
                  <td><code>start_skill_session</code></td>
                  <td>Declares intent before coding, recording target files, skills involved, and the architectural <em>why</em> behind the change.</td>
                </tr>
                <tr>
                  <td><strong>Capture & Reconcile</strong></td>
                  <td><code>log_decision</code></td>
                  <td>Logs deliberate architectural choices and trade-offs between concrete alternatives (e.g., PostgreSQL vs SQLite, Polling vs WebSockets).</td>
                </tr>
                <tr>
                  <td><strong>Capture & Reconcile</strong></td>
                  <td><code>ingest_queue</code></td>
                  <td>Reconciles commit metadata deposited into <code>.learn/queue/</code> by the non-blocking Git post-commit hook against declared intents.</td>
                </tr>
                <tr>
                  <td><strong>Knowledge & Mastery</strong></td>
                  <td><code>register_knowledge_item</code></td>
                  <td>Registers a key conceptual component, architectural pattern, or tricky bug fix anchored to tracked repository files (Basic, Intermediate, or Advanced).</td>
                </tr>
                <tr>
                  <td><strong>Knowledge & Mastery</strong></td>
                  <td><code>record_explanation</code></td>
                  <td>Records your explain-back in your own words, paired with an honest 1–5 confidence rating to establish your comprehension baseline.</td>
                </tr>
                <tr>
                  <td><strong>Knowledge & Mastery</strong></td>
                  <td><code>list_stale_items</code></td>
                  <td>Surfaces concepts whose underlying source files have been modified by newer Git commits since you last explained them.</td>
                </tr>
                <tr>
                  <td><strong>Spaced Repetition</strong></td>
                  <td><code>review_due</code></td>
                  <td>Pulls knowledge items due for active review, scheduling retention checks according to the SuperMemo SM-2 algorithm.</td>
                </tr>
                <tr>
                  <td><strong>Spaced Repetition</strong></td>
                  <td><code>record_review</code></td>
                  <td>Updates recall scores, intervals, and ease factors based on your answers to active review questions.</td>
                </tr>
                <tr>
                  <td><strong>Spaced Repetition</strong></td>
                  <td><code>snooze_item</code></td>
                  <td>Politely defers an item when you are in flow or facing a deadline, without resetting your spaced repetition progress.</td>
                </tr>
                <tr>
                  <td><strong>Discovery & Trivia</strong></td>
                  <td><code>refresh_technologies</code></td>
                  <td>Deterministically scans package manifests (<code>pyproject.toml</code>, <code>package.json</code>, etc.) to keep your tech stack up to date.</td>
                </tr>
                <tr>
                  <td><strong>Discovery & Trivia</strong></td>
                  <td><code>add_did_you_know</code></td>
                  <td>Curates verified, sourced technical trivia, language origins, spec evolutions, or pop-culture connections for the floating companion.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section class="about-section">
          <div class="about-section-header">
            <span class="about-section-badge">Best Practices</span>
            <h2>How to Use LearnLoop to Get the Most Out of It</h2>
          </div>
          <div class="about-workflow-list">
            <div class="about-workflow-step">
              <div class="step-num-pill">1</div>
              <div class="step-content">
                <h3>Start Every Session with a 60-Second Briefing</h3>
                <p>
                  Before writing any new code, ask your agent: <em>“Give me the session briefing”</em> or run <code>learnloop briefing</code> in your terminal.
                  Review recent commits and take care of the single recommended review question if one is due.
                </p>
              </div>
            </div>
            <div class="about-workflow-step">
              <div class="step-num-pill">2</div>
              <div class="step-content">
                <h3>Take the Codebase Tour When Onboarding</h3>
                <p>
                  When starting a new project or returning after a break, ask: <em>“Give me a tour of this project”</em>.
                  LearnLoop will walk you through entry points, configuration manifests, and core abstractions from simple to complex.
                </p>
              </div>
            </div>
            <div class="about-workflow-step">
              <div class="step-num-pill">3</div>
              <div class="step-content">
                <h3>Have Your Agent Declare Intent & Log Architectural Decisions</h3>
                <p>
                  Before your AI writes a substantial piece of code, ensure it calls <code>start_skill_session</code> with the files to touch and why.
                  When choosing between alternatives (e.g. libraries, database schemas, API styles), ensure it calls <code>log_decision</code>.
                  Months from now, you’ll never have to wonder why an architectural path was taken.
                </p>
              </div>
            </div>
            <div class="about-workflow-step">
              <div class="step-num-pill">4</div>
              <div class="step-content">
                <h3>Commit Frequently: Git is the Proof of Outcome</h3>
                <p>
                  Never log what the agent merely "attempted" as learning. LearnLoop verifies exposure only when you commit code.
                  The silent Git post-commit hook logs commits into <code>.learn/queue/</code> without adding any latency to your Git workflow.
                </p>
              </div>
            </div>
            <div class="about-workflow-step">
              <div class="step-num-pill">5</div>
              <div class="step-content">
                <h3>Explain It Back in Your Own Words</h3>
                <p>
                  Whenever an important component is completed or a subtle bug is resolved, register it with <code>register_knowledge_item</code>.
                  Then take 60 seconds to explain how it works in your own words using <code>record_explanation</code>.
                  Self-rating your confidence (1 to 5) turns passive AI code delivery into active cognitive synthesis.
                </p>
              </div>
            </div>
            <div class="about-workflow-step">
              <div class="step-num-pill">6</div>
              <div class="step-content">
                <h3>Practice Spaced Reviews & Mock Interviews</h3>
                <p>
                  Once a week or before an upcoming interview or team demo, ask your agent: <em>“Review due concepts with me”</em> or <em>“Run a mock interview on this project”</em>.
                  Your AI will ask targeted questions one at a time, test your understanding, and cement the knowledge into long-term recall.
                </p>
              </div>
            </div>
          </div>
        </section>

        <section class="about-section">
          <div class="about-section-header">
            <span class="about-section-badge">Security & Architecture</span>
            <h2>Security, Privacy & Local-First Design</h2>
          </div>
          <div class="about-grid-3">
            <div class="about-card">
              <div class="about-card-title">🔐 Strict Read-Only Dashboard</div>
              <div class="about-card-body">
                The local web dashboard (<code>127.0.0.1:8765</code>) connects to SQLite with <code>?mode=ro</code>.
                It uses a zero-JavaScript architecture, strict Content Security Policy (<code>default-src 'none'</code>), and mandatory HTML escaping.
              </div>
            </div>
            <div class="about-card">
              <div class="about-card-title">🛡️ Secret Redaction Engine</div>
              <div class="about-card-body">
                LearnLoop applies automated regex sanitization across free-text explanations and commit messages to prevent accidental logging of API keys, bearer tokens, and credentials.
              </div>
            </div>
            <div class="about-card">
              <div class="about-card-title">📄 Pure Markdown Artifacts</div>
              <div class="about-card-body">
                Zero proprietary lock-in. LearnLoop atomically generates clean, portable Markdown files in your repository’s <code>.learn/concepts.md</code> and <code>.learn/docs/</code>.
              </div>
            </div>
          </div>
        </section>
        """


class DashboardServer(http.server.ThreadingHTTPServer):
    """Threading HTTPServer with allow_reuse_address disabled to prevent port collisions/hijacking."""

    allow_reuse_address = False
    daemon_threads = True


def run_dashboard_server(port: int = 8765, db_path: Path | None = None) -> int:
    """Run the read-only dashboard HTTP server on 127.0.0.1:<port>."""
    from learnloop.config import Settings

    settings = Settings.load()
    resolved_db_path = db_path or settings.db_path

    # Verify database exists and migration version is up-to-date
    if not resolved_db_path.exists():
        sys.stderr.write("Error: database does not exist. Run learnloop first.\n")
        return 1

    # Check migration version
    required_version = get_required_migration_version()
    try:
        conn = sqlite3.connect(resolved_db_path.resolve().as_uri() + "?mode=ro", uri=True)
        current_version = conn.execute("PRAGMA user_version").fetchone()[0]
        conn.close()
        if current_version < required_version:
            sys.stderr.write("run: learnloop doctor\n")
            return 1
    except sqlite3.OperationalError as exc:
        sys.stderr.write(f"Error opening database: {exc}\n")
        return 1

    DashboardHandler.server_port = port
    DashboardHandler.db_path = resolved_db_path

    try:
        server = DashboardServer(("127.0.0.1", port), DashboardHandler)
    except OSError as exc:
        sys.stderr.write(f"Error: port {port} is already in use ({exc}).\n")
        return 1

    sys.stdout.write(f"LearnLoop dashboard running at http://127.0.0.1:{port}/\n")
    sys.stdout.flush()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

    return 0
