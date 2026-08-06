"""Citizen-facing runtime judgments are intentionally suspended.

Raw scheme evidence remains available. A future diagnosis contract must be
computed once at load time, registered in DATA_CLAIMS.md, and consumed by both
the Python and TypeScript action-brief surfaces without runtime formulas.
"""

from __future__ import annotations

import sqlite3

from action_brief.models import DiagnosisItem


def schemes_with_district_data(
    conn: sqlite3.Connection, district: str, state: str
) -> list[str]:
    """Return no runtime-judgment coverage until a load-time contract exists."""
    return []


def build_diagnosis(
    conn: sqlite3.Connection, district: str, state: str
) -> list[DiagnosisItem]:
    """Return no unsourced severity or threshold judgments."""
    return []
