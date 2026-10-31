# LearnLoop

![Version](https://img.shields.io/badge/version-0.7.0-blue.svg) ![License](https://img.shields.io/badge/license-MIT-green.svg)

An MCP server that shows you where your AI coding agent did work you can't yet do alone, then gives you
short, targeted practice to close the gap.

> ### 🔒 100% Local-First & Zero Workspace Pollution ("Ghost Mode")
> **Your repository and your data stay clean and private.**
> - **Zero Repo Pollution:** LearnLoop runs completely in the background without injecting `.learn/` folders or creating PR/git clutter. Workspace artifacts (commit queues, concept logs, terminal scripts) are isolated in `~/.learnloop/workspaces/<hash>/`.
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
Agent --intent--> track_intent(action="start_session") --\
                                                         +--> track_intent(action="reconcile") --> verified exposure
git post-commit --> .learn/queue -----------------------/                                         (+ your attempts => mastery)

Agent/Learner --> manage_knowledge(action="register") --> concepts.md
git commits   --> staleness detection                 --> manage_knowledge(action="list", stale_only=True)
```

### 💡 Dual-Loop Learning: Dashboard vs. IDE

LearnLoop operates across two complementary learning surfaces:

1. **Local Dashboard (Mission Control):**
   - Visualizes your SuperMemo-2 (SM-2) retention curve, project readiness score (0-100), and unreviewed commit queue.
   - Flags **Stale Invariants** whenever new Git commits modify code you previously explained.
   - Provides quick 2-minute self-grading card decks.

2. **Your IDE (Interactive AI Sparring Partner):**
   - **Why learning inside your IDE is superior:** Your AI coding assistant (Cursor, Windsurf, VS Code, Claude, Antigravity) reads your active codebase, AST, and recent Git diffs. It doesn't just show flashcards—it **challenges your architectural decisions**, tests boundary conditions, and spots subtle misunderstandings in real time.
   - **How to spar with LearnLoop in your IDE chat:**
     - `/review` (or *"Review my due concepts"*): Pulls items due today under SM-2 (`manage_reviews(action="due")`) and tests your understanding one question at a time.
     - `/interview` (or *"Interview me on this project"*): Adopts a tech-lead persona and drills deeply into your architectural trade-offs, edge cases, and failure modes.
     - `/tour` (or *"Tour the codebase"*): Walks you through cognitive bands (Basic &rarr; Intermediate &rarr; Advanced) with comprehension checkpoints at each level.
     - `/catch-up` (or *"Catch me up"*): Gives you a 2-minute briefing on recent commits, drifted invariants, and pending review cards.

---

## 🚀 Quick Start (Local Clone Installation)

**No external cloud dependencies required!** LearnLoop auto-detects your IDE and configures everything in 30 seconds:

### Windows (Local PowerShell):
```powershell
.\setup.ps1
```

### macOS & Linux (Local Terminal):
```bash
./setup.sh
```

### Python Developers (pip / uv):
```bash
pip install -e ".[dev]"
learnloop init
```

> **🌐 Dynamic Web Installer:** When hosting the website or accessing your deployed documentation, copy-paste the auto-detected one-liner (`irm https://<your-host>/setup.ps1 | iex` or `curl -fsSL https://<your-host>/setup.sh | bash`) from the website download dock—the command automatically adapts to whichever domain or port is serving it.

### What This Does Automatically (Zero Project Pollution):
- 🎯 **Session-Aware IDE Detection**: Automatically identifies the exact editor hosting your current terminal session (`VS Code`, `Cursor`, `Windsurf`, `Claude`, `Zed`, or `Antigravity`).
- 🔒 **Clean Isolation**: Only writes configurations for your active editor. It will **never** dump unwanted rules or configs for other editors into your repository.
- ⚙️ **Configures MCP & Rules**: Sets up the Model Context Protocol server configuration and canonical LearnLoop companion instructions.
- 🛡️ **Ghost Mode Git Hook**: Installs the non-blocking post-commit verification hook and adds `.learn/` to `.git/info/exclude` to guarantee 100% zero workspace clutter.

---

## 🖥️ Viewing Both Sites

LearnLoop includes two distinct, rich web applications for different workflows:

| Site | URL | Tech Stack | How to Run | Purpose |
| :--- | :--- | :--- | :--- | :--- |
| **Local Dashboard** *(Mission Control)* | `http://127.0.0.1:8765` | FastAPI + Next.js static / HTML5 | `learnloop dashboard`<br>*(or `python -m learnloop.dashboard`)* | Private, local-first analytics: SuperMemo-2 retention curves, project readiness (0-100), commit queue, live stale invariant alerts, and interactive setup wizard (`/setup`). |
| **Marketing & Docs Web Portal** | `http://localhost:3000` | Next.js 16 + React 19 + TailwindCSS | `cd website && npm run dev` | Public product website: interactive dual-mode execution showcase (AI-autonomous vs developer-initiated), 4-cluster tool matrix, terminal simulations, and comprehensive documentation. |

> [!TIP]
> **Native Desktop Window**: You can also launch the dashboard inside a native Microsoft Edge WebView2 desktop app window by running:
> ```bash
> learnloop gui
> # or
> learnloop dashboard --gui
> ```

---

## 🧪 End-to-End Testing & Verification Walkthrough

To verify LearnLoop end-to-end from environment health to live AI pairing and UI inspection, follow these steps:

### 1. Verify Health & Dependencies
```bash
# 1. Run diagnostic self-check (validates SQLite, migrations, seed taxonomy)
learnloop doctor

# 2. Scan active project technologies (detects Python, NPM, Go, Rust ecosystems)
learnloop techscan
```

### 2. Launch & Inspect Both Sites
Open two terminal windows to run both web applications simultaneously:
```bash
# Terminal 1: Launch Local Mission Control Dashboard (Port 8765)
learnloop dashboard

# Terminal 2: Launch Marketing & Documentation Web Portal (Port 3000)
cd website
npm run dev
```
- Open `http://127.0.0.1:8765` to inspect your personal learning progress, review queue, and setup wizard (`/setup`).
- Open `http://localhost:3000` to explore the marketing web portal and dual-mode execution breakdown.

### 3. Test the Active AI Pairing Loop (Zero Workspace Pollution)
In your AI-assisted IDE (VS Code, Cursor, Windsurf, Claude Code, or Antigravity):
1. **Declare Intent**: Before writing code, the AI silently calls:
   `track_intent(action="start_session", summary="Implement feature X", files=["src/example.py"])`
2. **Commit Code**: Make a standard Git commit:
   ```bash
   git commit -m "feat(core): implement feature X"
   ```
   *The post-commit hook records commit metadata into `~/.learnloop/workspaces/<hash>/queue/` without polluting your project.*
3. **Reconcile**: The AI reconciles Git proof with intent:
   `track_intent(action="reconcile")`
4. **Verify Zero Pollution**: Run `git status` in your project root. **Zero `.learn/` files or untracked folders will appear.**

### 4. Run the Full Automated Test Suite
```bash
# Run 336 unit tests with pytest
pytest tests/unit -v

# Run queue ingestion and reconciliation integration tests
pytest tests/test_queue_ingestion.py -v
```

---

## 🔧 CLI Commands

### Core Commands:
- `learnloop init [--repo .] [--ide auto|vscode|cursor|claude|windsurf|zed|agents|all] [--all] [--no-integrate] [--in-repo]`:
  Initialize `.learn/` and post-commit hook. By default (`--ide auto`), detects your active host editor and configures **only** that IDE with zero repository pollution.
- `learnloop setup [--port 8765] [--browser] [--no-browser]`: Interactive 3-step setup wizard (web or desktop window).
- `learnloop gui [--port 8765] [--route /setup|/]`: Launch native Microsoft Edge WebView2 desktop application window.
- `learnloop dashboard [--port 8765] [--gui]`: Web dashboard on `127.0.0.1:8765` (optional `--gui` window).
- `learnloop integrate [--repo .] [--ide auto|vscode|cursor|claude|windsurf|zed|agents|all] [--force] [--terminal] [--env] [--all]`:
  Targeted or universal IDE integration utility.
- `learnloop record-commit [--repo .]`: Record recent commit metadata (called by git hook).
- `learnloop backfill [--repo .] [--limit 50]`: Ingest existing commit history.
- `learnloop concepts [--repo .]`: Regenerate `.learn/concepts.md`.
- `learnloop review [--repo .]`: Interactive spaced repetition review.
- `learnloop briefing [--repo .]`: Session-start briefing.
- `learnloop doctor`: Verify database, taxonomy, hooks, and migrations.
- `learnloop techscan [--repo .]`: Scan repository dependencies.

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

## 🛠️ MCP Tools (Domain Clustered)

LearnLoop uses **4 high-level domain tools** designed for minimal token overhead (-45% schema tokens compared to individual tools). `project_id` is automatically resolved from your workspace.

### 1. `track_intent` (Active Coding & Git Verification)
- `start_session`: Start a work session with target files, summary, and intent tracking.
- `log_decision`: Log architectural decisions with alternatives considered and trade-offs.
- `reconcile`: Verify what the AI actually built against git commits in `.learn/queue`.
- `init_project`: Optional initial project handshake (auto-detected by default).

### 2. `manage_reviews` (Spaced Repetition & Catch-Up)
- `briefing`: Calm, session-start briefing showing recent activity and items due.
- `due`: Query concepts and decisions currently due for spaced repetition review.
- `record`: Record quiz/review outcomes (rating 0.0 to 1.0) to update repetition intervals.
- `snooze`: Temporarily postpone an item's review schedule.

### 3. `manage_knowledge` (Knowledge Catalog & Explanations)
- `register`: Catalog new components, architectural decisions, concepts, or bug-fixes.
- `list`: Browse registered knowledge items (compact by default, optional `detailed=True` or `stale_only=True`).
- `explain`: Record developer explain-backs with self-ratings to demonstrate mastery.
- `prompt`: Generate structured prompt questions for explaining a specific component.
- `readiness`: Check project readiness score (1 to 5) across exposure and mastery.

### 4. `explore_project` (Codebase Exploration & Insights)
- `tour`: Structural architectural walkthrough highlighting entry points and data flows.
- `detect_tech`: Scan and refresh repository technology stack detection.
- `add_fact`: Add a verified, high-signal technical insight or "did you know".

## 🎯 How It Works

### With AI Assistants (Automatic Zero-Config):
1. **Session Start**: AI calls `manage_reviews(action="briefing")` for context.
2. **Architecture**: AI calls `explore_project(action="tour")` when asked for walkthroughs.
3. **Before Coding**: AI calls `track_intent(action="start_session", files=[...], summary="...")`.
4. **Architectural Choices**: AI calls `track_intent(action="log_decision", ...)` to document trade-offs.
5. **After Commits**: Non-blocking git hook logs commit $\rightarrow$ AI calls `track_intent(action="reconcile")`.
6. **Knowledge Catalog**: AI calls `manage_knowledge(action="register", ...)` for new components.
7. **Spaced Reviews**: AI tests the learner via `manage_reviews(action="due")` and records responses.
8. **Technical Discoveries**: AI adds verified findings via `explore_project(action="add_fact", ...)`.

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


## 📋 Recent Updates

### 2026-10-31 (v0.7.0)
- **Universal Autonomous Agent Setup (`prompt.md`)**: Published self-executing instruction manual ([`prompt.md`](prompt.md) and [`website/public/prompt.md`](website/public/prompt.md)) enabling any frontier coding agent (Claude Code, Cursor, Windsurf, Claude Desktop, Antigravity, VS Code / Copilot, Zed) to autonomously configure LearnLoop globally via `uvx` directly from GitHub with zero repo cloning, zero PyPI overhead, and automatic companion rule injection.
- **Self-Testing & Interactive Verification Protocol**: Integrated an automated post-install loop into `prompt.md` where the agent tests MCP tool availability (`manage_reviews(action="briefing")`), prompts the developer if an IDE reload is required, and confirms workspace git commit tracking.
- **Hero "Build With Your Favorite AI Agent" Card**: Featured an interactive 1-click prompt setup card in the marketing website Hero (`AgentSetupCard.tsx`) with brand badges for Claude, Cursor, Windsurf, Antigravity, and Copilot matching modern cloud developer standards.

### 2026-10-29 (v0.6.4)
- **Terminal-First ASCII Architecture Specification**: Streamlined the "One protocol. Every editor on your machine." section (`CodeFlow.tsx`) to showcase a dedicated, high-contrast ASCII architecture specification with instant 1-click clipboard copying, eliminating image overhead and toggle tabs.

### 2026-10-29 (v0.6.3)
- **Empirical Token Efficiency Benchmark**: Measured and verified exact token usage across 4 frontier model tokenizers (Claude 3.5 Sonnet, GPT-4o / o1, Gemini 1.5/2.0 Pro, and DeepSeek-V3 / Llama 3) across each of LearnLoop's 4 domain-clustered tools.
- **Interactive Marketing Web Benchmark Showcase**: Integrated interactive `TokenBenchmark` component into homepage Bento Grid and Developer Documentation (`/docs`), featuring live model tabs, schema overhead meters, typical payload footprints, and empirical proof of up to 24% baseline prompt savings.

### 2026-10-29 (v0.6.2)
- **Dynamic Installation Origin**: Decoupled setup scripts from hardcoded domain references across the marketing website (`DownloadSection.tsx`) and developer documentation (`QuickstartCommands.tsx`) using the new client-side `useOrigin` hook. Commands now adapt in real-time to match whatever host or port serves the page (`window.location.origin` or `NEXT_PUBLIC_SITE_URL`).
- **Local Clone Installation First**: Reoriented root `README.md` quickstart instructions to prioritize local scripts (`.\setup.ps1` and `./setup.sh`) and local pip development, eliminating external domain dependencies for repository contributors.
- **Hero Horizon Contrast & Accessibility**: Replaced parent section mask with an isolated background overlay, preserving the signature luminous bottom curved horizon while elevating the CTA dock and buttons to 100% opacity with solid dark contrast.

### 2026-10-28 (v0.6.1)
- **Visual Architecture Flow Diagram**: Replaced the ASCII-only canvas in the "One protocol. Every editor on your machine." section with a high-definition visual architecture diagram featuring glowing protocol buses, central engine topology, and dual view-toggle (Visual Flow vs. ASCII Spec) for maximum developer clarity.
- **Hero Curve Shadow & Dark Glass Dock**: Restored the signature dramatic bottom curved mask shadow transitioning seamlessly into the light page below, while framing the CTA buttons inside an elevated frosted dark glass dock (`bg-black/75 backdrop-blur-xl border border-white/20`) for razor-sharp focus and zero wash-out.
- **Alternating Dark & Light Section Rhythm**: Implemented the rhythmic alternating section background pattern across the homepage: Hero (Dark with bottom curve) → PrivacyCore (White) → BentoGrid (Dark) → ExecutionModes (White) → CodeFlow (Dark) → DownloadSection (White) → Footer (Dark).
- **Dedicated OS Platform Switcher**: Streamlined the download switcher to focus exclusively on target OS binaries (Windows, macOS, Linux) with 1-click commands (PowerShell, CMD, Bash) and direct standalone executable downloads.
- **Automated MCP Setup Documentation**: Aligned the documentation portal (/docs) and landing page to explicitly highlight that running the installer or `learnloop init` automatically detects the active IDE and configures MCP server settings and AI companion instructions—zero manual JSON editing required.

### 2026-10-28 (v0.6.0)
- **100% Zero-Workspace-Pollution "Ghost Mode"**: Workspace artifacts (commit queue, concept journals, terminal scripts) are now routed by default to isolated OS user-data storage (`~/.learnloop/workspaces/<project_slug_hash>/`), completely eliminating workspace directory pollution, `.gitignore` churn, and Git PR noise for team projects.
- **Git Hook Local Isolation Safeguard**: Automatic post-commit hook setup now appends local exclusions to `.git/info/exclude`, providing git-level protection against accidental tracking without modifying tracked repository files.
- **Seamless Legacy Backwards-Compatibility**: Retains full backwards compatibility with existing repositories that contain legacy `.learn/` folders, preserving existing files and tests without breaking changes.

### 2026-10-28 (v0.5.3)
- **Marketing Website Dual-Mode Execution Showcase**: Added interactive dual-mode execution breakdown (ExecutionModes.tsx) to the homepage and documentation, visually distinguishing AI-autonomous background pairing hygiene (~80% of calls) from developer-initiated interactive sparring (/review, /interview, /tour).
- **Cluster Summary Matrix**: Added responsive execution comparison matrix detailing trigger drivers, automation rules, and sample actions across all 4 tool clusters.
- **IDE Socratic Sparring Alignment**: Refined dashboard prompt chips across Review Queue, Overview, and Knowledge Catalog to emphasize native LearnLoop MCP prompts (/review, /interview, /tour, /catch-up) and natural conversational triggers.
- **Real-Time Code Drift Calculation**: Integrated dynamic commit drift detection in HTTP API and dashboard concept catalog with live stale invariant badges.
- **Standalone Binary Packaging**: Streamlined static asset packaging with PyInstaller bundling of Next.js web application into standalone executable.
