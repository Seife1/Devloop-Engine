# LearnLoop Agent Setup Instructions

These are official instructions to configure the LearnLoop learning companion MCP server in any AI coding environment globally. All instructions are designed to be autonomously executed by the AI agent itself.

Complete all of the following steps yourself by running the terminal commands or editing configuration files directly. Do not ask the developer to perform manual configuration.

---

## What is LearnLoop?
LearnLoop is a cognitive learning companion MCP server that bridges the gap between what AI builds and what the developer can explain and defend. It exposes 4 domain-clustered MCP tools:
1. `track_intent`: Active coding sessions, architectural decisions, and commit reconciliations.
2. `manage_reviews`: Spaced repetition catch-up briefings, due reviews, and flashcard practice.
3. `manage_knowledge`: Component registration, knowledge cataloging, and code comprehension checks.
4. `explore_project`: Codebase architectural tours and technological insights.

---

## Step 1: Detect Host Environment & Register LearnLoop MCP Globally

Inspect your runtime host environment (or configure the user's active IDE/Agent) using the global or user-level configuration path. LearnLoop runs via `uvx` directly from GitHub—no local repo cloning or PyPI installation required.

### 1. Claude Code
Run the following terminal command:
```bash
claude mcp add learnloop uvx --from git+https://github.com/Seife1/Devloop-Engine.git learnloop
```

### 2. Cursor
Add to the global MCP config at `~/.cursor/mcp.json` (Windows: `%USERPROFILE%\.cursor\mcp.json` or project `.cursor/mcp.json`):
```json
{
  "mcpServers": {
    "learnloop": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/Seife1/Devloop-Engine.git",
        "learnloop"
      ]
    }
  }
}
```

### 3. Windsurf / Devin Desktop
Add to global configuration at `~/.codeium/windsurf/mcp_config.json`:
```json
{
  "mcpServers": {
    "learnloop": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/Seife1/Devloop-Engine.git",
        "learnloop"
      ]
    }
  }
}
```

### 4. Claude Desktop
Add to:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
```json
{
  "mcpServers": {
    "learnloop": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/Seife1/Devloop-Engine.git",
        "learnloop"
      ]
    }
  }
}
```

### 5. Antigravity IDE / Gemini Code Assist
Add to global config `~/.gemini/config/mcp_config.json` or workspace `.agents/mcp_config.json`:
```json
{
  "mcpServers": {
    "learnloop": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/Seife1/Devloop-Engine.git",
        "learnloop"
      ]
    }
  }
}
```

### 6. VS Code / GitHub Copilot
Add to `.vscode/mcp.json` in the workspace or user settings:
```json
{
  "mcpServers": {
    "learnloop": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/Seife1/Devloop-Engine.git",
        "learnloop"
      ]
    }
  }
}
```

### 7. Zed
Add to `.zed/settings.json`:
```json
{
  "context_servers": {
    "learnloop": {
      "command": {
        "path": "uvx",
        "args": [
          "--from",
          "git+https://github.com/Seife1/Devloop-Engine.git",
          "learnloop"
        ]
      }
    }
  }
}
```

---

## Step 2: Inject the Companion Agent Steering Rules

You MUST inject the LearnLoop companion rules into the agent instruction file corresponding to your host. Without these rules, the agent will not proactively track intents or conduct reviews.

Target rule files:
- **Claude Code**: `~/.claude/CLAUDE.md` (or project `CLAUDE.md`)
- **Cursor**: `~/.cursorrules` (or project `.cursorrules`)
- **Windsurf**: `~/.windsurfrules` (or project `.windsurfrules`)
- **Antigravity / Universal**: `AGENTS.md` and `GEMINI.md`
- **GitHub Copilot**: `.github/copilot-instructions.md`

Append this exact block:

```markdown
## LearnLoop (Learning Companion)

You are paired with a developer who builds with AI and wants to understand and retain everything built. Use the 4 LearnLoop MCP tools (`project_id` is automatically resolved):

1. **Active Coding** (`track_intent`):
   - Before implementing meaningful work: call `track_intent(action="start_session", summary="...", files=[...])`.
   - When choosing between real technical alternatives: call `track_intent(action="log_decision", choice="...", alternatives=[...], tradeoffs="...")`.
   - After commits: call `track_intent(action="reconcile")`. NEVER log what you merely "did" as learning; git commits are the proof.
2. **Spaced Repetition & Catch-up** (`manage_reviews`):
   - At session start: call `manage_reviews(action="briefing")` for a calm catch-up briefing.
   - For reviews/interview prep: call `manage_reviews(action="due")`, ask ONE question at a time, and record outcomes with `manage_reviews(action="record", ...)`.
3. **Knowledge Catalog** (`manage_knowledge`):
   - When creating a component or fixing a subtle bug: call `manage_knowledge(action="register", key="...", title="...", kind="...", band="...", files=[...], summary="...")`.
   - To inspect concepts: call `manage_knowledge(action="list")` (compact by default).
4. **Codebase Exploration** (`explore_project`):
   - For codebase walkthroughs or onboarding: call `explore_project(action="tour")`. Walk bands in strict order (Basic -> Intermediate -> Advanced). At the end of each band, pause and prompt ONE targeted reflective question grounded in the code just covered. If the learner answers, call `manage_knowledge(action="explain", key=..., learner_text=..., score=...)`; if they say "continue" or "skip", advance immediately.
   - When introducing new technologies: call `explore_project(action="add_fact", ...)` with a verified technical insight.
```

---

## Step 3: Project Workspace Initialization

In the developer's current project workspace, run the non-blocking initialization command to hook git commits and create the local `.learn/` directory:

```bash
uvx --from git+https://github.com/Seife1/Devloop-Engine.git learnloop init
```

*Note: If the developer is in a repository, this attaches a lightweight post-commit hook so any git commits are automatically verified.*

---

## Step 4: Verification, Self-Testing & Reload Notice

1. **Verify Tool Availability**:
   - Check if MCP tools `track_intent`, `manage_reviews`, `manage_knowledge`, and `explore_project` are actively registered and visible in your toolset.
   - Test a lightweight call (e.g. `manage_reviews(action="briefing")` or `manage_knowledge(action="list")`).
2. **If Tools Are Not Yet Visible**:
   - Notify the developer that their host IDE/Agent requires a one-time restart or window reload (e.g., `Developer: Reload Window` in VS Code / Cursor, or `/reload` in Claude) to load newly registered MCP servers.
   - After reloading, verify the tool list again.

---

## Step 5: Report to Developer

Present the setup status clearly:

```
┌─ LearnLoop AI Companion Setup Complete ────────────────────────┐
│  ✓ MCP Server:  learnloop (registered globally via uvx)        │
│  ✓ Agent Rules: Companion instructions ingested                │
│  ✓ Workspace:   Initialized (.learn/ + commit tracking ready)  │
│                                                                │
│  ⚡ Note: If MCP tools are not showing, reload your IDE window  │
└────────────────────────────────────────────────────────────────┘
```
Explain briefly what was configured and invite them to start a session or run a briefing:
`"I'm all set up as your LearnLoop learning companion. Would you like a catch-up briefing or to start our first learning session?"`
