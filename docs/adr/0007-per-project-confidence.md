# ADR 0007: Per-project confidence replaces skill mastery

**Status:** accepted

**Context.**
In v0.1–v0.3, LearnLoop attempted to track global language and framework skill mastery (e.g. `python.testing`, `databases.sqlite`) across all of a developer's activities. However, in practice, developers building software with AI coding agents do not struggle with abstract textbook language skills—they struggle with understanding and defending their *own concrete project*: what specific files do, why architectural choices were made, how bug fixes work, and what changed when the AI updated code later.

Carrying mastery scores between unrelated projects created a false sense of security or irrelevant skill gaps. Furthermore, exposing a dozen abstract skill and quiz tools alongside concrete project knowledge tools caused context bloat in the MCP tool catalog and agent confusion during pair programming.

**Decisions.**
1. **Per-Project Confidence as Sole Metric:**
   - The primary unit of learning is the project knowledge item (`knowledge_items`), anchored to 1–12 real repository files.
   - We do not measure abstract language skill and we do not carry mastery or scores between projects. Everything shown to a learner is strictly scoped per project.

2. **Readiness Summary & Self-Rating:**
   - Project progress is communicated via concrete readiness counts (total parts, explained/shaky/unexplained by band, stale count, due count) and factual headlines (e.g. "14 of 19 parts explained"). No percentages and no arbitrary scores.
   - Explain-backs support an optional 1–5 `self_rating` logged alongside rubric evaluation as plain facts without verdict wording.

3. **Per-Project Profile Overrides:**
   - Projects can override the global learner profile preferences (level, goal, session minutes, audience) via `project_profile`. The effective profile coalesces project overrides over global defaults.

4. **Legacy Tables & Tool Gating:**
   - Historical tables (`skills`, `attempts`, `skill_mastery`, `mistakes`, `quizzes`, `quiz_questions`, `quiz_answers`) are preserved to prevent loss of existing learner history.
   - Legacy skill and quiz tools (`list_skills`, `propose_skill`, `get_skill_map`, `find_gaps`, `submit_attempt`, `get_teaching_context`, `create_quiz`, `record_quiz_result`, `flag_misunderstanding`) and the `teach-me` prompt are deprecated.
   - Legacy tools are registered on the MCP server *only* when `LEARNLOOP_LEGACY_TOOLS=1` (default off) to minimize MCP context window consumption and prevent agent decision confusion.
