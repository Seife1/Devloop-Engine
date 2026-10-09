"""CLI. `learnloop` with no arguments starts the MCP server (stdio).

`record-commit` is called by the git hook: it must be fast and must NEVER fail the commit.
"""

from __future__ import annotations

import argparse
import stat
import subprocess
import sys
from pathlib import Path

from learnloop.logging import setup_logging

HOOK_MARKER = "# learnloop-hook"


def _hook_text(python: str | None = None) -> str:
    """Generate the post-commit hook body.

    Single source of truth for hook content. Uses the absolute interpreter path
    so the hook works even when the venv is not on PATH (common on Windows).
    Forward slashes and quoting for sh compatibility.
    """
    py = (python if python is not None else sys.executable).replace("\\", "/")
    return (
        "#!/bin/sh\n"
        f"{HOOK_MARKER}\n"
        "# Fast, non-blocking, never fails the commit.\n"
        "# Writes a redacted metadata record to .learn/queue/.\n"
        f'( "{py}" -m learnloop record-commit '
        '--repo "$(git rev-parse --show-toplevel)" ) >/dev/null 2>&1 &\n'
        "exit 0\n"
    )



def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], capture_output=True, text=True, check=True, timeout=10
    ).stdout


def cmd_serve() -> int:
    from learnloop.server import build_server

    setup_logging()
    build_server().run()  # stdio transport
    return 0


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


def cmd_init(repo: Path) -> int:
    learn = repo / ".learn"
    (learn / "queue").mkdir(parents=True, exist_ok=True)
    (learn / ".gitignore").write_text("queue/\n", encoding="utf-8")
    hook = repo / ".git" / "hooks" / "post-commit"
    if not (repo / ".git").is_dir():
        sys.stderr.write("Not a git repository root; created .learn/ only.\n")
        return 1
    body = _hook_text()
    if hook.exists() and HOOK_MARKER not in hook.read_text("utf-8"):
        sys.stderr.write(f"{hook} already exists and isn't ours; add `learnloop record-commit` manually.\n")
        return 1
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_bytes(body.encode("utf-8"))
    hook.chmod(hook.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    sys.stderr.write(f"Initialised {learn} and installed post-commit hook.\n")
    return 0


def cmd_doctor() -> int:
    import re
    import sqlite3 as _sqlite3

    from learnloop.config import Settings
    from learnloop.persistence.db import connect

    sys.stderr.write(f"sqlite: {_sqlite3.sqlite_version}\n")
    s = Settings.load()
    conn = connect(s.db_path)
    n = conn.execute("SELECT COUNT(*) FROM skills").fetchone()[0]
    sys.stderr.write(f"db: {s.db_path}\nskills seeded: {n}\n")

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
        match = re.search(r'"([^"]+)"\s+-m\s+learnloop', text)
        if match:
            interp = Path(match.group(1))
            if not interp.exists():
                sys.stderr.write(
                    f"WARNING: hook in {repo}: interpreter {interp} not found. "
                    f'Re-run: learnloop init --repo "{repo}"\n'
                )

    conn.close()
    sys.stderr.write("ok\n")
    return 0


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="learnloop")
    sub = p.add_subparsers(dest="cmd")
    for name in ("init", "record-commit"):
        sp = sub.add_parser(name)
        sp.add_argument("--repo", type=Path, default=Path.cwd())
    sub.add_parser("doctor")
    args = p.parse_args(argv)
    if args.cmd == "init":
        code = cmd_init(args.repo)
    elif args.cmd == "record-commit":
        code = cmd_record_commit(args.repo)
    elif args.cmd == "doctor":
        code = cmd_doctor()
    else:
        code = cmd_serve()
    raise SystemExit(code)
