"""PostgreSQL connection adapter matching the sqlite3.Connection interface.

Translates SQLite-specific SQL on the fly:
- ? placeholders → %s (skips ? inside string literals)
- INSERT OR REPLACE INTO → INSERT INTO ... ON CONFLICT DO UPDATE SET ...
- INSERT OR IGNORE INTO  → INSERT INTO ... ON CONFLICT DO NOTHING
- PRAGMA statements      → silently skipped
"""

from __future__ import annotations

import re


# ---------------------------------------------------------------------------
# SQL translation helpers
# ---------------------------------------------------------------------------

_INSERT_OR_REPLACE = re.compile(
    r"\bINSERT\s+OR\s+REPLACE\s+INTO\b",
    flags=re.IGNORECASE,
)
_INSERT_OR_IGNORE = re.compile(
    r"\bINSERT\s+OR\s+IGNORE\s+INTO\b",
    flags=re.IGNORECASE,
)
_COLS_VALUES = re.compile(
    r"\bINSERT\s+INTO\s+\w+\s*\(([^)]+)\)\s*VALUES\s*\(([^)]+)\)",
    flags=re.IGNORECASE | re.DOTALL,
)


def _translate_insert_or_replace(sql: str) -> str:
    """Convert INSERT OR REPLACE … to INSERT … ON CONFLICT DO UPDATE SET …"""
    if not _INSERT_OR_REPLACE.search(sql):
        return sql

    # Strip "OR REPLACE" from the keyword
    sql = _INSERT_OR_REPLACE.sub("INSERT INTO", sql)

    # If we can parse the column list, build a proper UPDATE SET clause.
    match = _COLS_VALUES.search(sql)
    if match:
        cols = [c.strip() for c in match.group(1).split(",")]
        update_parts = [f"{c}=EXCLUDED.{c}" for c in cols if c.lower() != "id"]
        if update_parts:
            sql = sql.rstrip("; \n") + " ON CONFLICT DO UPDATE SET " + ", ".join(update_parts)
        else:
            sql = sql.rstrip("; \n") + " ON CONFLICT DO NOTHING"
    else:
        # Fallback: no-op on conflict (safe but may silently skip)
        sql = sql.rstrip("; \n") + " ON CONFLICT DO NOTHING"

    return sql


def _translate_insert_or_ignore(sql: str) -> str:
    """Convert INSERT OR IGNORE … to INSERT … ON CONFLICT DO NOTHING."""
    if not _INSERT_OR_IGNORE.search(sql):
        return sql
    sql = _INSERT_OR_IGNORE.sub("INSERT INTO", sql)
    sql = sql.rstrip("; \n") + " ON CONFLICT DO NOTHING"
    return sql


def _replace_placeholders(sql: str) -> str:
    """Replace ? with %s, but leave ? inside single-quoted string literals alone."""
    result: list[str] = []
    in_string = False
    i = 0
    while i < len(sql):
        ch = sql[i]
        if ch == "'" and not in_string:
            in_string = True
            result.append(ch)
        elif ch == "'" and in_string:
            # Escaped quote ''
            if i + 1 < len(sql) and sql[i + 1] == "'":
                result.append("''")
                i += 2
                continue
            in_string = False
            result.append(ch)
        elif ch == "?" and not in_string:
            result.append("%s")
        else:
            result.append(ch)
        i += 1
    return "".join(result)


def _translate_sql(sql: str) -> str:
    """Apply all SQLite → PostgreSQL SQL translations."""
    sql = _translate_insert_or_replace(sql)
    sql = _translate_insert_or_ignore(sql)
    sql = _replace_placeholders(sql)
    return sql


# ---------------------------------------------------------------------------
# Adapter classes
# ---------------------------------------------------------------------------

class PgCursorAdapter:
    """Wraps a psycopg cursor to present the subset of sqlite3.Cursor used here."""

    def __init__(self, cursor: object) -> None:
        self._cursor = cursor

    def fetchall(self) -> list[dict]:
        return self._cursor.fetchall()  # type: ignore[attr-defined]

    def fetchone(self) -> dict | None:
        return self._cursor.fetchone()  # type: ignore[attr-defined]

    @property
    def lastrowid(self) -> None:
        # psycopg3 exposes pgresult.cmd_tuples; lastrowid not directly available.
        return None

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount  # type: ignore[attr-defined]


class PgConnectionAdapter:
    """Wraps psycopg.Connection to match the sqlite3.Connection interface.

    All callers use .execute(), .executemany(), .executescript(), .commit(),
    and .close() — this adapter covers exactly those methods.
    """

    def __init__(self, conn: object) -> None:
        self._conn = conn

    def execute(self, sql: str, params: tuple | list | None = None) -> PgCursorAdapter:
        translated = _translate_sql(sql)
        cursor = self._conn.execute(translated, params or ())  # type: ignore[attr-defined]
        return PgCursorAdapter(cursor)

    def executemany(self, sql: str, params_list: list) -> None:
        translated = _translate_sql(sql)
        for params in params_list:
            self._conn.execute(translated, params)  # type: ignore[attr-defined]

    def executescript(self, sql: str) -> None:
        """Execute multiple semicolon-separated statements, skipping PRAGMA."""
        for stmt in sql.split(";"):
            stmt = stmt.strip()
            if not stmt:
                continue
            if re.match(r"PRAGMA\s+", stmt, flags=re.IGNORECASE):
                continue
            translated = _translate_sql(stmt)
            self._conn.execute(translated)  # type: ignore[attr-defined]

    def commit(self) -> None:
        self._conn.commit()  # type: ignore[attr-defined]

    def close(self) -> None:
        self._conn.close()  # type: ignore[attr-defined]

    def __enter__(self) -> "PgConnectionAdapter":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
