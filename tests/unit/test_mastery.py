from datetime import UTC, datetime, timedelta

import pytest

from learnloop.domain import mastery as m

T0 = datetime(2026, 1, 1, tzinfo=UTC)


def test_untested_is_prior_not_zero():
    assert m.effective_mastery(m.MasteryState(), T0) == m.PRIOR


def test_first_good_attempt_moves_but_confidence_is_low():
    s = m.update(m.MasteryState(), 1.0, T0)
    assert 0.5 < s.mastery < 1.0
    assert m.confidence(s.attempts) == "low"


def test_repeated_success_converges_up():
    s = m.MasteryState()
    for _ in range(10):
        s = m.update(s, 1.0, T0)
    assert s.mastery > 0.9
    assert m.confidence(s.attempts) == "high"


def test_mastery_decays_toward_prior():
    s = m.update(m.MasteryState(), 1.0, T0)
    later = T0 + timedelta(days=m.HALF_LIFE_DAYS)
    expected = m.PRIOR + (s.mastery - m.PRIOR) / 2
    assert m.effective_mastery(s, later) == pytest.approx(expected)


def test_hints_reduce_score_with_cap():
    assert m.adjust_for_hints(1.0, 0) == 1.0
    assert m.adjust_for_hints(1.0, 2) == pytest.approx(0.8)
    assert m.adjust_for_hints(1.0, 99) == pytest.approx(0.7)


def test_rejects_out_of_range_score():
    with pytest.raises(ValueError):
        m.update(m.MasteryState(), 1.5, T0)
