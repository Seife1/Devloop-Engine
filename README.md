# LearnLoop

An MCP server that shows you where your AI coding agent did work you can't yet do alone, then gives you
short, targeted practice to close the gap.

**Core idea:** *exposure* (what the AI built, verified against git) is tracked separately from *mastery*
(what you demonstrated in your own graded attempts and explain-backs).

> ### 💡 The "AI Illusion of Competence"
> When an AI coding agent writes code that runs, reading it feels effortless. This creates a false sense
> of ownership. True technical mastery isn't having working code—it's being able to defend every decision,
> architectural pattern, and trade-off in an interview or code review without the AI.
>
> **How to protect yourself:**
> 1. **Commit frequently:** LearnLoop verifies AI work through Git commits. Uncommitted code is invisible.
> 2. **Take the tour:** Ask your AI *"give me a tour"* to understand entry points, data flows, and folder layout.
> 3. **Explain it back:** Check `.learn/concepts.md` and explain components in your own words.

```
Agent --intent--> start_skill_session --\
                                         +--> reconcile --> verified exposure --> find_gaps
git post-commit --> .learn/queue --------/                                         (+ your attempts => mastery)

Agent/Learner --> register_knowledge_item --> concepts.md
git commits   --> staleness detection     --> list_stale_items
```

## Quick start

```bash
pip install -e ".[dev]"
learnloop doctor                  # creates the DB, seeds the skill taxonomy, checks hooks
cd your-project && learnloop init # creates .learn/, installs the post-commit hook
learnloop backfill                # backfills pre-existing commits into .learn/queue
```

Add to your IDE's MCP config:

```json
{ "mcpServers": { "learnloop": { "command": "learnloop" } } }
```

Then paste `integrations/rules/CLAUDE.md.template` into your `CLAUDE.md` / `.cursorrules` so the agent
actually calls the tools.

## Tools (v0.4.0)

- **Knowledge Items & Memory:** `set_learner_profile` · `register_knowledge_item` · `record_explanation` · `list_items` · `list_stale_items`
- **Tour:** `get_project_tour`
- **Capture & Git Reconcile:** `start_project` · `start_skill_session` · `log_decision` · `flag_misunderstanding` · `ingest_queue`
- **Skills & Gaps:** `list_skills` · `propose_skill` · `get_skill_map` · `find_gaps` · `submit_attempt`
- **Lessons & Quizzes:** `get_teaching_context` · `create_quiz` · `record_quiz_result`

## Prompts

- `teach-me`: Start an interactive lesson grounded in your repository's commits.
- `tour`: Start an interactive codebase walkthrough from basic entry points to advanced components.

## Status

| Feature | Status | Details |
| :--- | :--- | :--- |
| Git post-commit hook queue | **Built** | Metadata-only JSON in `.learn/queue/`, non-blocking |
| Intent-commit reconciliation | **Built** | `exposure` verified against git commits |
| Backfill & tracked file snapshots | **Built** | `learnloop backfill` seeds existing repos |
| Project-grounded knowledge items | **Built** | Anchored to real project paths, bands Basic/Intermediate/Advanced |
| Learner profile | **Built** | Singleton preferences (`school` through `senior`, goals, audience) |
| Deterministic concept log | **Built** | Safe atomic generation of `.learn/concepts.md` |
| Project tour bundle | **Built** | Bounded evidence bundle (< 8 KB), entry points, manifests |
| Derived staleness detection | **Built** | Detects newer commits touching explained files |
| Spaced repetition scheduler | *Planned (Phase B)* | SM-2 interval calculations and pull-based reviews |
| Session-start briefing | *Planned (Phase B)* | Quick catch-up briefing (< 3 KB) |
| Resources (windowed, token-capped)| *Planned* | See `docs/adr/` |

## Develop

`make test` · `make lint` · `make inspect` (MCP Inspector). Logs go to stderr only; never `print()`.
