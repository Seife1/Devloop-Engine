#!/usr/bin/env python3
"""HTTP/SSE server for LearnLoop MCP plugin with proper MCP protocol support.

This module delegates directly to `learnloop.http_server` inside the LearnLoop package.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure src/ is on sys.path if running directly from the repository
src_dir = Path(__file__).resolve().parent / "src"
if src_dir.is_dir() and str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from learnloop.http_server import *  # noqa: F403
from learnloop.http_server import app, main

if __name__ == "__main__":
    main()
