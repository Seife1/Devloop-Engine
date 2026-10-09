"""Pure evidence ranking for LearnLoop lessons. No I/O, deterministic."""

from __future__ import annotations

import re
from collections.abc import Collection

_STOPWORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "in",
    "on",
    "at",
    "to",
    "for",
    "of",
    "with",
    "by",
    "from",
    "into",
    "that",
    "this",
    "is",
    "it",
}


def _is_skill_related(target_skill: str, skill: str) -> bool:
    if skill == target_skill:
        return True
    if target_skill.startswith(skill + "."):
        return True
    if skill.startswith(target_skill + "."):
        return True
    return False


def _is_noise(path: str) -> bool:
    p = path.lower()
    name = p.rsplit("/", 1)[-1]
    if name.startswith("readme"):
        return True
    if p.startswith((".github/", ".gitlab/", ".circleci/")) or name in (
        ".gitlab-ci.yml",
        "jenkinsfile",
        ".travis.yml",
    ):
        return True
    if name.endswith(".lock") or name in (
        "package-lock.json",
        "pnpm-lock.yaml",
        "poetry.lock",
        "uv.lock",
        "pipfile.lock",
        "cargo.lock",
    ):
        return True
    if name.startswith("license") or name.startswith("changelog") or name in (
        ".gitignore",
        ".gitattributes",
        ".editorconfig",
    ):
        return True
    return False


def rank_evidence_files(
    skill_id: str,
    commit_files: list[str],
    declared_touched: Collection[str],
    intent_text: str,
    mapped_skills_by_file: dict[str, list[str]],
) -> list[str]:
    """Rank commit files for teaching evidence in a deterministic order.

    Order:
      1. declared+touched files (alphabetical)
      2. files whose mapped skills include the target skill or parent/child (alphabetical)
      3. files whose path tokens overlap intent summary/rationale (highest overlap first, then path)
      4. remaining files (alphabetical)

    Noise files (README, CI, lockfiles, etc.) are excluded unless they map to the skill
    or were explicitly declared and touched.
    """
    declared_set = set(declared_touched)
    unique_commit_files = sorted(set(commit_files))

    intent_tokens = {
        t for t in re.split(r"[^\w]+", intent_text.lower()) if len(t) >= 2 and t not in _STOPWORDS
    }

    tier0: list[str] = []
    tier1: list[str] = []
    tier2: list[tuple[int, str]] = []
    tier3: list[str] = []

    for f in unique_commit_files:
        mapped_skills = mapped_skills_by_file.get(f, [])
        maps_to_skill = any(_is_skill_related(skill_id, s) for s in mapped_skills)
        is_declared_touched = f in declared_set

        # Exclude noise unless it maps to the skill or was declared+touched
        if _is_noise(f) and not maps_to_skill and not is_declared_touched:
            continue

        if is_declared_touched:
            tier0.append(f)
        elif maps_to_skill:
            tier1.append(f)
        else:
            path_tokens = {
                t for t in re.split(r"[/._\-]+", f.lower()) if len(t) >= 2 and t not in _STOPWORDS
            }
            overlap = len(path_tokens & intent_tokens)
            if overlap > 0:
                tier2.append((overlap, f))
            else:
                tier3.append(f)

    tier0.sort()
    tier1.sort()
    # Sort tier2 by descending overlap, then alphabetical by path
    tier2.sort(key=lambda item: (-item[0], item[1]))
    tier3.sort()

    return tier0 + tier1 + [item[1] for item in tier2] + tier3
