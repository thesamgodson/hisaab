"""Database connection and initialization for Hisaab."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from db.schema import SCHEMA

# Resolve relative to the project root (parent of the db/ package directory).
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

DB_PATH = _PROJECT_ROOT / "data" / "hisaab.db"
CURATED_DIR = _PROJECT_ROOT / "data" / "curated"


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()
