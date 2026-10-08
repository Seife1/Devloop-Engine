"""Logging goes to STDERR only. With stdio transport, stdout IS the protocol channel."""

from __future__ import annotations

import logging
import os
import sys


def setup_logging() -> None:
    level = os.environ.get("LEARNLOOP_LOG", "INFO").upper()
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger("learnloop")
    root.handlers[:] = [handler]
    root.setLevel(level)
