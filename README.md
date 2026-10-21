# LearnLoop

An MCP server that shows you where your AI coding agent did work you can't yet do alone, then gives you
short, targeted practice to close the gap.

> ### 🔒 100% Local-First & Zero Data Sharing
> **Your data never leaves your machine.**
> - **Local SQLite DB:** Your learning logs, review history, and commit tracking stay entirely on your disk.
> - **Local Dashboard:** Runs strictly on `http://127.0.0.1:8765` in read-only mode with zero external CDN dependencies.
> - **Zero Telemetry:** NO data is transmitted to external servers, cloud metrics, or third parties—not even the creator.

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

## 🚀 Quick Start (Zero-Dependency One-Liner)

**No Python, Node, or configuration required!** LearnLoop auto-detects your IDE and configures everything in 30 seconds:

### Windows (PowerShell):
```powershell
irm https://learnloop.dev/setup.ps1 | iex
```

### macOS & Linux (Terminal):
```bash
curl -fsSL https://learnloop.dev/setup.sh | bash
```

### Python Developers (pip / uv):
```bash
pip install -e ".[dev]"
learnloop init --integrate
```

### What This Does Automatically:
- ✅ **Detects your IDE** (VS Code, Cursor, Claude, WindSurf, Zed)
- ✅ **Configures MCP settings** for AI assistants
- ✅ **Adds LearnLoop rules** to IDE configs
- ✅ **Creates terminal shortcuts** (`learnloop-tools`)
- ✅ **Sets up environment aliases** (`llb`, `llr`, `lld`)

### Terminal Usage (Anywhere):
```bash
# Get session briefing
learnloop-tools briefing

# Start work session
learnloop-tools start-session "Implement feature" "file1.py,file2.py"

# Review knowledge
learnloop-tools review

# Open dashboard
learnloop-tools dashboard

# See all commands
learnloop-tools help
```

## 🔧 Manual Setup (Optional)

If you prefer manual configuration:

```bash
pip install -e ".[dev]"
learnloop doctor                  # creates the DB, seeds the skill taxonomy, checks hooks
cd your-project && learnloop init # creates .learn/, installs the post-commit hook
learnloop backfill                # backfills pre-existing commits into .learn/queue
```

For IDE integration:

```bash
# Auto-integrate with detected IDE
learnloop integrate --ide auto

# Or specify IDE
learnloop integrate --ide vscode
learnloop integrate --ide cursor
learnloop integrate --ide claude
```

## 📋 CLI Commands

### Core Commands:
- `learnloop gui [--port 8765] [--route /setup|/]`: Launch native Microsoft Edge WebView2 desktop application window
- `learnloop setup [--port 8765] [--browser] [--no-browser]`: Interactive 3-step setup wizard
- `learnloop dashboard [--port 8765] [--gui]`: Web dashboard on `127.0.0.1:8765` (optional `--gui` window)
- `learnloop init [--repo .] [--integrate]`: Initialize `.learn/` with optional IDE integration
- `learnloop integrate [--ide auto|vscode|cursor|claude|windsurf|zed|all] [--terminal] [--env] [--all]`: Universal integration
- `learnloop record-commit [--repo .]`: Record recent commit metadata (called by git hook)
- `learnloop backfill [--repo .] [--limit 50]`: Ingest existing commit history
- `learnloop concepts [--repo .]`: Regenerate `.learn/concepts.md`
- `learnloop review [--repo .]`: Interactive spaced repetition review
- `learnloop briefing [--repo .]`: Session-start briefing
- `learnloop doctor`: Verify database, taxonomy, hooks
- `learnloop techscan [--repo .]`: Scan repository dependencies

### Terminal Shortcuts (after `learnloop integrate --terminal`):
- `learnloop-tools briefing`: Get session update
- `learnloop-tools start-session`: Start work session
- `learnloop-tools review`: Review knowledge
- `learnloop-tools register`: Register knowledge item
- `learnloop-tools dashboard`: Open dashboard
- `learnloop-tools integrate`: Integrate with IDEs

### Environment Aliases (after sourcing):
- `llb`: Get briefing
- `llr`: Start review  
- `lld`: Open dashboard

## 🌐 HTTP/SSE Deployment

Deploy as a hosted HTTP service (not PyPI):

```bash
# Install HTTP dependencies
pip install -r requirements_http.txt

# Start HTTP server
python learnloop_http.py
# Access: http://localhost:8000
```

### Endpoints:
- `GET /` - Server info
- `POST /api/initialize` - Initialize project
- `GET /api/tools` - List tools
- `POST /api/execute` - Execute tool
- `GET /api/events` - Server-Sent Events stream
- `GET /health` - Health check

## 🛠️ Tools (v2.0.0)

### Learning & Tracking:
- `start_skill_session` - Start work session with intent tracking
- `get_session_briefing` - Get session-start update
- `get_project_tour` - Architecture walkthrough
- `log_decision` - Log design decisions

### Knowledge Management:
- `register_knowledge_item` - Register concepts for spaced repetition
- `record_explanation` - Record explanations with self-rating
- `review_due` - Get items due for review
- `record_review` - Record review outcomes
- `snooze_review` - Snooze review items

### Git Integration:
- `ingest_queue` - Process commit queue
- `list_stale_items` - List items needing review due to changes
- `get_project_readiness` - Get project readiness level

### Insights & Discovery:
- `add_did_you_know` - Add technical insights
- `refresh_technologies` - Refresh technology detection

## 🎯 How It Works

### With AI Assistants (after integration):
1. **Session Start**: AI calls `get_session_briefing` automatically
2. **Architecture**: AI calls `get_project_tour` for walkthroughs  
3. **Work**: AI calls `start_skill_session` before coding
4. **Decisions**: AI calls `log_decision` for alternatives
5. **After Commits**: AI calls `ingest_queue` to track work
6. **Knowledge**: AI offers `register_knowledge_item` for key concepts
7. **Reviews**: AI helps with `review_due` and `record_review`
8. **Insights**: AI adds `add_did_you_know` for technical facts

### Git Integration:
- Post-commit hooks track AI work automatically
- Commits verify exposure (what AI built)
- Staleness detection alerts when code changes
- Backfill processes existing commit history

## 📊 Dashboard

Access the dashboard at `http://localhost:8765`:

- **Project Overview**: Activity visualization
- **Knowledge Tracking**: Item status and reviews
- **Staleness Detection**: Files changed since explanation
- **Best Practices**: Learning workflow guide
- **Progress Metrics**: Readiness levels and milestones

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   AI Assistant  │    │   LearnLoop     │    │     Git         │
│   (Any IDE)     │◄──►│   MCP Server    │◄──►│   Repository    │
│                 │    │                 │    │                 │
│ • MCP Tools     │    │ • Auto-tracking │    │ • Post-commit   │
│ • Rules         │    │ • Reconciliation│    │   hooks         │
│ • Integration   │    │ • Spaced rep.   │    │ • Commit queue  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │
         │                        │
         ▼                        ▼
┌─────────────────┐    ┌─────────────────┐
│   Terminal      │    │   Dashboard     │
│   Interface     │    │   (Web UI)      │
│                 │    │                 │
│ • learnloop-tools│   │ • Visualization │
│ • Aliases       │    │ • Insights      │
│ • Environment   │    │ • Best Practices│
└─────────────────┘    └─────────────────┘
```

## 🚀 Deployment Options

### 1. **Local Development** (Recommended for testing):
```bash
pip install -e ".[dev]"
learnloop init --integrate
learnloop dashboard
```

### 2. **HTTP Service** (Your distribution strategy):
```bash
# Deploy as HTTP/SSE service
python learnloop_http.py --host 0.0.0.0 --port 8000

# Docker deployment
docker build -t learnloop .
docker run -p 8000:8000 -p 8765:8765 learnloop
```

### 3. **Remote & LAN Setup (Connect Another PC over Wi-Fi)**:

Run LearnLoop on your main workstation and connect any remote IDE (Windsurf, VS Code, Cursor) from another computer on the same network.

**On the Host PC (Server):**
```bash
python learnloop_http.py --host 0.0.0.0 --port 8000
```
*(Find your host IP using `ipconfig` or `ifconfig`, e.g. `192.168.10.199`)*

**On the Other PC (One-Fly Setup):**
Navigate to your project directory in terminal and run a single command:

* **Windows (PowerShell):**
  ```powershell
  irm http://<HOST-IP>:8000/setup.ps1 | iex
  ```
* **macOS / Linux (Bash):**
  ```bash
  curl -sSL http://<HOST-IP>:8000/setup.sh | bash
  ```

This single command automatically:
1. Ingests the official 8-rule `AGENTS.md` and `.windsurfrules` into your workspace.
2. Injects the `learnloop` server configuration with `mcp-remote` into Windsurf (`mcp_config.json`), VS Code (`.vscode/settings.json`), and Cursor.
3. Connects your remote IDE over the local network with zero manual JSON editing.

### 4. **Platform Cloud Deployments**:
- **Fly.io**, **Railway.app**, **Render.com**
- Supports both modern **Streamable HTTP** (`/mcp`) and legacy **HTTP+SSE** (`/sse`).

## 📈 Status

| Feature | Status | Details |
| :--- | :--- | :--- |
| Universal IDE Integration | **✅ Built** | Auto-detects VS Code, Cursor, Claude, WindSurf, Zed |
| Terminal Integration | **✅ Built** | `learnloop-tools`, aliases, environment setup |
| HTTP/SSE Deployment | **✅ Built** | Streamable endpoints, real-time events |
| Git Integration | **✅ Built** | Automatic tracking via post-commit hooks |
| Dashboard | **✅ Built** | Visual insights, best practices guide |
| Spaced Repetition | **✅ Built** | SM-2 algorithm with review scheduling |
| Knowledge Management | **✅ Built** | Item registration, concepts.md generation |
| Staleness Detection | **✅ Built** | Alerts when explained code changes |
| Progressive Enhancement | **✅ Built** | Readiness levels, feature unlocking |
| Multi-project Support | **✅ Built** | Data isolation, independent tracking |
| Security Features | **✅ Built** | Code redaction, local-only binding |

## 🔒 Security & Privacy

- **Local-First**: Data stays on your machine by default
- **Code Redaction**: Best-effort secret detection
- **HTTP Security**: Optional authentication for production
- **Git Integration**: Non-invasive hooks, preserves existing functionality
- **Dashboard**: Local-only binding (`127.0.0.1`)

## 🆘 Troubleshooting

**IDE not detecting?**
```bash
# Force specific IDE
learnloop integrate --ide vscode --force
```

**Terminal tools not working?**
```bash
# Use full path
./.learn/tools.sh briefing

# Or add to PATH
export PATH="$PATH:$(pwd)/.learn"
```

**Dashboard not loading?**
```bash
# Check if running
learnloop dashboard --port 8765

# Access: http://localhost:8765
```

## 🎯 The Goal

**Zero friction, maximum learning.** You focus on building with AI, LearnLoop handles:
- Tracking what AI builds
- Reinforcing what you learn  
- Showing progress
- Preparing you to explain your code

No manual file copying. No complex setup. Just `learnloop integrate --all` and start learning! 🚀

## 📚 Learn More

- [Universal Integration Guide](UNIVERSAL_INTEGRATION.md) - Complete integration details
- [Testing Guide](TEST_INSTRUCTIONS.md) - How to test with real projects
- [HTTP Deployment](DEPLOYMENT.md) - HTTP/SSE distribution strategy
- [Setup & Testing](SETUP_AND_TESTING.md) - Comprehensive testing workflow

## 🛠️ Development

```bash
# Run tests
python -m pytest tests/ -v

# Run linter
python -m black src/ tests/

# Start development server
python -m learnloop.dashboard
```

Logs go to stderr only; never `print()`.
