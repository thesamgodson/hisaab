from __future__ import annotations

import sqlite3
from typing import Any


def get_grievance_channels(
    conn: sqlite3.Connection,
    schemes: list[str],
) -> list[dict[str, Any]]:
    """Return grievance channels for a list of schemes, sorted by scheme then level."""
    if not schemes:
        return []
    placeholders = ",".join("?" * len(schemes))
    rows = conn.execute(
        f"""SELECT * FROM grievance_channels
            WHERE scheme IN ({placeholders})
            ORDER BY scheme,
                     CASE level WHEN 'district' THEN 1 WHEN 'state' THEN 2
                                WHEN 'national' THEN 3 ELSE 4 END""",
        schemes,
    ).fetchall()
    return [dict(r) for r in rows]
