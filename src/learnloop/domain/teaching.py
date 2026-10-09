"""How much support a lesson should give. Support fades as demonstrated mastery rises."""

from __future__ import annotations

from typing import Literal

Level = Literal["guided", "standard", "challenge"]


def level_for(mastery: float | None, attempts: int) -> Level:
    """guided: explain first, worked example, hints allowed.
    standard: learner predicts before the reveal.
    challenge: no hints; learner writes or fixes code unaided.
    A single attempt is too noisy to fade support, so it takes >= 3 to leave 'guided'."""
    if mastery is None or attempts < 3:
        return "guided"
    if mastery < 0.6:
        return "guided"
    if mastery < 0.8:
        return "standard"
    return "challenge"
