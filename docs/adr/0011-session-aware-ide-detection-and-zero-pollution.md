# ADR 0011: Session-Aware Active IDE Detection and Non-Polluting Initialization

## Status
Accepted

## Context
When running `learnloop init` in a project, LearnLoop previously invoked `LearnLoopIntegrator().run(["--all"])`. This caused significant issues:
1. **Repository Pollution**: Even when a developer was working exclusively in VS Code, `learnloop init` created or modified rule and configuration files for every known editor on their computer (`.cursorrules`, `CLAUDE.md`, `.windsurfrules`, `.zed/settings.json`, `AGENTS.md`, `GEMINI.md`).
2. **Unwanted Shell Artifacts**: Default initialization dumped script wrappers (`tools.sh`, `tools.bat`) and profile modifications (`environment.sh`, `LearnLoop.ps1`) into `.learn/`.
3. **Filesystem vs Session Confusion**: Naive filesystem-based detection (checking if `~/.cursor` or `~/.codeium` exists on disk) detected every IDE ever installed on the computer rather than the editor the developer was actively typing in. Furthermore, because Cursor and Windsurf are forks of VS Code, simple `TERM_PROGRAM` checks falsely identified them as standard VS Code.

Developers expect a clean, respectful initialization experience where only the active editor is touched, leaving git status clean and free of files for editors they are not using.

## Decision

### 1. Two-Layer Dynamic Session Detection (`LearnLoopIntegrator.detect_active_ide`)
LearnLoop prioritizes the hosting terminal's active process and environment signatures over disk paths:

- **Layer 1: Live Terminal Session Environment**
  - **Cursor**: Evaluated first. Inspects `CURSOR_TRACE_ID`, `CURSOR_VERSION`, or `"cursor"` in `TERM_PROGRAM`, `VSCODE_CWD`, `VSCODE_GIT_IPC_HANDLE`.
  - **Windsurf**: Evaluated second. Inspects `WINDSURF_VERSION` or `"windsurf"` in `TERM_PROGRAM`, `VSCODE_CWD`, `VSCODE_GIT_IPC_HANDLE`.
  - **Antigravity**: Inspects `ANTIGRAVITY_AGENT == 1` or `"antigravity"` in `VSCODE_CWD`.
  - **VS Code**: Evaluated after forks. Inspects `TERM_PROGRAM == "vscode"` or `VSCODE_PID` without fork signatures.
  - **Zed**: Inspects `TERM_PROGRAM == "zed"` or `ZED_TERM`.
  - **Claude Code**: Inspects `CLAUDE_CODE` or `CLAUDE_PROJECT_DIR`.

- **Layer 2: Project Marker Fallback (Standalone Terminals)**
  If run in an external shell (e.g. Windows Terminal, PowerShell, or bash outside any IDE):
  - Checks if project markers exist (`.cursor/`, `.windsurf/`, `.vscode/`, `CLAUDE.md`, `.zed/`).
  - If no markers exist, defaults to universal `AGENTS.md` and `GEMINI.md`.

### 2. Strict Target Isolation
During `learnloop init`:
- LearnLoop now instantiates `LearnLoopIntegrator(project_root=repo)` explicitly.
- It targets **only** the detected active IDE (`--ide auto`), configuring its specific MCP JSON and companion instructions.
- All other editors are untouched.
- Terminal wrapper scripts (`tools.sh`, `tools.bat`) and shell aliases (`environment.sh`, `LearnLoop.ps1`) are omitted from default `init` and only generated when `--all` or `--terminal`/`--env` is explicitly passed.

### 3. Dedicated VS Code MCP Support
In addition to `.vscode/settings.json`, LearnLoop writes native Model Context Protocol configuration to `.vscode/mcp.json` to support both modern VS Code native MCP and extensions (Cline, Roo Code).

### 4. CLI Arguments
Added explicit controls to `learnloop init`:
- `--ide [auto|vscode|cursor|claude|windsurf|zed|agents|all]`: Target specific editor or auto-detect.
- `--all`: Opt-in to configure all IDEs, terminal wrappers, and shell scripts.
- `--no-integrate`: Skip editor integration completely.

## Consequences
- **Zero Repo Pollution**: Initializing LearnLoop in a VS Code project creates only `.vscode/settings.json` and `.vscode/mcp.json`.
- **Accurate Fork Recognition**: Cursor and Windsurf are properly distinguished from their upstream VS Code base.
- **Predictable Cleanliness**: No unwanted shell wrappers or foreign rule files appear in git status.
