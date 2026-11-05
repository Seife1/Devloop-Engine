# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
