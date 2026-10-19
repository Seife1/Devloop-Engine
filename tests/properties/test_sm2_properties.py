"""Property-based tests for SM-2 algorithm parameter constraints.

This module tests the SM-2 spaced repetition algorithm using property-based
testing with Hypothesis to ensure parameter constraints are maintained.
"""

from hypothesis import given, strategies as st
import random
from datetime import datetime, timezone, timedelta

from learnloop.domain.scheduling import ScheduleState, update_schedule
from learnloop.domain import clock


def random_schedule_state():
    """Generate random schedule state for testing."""
    return ScheduleState(
        interval_days=random.randint(1, 1000),
        ease=random.uniform(1.3, 3.0),
        reps=random.randint(0, 100),
        due_at=clock.iso(clock.utcnow() + timedelta(days=random.randint(1, 365))),
        last_reviewed_at=clock.iso(clock.utcnow()),
    )


@given(score=st.floats(min_value=0.0, max_value=1.0))
def test_sm2_parameter_constraints(score: float) -> None:
    """Property P7: SM-2 parameter constraints are always maintained.
    
    **Validates: Requirements 15.2, 15.3, 15.4, 15.9, 15.10, 23.9, 23.10, 23.11**
    
    This property verifies that regardless of input score and initial schedule,
    the SM-2 algorithm always produces valid parameters.
    """
    # Generate random initial schedule
    initial = random_schedule_state()
    
    # Apply update
    updated = update_schedule(
        interval_days=initial.interval_days,
        ease=initial.ease,
        reps=initial.reps,
        score=score,
        now=None,
        is_stale=False,
    )
    
    # Verify constraints
    assert 1.3 <= updated.ease <= 3.0, f"Ease factor {updated.ease} out of bounds [1.3, 3.0]"
    assert updated.interval_days >= 1, f"Interval {updated.interval_days} must be >= 1"
    assert updated.reps >= 0, f"Reps {updated.reps} must be >= 0"


@given(
    score=st.floats(min_value=0.0, max_value=1.0),
    stale=st.booleans()
)
def test_sm2_with_staleness(score: float, stale: bool) -> None:
    """Test SM-2 maintains constraints with staleness penalty."""
    initial = random_schedule_state()
    
    updated = update_schedule(
        interval_days=initial.interval_days,
        ease=initial.ease,
        reps=initial.reps,
        score=score,
        now=None,
        is_stale=stale,
    )
    
    assert 1.3 <= updated.ease <= 3.0, f"Ease factor out of bounds: {updated.ease}"
    assert updated.interval_days >= 1, f"Interval must be >= 1: {updated.interval_days}"
    assert updated.reps >= 0, f"Reps must be >= 0: {updated.reps}"


def test_sm2_edge_cases() -> None:
    """Test edge cases of SM-2 algorithm."""
    initial = random_schedule_state()
    # Perfect score (1.0)
    perfect = update_schedule(
        interval_days=initial.interval_days,
        ease=initial.ease,
        reps=initial.reps,
        score=1.0,
        now=None,
        is_stale=False,
    )
    assert 1.3 <= perfect.ease <= 3.0
    assert perfect.interval_days >= 1
    
    # Zero score
    zero = update_schedule(
        interval_days=initial.interval_days,
        ease=initial.ease,
        reps=initial.reps,
        score=0.0,
        now=None,
        is_stale=False,
    )
    assert 1.3 <= zero.ease <= 3.0
    assert zero.interval_days >= 1
    
    # Reset condition (score < 0.5)
    reset = update_schedule(
        interval_days=365,
        ease=2.5,
        reps=100,
        score=0.4,
        now=None,
        is_stale=False,
    )
    assert reset.reps == 0, f"Should reset reps on low score, got {reset.reps}"
    assert reset.interval_days == 1, f"Should reset to interval=1, got {reset.interval_days}"
