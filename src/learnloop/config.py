"""Runtime settings. Local-first: the DB lives in the OS user-data dir, never in a repo."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

from platformdirs import user_data_dir


def get_workspace_storage_dir(repo: Path | str) -> Path:
    """Return the isolated storage path for workspace commits, queues, and journals.

    Ghost Mode (Zero-Pollution Guarantee):
    - If <repo>/.learn already exists, it is preserved for backward compatibility.
    - Otherwise, all artifacts (commit queue, concept journals) are routed to:
      user_data_dir("learnloop") / "workspaces" / <slug_hash>
      leaving the repository workspace 100% clean with zero files or folders created.
    """
    repo_path = Path(repo).resolve()
    legacy_dir = repo_path / ".learn"
    if legacy_dir.is_dir():
        return legacy_dir

    path_str = str(repo_path).lower().replace("\\", "/")
    slug = f"{repo_path.name}-{hashlib.sha256(path_str.encode('utf-8')).hexdigest()[:12]}"
    target = Path(user_data_dir("learnloop")) / "workspaces" / slug
    target.mkdir(parents=True, exist_ok=True)
    return target


@dataclass(frozen=True)
class Settings:
    db_path: Path
    abandon_days: int = 14  # open intents older than this become "abandoned"
    max_queue_files: int = 200  # per ingest call
    max_queue_file_bytes: int = 200_000

    @classmethod
    def load(cls) -> Settings:
        override = os.environ.get("LEARNLOOP_DB")
        if override:
            path = Path(override)
        else:
            in_repo_db = Path.cwd() / ".learn" / "learnloop.db"
            if in_repo_db.exists():
                path = in_repo_db
            else:
                path = Path(user_data_dir("learnloop")) / "learnloop.db"
        return cls(db_path=path)
