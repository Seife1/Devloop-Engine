"""SM-2-style spaced repetition scheduler. Pure domain logic, no I/O."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Final

from learnloop.domain import clock
from learnloop.domain.errors import ValidationError

DEFAULT_EASE: Final[float] = 2.3
MIN_EASE: Final[float] = 1.3
MAX_EASE: Final[float] = 3.0
MAX_INTERVAL_DAYS: Final[int] = 120


@dataclass(frozen=True)
class ScheduleState:
    interval_days: int
    ease: float
    reps: int
    due_at: str
    last_reviewed_at: str | None


def initial_schedule(now: datetime | None = None, is_stale: bool = False) -> ScheduleState:
    """Create initial schedule state for a newly explained knowledge item."""
    now_dt = now or clock.utcnow()
    interval = 1
    due_dt = now_dt if is_stale else now_dt + timedelta(days=interval)
    return ScheduleState(
        interval_days=interval,
        ease=DEFAULT_EASE,
        reps=0,
        due_at=clock.iso(due_dt),
        last_reviewed_at=clock.iso(now_dt),
    )


def update_schedule(
    interval_days: int,
    ease: float,
    reps: int,
    score: float,
    now: datetime | None = None,
    is_stale: bool = False,
) -> ScheduleState:
    """Calculate next review schedule based on attempt score (0.0 .. 1.0).

    Rules:
      - score >= 0.8:
          first rep (reps=0)  -> interval = 1
          second rep (reps=1) -> interval = 3
          subsequent reps     -> interval = round(interval * ease)
          ease += 0.1, reps += 1
      - 0.5 <= score < 0.8:
          interval = max(1, round(interval * 1.2))
          ease unchanged, reps += 1
      - score < 0.5:
          interval = 1
          ease -= 0.2
          reps = 0
      - ease clamped between 1.3 and 3.0
      - interval capped at 120 days
      - stale items are due immediately: due_at = min(due_at, now)
    """
    if not (0.0 <= score <= 1.0):
        raise ValidationError(f"Score must be between 0.0 and 1.0, got {score}")

    now_dt = now or clock.utcnow()

    if score >= 0.8:
        if reps == 0:
            next_interval = 1
        elif reps == 1:
            next_interval = 3
        else:
            next_interval = round(interval_days * ease)
        next_ease = ease + 0.1
        next_reps = reps + 1
    elif score >= 0.5:
        next_interval = max(1, round(interval_days * 1.2))
        next_ease = ease
        next_reps = reps + 1
    else:
        next_interval = 1
        next_ease = ease - 0.2
        next_reps = 0

    clamped_ease = round(max(MIN_EASE, min(MAX_EASE, next_ease)), 2)
    clamped_interval = max(1, min(MAX_INTERVAL_DAYS, next_interval))

    due_dt = now_dt + timedelta(days=clamped_interval)
    if is_stale:
        due_dt = min(due_dt, now_dt)

    return ScheduleState(
        interval_days=clamped_interval,
        ease=clamped_ease,
        reps=next_reps,
        due_at=clock.iso(due_dt),
        last_reviewed_at=clock.iso(now_dt),
    )


def calculate_snooze_until(days: int, now: datetime | None = None) -> str:
    """Calculate ISO timestamp for snoozing an item between 1 and 30 days."""
    if not (1 <= days <= 30):
        raise ValidationError(f"Snooze days must be between 1 and 30, got {days}")
    now_dt = now or clock.utcnow()
    return clock.iso(now_dt + timedelta(days=days))
