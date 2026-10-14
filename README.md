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

## CLI Commands

- `learnloop`: Start the MCP server over stdio.
- `learnloop init [--repo .]`: Initialize `.learn/` and install the post-commit git hook.
- `learnloop record-commit [--repo .]`: Record recent commit metadata to `.learn/queue/` (called by git hook).
- `learnloop backfill [--repo .] [--limit 50]`: Ingest existing commit history into the queue.
- `learnloop concepts [--repo .]`: Regenerate `.learn/concepts.md` from registered items.
- `learnloop review [--repo .]`: Conduct an interactive command-line spaced review session.
- `learnloop briefing [--repo .]`: Output today's session-start briefing in the terminal.
- `learnloop doctor`: Verify database migrations, taxonomy seeds, and git hooks.
- `learnloop dashboard [--port 8765]`: Start the local read-only web dashboard on `127.0.0.1:8765`.
- `learnloop techscan [--repo .]`: Deterministically scan repository dependencies and technologies.

## Tools (v0.5.3)

- **Technologies & Facts:** `refresh_technologies` · `add_did_you_know`
- **Knowledge Items & Readiness:** `register_knowledge_item` · `record_explanation` (with optional `self_rating`) · `list_items` · `list_stale_items` · `get_project_readiness`
- **Tour & Review:** `get_project_tour` · `review_due` · `record_review` · `snooze_review` · `get_session_briefing`
- **Capture & Git Reconcile:** `start_project` · `start_skill_session` (skills optional) · `log_decision` · `ingest_queue`
- **Profile:** `set_learner_profile` (supports optional `project_id` override)
- **Legacy Tools (opt-in via `LEARNLOOP_LEGACY_TOOLS=1`):** `list_skills` · `propose_skill` · `get_skill_map` · `find_gaps` · `submit_attempt` · `get_teaching_context` · `create_quiz` · `record_quiz_result` · `flag_misunderstanding`

## Prompts

- `tour`: Start an interactive codebase walkthrough from basic entry points to advanced components.
- `catch-up`: Deliver a quick session-start briefing on what changed.
- `review`: Run today's spaced repetition review of knowledge items.
- `mock-interview`: Conduct an interview on the project.
- `did-you-know`: Find and suggest verified technical facts related to project technologies.
- `teach-me` *(deprecated)*: Prefer tour, review, or mock-interview for per-project confidence.

## Status

| Feature | Status | Details |
| :--- | :--- | :--- |
| Git post-commit hook queue | **Built** | Metadata-only JSON in `.learn/queue/`, non-blocking |
| Intent-commit reconciliation | **Built** | `exposure` verified against git commits |
| Backfill & tracked file snapshots | **Built** | `learnloop backfill` seeds existing repos (single snapshot row) |
| Project-grounded knowledge items | **Built** | Anchored to real project paths, bands Basic/Intermediate/Advanced |
| Learner profile & project overrides | **Built** | Global preferences + per-project overrides via `project_profile` |
| Count-based project readiness | **Built** | `get_project_readiness` & briefing readiness (no percentages or scores) |
| Deterministic concept log | **Built** | Safe atomic generation of `.learn/concepts.md` with self-ratings |
| Local read-only dashboard | **Built** | `learnloop dashboard` on 127.0.0.1, mode=ro, custom Markdown renderer, no JS |
| Project tour bundle | **Built** | Bounded evidence bundle (< 8 KB), entry points, manifests |
| Derived staleness detection | **Built** | Detects newer commits touching explained files |
| Spaced repetition scheduler | **Built** | SM-2 interval calculations and pull-based reviews |
| Session-start briefing | **Built** | Quick catch-up briefing (< 3 KB) with compact readiness counts |
| Technologies & references scan | **Built** | Deterministic dependency and language detection (Step 3) |
| Sourced "Did you know" | **Built** | Verified web-sourced technical facts with mandatory links (Step 4) |
| Resources (windowed, token-capped)| *Planned* | See `docs/adr/` |

## Limits

- **Redaction is best-effort regex:** Free-text sanitization relies on regular expressions for secrets, credentials, and sensitive patterns. It cannot guarantee catch-all detection for all proprietary formats.
- **Staleness sees committed changes only:** Staleness detection evaluates git commits ingested into the database; uncommitted file edits or git stash changes are invisible to staleness.
- **One-second timestamp resolution:** Commit ordering and staleness comparisons use ISO timestamps with one-second resolution. Ties (commits within the same second) are not strictly greater than baseline.
- **The server cannot verify who wrote an answer:** LearnLoop evaluates and logs explanations and quiz answers submitted to its tools; the MCP server cannot verify whether the learner or the AI authored an answer.

## Develop

`make test` · `make lint` · `make inspect` (MCP Inspector). Logs go to stderr only; never `print()`.
