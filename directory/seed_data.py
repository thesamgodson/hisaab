"""Seed grievance channels from the tracked, source-verified registry."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

_REGISTRY = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "curated"
    / "grievance_channels_all_latest.json"
)


def _channels() -> list[dict[str, Any]]:
    rows = json.loads(_REGISTRY.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("grievance channel registry must be a JSON list")
    return rows


def seed_grievance_channels(conn: sqlite3.Connection) -> int:
    """Insert the verified registry without stale hardcoded phones or claims."""
    rows = _channels()
    conn.execute("DELETE FROM grievance_channels")
    for channel in rows:
        conn.execute(
            """INSERT OR REPLACE INTO grievance_channels
               (scheme, level, authority, portal_name, portal_url, phone,
                description, escalation_scheme, source_url, scraped_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                channel["scheme"],
                channel["level"],
                channel.get("authority"),
                channel["portal_name"],
                channel["portal_url"],
                channel.get("phone"),
                channel.get("description"),
                channel.get("escalation_scheme"),
                channel["source_url"],
                channel["scraped_at"],
            ),
        )
    conn.commit()
    return len(rows)
