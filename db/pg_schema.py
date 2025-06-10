"""SQLite DDL → PostgreSQL DDL translation."""

from __future__ import annotations

import re


def sqlite_to_pg(schema: str) -> str:
    """Convert SQLite DDL to PostgreSQL-compatible DDL.

    Handles:
    - INTEGER PRIMARY KEY AUTOINCREMENT → SERIAL PRIMARY KEY
    - datetime('now') → now()
    - PRAGMA statements → removed
    """
    s = schema

    # AUTOINCREMENT → SERIAL
    s = re.sub(
        r"INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT",
        "SERIAL PRIMARY KEY",
        s,
        flags=re.IGNORECASE,
    )

    # datetime('now') → now()
    s = s.replace("datetime('now')", "now()")

    # Remove PRAGMA lines entirely
    s = re.sub(r"PRAGMA\s+[^;]+;?", "", s, flags=re.IGNORECASE)

    return s
