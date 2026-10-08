"""Runtime settings. Local-first: the DB lives in the OS user-data dir, never in a repo."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_data_dir


@dataclass(frozen=True)
class Settings:
    db_path: Path
    abandon_days: int = 14  # open intents older than this become "abandoned"
    max_queue_files: int = 200  # per ingest call
    max_queue_file_bytes: int = 200_000

    @classmethod
    def load(cls) -> Settings:
        override = os.environ.get("LEARNLOOP_DB")
        path = Path(override) if override else Path(user_data_dir("learnloop")) / "learnloop.db"
        return cls(db_path=path)
