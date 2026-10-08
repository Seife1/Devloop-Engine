# ADR 0001: Exposure and mastery are separate numbers

**Status:** accepted

**Context.** Accepting AI-written code feels like learning. If the skill map rose whenever the AI
committed code, the tool would create the false confidence it exists to remove.

**Decision.**
- *Exposure* = verified events: a declared intent matched by a real git commit (reconciliation).
- *Mastery* = moves only from the learner's own graded attempts, time-decayed toward a neutral prior.
- Every mastery number is reported with attempt count and confidence. `untested` is unknown, not 0%.
- Commits with no declared intent are `unexplained` and give no exposure until explained.

**Consequences.** The agent can't inflate the skill map by claiming work; the hook can't either.
Gaps = high exposure, low or unknown mastery.
