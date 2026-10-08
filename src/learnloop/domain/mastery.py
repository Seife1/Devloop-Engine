"""Mastery model.

Mastery moves ONLY from the learner's own attempts (never from what the AI did).
It is a time-decayed moving average that regresses toward a neutral prior, and every
number is reported together with how many attempts back it (confidence).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

PRIOR = 0.5
HALF_LIFE_DAYS = 60.0
MAX_HINT_PENALTY_STEPS = 3
HINT_PENALTY = 0.1

Confidence = Literal["none", "low", "medium", "high"]


@dataclass(frozen=True)
class MasteryState:
    mastery: float = PRIOR
    attempts: int = 0
    updated_at: datetime | None = None


def effective_mastery(state: MasteryState, now: datetime) -> float:
    """Stored mastery, decayed toward the prior as time passes without practice."""
    if state.attempts == 0 or state.updated_at is None:
        return PRIOR
    days = max(0.0, (now - state.updated_at).total_seconds() / 86400)
    return PRIOR + (state.mastery - PRIOR) * 0.5 ** (days / HALF_LIFE_DAYS)


def adjust_for_hints(score: float, hints_used: int) -> float:
    steps = min(max(hints_used, 0), MAX_HINT_PENALTY_STEPS)
    return score * (1 - HINT_PENALTY * steps)


def update(state: MasteryState, score: float, now: datetime) -> MasteryState:
    if not 0.0 <= score <= 1.0:
        raise ValueError("score must be between 0 and 1")
    base = effective_mastery(state, now)
    alpha = max(0.15, 1 / (state.attempts + 2))  # early attempts move the estimate a lot
    return MasteryState(base + alpha * (score - base), state.attempts + 1, now)


def confidence(attempts: int) -> Confidence:
    if attempts == 0:
        return "none"
    if attempts < 3:
        return "low"
    if attempts < 8:
        return "medium"
    return "high"
