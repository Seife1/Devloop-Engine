"""Suggest skills for changed files. Used to help the agent explain an 'unexplained' commit;
suggestions NEVER create exposure on their own."""

from __future__ import annotations

import sqlite3


def _rules(path: str) -> list[str]:
    p = path.lower()
    name = p.rsplit("/", 1)[-1]
    out: list[str] = []
    if p.endswith(".py"):
        out.append("python")
        if name.startswith("test_") or name.endswith("_test.py") or "/tests/" in f"/{p}":
            out.append("python.testing")
        if name == "conftest.py":
            out.append("python.testing.fixtures")
    if p.endswith((".ts", ".tsx")):
        out.append("typescript")
    if p.endswith((".js", ".jsx", ".mjs")):
        out.append("javascript")
    if p.endswith(".sql"):
        out.append("databases.sql")
    if "migration" in p or "alembic" in p:
        out.append("databases.migrations")
    if name == "dockerfile" or name.startswith("docker-compose"):
        out.append("devops.docker")
    if p.startswith(".github/workflows/"):
        out.append("devops.ci")
    if name in ("pyproject.toml", "setup.py", "setup.cfg"):
        out.append("python.packaging")
    if "auth" in p or "login" in p:
        out.append("web.auth")
    return out


def suggest_skills(conn: sqlite3.Connection, files: list[str]) -> list[str]:
    known = {r["id"] for r in conn.execute("SELECT id FROM skills")}
    found: list[str] = []
    for f in files:
        for s in _rules(f):
            if s in known and s not in found:
                found.append(s)
    return found
