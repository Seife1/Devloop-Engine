"""Persistence layer for LearnLoop.

Provides both synchronous (db.py) and asynchronous (async_db.py) database access.
"""

from learnloop.persistence.db import connect, migrate, seed_taxonomy
from learnloop.persistence.db_resilience import (
    DatabaseResilience,
    WriteOperation,
    get_resilient_connection,
)

__all__ = [
    "connect",
    "migrate",
    "seed_taxonomy",
    "DatabaseResilience",
    "WriteOperation",
    "get_resilient_connection",
]

# Optional async database support (requires aiosqlite)
try:
    from learnloop.persistence.async_db import AsyncDatabase
    __all__.append("AsyncDatabase")
except ImportError:
    pass
