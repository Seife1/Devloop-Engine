"""Gap = exposure the learner has had that mastery has not caught up with."""

from __future__ import annotations

from dataclasses import dataclass

from learnloop.domain.mastery import PRIOR, Confidence, confidence


@dataclass(frozen=True)
class SkillStanding:
    skill_id: str
    name: str
    exposure: int
    mastery: float | None  # effective mastery, None if never practiced
    attempts: int

    @property
    def confidence(self) -> Confidence:
        return confidence(self.attempts)

    @property
    def status(self) -> str:
        if self.attempts == 0:
            return "untested"
        return "ok" if (self.mastery or 0) >= 0.75 else "gap"


def priority(s: SkillStanding) -> float:
    """Higher = learn this first. Untested skills are treated as neutral (0.5), so they
    outrank mastered skills but not demonstrated weaknesses with the same exposure."""
    m = PRIOR if s.mastery is None else s.mastery
    return s.exposure * (1 - m)


def rank_gaps(standings: list[SkillStanding], limit: int = 5) -> list[SkillStanding]:
    candidates = [s for s in standings if s.exposure > 0 and s.status != "ok"]
    return sorted(candidates, key=priority, reverse=True)[:limit]
