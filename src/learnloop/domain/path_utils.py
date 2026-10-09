"""Path utilities for LearnLoop. Pure domain logic, no I/O."""

from __future__ import annotations

import re

from learnloop.domain.errors import ValidationError

_WIN_DRIVE = re.compile(r"^[a-zA-Z]:")


def normalise_path(path: str) -> str:
    """Normalise and validate a project-relative file path.

    - Converts backslashes to forward slashes.
    - Strips leading and trailing whitespace.
    - Strips leading './'.
    - Rejects absolute paths (starts with '/', '\\', or Windows drive letter).
    - Rejects parent traversal ('..').
    - Bounds length to <= 300 characters.
    """
    if not isinstance(path, str):
        raise ValidationError("Path must be a string.")

    cleaned = path.strip()
    if not cleaned:
        raise ValidationError("Path cannot be empty.")

    if cleaned.startswith(("/", "\\")):
        raise ValidationError(f"Absolute path not allowed: {path!r}")
    if _WIN_DRIVE.match(cleaned):
        raise ValidationError(f"Absolute path with drive letter not allowed: {path!r}")

    p = cleaned.replace("\\", "/")

    segments = p.split("/")
    for seg in segments:
        if seg == "..":
            raise ValidationError(f"Parent directory traversal ('..') not allowed: {path!r}")

    while p.startswith("./"):
        p = p[2:]

    parts = [seg for seg in p.split("/") if seg and seg != "."]
    if not parts:
        raise ValidationError(f"Path resolves to empty: {path!r}")

    normalised = "/".join(parts)
    if len(normalised) > 300:
        raise ValidationError(f"Path exceeds 300 characters ({len(normalised)} chars): {path!r}")

    return normalised


def validate_path(path: str) -> str:
    return normalise_path(path)
