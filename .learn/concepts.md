# Project Concepts & Learning Guide

> ### 💡 The "AI Illusion of Competence"
> When an AI writes code that works, reading it feels easy. This creates a false sense of
> ownership. True mastery isn't having working code—it's being able to defend every
> decision, file, and trade-off in an interview or code review without the AI.
>
> **How to protect yourself:**
> 1. **Commit early & often:** LearnLoop tracks learning through Git commits.
>    Uncommitted edits are invisible.
> 2. **Take the tour:** Ask your AI *"give me a tour"* to understand entry points and flows.
> 3. **Explain it back:** When prompted, explain what the code does in your own words.
>
> *Note: Explanations below are AI-assisted study notes and may be incomplete or mistaken.*

## Basic

### Architecture & Intent Reconcile Loop (`architecture.overview`)
- **Kind**: concept | **Status**: unexplained | **Depth**: 1/5 (what)
- **Files**: `README.md`, `pyproject.toml`
- **Summary**: LearnLoop is an MCP companion server that separates AI code exposure from human developer mastery, reconciling IDE intents against git commits.

### Git Hook & Offline Commit Queue (`capture.hook_queue`)
- **Kind**: component | **Status**: unexplained | **Depth**: 1/5 (what)
- **Files**: `integrations/hooks/post-commit`, `src/learnloop/capture/queue.py`
- **Summary**: The non-blocking post-commit hook writing redacted commit metadata to .learn/queue/ for pull-based ingestion.

### CLI & Stdio Entry Point (`entrypoint.cli`)
- **Kind**: component | **Status**: unexplained | **Depth**: 1/5 (what)
- **Files**: `src/learnloop/__main__.py`, `src/learnloop/cli.py`
- **Summary**: The command-line interface providing learnloop (stdio MCP server), init (hook installer), record-commit, backfill, and doctor.

### FastMCP Server Wiring (`server.mcp`)
- **Kind**: component | **Status**: unexplained | **Depth**: 1/5 (what)
- **Files**: `src/learnloop/server.py`
- **Summary**: Assembles and runs the FastMCP stdio server, exposing capture, knowledge items, tour, and teaching tools.

## Intermediate

*(No items in this section yet)*

## Advanced

*(No items in this section yet)*
