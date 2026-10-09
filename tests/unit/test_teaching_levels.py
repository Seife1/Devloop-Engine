import pytest

from learnloop.domain.teaching import level_for


@pytest.mark.parametrize(
    "mastery,attempts,expected",
    [
        (None, 0, "guided"),
        (0.95, 1, "guided"),  # one lucky attempt must not remove support
        (0.95, 2, "guided"),
        (0.5, 5, "guided"),
        (0.7, 5, "standard"),
        (0.9, 5, "challenge"),
    ],
)
def test_support_fades_only_with_enough_evidence(mastery, attempts, expected):
    assert level_for(mastery, attempts) == expected
