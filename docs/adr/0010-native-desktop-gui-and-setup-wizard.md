# ADR 0010: Native Desktop GUI and Browser-Based Setup Wizard

## Status
Accepted

## Context
LearnLoop is designed to operate both as a high-performance Model Context Protocol (MCP) server for AI coding assistants (Cursor, VS Code, Claude Code, Windsurf) and as an interactive learning companion for developers.

However, onboarding posed high friction for Windows and desktop developers:
1. Double-clicking `learnloop.exe` in Windows Explorer opened a blank console window and hung waiting for stdio JSON-RPC inputs, offering no visual affordance or feedback.
2. Configuring IDEs required running multiple CLI commands (`learnloop init`, `learnloop integrate`, `learnloop doctor`).
3. Running a web dashboard kept a terminal window alive and mixed LearnLoop tabs into the developer's crowded daily browser session.

We needed a seamless, zero-friction desktop experience that preserves silent MCP stdio execution when spawned by an AI agent while offering a first-class native desktop application when launched by a human.

## Decision

### 1. Smart TTY Launch Detection
In `learnloop.cli.main()`, when executed without arguments:
- If `sys.stdin.isatty()` is `False`: The process was spawned via piped stdio by an IDE (Cursor, VS Code, Windsurf). It silently runs the FastMCP stdio server (`cmd_serve()`).
- If `sys.stdin.isatty()` is `True`: The process was launched interactively by a user (double-click in Windows Explorer or invocation in a terminal). It boots the setup server and launches the desktop GUI (`cmd_setup(use_gui=True)`).

### 2. Native Desktop Window via Microsoft Edge WebView2 (`learnloop.gui`)
For desktop GUI mode:
- **Built-in Windows Runtime**: Uses Microsoft Edge Chromium WebView2, preinstalled on Windows 10/11, via `pywebview`.
- **Console Window Detachment**: On Windows, the application calls `ctypes.windll.user32.ShowWindow(hwnd, 0)` to seamlessly hide the black command prompt window upon interactive GUI launch.
- **Persistent Cache Isolation**: Stores WebView2 user profile data in `%LOCALAPPDATA%\learnloop\webview2_cache` (rather than temp directories) to eliminate file-lock deletion warnings and enable persistent UI state.
- **Graceful Browser Fallback**: If WebView2 or GUI dependencies fail to load, LearnLoop automatically falls back to opening the system's default web browser (`webbrowser.open()`).
- **Synchronized Lifecycle**: When the user closes the native desktop window, the embedded background HTTP server is cleanly shut down and the process exits.

### 3. Interactive 3-Step Setup Wizard
Implemented inside `learnloop.dashboard.server`:
- `GET /setup`: Dark-mode onboarding interface with:
  - Auto-detected IDE toggle switches (Cursor, VS Code, Windsurf, Claude Desktop, Zed, AGENTS.md/GEMINI.md).
  - Storage location choice: Global Developer Library (`%LOCALAPPDATA%\learnloop`) vs. In-Project (`.learn/`).
  - Automated Git post-commit tracking hook toggle.
- `POST /api/setup`: Executes `LearnLoopIntegrator`, configures selected IDE rules, initializes database migrations, and redirects to the live dashboard.
- `POST /api/shutdown`: Graceful HTTP termination endpoint invoked by the in-UI "Stop" button in the dashboard header.

### 4. CLI Controls
- `learnloop gui [--port 8765] [--route /setup|/]`: Explicitly launch the native desktop window.
- `learnloop setup [--port 8765] [--browser] [--no-browser]`: Run the setup wizard with optional browser fallback.
- `learnloop dashboard [--port 8765] [--gui]`: Open the dashboard with optional native window.

## Consequences

- **Zero-Friction Desktop Onboarding**: Developers can double-click a single executable to configure their entire AI coding environment in seconds.
- **Dual-Mode Single Binary**: One standalone executable (`dist/learnloop.exe`, ~26.8 MB) serves as both the headless MCP stdio engine for AI agents and the native GUI application for humans.
- **Cross-Platform Resilience**: Linux and headless CI environments gracefully fall back to stdio or headless browser-less HTTP execution without crashing.
