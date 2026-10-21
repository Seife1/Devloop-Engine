"""Native desktop GUI window using Edge WebView2 (pywebview) for Windows/macOS/Linux.

Provides a dedicated, native application window for LearnLoop setup and dashboard,
free from external browser tabs and console clutter.
"""

from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path
from typing import Any

from learnloop.dashboard.server import create_dashboard_server


def is_gui_available() -> bool:
    """Return True if pywebview is installed and available in the environment."""
    try:
        import webview

        return hasattr(webview, "create_window") and hasattr(webview, "start")
    except Exception:
        return False


def hide_console_window() -> bool:
    """On Windows, hide the black console window if running as an interactive GUI application."""
    if sys.platform == "win32":
        try:
            import ctypes

            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                # SW_HIDE = 0
                ctypes.windll.user32.ShowWindow(hwnd, 0)
                return True
        except Exception:
            pass
    return False


def show_console_window() -> bool:
    """On Windows, restore the console window if it was hidden."""
    if sys.platform == "win32":
        try:
            import ctypes

            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                # SW_SHOW = 5
                ctypes.windll.user32.ShowWindow(hwnd, 5)
                return True
        except Exception:
            pass
    return False


def get_webview2_cache_dir() -> Path:
    """Return a persistent cache directory for WebView2 user data to avoid temp locks and speed up reload."""
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        base = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
    else:
        base = Path.home() / ".cache"
    cache_dir = base / "learnloop" / "webview2_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def launch_desktop_gui(
    port: int = 8765,
    route: str = "/setup",
    hide_console: bool = True,
    title: str = "LearnLoop - Developer Learning Companion",
    width: int = 1120,
    height: int = 800,
    min_width: int = 840,
    min_height: int = 600,
    db_path: Path | None = None,
) -> int:
    """Launch the native desktop window with embedded WebView2 pointing to the local dashboard.

    If pywebview is unavailable or fails to initialize, gracefully falls back to the default browser.
    """
    # 1. Attempt to hide the console window early on Windows
    if hide_console:
        hide_console_window()

    # 2. Start the local server
    try:
        server, actual_port = create_dashboard_server(port=port, db_path=db_path)
    except Exception as exc:
        show_console_window()
        sys.stderr.write(f"LearnLoop GUI server failed to start: {exc}\n")
        return 1

    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    url = f"http://127.0.0.1:{actual_port}{route}"

    # 3. Try to launch native WebView2 desktop window
    if is_gui_available():
        try:
            import webview

            # Configure persistent cache for WebView2 on Windows
            if sys.platform == "win32":
                cache_dir = get_webview2_cache_dir()
                os.environ["WEBVIEW2_USER_DATA_FOLDER"] = str(cache_dir)

            window = webview.create_window(
                title=title,
                url=url,
                width=width,
                height=height,
                min_size=(min_width, min_height),
                background_color="#0d1117",
            )

            # Start webview event loop (blocks until window is closed by user)
            gui_engine = "edgechromium" if sys.platform == "win32" else None
            webview.start(gui=gui_engine)

            # Window was closed by user -> shutdown server and exit cleanly
            try:
                server.shutdown()
                server.server_close()
            except Exception:
                pass
            return 0
        except Exception as exc:
            # Native window creation failed; fall back to browser
            sys.stderr.write(f"WebView2 window unavailable ({exc}); falling back to default browser.\n")

    # 4. Fallback: Launch in default web browser
    try:
        import webbrowser

        webbrowser.open(url)
    except Exception:
        pass

    sys.stdout.write(f"LearnLoop dashboard running at {url}\n")
    sys.stdout.flush()

    try:
        # Keep process alive while server handles requests
        while server_thread.is_alive():
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            server.shutdown()
            server.server_close()
        except Exception:
            pass

    return 0
