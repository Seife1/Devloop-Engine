"""Depth ladder and level mapping. Pure domain logic, no I/O."""

from __future__ import annotations

from typing import Final

from learnloop.domain.errors import ValidationError

DEPTH_LADDER: Final[dict[int, str]] = {
    1: "what",
    2: "how",
    3: "why",
    4: "trade-offs",
    5: "scale/failure",
}

LEVEL_START_DEPTH: Final[dict[str, int]] = {
    "school": 1,
    "beginner": 1,
    "junior": 2,
    "mid": 3,
    "senior": 3,
}


def start_depth(level: str) -> int:
    """Return the starting depth (1..3) for a given learner profile level."""
    cleaned = level.strip().lower()
    if cleaned not in LEVEL_START_DEPTH:
        raise ValidationError(
            f"Unknown level {level!r}. Expected one of: {sorted(LEVEL_START_DEPTH.keys())}"
        )
    return LEVEL_START_DEPTH[cleaned]


def depth_description(depth: int) -> str:
    """Return the explanatory focus for a depth level 1..5."""
    if depth not in DEPTH_LADDER:
        raise ValidationError(f"Depth {depth} out of range (expected 1..5)")
    return DEPTH_LADDER[depth]
