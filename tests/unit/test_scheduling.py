from __future__ import annotations

from datetime import UTC, datetime

import pytest

from learnloop.domain.errors import ValidationError
from learnloop.domain.scheduling import (
    DEFAULT_EASE,
    MAX_EASE,
    MAX_INTERVAL_DAYS,
    MIN_EASE,
    calculate_snooze_until,
    initial_schedule,
    update_schedule,
)

NOW = datetime(2026, 3, 1, 10, 0, 0, tzinfo=UTC)


def test_initial_schedule_normal():
    sched = initial_schedule(now=NOW, is_stale=False)
    assert sched.interval_days == 1
    assert sched.ease == DEFAULT_EASE
    assert sched.reps == 0
    assert sched.due_at == "2026-03-02T10:00:00+00:00"
    assert sched.last_reviewed_at == "2026-03-01T10:00:00+00:00"


def test_initial_schedule_stale():
    sched = initial_schedule(now=NOW, is_stale=True)
    assert sched.interval_days == 1
    assert sched.ease == DEFAULT_EASE
    assert sched.reps == 0
    assert sched.due_at == "2026-03-01T10:00:00+00:00"
    assert sched.last_reviewed_at == "2026-03-01T10:00:00+00:00"


@pytest.mark.parametrize(
    ("score", "curr_interval", "curr_ease", "curr_reps", "expected_interval", "expected_ease", "expected_reps"),
    [
        # Rep 0 success (score >= 0.8) -> interval=1, ease+=0.1, reps=1
        (1.0, 1, 2.3, 0, 1, 2.4, 1),
        (0.8, 1, 2.3, 0, 1, 2.4, 1),
        # Rep 1 success -> interval=3, ease+=0.1, reps=2
        (0.9, 1, 2.4, 1, 3, 2.5, 2),
        # Rep 2+ success -> interval=round(interval * ease), ease+=0.1, reps+=1
        (0.85, 3, 2.5, 2, 8, 2.6, 3),  # round(3 * 2.5) = 8
        (0.8, 8, 2.6, 3, 21, 2.7, 4),  # round(8 * 2.6) = 21
        # Moderate score (0.5 <= score < 0.8) -> interval=round(interval * 1.2), ease unchanged, reps+=1
        (0.7, 3, 2.3, 2, 4, 2.3, 3),   # round(3 * 1.2) = 4
        (0.5, 1, 2.3, 0, 1, 2.3, 1),   # max(1, round(1 * 1.2)) = 1
        # Low score (< 0.5) -> interval=1, ease-=0.2, reps=0
        (0.4, 21, 2.5, 4, 1, 2.3, 0),
        (0.0, 5, 2.0, 2, 1, 1.8, 0),
    ],
)
def test_update_schedule_progression(
    score: float,
    curr_interval: int,
    curr_ease: float,
    curr_reps: int,
    expected_interval: int,
    expected_ease: float,
    expected_reps: int,
):
    sched = update_schedule(
        interval_days=curr_interval,
        ease=curr_ease,
        reps=curr_reps,
        score=score,
        now=NOW,
    )
    assert sched.interval_days == expected_interval
    assert sched.ease == expected_ease
    assert sched.reps == expected_reps


def test_update_schedule_clamps_ease():
    # Test lower bound clamping
    sched = update_schedule(interval_days=1, ease=1.35, reps=1, score=0.2, now=NOW)
    assert sched.ease == MIN_EASE  # 1.35 - 0.2 = 1.15 -> clamped to 1.3

    # Test upper bound clamping
    sched2 = update_schedule(interval_days=10, ease=2.95, reps=2, score=0.9, now=NOW)
    assert sched2.ease == MAX_EASE  # 2.95 + 0.1 = 3.05 -> clamped to 3.0


def test_update_schedule_caps_max_interval():
    # Max interval cap at 120 days
    sched = update_schedule(interval_days=100, ease=2.5, reps=5, score=0.9, now=NOW)
    # 100 * 2.5 = 250 -> capped at 120
    assert sched.interval_days == MAX_INTERVAL_DAYS


def test_update_schedule_stale_due_immediately():
    sched = update_schedule(interval_days=10, ease=2.5, reps=2, score=0.9, now=NOW, is_stale=True)
    assert sched.interval_days == 25
    assert sched.due_at == "2026-03-01T10:00:00+00:00"


def test_update_schedule_invalid_score():
    with pytest.raises(ValidationError, match="Score must be between 0.0 and 1.0"):
        update_schedule(interval_days=1, ease=2.3, reps=0, score=-0.1, now=NOW)

    with pytest.raises(ValidationError, match="Score must be between 0.0 and 1.0"):
        update_schedule(interval_days=1, ease=2.3, reps=0, score=1.1, now=NOW)


def test_calculate_snooze_until():
    snooze_7 = calculate_snooze_until(days=7, now=NOW)
    assert snooze_7 == "2026-03-08T10:00:00+00:00"

    snooze_1 = calculate_snooze_until(days=1, now=NOW)
    assert snooze_1 == "2026-03-02T10:00:00+00:00"

    snooze_30 = calculate_snooze_until(days=30, now=NOW)
    assert snooze_30 == "2026-03-31T10:00:00+00:00"

    with pytest.raises(ValidationError, match="Snooze days must be between 1 and 30"):
        calculate_snooze_until(days=0, now=NOW)

    with pytest.raises(ValidationError, match="Snooze days must be between 1 and 30"):
        calculate_snooze_until(days=31, now=NOW)
