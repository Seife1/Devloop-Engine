"""Service for managing sourced technical facts ('Did you know')."""

from __future__ import annotations

import hashlib
import ipaddress
import sqlite3
import urllib.parse
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from learnloop.capture.redaction import redact
from learnloop.capture.techscan import redact_credentials
from learnloop.domain.errors import ValidationError
from learnloop.services.capture_service import require_project

MAX_DAILY_FACTS = 10


def validate_source_url(url: str) -> str:
    """Validate that source_url is an https URL with a valid domain host (no userinfo/IP literal)."""
    cleaned = url.strip()
    if not cleaned or len(cleaned) > 500:
        raise ValidationError("source_url must be between 1 and 500 characters")

    for ch in cleaned:
        if ch in ("<", ">", '"', "'", " ", "\t", "\r", "\n") or ord(ch) < 32:
            raise ValidationError("source_url contains invalid characters")

    try:
        parsed = urllib.parse.urlparse(cleaned)
    except Exception as exc:
        raise ValidationError(f"Invalid source_url: {exc}") from exc

    if parsed.scheme.lower() != "https":
        raise ValidationError("source_url must strictly use https scheme")

    if not parsed.netloc:
        raise ValidationError("source_url must include a hostname")

    if parsed.username or parsed.password or "@" in parsed.netloc:
        raise ValidationError("source_url must not contain userinfo/credentials")

    hostname = (parsed.hostname or "").strip().lower()
    if not hostname:
        raise ValidationError("source_url must include a valid hostname")

    if hostname in ("localhost", "0.0.0.0", "127.0.0.1", "::1"):
        raise ValidationError(f"source_url host {hostname!r} is not allowed")

    # Reject IP address literals (IPv4 and IPv6)
    try:
        ipaddress.ip_address(hostname)
        raise ValidationError(f"source_url host must be a domain name, not an IP address literal: {hostname}")
    except ValueError:
        # Expected: hostname is a domain name, not an IP literal
        pass

    if "." not in hostname or hostname.endswith("."):
        raise ValidationError(f"source_url host {hostname!r} is not a valid domain name")

    return cleaned


def validate_retrieved_at(retrieved_at: str) -> str:
    """Validate that retrieved_at is a valid ISO 8601 UTC timestamp not in the future."""
    cleaned = retrieved_at.strip()
    if not cleaned:
        raise ValidationError("retrieved_at must be provided")

    try:
        dt = datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
    except Exception as exc:
        raise ValidationError(f"retrieved_at must be a valid ISO 8601 timestamp: {exc}") from exc

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)

    now = datetime.now(UTC)
    if dt > now + timedelta(minutes=5):
        raise ValidationError("retrieved_at cannot be in the future")

    return dt.astimezone(UTC).isoformat()


def add_did_you_know(
    conn: sqlite3.Connection,
    project_id: str,
    topic: str,
    fact: str,
    source_url: str,
    source_title: str,
    retrieved_at: str,
    technology: str | None = None,
) -> dict[str, Any]:
    """Add a verified technical fact with mandatory HTTPS source verification and rate limits."""
    require_project(conn, project_id)

    clean_topic = topic.strip()
    if not clean_topic or len(clean_topic) > 80:
        raise ValidationError("topic must be between 1 and 80 characters")

    clean_fact = fact.strip()
    if not clean_fact or len(clean_fact) > 300:
        raise ValidationError("fact must be between 1 and 300 characters")

    clean_title = source_title.strip()
    if not clean_title or len(clean_title) > 200:
        raise ValidationError("source_title must be between 1 and 200 characters")

    valid_url = validate_source_url(source_url)
    valid_retrieved = validate_retrieved_at(retrieved_at)

    clean_tech = technology.strip()[:80] if technology and technology.strip() else None

    # Idempotency check on (project_id, source_url, normalized fact hash)
    normalized_fact = " ".join(clean_fact.split()).lower()
    fact_hash = hashlib.sha256(normalized_fact.encode("utf-8")).hexdigest()[:32]

    existing = conn.execute(
        "SELECT id, project_id, topic, fact, source_url, source_title, retrieved_at, technology, created_at "
        "FROM project_facts WHERE project_id = ? AND source_url = ? AND fact_hash = ?",
        (project_id, valid_url, fact_hash),
    ).fetchone()

    if existing:
        return {
            "id": existing["id"],
            "project_id": existing["project_id"],
            "topic": existing["topic"],
            "fact": existing["fact"],
            "source_url": existing["source_url"],
            "source_title": existing["source_title"],
            "retrieved_at": existing["retrieved_at"],
            "technology": existing["technology"],
            "created_at": existing["created_at"],
            "created": False,
        }

    # Daily rate limit check (max 5 facts per project per UTC calendar day)
    now_utc = datetime.now(UTC)
    today_utc = now_utc.strftime("%Y-%m-%d")
    daily_count = conn.execute(
        "SELECT COUNT(*) FROM project_facts WHERE project_id = ? AND strftime('%Y-%m-%d', created_at) = ?",
        (project_id, today_utc),
    ).fetchone()[0]

    if daily_count >= MAX_DAILY_FACTS:
        raise ValidationError(f"Daily limit of {MAX_DAILY_FACTS} facts reached for this project (UTC day)")

    # Redact all agent free text
    redacted_topic = redact(redact_credentials(clean_topic))
    redacted_fact = redact(redact_credentials(clean_fact))
    redacted_title = redact(redact_credentials(clean_title))
    redacted_tech = redact(redact_credentials(clean_tech)) if clean_tech else None

    fact_id = uuid.uuid4().hex[:12]
    created_at = now_utc.isoformat()

    conn.execute(
        "INSERT INTO project_facts "
        "(id, project_id, topic, fact, source_url, source_title, "
        "retrieved_at, technology, fact_hash, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            fact_id,
            project_id,
            redacted_topic,
            redacted_fact,
            valid_url,
            redacted_title,
            valid_retrieved,
            redacted_tech,
            fact_hash,
            created_at,
        ),
    )
    conn.commit()

    return {
        "id": fact_id,
        "project_id": project_id,
        "topic": redacted_topic,
        "fact": redacted_fact,
        "source_url": valid_url,
        "source_title": redacted_title,
        "retrieved_at": valid_retrieved,
        "technology": redacted_tech,
        "created_at": created_at,
        "created": True,
    }


def list_facts(conn: sqlite3.Connection, project_id: str, limit: int = 10) -> list[dict[str, Any]]:
    """Return latest facts for a project in deterministic order."""
    rows = conn.execute(
        "SELECT id, project_id, topic, fact, source_url, source_title, retrieved_at, technology, created_at "
        "FROM project_facts WHERE project_id = ? "
        "ORDER BY created_at DESC, id DESC LIMIT ?",
        (project_id, limit),
    ).fetchall()

    return [
        {
            "id": r["id"],
            "project_id": r["project_id"],
            "topic": r["topic"],
            "fact": r["fact"],
            "source_url": r["source_url"],
            "source_title": r["source_title"],
            "retrieved_at": r["retrieved_at"],
            "technology": r["technology"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]
