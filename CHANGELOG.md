# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.10.1] - 2026-11-05

### Fixed
- **Dashboard Socket Conflict Recovery (`src/learnloop/cli.py`, `src/learnloop/gui.py`)**:
  - `learnloop dashboard` now detects if the background daemon is already listening on `http://127.0.0.1:8765/`, opening the browser or desktop window directly without throwing `[Errno 10048]` / `EADDRINUSE`.
  - Added graceful fallback in `cmd_dashboard` for socket address reuse errors, cleanly detecting running LearnLoop instances or reporting actionable port alternatives (`--port <number>`).
- **Interactive Uninstallation & Purge Flow (`src/learnloop/cli.py`, `src/learnloop/daemon.py`)**:
  - Added an interactive prompt to `learnloop uninstall`: `Also purge all local databases & learning history? [y/N]:` so users can choose full data removal in one step without needing to re-run with flags.
  - Added top-level `--purge` CLI argument (`learnloop --purge`), routing cleanly to `cmd_uninstall(purge=True)`.
  - Added automatic daemon termination (`stop_daemon()`) before file cleanup to ensure SQLite file locks are released on Windows.
  - Expanded purge scope to thoroughly clean `~/.learnloop` (logs, configs, rules), OS user data directory (`user_data_dir("learnloop")` containing `learnloop.db` and workspaces), and legacy in-repo `.learn` directories.

---

## [0.10.0] - 2026-11-05

### Removed
- **Pruned Redundant `learnloop integrate` Subcommand**: Removed `integrate` CLI subcommand in favor of `learnloop init`, which handles auto-detection and IDE configuration cleanly without manual duplication.
- **Removed Legacy Shell Wrapper Scripts (`src/learnloop/integrator.py`)**: Deleted dead generators for `tools.sh`, `tools.bat`, `environment.sh`, `LearnLoop.ps1`, and alias shortcuts (`llb`, `llr`, `lld`), eliminating confusing filesystem clutter and enforcing clean, direct usage of the global `learnloop` CLI binary.

---

## [0.9.0] - 2026-11-05

### Added
- **Topology & Environment Auto-Detection (`src/learnloop/daemon.py`)**:
  - Automatically identifies whether the runtime environment is **Native**, **WSL2**, **DevContainer / Docker**, or **Remote SSH**.
  - Binds the MCP daemon to `0.0.0.0:8765` so host editors (e.g. Windows VS Code connected to WSL) access the server seamlessly, generating remote port forwarding tips (`ssh -L 8765:localhost:8765`) when cross-network access is detected.
- **Automatic Daemon Lifecycle Management (`src/learnloop/daemon.py`)**:
  - Automatically launches the background streamable HTTP/SSE server on port `8765` if offline during `learnloop init` or `learnloop doctor`, tracks its PID (`~/.learnloop/daemon.pid`), and verifies readiness within a 3.5s timeout.
- **5-Stage Comprehensive Diagnostic Engine in `learnloop doctor`**:
  - **[1/5] Host Environment & Topology**: Platform, runtime type, and remote port forwarding directives.
  - **[2/5] Local Data Integrity**: Database health, skill taxonomy catalog, registered concepts, and Git hook validation.
  - **[3/5] MCP Daemon & Network Reachability**: Active daemon process status, PID, and universal streamable HTTP/SSE binding.
  - **[4/5] Protocol Handshake & Tool Registry**: Live latency measurement, JSON-RPC `/mcp/v1/tools` verification, and active domain dispatchers.
  - **[5/5] AI Trust & Verification Evidence Card**: Explicitly displays the 3 pillars of trust (100% Local SQLite, Proof-of-Outcome via Git commit SHAs, Ghost Mode zero repo pollution).
- **Live Verification Stage in `learnloop init`**:
  - Concludes project initialization with a live reachability probe against the hosted daemon, displaying live latency and active capabilities.

### Changed
- **Universal Streamable HTTP / SSE IDE Integration**: Updated `get_mcp_config` in `src/learnloop/integrator.py` to default to streamable HTTP (`/mcp`) and SSE (`/sse`) across VS Code, Cursor, Windsurf, and Claude Desktop, eliminating brittle stdio shell translation across OS boundaries.

---

## [0.8.3] - 2026-11-05

### Added
- **Unified Modern Developer Card for `learnloop init`**: Redesigned the initialization terminal output into a structured, Astral (`uv`) / Bun aesthetic 3-step card:
  - `[1/3] Arming Git Post-Commit Tracking Hook...` (displays verified `.git/hooks/post-commit` path)
  - `[2/3] Initializing Local Knowledge & State Storage...` (details exact storage directory, SQLite database file, and journal markdown)
  - `[3/3] Configuring IDE Model Context Protocol (MCP)...` (shows exact IDE configuration and rule paths touched)
  - **`READY FOR AI CODING` Actionable Summary**: Features high-visibility starter prompts to ask the AI in editor chat (`"Give me a tour of this project"`, `"Teach me how this works"`) and key CLI commands (`learnloop briefing`, `learnloop dashboard`).

### Changed
- **`LearnLoopIntegrator` Quiet Mode**: Added `quiet: bool` execution mode to `LearnLoopIntegrator.run()` to suppress redundant emoji headers and output clutter when called programmatically by `learnloop init`, returning structured metadata (`detected_ides`, `integrated_paths`).

---

## [0.8.2] - 2026-11-05

### Fixed
- **Dashboard Web Dependencies in Core Package**: Promoted `fastapi`, `uvicorn`, `sse-starlette`, and `python-multipart` from optional `[http]` extras into core `dependencies` in `pyproject.toml`. Resolves `No module named 'fastapi'` error when running `learnloop dashboard` on fresh package installations (`uv tool` or `pip`).
- **Graceful Import Error Handling**: Enhanced `cmd_dashboard` with dedicated `ImportError` interception, offering single-command remediation instructions (`learnloop update`).

---

## [0.8.1] - 2026-11-05

### Fixed
- **Human-Actionable Briefing Guidance**: Mapped raw internal machine slugs in `learnloop briefing` (e.g. `tour`, `review`, `explain-stale`, `nothing`) to clear human instructions (e.g., `Ask AI in your IDE: 'Give me a tour of this project' (or run: learnloop concepts)`), preventing users from mistakenly running non-existent CLI subcommands.
- **Interactive Stderr Notice for `learnloop serve`**: When `learnloop serve` is invoked directly by a human in an interactive TTY terminal rather than through an IDE pipe, it prints an informative notice to `sys.stderr` explaining that it is listening for JSON-RPC messages and pointing to `learnloop dashboard` for the web UI, keeping `stdout` 100% clean for MCP clients.

---

## [0.8.0] - 2026-11-05

### Added
- **Automated Update Notification & Self-Updater (`src/learnloop/updater.py`)**:
  - **Non-blocking Background Update Check**: Checks for newer releases with a 24-hour local cache TTL (`~/.learnloop/cache/update_check.json`), guaranteeing zero latency on local CLI commands and 100% privacy (zero telemetry).
  - **Native `learnloop update` CLI Command**: Self-updates the local installation in under 2 seconds. Automatically replaces standalone binaries (`~/.learnloop/bin/`) via safe Windows rename technique or triggers `uv`/`pip` updates.
  - **Standard `--version` / `-V` CLI Flag**: Displays the active version (`learnloop v0.8.0`).
  - **Terminal Update Notification Banner**: Displays a modern, non-intrusive micro-banner when a newer version is released during interactive commands (`doctor`, `briefing`, `setup`, `dashboard`).
  - **Cloudflare Version Endpoint (`/version.json`)**: Real-time static CDN metadata endpoint serving latest version and changelog information for zero-latency lookups.
  - **Web Dashboard API Endpoint (`GET /api/version`)**: Returns current and latest version status for UI update badges.

---

## [0.7.7] - 2026-11-05

### Added
- **Categorized Workflow CLI Help (`learnloop --help`)**: Completely overhauled CLI documentation with Modern Developer Aesthetic styling (Astral uv / Bun inspiration) and ANSI color formatting. Organizes all 15 commands into three structured tiers:
  - `DAILY LEARNING & WORKFLOW`: `briefing`, `review`, `concepts`, `dashboard`, `gui`
  - `PROJECT SETUP & INTEGRATION`: `init`, `integrate`, `techscan`, `backfill`
  - `DIAGNOSTICS & ENGINE`: `doctor`, `serve`, `http`, `setup`, `uninstall`
  Eliminates undocumented subcommands by providing complete one-line descriptions for `record-commit`, `concepts`, `review`, `briefing`, `techscan`, `backfill`, `doctor`, and `dashboard`. Respects `NO_COLOR` standard and non-TTY pipes.
- **Modern Developer Aesthetic & Live Editor Detection in Installers**: Upgraded `setup.ps1` and `setup.sh` with platform badges, live auto-detection of installed AI editors (`⚡ Detected Editors: Cursor, VS Code (ready for zero-config MCP)`), and smooth 3-step progress indicators.

---

## [0.7.6] - 2026-11-05

### Added
- **Native `learnloop uninstall` CLI Subcommand**: Added clean, safe uninstallation capability to the CLI. Unregisters MCP configurations across VS Code, Cursor, Windsurf, Claude Desktop, and Zed (preserving all other user-configured MCP servers), removes Git post-commit tracking hooks, and safely deletes `~/.learnloop/bin/` binary. Includes optional `--purge` flag for complete removal of local learning databases and `--yes` for automated scripting.
- **Structured 3-Step Quickstart Onboarding Guidance**: Enhanced post-installation completion banners in `setup.ps1` and `setup.sh` to explicitly guide fresh developers through health self-check (`learnloop doctor`), Ghost Mode project connection (`learnloop init`), and local mission control dashboard (`learnloop dashboard`).

---

## [0.7.5] - 2026-11-04

### Added
- **Multi-Platform Automated Release Pipeline (`.github/workflows/release.yml`)**: Automated GitHub Actions CI workflow triggered on tag pushes (`v*`) and manual dispatch. Compiles standalone single-file zero-dependency executables for Windows (`learnloop-windows-x64.exe`), Linux (`learnloop-linux-x64`), and macOS (`learnloop-darwin-arm64` and `learnloop-darwin-x64`) using PyInstaller, verifies binary execution with self-test diagnostics, computes SHA256 checksums, and publishes official GitHub Releases.
- **Website Prebuild Installer Sync**: Added `website/scripts/sync-installers.mjs` and hooked into `npm run build` prebuild to ensure one-shot installer scripts (`setup.sh`, `setup.ps1`) are synchronized automatically into website distribution assets on every Cloudflare build.
- **Streamlined Terminal-First Installation UX**: Replaced ambiguous dual download buttons with a unified, high-contrast hero command block featuring a one-click copy button (`⚡ COPY INSTALL COMMAND`), eliminating script execution friction and binary PATH discovery issues across Windows, macOS, and Linux.

---

## [0.7.4] - 2026-11-04

### Fixed
- **Website Download 404 Prevention**: Replaced single fragile GitHub release link with dual options: direct download of verified one-shot installer scripts (`/setup.sh` on Linux/macOS, `/setup.ps1` on Windows) served directly from website public directory (guaranteed HTTP 200), alongside direct binary release asset links.
- **macOS Release Asset Routing**: Corrected macOS download URL to target `learnloop-darwin-arm64` matching CI workflow release outputs rather than non-existent universal binary.
- **Shell Profile Fallback**: Enhanced `setup.sh` to guarantee `export PATH="$PATH:$BIN_DIR"` is written to `~/.profile` when minimal Linux environments lack `.bashrc` or `.zshrc`.

---

## [0.7.3] - 2026-11-04

### Changed
- **Ghost Mode IDE Integration**: `learnloop init` and `learnloop integrate` now write configurations to global user-level profiles by default (VS Code user settings, Cline/Roo MCP, Cursor `~/.cursor/mcp.json`, Windsurf global MCP, Claude Desktop, and Zed global settings), leaving repositories 100% clean with zero untracked `.vscode/` or editor files.
- **In-Repo Opt-In (`--in-repo`)**: Added explicit `--in-repo` flag to `learnloop init` and `learnloop integrate` for development teams wanting committed in-repository configuration.

---

## [0.7.2] - 2026-11-04

### Added
- **Explicit MCP `serve` Subcommand**: Added `learnloop serve` with options `--transport [stdio|sse|http]`, `--repo`, `--host`, and `--port`. Decouples MCP stdio serving from terminal `isatty()` heuristics.

### Fixed
- **IDE Subprocess Command Arguments**: Updated `integrator.py` MCP configuration generator to emit `"args": ["serve"]` ensuring reliable stdio handshakes in VS Code, Cursor, Windsurf, Claude, and Zed.
- **Filesystem Permission Guarding**: Hardened `_resolve_command()` against `PermissionError` when probing user bin locations in restricted/sandboxed environments.

---

## [0.7.1] - 2026-11-03

### Fixed
- **Remote Setup Syntax**: Resolved premature Python heredoc termination in `/setup.sh` endpoint within `http_server.py`, eliminating `dp: command not found` fatal crashes on macOS/Linux.
- **Linux Architecture Handling**: Added dynamic `$ARCH` inspection in `setup.sh` to route ARM64 Linux systems (AWS Graviton, Raspberry Pi, Apple Silicon Docker) seamlessly to native `uv` rather than downloading incompatible `x86_64` binaries.
- **Installer PATH Injection**: Removed premature `exit 0` calls in `setup.sh` fallback blocks so user shell profiles (`~/.bashrc`, `~/.zshrc`, `~/.profile`) are reliably updated with `~/.learnloop/bin`.
- **Windows Parity**: Added automatic `uv` and Python fallback to `setup.ps1` when GitHub Release binary downloads are unreachable, and guarded `$PSScriptRoot` against null references during remote `irm | iex` execution.
- **IDE Subprocess Resolution**: Updated `integrator.py` to resolve absolute binary paths (`~/.learnloop/bin/learnloop`) so GUI IDEs on macOS/Linux (Cursor, Claude Desktop, VS Code) do not fail with `spawn learnloop ENOENT`.
- **Build Verification**: Hardened `scripts/build_binary.py` to return the test runner's exit code so broken binaries fail CI before publication.
- **GLIBC Backward Compatibility**: Pinned GitHub Actions Linux release builder to `ubuntu-22.04` (glibc 2.35).

### Added
- **Production Container Infrastructure**: Added official root `Dockerfile` (Python 3.12-slim, non-root `learnloop` user, `/data` volume) and pinned root `requirements.txt`.
- **Clean Installer UX**: Streamlined `setup.sh` and `setup.ps1` terminal output with 3 numbered stages, silenced 33-line dependency dumps, and added prominent terminal activation prompts.

---

## [0.7.0] - 2026-10-31

### Added
- **Autonomous Agent Setup (`prompt.md`)**: Published self-executing instruction manual enabling any frontier coding agent (Claude Code, Cursor, Windsurf, Claude Desktop, Antigravity, VS Code, Zed) to autonomously configure LearnLoop globally via `uvx` directly from GitHub with zero repo cloning and zero PyPI overhead.
- **Self-Testing Verification Protocol**: Integrated an automated post-install loop into `prompt.md` where agents test MCP tool availability (`manage_reviews(action="briefing")`), prompt for IDE reloads when needed, and confirm Git commit tracking.
- **Hero "Build With Your Favorite AI Agent" Showcase**: Added interactive 1-click prompt setup card in marketing website Hero with brand badges for Claude, Cursor, Windsurf, Antigravity, and Copilot.

---

## [0.6.4] - 2026-10-29

### Changed
- **Terminal-First ASCII Architecture**: Streamlined the "One protocol. Every editor on your machine." section (`CodeFlow.tsx`) to showcase a dedicated, high-contrast ASCII architecture specification with instant 1-click clipboard copying.
- **Website Navigation Polish**: Added active route awareness in top navigation bar with glowing indicators.

---

## [0.6.3] - 2026-10-29

### Added
- **Empirical Token Efficiency Benchmark**: Measured exact token usage across 4 frontier model tokenizers (Claude 3.5 Sonnet, GPT-4o / o1, Gemini 1.5/2.0 Pro, DeepSeek-V3 / Llama 3) across each of LearnLoop's 4 domain-clustered tools.
- **Interactive Benchmark Showcase**: Added interactive `TokenBenchmark` component to homepage Bento Grid and Developer Documentation (`/docs`), demonstrating up to 24% baseline prompt savings and ~45% reduction in multi-turn context churn.

---

## [0.6.2] - 2026-10-29

### Changed
- **Dynamic Installation Origin**: Decoupled setup scripts from hardcoded domain references across the website using client-side `useOrigin` hook. Commands adapt in real-time to match whichever host or port serves the page.
- **Local Clone Installation First**: Reoriented root `README.md` quickstart instructions to prioritize local scripts (`.\setup.ps1` and `./setup.sh`).

---

## [0.6.1] - 2026-10-28

### Added
- **Visual Architecture Flow**: Added visual architecture diagram with glowing protocol buses, central engine topology, and dual view-toggle (Visual Flow vs. ASCII Spec).
- **Hero Curve Shadow & Dark Glass Dock**: Added bottom curved mask shadow transitioning into light page below, framing CTA buttons inside a frosted dark glass dock.
- **Alternating Page Rhythm**: Structured homepage sections with alternating dark and light backgrounds.

---

## [0.6.0] - 2026-10-28

### Added
- **100% Zero-Workspace-Pollution "Ghost Mode"**: Workspace artifacts (commit queues, concept journals, terminal scripts) route by default to isolated OS user-data storage (`~/.learnloop/workspaces/<hash>/`), completely eliminating workspace directory pollution, `.gitignore` churn, and Git PR noise for team projects.
- **Git Hook Local Isolation Safeguard**: Automatic post-commit hook setup appends local exclusions to `.git/info/exclude` for git-level protection against accidental tracking.
- **Seamless Backwards-Compatibility**: Retains full compatibility with existing repositories that contain legacy `.learn/` folders.

---

## [0.5.3] - 2026-10-28

### Added
- **Dual-Mode Execution Showcase**: Added interactive breakdown visually distinguishing AI-autonomous background pairing hygiene (~80% of calls) from developer-initiated interactive sparring (`/review`, `/interview`, `/tour`).
- **Real-Time Code Drift Calculation**: Integrated dynamic commit drift detection in HTTP API and dashboard concept catalog with live stale invariant badges.
