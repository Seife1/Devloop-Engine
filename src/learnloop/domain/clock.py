from __future__ import annotations

from datetime import UTC, datetime


def utcnow() -> datetime:
    return datetime.now(UTC)


def iso(dt: datetime) -> str:
    """One canonical timestamp format, so string comparison == time comparison."""
    return dt.astimezone(UTC).isoformat(timespec="seconds")


def parse(s: str) -> datetime:
    return datetime.fromisoformat(s).astimezone(UTC)
