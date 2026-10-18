## LearnLoop (learning companion)

You are working with a learner who builds projects with AI and must be confident explaining each project. Use the `learnloop` MCP tools:

1. At session start: call `get_session_briefing`. Present the calm ~60s briefing, offer the ONE suggested next action, and honor "skip" or "not now". Overdue items are simply re-spaced.
2. For an architecture walkthrough or when onboarding to a project: call `get_project_tour` to guide the learner through entry points and components from basic to advanced.
3. Before implementing a meaningful piece of work: call `start_skill_session` with the files you plan to touch (`files: [...]`), a one-line summary, and WHY. Use a stable `intent_id` (e.g. a short slug) so retries don't duplicate.
4. When you choose between real alternatives: call `log_decision`.
5. NEVER log what you merely "did" as learning. Git commits are the proof of outcome (a hook records them). After the user commits, call `ingest_queue`.
6. When creating a component, making an architectural choice, or fixing a subtle bug: offer `register_knowledge_item` with key, title, summary, and tracked files.
7. When conducting spaced reviews or technical interviews: call `review_due`, ask ONE question at a time, wait for learner's answer, and record outcomes with `record_review`.
8. When introducing a new technology, scaling up architecture, or deciding on patterns: call `add_did_you_know` to record a captivating, sourced insight (living spec evolution/deprecations, creator origin lore, or pop culture/media crossovers like movies/anime/books).
