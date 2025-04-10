"""Shared formatting helpers and constants for journalist briefs."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from db import DB_PATH

BRIEFS_DIR = Path(__file__).resolve().parent.parent / "data" / "briefs"
FIN_YEAR = "2024-2025"


def get_conn() -> sqlite3.Connection:
    """Return a new read-only database connection with Row factory."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def fmt_inr(amount: float, unit: str = "rupees") -> str:
    """Format as crore / lakh."""
    if unit == "lakhs":
        if abs(amount) >= 100:
            return f"\u20b9{amount / 100:.2f} crore"
        return f"\u20b9{amount:.2f} lakh"
    if abs(amount) >= 10000000:
        return f"\u20b9{amount / 10000000:.2f} crore"
    if abs(amount) >= 100000:
        return f"\u20b9{amount / 100000:.2f} lakh"
    return f"\u20b9{amount:,.0f}"


def pct(value: float) -> str:
    """Format a percentage value."""
    return f"{value:.1f}%"
