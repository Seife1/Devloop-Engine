# LearnLoop

An MCP server that shows you where your AI coding agent did work you can't yet do alone, then gives you
short, targeted practice to close the gap.

**Core idea:** *exposure* (what the AI built, verified against git) is tracked separately from *mastery*
(what you demonstrated in your own graded attempts).

```
Agent --intent--> start_skill_session --\
                                         +--> reconcile --> verified exposure --> find_gaps
git post-commit --> .learn/queue --------/                                         (+ your attempts => mastery)
```

## Quick start

```bash
pip install -e ".[dev]"
learnloop doctor                  # creates the DB, seeds the skill taxonomy
cd your-project && learnloop init # creates .learn/, installs the post-commit hook
```

Add to your IDE's MCP config:

```json
{ "mcpServers": { "learnloop": { "command": "learnloop" } } }
```

Then paste `integrations/rules/CLAUDE.md.template` into your `CLAUDE.md` / `.cursorrules` so the agent
actually calls the tools.

## Tools (v0.2)

`start_project` · `list_skills` · `start_skill_session` · `log_decision` · `flag_misunderstanding` ·
`ingest_queue` · `get_skill_map` · `find_gaps` · `submit_attempt` ·
`get_teaching_context` · `create_quiz` · `record_quiz_result`

Prompt: `teach-me`. (If your IDE doesn't surface MCP prompts, just say "teach me" — the tool result carries
the same instructions.)

## Not built yet

Resources (windowed, token-capped), `/milestone-review`, spaced repetition, journal writer, week-summary compaction. See `docs/adr/`.

## Develop

`make test` · `make lint` · `make inspect` (MCP Inspector). Logs go to stderr only; never `print()`.
