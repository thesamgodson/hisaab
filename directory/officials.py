from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any

_FRESH_DAYS = 90
_EXPIRED_DAYS = 180


def get_officials(
    conn: sqlite3.Connection,
    district: str,
    state: str,
) -> list[dict[str, Any]]:
    """Return officials for a district with freshness status."""
    rows = conn.execute(
        """SELECT * FROM district_officials
           WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?)
           ORDER BY role""",
        (district, state),
    ).fetchall()

    now = datetime.now()
    results: list[dict[str, Any]] = []
    for row in rows:
        r = dict(row)
        scraped = datetime.fromisoformat(r["scraped_at"])
        age_days = (now - scraped).days

        if age_days > _EXPIRED_DAYS:
            results.append({
                "role": r["role"],
                "name": None,
                "phone": None,
                "email": None,
                "office_address": None,
                "source_url": r["source_url"],
                "scraped_at": r["scraped_at"],
                "freshness": "expired",
            })
        else:
            freshness = "stale" if age_days > _FRESH_DAYS else "fresh"
            results.append({
                "role": r["role"],
                "name": r["name"],
                "phone": r["phone"],
                "email": r["email"],
                "office_address": r["office_address"],
                "source_url": r["source_url"],
                "scraped_at": r["scraped_at"],
                "freshness": freshness,
            })
    return results
