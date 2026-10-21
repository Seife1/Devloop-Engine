"""CLI. `learnloop` with no arguments starts the MCP server (stdio).

`record-commit` is called by the git hook: it must be fast and must NEVER fail the commit.
"""

from __future__ import annotations

import argparse
import sqlite3
import stat
import subprocess
import sys

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from pathlib import Path

from learnloop.logging import setup_logging

HOOK_MARKER = "# learnloop-hook"

HOOK_TEMPLATE_PYTHON = (
    "#!/bin/sh\n"
    f"{HOOK_MARKER}\n"
    "# Fast, non-blocking, never fails the commit.\n"
    "# Writes a redacted metadata record to .learn/queue/.\n"
    '( "{python}" -m learnloop record-commit '
    '--repo "$(git rev-parse --show-toplevel)" ) >/dev/null 2>&1 &\n'
    "exit 0\n"
)
HOOK_TEMPLATE = HOOK_TEMPLATE_PYTHON

HOOK_TEMPLATE_BINARY = (
    "#!/bin/sh\n"
    f"{HOOK_MARKER}\n"
    "# Fast, non-blocking, never fails the commit.\n"
    "# Writes a redacted metadata record to .learn/queue/.\n"
    '( "{binary}" record-commit '
    '--repo "$(git rev-parse --show-toplevel)" ) >/dev/null 2>&1 &\n'
    "exit 0\n"
)


def _hook_text(executable: str | None = None) -> str:
    """Generate the post-commit hook body.

    Single source of truth for hook content. Uses the absolute interpreter or binary path
    so the hook works even when the executable is not on PATH (common on Windows).
    Forward slashes and quoting for sh compatibility.
    """
    exe = (executable if executable is not None else sys.executable).replace("\\", "/")
    if getattr(sys, "frozen", False):
        return HOOK_TEMPLATE_BINARY.format(binary=exe)
    return HOOK_TEMPLATE_PYTHON.format(python=exe)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True, timeout=10
    ).stdout


def cmd_serve() -> int:
    from learnloop.server import build_server

    setup_logging()
    build_server().run()  # stdio transport
    return 0


def cmd_dashboard(port: int = 8765, use_gui: bool = False) -> int:
    if use_gui:
        from learnloop.gui import is_gui_available, launch_desktop_gui

        if is_gui_available():
            return launch_desktop_gui(port=port, route="/", hide_console=True)

    from learnloop.dashboard.server import run_dashboard_server

    return run_dashboard_server(port=port)


def cmd_gui(port: int = 8765, route: str = "/setup", hide_console: bool = True) -> int:
    from learnloop.gui import launch_desktop_gui

    return launch_desktop_gui(port=port, route=route, hide_console=hide_console)


def cmd_setup(port: int = 8765, open_browser: bool = True, use_gui: bool = True) -> int:
    if use_gui and open_browser:
        from learnloop.gui import is_gui_available, launch_desktop_gui

        if is_gui_available():
            return launch_desktop_gui(port=port, route="/setup", hide_console=True)

    import threading
    import time
    from learnloop.dashboard.server import run_dashboard_server

    if open_browser:
        def _launch_browser():
            time.sleep(0.6)
            try:
                import webbrowser
                webbrowser.open(f"http://127.0.0.1:{port}/setup")
            except Exception:
                pass

        threading.Thread(target=_launch_browser, daemon=True).start()

    return run_dashboard_server(port=port)


def cmd_record_commit(repo: Path) -> int:
    try:
        from learnloop.capture.queue import write_queue_entry
        from learnloop.domain import clock

        sha = _git(repo, "rev-parse", "HEAD").strip()
        message = _git(repo, "log", "-1", "--format=%s")
        committed = clock.iso(clock.parse(_git(repo, "log", "-1", "--format=%cI").strip()))
        files = [
            f
            for f in _git(
                repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "--root", "HEAD"
            ).splitlines()
            if f
        ]
        write_queue_entry(repo, sha, message.strip(), files, committed)
    except Exception as exc:  # noqa: BLE001 - a learning tool must never break `git commit`
        sys.stderr.write(f"learnloop: skipped ({exc})\n")
    return 0


def cmd_backfill(repo: Path, limit: int = 50) -> int:
    try:
        import hashlib

        from learnloop.capture.queue import MAX_FILES_BACKFILL, write_queue_entry
        from learnloop.capture.redaction import is_ignored
        from learnloop.domain import clock

        if not (repo / ".git").is_dir():
            sys.stderr.write("Not a git repository root; backfill skipped.\n")
            return 1

        head_sha = _git(repo, "rev-parse", "HEAD").strip()
        if not head_sha:
            sys.stderr.write("Empty git repository; backfill skipped.\n")
            return 0

        commit_shas = [
            s.strip()
            for s in _git(repo, "log", f"-{limit}", "--format=%H").splitlines()
            if s.strip()
        ]
        written = 0
        for sha in commit_shas:
            message = _git(repo, "log", "-1", "--format=%s", sha).strip()
            raw_committed = _git(repo, "log", "-1", "--format=%cI", sha).strip()
            committed = clock.iso(clock.parse(raw_committed))
            files = [
                f
                for f in _git(
                    repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "--root", sha
                ).splitlines()
                if f
            ]
            write_queue_entry(repo, sha, message, files, committed, origin="backfill")
            written += 1

        raw_tracked = [f for f in _git(repo, "ls-files").splitlines() if f]
        tracked = [f for f in raw_tracked if not is_ignored(f)][:MAX_FILES_BACKFILL]
        snapshot_sha = hashlib.sha1(f"learnloop:backfill:snapshot:{head_sha}".encode()).hexdigest()
        head_committed = clock.iso(clock.parse(_git(repo, "log", "-1", "--format=%cI", head_sha).strip()))
        write_queue_entry(
            repo,
            snapshot_sha,
            "learnloop: tracked files snapshot",
            tracked,
            head_committed,
            origin="backfill",
            kind="snapshot",
            max_files=MAX_FILES_BACKFILL,
        )
        sys.stderr.write(f"Backfilled {written} commits + tracked snapshot to .learn/queue/\n")
        return 0
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"learnloop backfill failed: {exc}\n")
        return 1


def _find_project_id(conn: sqlite3.Connection, repo: Path) -> str | None:
    repo_abs = str(repo.resolve())
    row = conn.execute(
        "SELECT id FROM projects WHERE repo_path=? COLLATE NOCASE"
        " ORDER BY (SELECT COUNT(*) FROM knowledge_items WHERE project_id=projects.id) DESC,"
        " created_at DESC LIMIT 1",
        (repo_abs,),
    ).fetchone()
    if not row:
        row = conn.execute(
            "SELECT id FROM projects WHERE repo_path=? COLLATE NOCASE LIMIT 1", (str(repo),)
        ).fetchone()
    return row["id"] if row else None


def cmd_concepts(repo: Path) -> int:
    try:
        from learnloop.config import Settings
        from learnloop.journal.concept_log import regenerate_concept_log
        from learnloop.persistence.db import connect

        settings = Settings.load()
        conn = connect(settings.db_path)
        try:
            project_id = _find_project_id(conn, repo)
            if not project_id:
                sys.stderr.write(f"No project registered for {repo}.\n")
                return 1
            written = regenerate_concept_log(conn, project_id, repo)
            if written:
                sys.stderr.write(f"Regenerated {repo / '.learn' / 'concepts.md'}\n")
            else:
                sys.stderr.write(f"Skipped regenerating concepts.md for {repo}\n")
            return 0
        finally:
            conn.close()
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"learnloop concepts failed: {exc}\n")
        return 1


def cmd_review(repo: Path) -> int:
    try:
        from learnloop.config import Settings
        from learnloop.persistence.db import connect
        from learnloop.services.review_service import review_due

        settings = Settings.load()
        conn = connect(settings.db_path)
        try:
            project_id = _find_project_id(conn, repo)
            if not project_id:
                sys.stderr.write(f"No project registered for {repo}.\n")
                return 1
            res = review_due(conn, project_id, limit=3)
            items = res["items"]
            waiting = res["waiting"]
            if not items:
                sys.stdout.write("No knowledge items due for review today.\n")
                return 0
            sys.stdout.write("Knowledge items due for review:\n")
            for it in items:
                stale_marker = " [STALE]" if it.get("is_stale") else ""
                key, title, d = it["key"], it["title"], it["depth_to_ask"]
                sys.stdout.write(f"  • {key}: {title} (depth {d}){stale_marker}\n")
                if it.get("summary"):
                    sys.stdout.write(f"    {it['summary']}\n")
            if waiting > 0:
                sys.stdout.write(f"\n{waiting} more items waiting for future sessions.\n")
            return 0
        finally:
            conn.close()
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"learnloop review failed: {exc}\n")
        return 1


def cmd_briefing(repo: Path) -> int:
    try:
        from learnloop.config import Settings
        from learnloop.persistence.db import connect
        from learnloop.services.briefing_service import get_session_briefing

        settings = Settings.load()
        conn = connect(settings.db_path)
        try:
            project_id = _find_project_id(conn, repo)
            if not project_id:
                sys.stderr.write(f"No project registered for {repo}.\n")
                return 1
            b = get_session_briefing(conn, project_id)
            changes = b["changes_since_briefing"]
            sys.stdout.write("LearnLoop Session Briefing:\n")
            sys.stdout.write(f"  New commits: {changes['new_commits']}\n")
            sys.stdout.write(f"  Unexplained commits: {changes['unexplained_commits']}\n")
            sys.stdout.write(f"  Stale items: {changes['stale_items_count']}\n")
            sys.stdout.write(f"  Due for review: {len(b['due'])} (waiting: {b['waiting']})\n")
            sys.stdout.write(f"  Suggested next action: {b['suggested_next']}\n")
            sys.stdout.write(
                "\nNote: Overdue items are simply re-spaced; there is never an urgent backlog or penalty.\n"
            )
            return 0
        finally:
            conn.close()
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"learnloop briefing failed: {exc}\n")
        return 1


def cmd_init(repo: Path, integrate: bool = False, in_repo: bool = False) -> int:
    from learnloop.journal.concept_log import init_concept_log

    learn = repo / ".learn"
    (learn / "queue").mkdir(parents=True, exist_ok=True)
    (learn / ".gitignore").write_text("queue/\n", encoding="utf-8")
    init_concept_log(repo)

    if in_repo:
        from learnloop.persistence.db import connect
        db_file = learn / "learnloop.db"
        conn = connect(db_file)
        conn.close()
        sys.stderr.write(f"Initialised in-repo database: {db_file}\n")

    hook = repo / ".git" / "hooks" / "post-commit"
    if not (repo / ".git").is_dir():
        sys.stderr.write("Notice: Not a git repository root; created .learn/concepts.md only.\n")
        sys.stderr.write("Tip: Run `git init` and make your first commit to activate LearnLoop tracking.\n")
        if integrate:
            from learnloop.integrator import LearnLoopIntegrator
            LearnLoopIntegrator().run(["--all"])
        return 1
    body = _hook_text()
    if hook.exists() and HOOK_MARKER not in hook.read_text("utf-8"):
        sys.stderr.write(f"{hook} already exists and isn't ours; add `learnloop record-commit` manually.\n")
        if integrate:
            from learnloop.integrator import LearnLoopIntegrator
            LearnLoopIntegrator().run(["--all"])
        return 1
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_bytes(body.encode("utf-8"))
    hook.chmod(hook.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    sys.stderr.write(f"Initialised {learn} and installed post-commit hook.\n")
    sys.stderr.write("Tip: Run `git commit` as you work so LearnLoop can track what your AI builds!\n")

    if integrate:
        from learnloop.integrator import LearnLoopIntegrator
        LearnLoopIntegrator().run(["--all"])

    return 0


def cmd_integrate(args: list[str]) -> int:
    try:
        from learnloop.integrator import LearnLoopIntegrator
        integrator = LearnLoopIntegrator()
        integrator.run(args)
        return 0
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"learnloop integrate failed: {exc}\n")
        return 1


def cmd_doctor() -> int:
    import re
    import sqlite3 as _sqlite3

    from learnloop.config import Settings
    from learnloop.persistence.db import connect

    sys.stderr.write(f"sqlite: {_sqlite3.sqlite_version}\n")
    s = Settings.load()
    conn = connect(s.db_path)
    n = conn.execute("SELECT COUNT(*) FROM skills").fetchone()[0]
    n_items = conn.execute("SELECT COUNT(*) FROM knowledge_items").fetchone()[0]
    has_reviews = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='item_reviews'"
    ).fetchone()
    n_due = 0
    if has_reviews:
        from learnloop.domain import clock

        now_s = clock.iso(clock.utcnow())
        n_due = conn.execute(
            "SELECT COUNT(*) FROM item_reviews WHERE due_at <= ?"
            " AND (snoozed_until IS NULL OR snoozed_until <= ?)",
            (now_s, now_s),
        ).fetchone()[0]

    sys.stderr.write(f"db: {s.db_path}\nskills seeded: {n}\nknowledge items: {n_items}\nitems due: {n_due}\n")

    for row in conn.execute("SELECT repo_path FROM projects"):
        repo = Path(row[0])
        hook = repo / ".git" / "hooks" / "post-commit"
        if not hook.exists():
            continue
        try:
            text = hook.read_text("utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if HOOK_MARKER not in text:
            continue
        match_py = re.search(r'"([^"]+)"\s+-m\s+learnloop', text)
        match_bin = re.search(r'"([^"]+)"\s+record-commit', text)
        target_path = None
        if match_py:
            target_path = Path(match_py.group(1))
        elif match_bin:
            target_path = Path(match_bin.group(1))

        if target_path and not target_path.exists():
            sys.stderr.write(
                f"WARNING: hook in {repo}: executable {target_path} not found. "
                f'Re-run: learnloop init --repo "{repo}"\n'
            )

    conn.close()
    sys.stderr.write("ok\n")
    return 0


def cmd_techscan(repo: Path) -> int:
    try:
        from typing import Any

        from learnloop.config import Settings
        from learnloop.persistence.db import connect
        from learnloop.services.technology_service import refresh_technologies

        settings = Settings.load()
        conn = connect(settings.db_path)
        try:
            project_id = _find_project_id(conn, repo)
            if not project_id:
                from learnloop.services.capture_service import start_project

                p = start_project(conn, repo.resolve().name, str(repo.resolve()))
                project_id = p["id"]

            res = refresh_technologies(conn, project_id)
            techs = res["technologies"]
            sys.stdout.write(f"Scanned {len(techs)} technologies in {repo}:\n")
            by_eco: dict[str, list[dict[str, Any]]] = {}
            for t in techs:
                by_eco.setdefault(t["ecosystem"], []).append(t)

            for eco in sorted(by_eco.keys()):
                sys.stdout.write(f"\n[{eco.upper()}]\n")
                for t in by_eco[eco]:
                    ver = f" ({t['version_spec']})" if t.get("version_spec") else ""
                    sys.stdout.write(f"  - {t['name']}{ver} [{t['source_file']}]\n")
            return 0
        finally:
            conn.close()
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"learnloop techscan failed: {exc}\n")
        return 1


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="learnloop")
    sub = p.add_subparsers(dest="cmd")

    init_p = sub.add_parser("init", help="Initialize LearnLoop in project")
    init_p.add_argument("--repo", type=Path, default=Path.cwd(), help="Repository path")
    init_p.add_argument("--integrate", action="store_true", help="Auto-integrate with IDEs")
    init_p.add_argument("--in-repo", action="store_true", help="Store SQLite DB inside .learn/ folder")

    for name in ("record-commit", "concepts", "review", "briefing", "techscan"):
        sp = sub.add_parser(name)
        sp.add_argument("--repo", type=Path, default=Path.cwd())

    bf = sub.add_parser("backfill")
    bf.add_argument("--repo", type=Path, default=Path.cwd())
    bf.add_argument("--limit", type=int, default=50)

    sub.add_parser("doctor")

    dash = sub.add_parser("dashboard")
    dash.add_argument("--port", type=int, default=8765)
    dash.add_argument("--gui", action="store_true", help="Open dashboard in native desktop GUI window")

    setup_p = sub.add_parser("setup", help="Launch interactive setup wizard")
    setup_p.add_argument("--port", type=int, default=8765, help="Port to run setup server on")
    setup_p.add_argument("--no-browser", action="store_true", help="Do not automatically open browser")
    setup_p.add_argument("--browser", action="store_true", help="Force opening in web browser instead of desktop window")

    gui_p = sub.add_parser("gui", help="Launch native desktop GUI window (Edge WebView2)")
    gui_p.add_argument("--port", type=int, default=8765, help="Port to run setup server on")
    gui_p.add_argument("--route", default="/setup", choices=["/setup", "/"], help="Starting view (/setup or /)")
    gui_p.add_argument("--no-hide-console", action="store_true", help="Keep console window visible")

    integ = sub.add_parser("integrate", help="Integrate with IDEs or terminal")
    integ.add_argument(
        "--ide",
        choices=["auto", "vscode", "cursor", "claude", "windsurf", "zed", "agents", "all"],
        default="auto",
        help="IDE to integrate with",
    )
    integ.add_argument("--force", action="store_true", help="Force overwrite")
    integ.add_argument("--terminal", action="store_true", help="Setup terminal integration")
    integ.add_argument("--env", action="store_true", help="Setup environment")
    integ.add_argument("--all", action="store_true", help="Setup everything")

    args = p.parse_args(argv)
    if args.cmd == "init":
        code = cmd_init(args.repo, integrate=args.integrate, in_repo=args.in_repo)
    elif args.cmd == "setup":
        code = cmd_setup(
            port=args.port,
            open_browser=not args.no_browser,
            use_gui=not args.browser and not args.no_browser,
        )
    elif args.cmd == "gui":
        code = cmd_gui(port=args.port, route=args.route, hide_console=not args.no_hide_console)
    elif args.cmd == "integrate":
        integ_args = []
        if args.ide:
            integ_args.extend(["--ide", args.ide])
        if args.force:
            integ_args.append("--force")
        if args.terminal:
            integ_args.append("--terminal")
        if args.env:
            integ_args.append("--env")
        if args.all:
            integ_args.append("--all")
        code = cmd_integrate(integ_args)
    elif args.cmd == "record-commit":
        code = cmd_record_commit(args.repo)
    elif args.cmd == "backfill":
        code = cmd_backfill(args.repo, args.limit)
    elif args.cmd == "concepts":
        code = cmd_concepts(args.repo)
    elif args.cmd == "review":
        code = cmd_review(args.repo)
    elif args.cmd == "briefing":
        code = cmd_briefing(args.repo)
    elif args.cmd == "doctor":
        code = cmd_doctor()
    elif args.cmd == "dashboard":
        code = cmd_dashboard(args.port, use_gui=args.gui)
    elif args.cmd == "techscan":
        code = cmd_techscan(args.repo)
    else:
        # Smart launch: if launched interactively by user (double-click in Explorer or running
        # learnloop without args in a terminal), launch the setup wizard in desktop window.
        # If piped from an IDE (Cursor, VS Code, etc.), silently run FastMCP stdio server.
        if sys.stdin and hasattr(sys.stdin, "isatty") and sys.stdin.isatty():
            code = cmd_setup(use_gui=True)
        else:
            code = cmd_serve()
    raise SystemExit(code)


if __name__ == "__main__":
    main()
