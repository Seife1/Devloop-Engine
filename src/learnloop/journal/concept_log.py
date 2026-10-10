"""Concept log generator. Deterministically renders <repo>/.learn/concepts.md."""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

from learnloop.capture.redaction import redact
from learnloop.domain.depth import depth_description

STARTER_CONCEPT_GUIDE = """\
# Project Concepts & Learning Guide

> ### 💡 The "AI Illusion of Competence"
> When an AI writes code that works, reading it feels easy. This creates a false sense of
> ownership. True mastery isn't having working code—it's being able to defend every
> decision, file, and trade-off in an interview or code review without the AI.
>
> **How to protect yourself:**
> 1. **Commit early & often:** LearnLoop tracks learning through Git commits. Uncommitted edits are invisible.
> 2. **Take the tour:** Ask your AI *"give me a tour"* to understand your entry points and data flow.
> 3. **Explain it back:** When prompted, explain what the code does in your own words.
>
> *Note: Explanations below are AI-assisted study notes and may be incomplete or mistaken.*

## Basic
*(No items in this section yet. As your AI builds components and you commit, they will appear here.)*

## Intermediate
*(No items in this section yet)*

## Advanced
*(No items in this section yet)*
"""


def is_safe_to_write_concepts(repo_path: Path | str) -> tuple[bool, Path | None, str]:
    """Validate safety requirements for writing .learn/concepts.md.

    Requirements:
    1. repo_path exists and is a directory.
    2. repo_path is a git repo (.git dir) OR already contains .learn/ dir.
    3. .learn is not a symlink.
    4. The resolved target is exactly <repo>/.learn/concepts.md.
    """
    try:
        repo = Path(repo_path).resolve()
        if not repo.exists() or not repo.is_dir():
            return False, None, f"repo_path does not exist or is not a directory: {repo}"

        is_git = (repo / ".git").is_dir()
        learn_dir = repo / ".learn"
        has_learn = learn_dir.is_dir()

        if not (is_git or has_learn):
            return False, None, f"repo_path is neither a git repository nor contains .learn/: {repo}"

        if learn_dir.exists() and learn_dir.is_symlink():
            return False, None, f".learn directory is a symlink: {learn_dir}"

        learn_dir.mkdir(parents=True, exist_ok=True)
        target = (learn_dir / "concepts.md").resolve()
        expected = (repo / ".learn" / "concepts.md").resolve()

        if target != expected:
            return False, None, f"Target path mismatch ({target} != {expected})"

        return True, target, ""
    except Exception as exc:  # noqa: BLE001
        return False, None, str(exc)


def init_concept_log(repo_path: Path | str) -> bool:
    """Write the Day-1 starter concepts.md if it does not exist yet."""
    safe, target, _ = is_safe_to_write_concepts(repo_path)
    if not safe or target is None:
        return False
    if target.exists():
        return True
    try:
        tmp_target = target.parent / f".{target.name}.tmp"
        tmp_target.write_text(STARTER_CONCEPT_GUIDE, encoding="utf-8")
        os.replace(tmp_target, target)
        return True
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"concept_log: could not write starter concepts.md: {exc}\n")
        return False


def generate_concept_markdown(conn: sqlite3.Connection, project_id: str) -> str:
    """Generate deterministic markdown content for the project's concept log."""
    lines: list[str] = [
        "# Project Concepts & Learning Guide",
        "",
        '> ### 💡 The "AI Illusion of Competence"',
        "> When an AI writes code that works, reading it feels easy. This creates a false sense of",
        "> ownership. True mastery isn't having working code—it's being able to defend every",
        "> decision, file, and trade-off in an interview or code review without the AI.",
        ">",
        "> **How to protect yourself:**",
        "> 1. **Commit early & often:** LearnLoop tracks learning through Git commits.",
        ">    Uncommitted edits are invisible.",
        '> 2. **Take the tour:** Ask your AI *"give me a tour"* to understand entry points and flows.',
        "> 3. **Explain it back:** When prompted, explain what the code does in your own words.",
        ">",
        "> *Note: Explanations below are AI-assisted study notes and may be incomplete or mistaken.*",
        "",
    ]

    bands = ["basic", "intermediate", "advanced"]
    band_titles = {
        "basic": "Basic",
        "intermediate": "Intermediate",
        "advanced": "Advanced",
    }

    for band in bands:
        lines.append(f"## {band_titles[band]}")
        lines.append("")

        items = conn.execute(
            "SELECT id, key, title, kind, summary, status, depth FROM knowledge_items"
            " WHERE project_id=? AND band=? ORDER BY key ASC",
            (project_id, band),
        ).fetchall()

        if not items:
            lines.append("*(No items in this section yet)*")
            lines.append("")
            continue

        for item in items:
            item_id = item["id"]
            key = item["key"]
            title = item["title"]
            kind = item["kind"]
            summary = redact(item["summary"])
            status = item["status"]
            depth = int(item["depth"])
            depth_focus = depth_description(depth)

            # Files
            files = [
                r["path"]
                for r in conn.execute(
                    "SELECT path FROM item_files WHERE item_id=? ORDER BY path ASC", (item_id,)
                ).fetchall()
            ]

            # Latest explanation
            exp_row = conn.execute(
                "SELECT learner_text, score, depth, created_at FROM explanations"
                " WHERE item_id=? ORDER BY created_at DESC, id DESC LIMIT 1",
                (item_id,),
            ).fetchone()

            lines.append(f"### {title} (`{key}`)")
            lines.append(
                f"- **Kind**: {kind} | **Status**: {status} | **Depth**: {depth}/5 ({depth_focus})"
            )
            if files:
                file_links = ", ".join(f"`{f}`" for f in files)
                lines.append(f"- **Files**: {file_links}")
            lines.append(f"- **Summary**: {summary}")

            if exp_row:
                exp_text = redact(exp_row["learner_text"])
                if len(exp_text) > 500:
                    exp_text = exp_text[:497] + "..."
                lines.append(f'- **Latest explanation** (score {exp_row["score"]:.1f}): "{exp_text}"')

            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def regenerate_concept_log(conn: sqlite3.Connection, project_id: str, repo_path: Path | str) -> bool:
    """Safely and atomically regenerate .learn/concepts.md.

    Returns True if written, False otherwise.
    """
    safe, target, reason = is_safe_to_write_concepts(repo_path)
    if not safe or target is None:
        sys.stderr.write(f"concept_log: skipped writing .learn/concepts.md ({reason})\n")
        return False

    try:
        md = generate_concept_markdown(conn, project_id)
        tmp_target = target.parent / f".{target.name}.tmp"
        tmp_target.write_text(md, encoding="utf-8")
        os.replace(tmp_target, target)
        return True
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"concept_log: error writing {target}: {exc}\n")
        return False
