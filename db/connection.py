"""Database connection and initialization for Hisaab.

Driver selection:
- Set HISAAB_DB_URL=postgresql://user:pass@host/db to use PostgreSQL.
- Unset (default): SQLite at data/hisaab.db.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from db.schema import SCHEMA

# Resolve relative to the project root (parent of the db/ package directory).
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

DB_PATH = _PROJECT_ROOT / "data" / "hisaab.db"
CURATED_DIR = _PROJECT_ROOT / "data" / "curated"

HISAAB_DB_URL: str = os.environ.get("HISAAB_DB_URL", "")


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Return a DB connection.

    Uses PostgreSQL if HISAAB_DB_URL starts with 'postgresql://', otherwise
    returns a standard sqlite3.Connection.  The PostgreSQL path returns a
    PgConnectionAdapter that matches the sqlite3.Connection interface.
    """
    if HISAAB_DB_URL.startswith("postgresql://"):
        return _get_pg_connection()  # type: ignore[return-value]
    return _get_sqlite_connection(db_path)


def _get_sqlite_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _get_pg_connection() -> object:
    """Return a psycopg connection wrapped in PgConnectionAdapter."""
    try:
        import psycopg  # noqa: PLC0415
        from psycopg.rows import dict_row  # noqa: PLC0415
    except ImportError as exc:
        raise ImportError(
            "psycopg not installed. Run: pip install 'psycopg[binary]>=3.1'"
        ) from exc

    from db.pg_adapter import PgConnectionAdapter  # noqa: PLC0415

    conn = psycopg.connect(HISAAB_DB_URL, row_factory=dict_row)
    return PgConnectionAdapter(conn)


def init_db(conn: sqlite3.Connection) -> None:
    """Initialise the DB schema.  Works for both SQLite and PostgreSQL."""
    from db.pg_adapter import PgConnectionAdapter  # noqa: PLC0415

    if isinstance(conn, PgConnectionAdapter):
        from db.pg_schema import sqlite_to_pg  # noqa: PLC0415

        pg_schema = sqlite_to_pg(SCHEMA)
        conn.executescript(pg_schema)
    else:
        conn.executescript(SCHEMA)
    conn.commit()
