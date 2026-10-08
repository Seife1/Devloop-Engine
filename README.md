# Devloop Engine

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
.\venv\Scripts\activate
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

## Tools (v0.1)

`start_project` · `list_skills` · `start_skill_session` · `log_decision` · `flag_misunderstanding` ·
`ingest_queue` · `get_skill_map` · `find_gaps` · `submit_attempt`

## Not built yet

Resources (windowed, token-capped), prompts (`/teach-me`, `/milestone-review`), quiz generation and
rubrics, spaced repetition, journal writer, week-summary compaction. See `docs/adr/`.

## Develop

python -m venv venv
. venv/Scripts/activate
pip install -e "[dev]"
pytest
