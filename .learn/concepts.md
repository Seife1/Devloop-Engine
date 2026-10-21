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
- **Kind**: concept | **Status**: explained | **Depth**: 1/5 (what)
- **Files**: `README.md`, `pyproject.toml`
- **Summary**: LearnLoop is an MCP companion server that separates AI code exposure from human developer mastery, reconciling IDE intents against git commits.
- **Latest explanation** (score 1.0): "git hook is source of thruth"

### Git Hook & Offline Commit Queue (`capture.hook_queue`)
- **Kind**: component | **Status**: shaky | **Depth**: 1/5 (what)
- **Files**: `integrations/hooks/post-commit`, `src/learnloop/capture/queue.py`
- **Summary**: The non-blocking post-commit hook writing redacted commit metadata to .learn/queue/ for pull-based ingestion.
- **Latest explanation** (score 0.5): "Alright, the post commit is not worked with running server it's totally independent, the aim is to reduce cpu overhead and avoiding slow down of the server, so what ever done on developer side it takes his time and save the hook"

### CLI & Stdio Entry Point (`entrypoint.cli`)
- **Kind**: component | **Status**: unexplained | **Depth**: 1/5 (what)
- **Files**: `src/learnloop/__main__.py`, `src/learnloop/cli.py`
- **Summary**: The command-line interface providing learnloop (stdio MCP server), init (hook installer), record-commit, backfill, and doctor.

### FastMCP Server Wiring (`server.mcp`)
- **Kind**: component | **Status**: unexplained | **Depth**: 1/5 (what)
- **Files**: `src/learnloop/server.py`
- **Summary**: Assembles and runs the FastMCP stdio server, exposing capture, knowledge items, tour, and teaching tools.

### <script>alert(1)</script> (`test.xss`)
- **Kind**: concept | **Status**: unexplained | **Depth**: 1/5 (what)
- **Files**: `pyproject.toml`
- **Summary**: Testing XSS protection in dashboard rendering

## Intermediate

### Zero-Dependency Standalone Binary & Universal Installer (`distribution.standalone_binary`)
- **Kind**: component | **Status**: unexplained | **Depth**: 1/5 (what)
- **Files**: `src/learnloop/cli.py`, `src/learnloop/config.py`
- **Summary**: Standalone zero-dependency binary packaging via PyInstaller and 1-line cross-platform installers (setup.ps1 / setup.sh) delivering 100% local-first SQLite and automated IDE integration.

### SQLite Schema Migrations & Backups (`persistence.migrations`)
- **Kind**: component | **Status**: unexplained | **Depth**: 1/5 (what)
- **Files**: `src/learnloop/persistence/db.py`
- **Summary**: Forward-only SQLite schema migrations tracked by PRAGMA user_version with automatic pre-migration backup files.

### Intent & Commit Reconciliation (`reconciliation.intent_commit`)
- **Kind**: component | **Status**: unexplained | **Depth**: 1/5 (what)
- **Files**: `src/learnloop/services/reconcile_service.py`
- **Summary**: Reconciliation service joining AI agent intent with git commit outcomes using file overlap and exponential time decay.

### HTTP & SSE Streaming Server (`server.http_sse`)
- **Kind**: component | **Status**: explained | **Depth**: 1/5 (what)
- **Files**: `DEPLOYMENT.md`, `learnloop_http.py`
- **Summary**: FastAPI wrapper hosting FastMCP tools over HTTP REST, SSE, and Streamable HTTP, with dynamic one-shot LAN setup endpoints (/setup.ps1, /setup.sh).
- **Latest explanation** (score 0.8): "Because since cloud or browser based ide are on remote, no need to a local terminal subprocess."

### Knowledge Staleness Detection (`staleness.detection`)
- **Kind**: concept | **Status**: explained | **Depth**: 1/5 (what)
- **Files**: `src/learnloop/domain/staleness.py`
- **Summary**: Pure domain logic determining when an explained item becomes stale based on newer git commits touching its files.
- **Latest explanation** (score 0.9): "If AI or other teammates update any codebase, the learnloop check a baseline commit, which is previously explained as stale by developer and marked as stale. So because of new commit it just calmly moved to the top of review queue, so the developer can refresh it, without penalizing the developer. So this is very good to be up to date on what have been changed for developer and refresh his knowledge."

## Advanced

### SM-2 Spaced Repetition Scheduling (`scheduling.sm2`)
- **Kind**: concept | **Status**: explained | **Depth**: 1/5 (what)
- **Files**: `src/learnloop/domain/scheduling.py`
- **Summary**: SM-2-style spaced repetition scheduler computing interval days, ease adjustments, and repetition counts from attempt scores.
- **Latest explanation** (score 0.8): "If the developer answer well, on the tour, which means he understands well, eventhough he may copy paste from other(that is the limitation). So the day jumps from 1 to 3 to review/recall"

### Path Normalization & Traversal Defense (`security.path_traversal`)
- **Kind**: concept | **Status**: unexplained | **Depth**: 1/5 (what)
- **Files**: `src/learnloop/domain/path_utils.py`
- **Summary**: Pure domain logic enforcing path normalization, cross-platform slashes, and blocking parent traversal and absolute path injection.
