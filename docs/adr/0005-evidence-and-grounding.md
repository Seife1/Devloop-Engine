# ADR 0005: Evidence grounding, finer skills, and ranked evidence

**Status:** accepted

**Context.**
In v0.2, quizzes could ask generic textbook questions unrelated to the learner's real codebase.
The taxonomy was coarse, and evidence files presented to teaching sessions were an unranked first-8
from arbitrary commits.

**Decision.**
1. **Declared Intent Files & Reconcile Verification:**
   - Agents declare planned files in `start_skill_session(files=[...])` stored in `intent_files`.
   - During reconcile, declared files present in the commit receive `touched=1`, others `touched=0`.
   - If all declared files were untouched, reconciliation verifies but records a warning.

2. **Deterministic Evidence Ranking:**
   - Evidence files in lessons are ordered deterministically: declared+touched files first,
     then files matching target skill or parent/child, then files overlapping intent tokens,
     then remaining paths.
   - Non-skill noise (README, CI, lockfiles) is filtered out unless mapped to the skill or declared+touched.

3. **Grounded Quizzes & Majority Rule:**
   - Questions in `create_quiz` accept an optional `source_file` validated against verified commit files.
   - Valid references are tagged `grounding='project'`; missing references are `grounding='generic'`.
   - If verified evidence exists for the skill, at least `ceil(n/2)` questions must be grounded.
   - Fabricated file paths are rejected with candidate file suggestions.

4. **Finer Skills Taxonomy & Proposals:**
   - Seeded fine-grained skills under `python.*`, `databases.*`, `git.*`, and `mcp.*`.
   - Added `propose_skill` for runtime proposals extending existing parent skills, protected by regex validation,
     difflib similarity thresholds against siblings (ratio < 0.85), and a daily rate limit of 5 proposals/day.

**Known limits.**
- The server still cannot verify that `learner_answer` is really typed by the human learner.
- Grounding proves that `source_file` existed in a verified commit for that skill, not that the question's text
  or rubric accurately tests the code within it.
