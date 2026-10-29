# 🚀 LearnLoop Universal Integration

**Zero repo pollution. Zero configuration.** LearnLoop automatically detects your active IDE session and configures only the tools you need.

## 🔧 One-Command Setup

```bash
# In your project directory
learnloop init
```

This automatically:
1. 🎯 **Detects your active IDE**: Inspects runtime session signatures (`VS Code`, `Cursor`, `Windsurf`, `Claude`, `Zed`, or `Antigravity`).
2. 🔒 **Configures ONLY that IDE**: Creates exact MCP settings and companion rules for your active editor without touching or dumping files for other editors.
3. 🛡️ **Installs git hook**: Non-blocking post-commit tracking in `.learn/`.

---

## 🎯 How It Works

### Session-Aware Detection (Default)
When you run `learnloop init` from your editor's integrated terminal:
- **VS Code**: Configures `.vscode/settings.json` and `.vscode/mcp.json`.
- **Cursor**: Configures `.cursorrules` and `.cursor/mcp.json`.
- **Windsurf**: Configures `.windsurfrules` and `.windsurf/mcp_config.json`.
- **Claude Code / Desktop**: Configures `CLAUDE.md` and Claude Desktop config.
- **Zed**: Configures `.zed/settings.json`.
- **Antigravity / Universal**: Configures `AGENTS.md` and `GEMINI.md`.

### Explicit Overrides (Optional)
If you ever want to force a specific IDE integration or run from an external terminal:
```bash
# Explicit target
learnloop init --ide vscode
learnloop init --ide cursor
learnloop init --ide windsurf
learnloop init --ide claude

# Skip integration entirely
learnloop init --no-integrate

# Full development setup (integrates all IDEs and creates shell wrappers)
learnloop init --all
```

### Terminal Shortcuts (Optional, via `learnloop integrate --terminal`)
```bash
learnloop integrate --terminal

# Now use:
learnloop-tools briefing      # Get session update
learnloop-tools start-session # Start work session  
learnloop-tools review        # Review knowledge
learnloop-tools dashboard     # Open dashboard
```

---

## 📋 IDE Support Matrix

| IDE | Live Session Detection | MCP Config | Companion Rules | Repo Pollution |
|-----|:---------------------:|:----------:|:---------------:|:--------------:|
| **VS Code** | ✅ (`TERM_PROGRAM`, `VSCODE_PID`) | `.vscode/settings.json` + `mcp.json` | Built-in | ❌ None (only VS Code) |
| **Cursor** | ✅ (`CURSOR_TRACE_ID`, `CURSOR_VERSION`) | `.cursor/mcp.json` | `.cursorrules` | ❌ None (only Cursor) |
| **Windsurf** | ✅ (`WINDSURF_VERSION`, Codeium path) | `.windsurf/mcp_config.json` | `.windsurfrules` | ❌ None (only Windsurf) |
| **Claude Desktop / Code** | ✅ (`CLAUDE_CODE`, `CLAUDE_PROJECT_DIR`) | `claude_desktop_config.json` | `CLAUDE.md` | ❌ None (only Claude) |
| **Zed** | ✅ (`TERM_PROGRAM=zed`, `ZED_TERM`) | `.zed/settings.json` | Built-in | ❌ None (only Zed) |
| **Antigravity / Agents** | ✅ (`ANTIGRAVITY_AGENT=1`) | Native IDE MCP | `AGENTS.md` + `GEMINI.md` | ❌ None (only Agents) |

---

## 🔍 What Gets Created

When running `learnloop init` in your project:
- **In VS Code**: `.vscode/settings.json` and `.vscode/mcp.json`
- **In Cursor**: `.cursorrules` and `.cursor/mcp.json`
- **In Windsurf**: `.windsurfrules` and `.windsurf/mcp_config.json`
- **In Claude**: `CLAUDE.md` (and updates global Claude Desktop JSON if installed)
- **In Zed**: `.zed/settings.json`
- **In Antigravity / Standalone**: `AGENTS.md` and `GEMINI.md`
- **Git Hook**: `.learn/hooks/post-commit` (verifies code you and your AI build)
- **Concepts Journal**: `.learn/concepts.md` (tracks explained components)

*Note: Terminal wrappers (`tools.sh`, `tools.bat`) and shell profiles (`environment.sh`, `LearnLoop.ps1`) are **not** created by default to keep projects completely clean. They are only created if you explicitly pass `--all` or `--terminal`.*

---

## 🎮 How AI Assistants Work With LearnLoop

LearnLoop uses 4 domain-clustered MCP tools with minimal token overhead:

1. **Session Start**: AI calls `manage_reviews(action="briefing")` for context.
2. **Architecture**: AI calls `explore_project(action="tour")` when asked for walkthroughs.
3. **Active Coding**: AI calls `track_intent(action="start_session", files=[...], summary="...")` before implementing.
4. **Architectural Decisions**: AI calls `track_intent(action="log_decision", ...)` to document trade-offs.
5. **After Commits**: Git post-commit hook logs commits $\rightarrow$ AI calls `track_intent(action="reconcile")`.
6. **Knowledge Catalog**: AI calls `manage_knowledge(action="register", ...)` for new components.
7. **Spaced Reviews**: AI tests the learner via `manage_reviews(action="due")` and records responses.

---

## ❓ Troubleshooting

**Want to re-run or force overwrite?**
```bash
learnloop integrate --ide auto --force
```

**Using an external terminal (e.g. Windows Terminal or Bash outside of your IDE)?**
LearnLoop automatically checks your repo for markers (`.vscode`, `.cursor`, `.windsurf`, etc.) or you can pass the target explicitly:
```bash
learnloop init --ide vscode
```

**MCP server not responding in IDE?**
1. Restart your editor so it reloads the MCP config.
2. Run `learnloop doctor` to verify SQLite database, skills taxonomy, and schema migrations.
3. Verify `learnloop` is accessible on your system PATH (`where.exe learnloop` or `which learnloop`).

---

## 🎯 The Goal

**Zero friction, zero repository pollution, maximum learning.** You focus on building with AI; LearnLoop quietly tracks what your AI builds and prepares you to defend your code.

Just `learnloop init` and start coding! 🚀
