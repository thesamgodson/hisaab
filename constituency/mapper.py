"""PIN → District → Constituency → MP mapping layer.

Data sources (how to populate the tables):
- pin_district_mapping: India Post PIN code directory.
    Download: https://data.gov.in/dataset/all-india-pincode-directory
    UUID on data.gov.in: 201ae2a6-88a3-4a8d-b3fd-69a839bca8b4
    Columns needed: pincode, districtname, statename, officename
    Load via: load_constituency_data() or constituency/seed_data.py

- constituency_district: Election Commission of India (ECI) delimitation order.
    Download: https://eci.gov.in/delimitation/
    Each Lok Sabha constituency spans 1-4 districts.  Map provided as CSV.
    Columns needed: constituency, state, district, constituency_type

- mp_info: ECI / Lok Sabha website — 18th Lok Sabha (elected June 2024).
    Download: https://sansad.in/ls/members
    Columns needed: constituency, mp_name, party, state, elected_year, source_url
"""

from __future__ import annotations

import csv
import io
import sqlite3
from typing import Any

from db import DB_PATH


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)


# ---------------------------------------------------------------------------
# Public query functions
# ---------------------------------------------------------------------------

def pin_to_district(pin_code: str) -> dict[str, Any] | None:
    """Return {district, state, office_name} for a 6-digit PIN code.

    Returns None if the PIN code is not in the database.
    PIN codes are stored without leading/trailing spaces and as plain strings.
    """
    clean = pin_code.strip()
    if not clean.isdigit() or len(clean) != 6:
        return None

    conn = _conn()
    try:
        row = conn.execute(
            "SELECT pin_code, district, state, office_name "
            "FROM pin_district_mapping WHERE pin_code = ?",
            (clean,),
        ).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def district_to_constituency(district: str, state: str) -> list[dict[str, Any]]:
    """Return Lok Sabha constituencies that include this district.

    A district can span multiple constituencies (e.g., large urban districts).
    Returns list of {constituency, state, district, constituency_type}.
    """
    conn = _conn()
    try:
        rows = conn.execute(
            """
            SELECT cd.constituency, cd.state, cd.district, cd.constituency_type
            FROM constituency_district cd
            WHERE UPPER(cd.district) = UPPER(?)
              AND UPPER(cd.state) = UPPER(?)
            ORDER BY cd.constituency
            """,
            (district, state),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_mp_info(constituency: str) -> dict[str, Any] | None:
    """Return MP info for a constituency: {mp_name, party, state, elected_year, source_url}.

    Lookup is case-insensitive.  Returns None if not found.
    """
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT constituency, mp_name, party, state, elected_year, source_url "
            "FROM mp_info WHERE UPPER(constituency) = UPPER(?)",
            (constituency,),
        ).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def get_districts_for_constituency(constituency: str) -> list[str]:
    """Return all districts that belong to a constituency."""
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT district FROM constituency_district "
            "WHERE UPPER(constituency) = UPPER(?) "
            "ORDER BY district",
            (constituency,),
        ).fetchall()
        return [r["district"] for r in rows]
    finally:
        conn.close()


def search_constituency(query: str) -> list[dict[str, Any]]:
    """Full-text-style search over constituency + MP names.

    Returns up to 10 matches as {constituency, mp_name, party, state}.
    Useful for the frontend search box.
    """
    pattern = f"%{query.upper()}%"
    conn = _conn()
    try:
        rows = conn.execute(
            """
            SELECT m.constituency, m.mp_name, m.party, m.state
            FROM mp_info m
            WHERE UPPER(m.constituency) LIKE ?
               OR UPPER(m.mp_name) LIKE ?
            ORDER BY m.constituency
            LIMIT 10
            """,
            (pattern, pattern),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Data loading helpers
# ---------------------------------------------------------------------------

def load_constituency_data(records: list[dict[str, Any]]) -> int:
    """Bulk-insert constituency mapping records.

    Each record must have keys: constituency, state, district.
    Optional key: constituency_type (defaults to 'LOK_SABHA').

    Returns the number of rows inserted/replaced.
    """
    if not records:
        return 0

    conn = _conn()
    count = 0
    try:
        for rec in records:
            conn.execute(
                """
                INSERT OR REPLACE INTO constituency_district
                    (constituency, state, district, constituency_type)
                VALUES (?, ?, ?, ?)
                """,
                (
                    rec["constituency"].strip().upper(),
                    rec["state"].strip().upper(),
                    rec["district"].strip().upper(),
                    rec.get("constituency_type", "LOK_SABHA").strip().upper(),
                ),
            )
            count += 1
        conn.commit()
    finally:
        conn.close()
    return count


def load_pin_data(records: list[dict[str, Any]]) -> int:
    """Bulk-insert PIN code → district mapping records.

    Each record must have keys: pin_code, district, state.
    Optional key: office_name.

    Returns the number of rows inserted/replaced.
    """
    if not records:
        return 0

    conn = _conn()
    count = 0
    try:
        for rec in records:
            pin = str(rec["pin_code"]).strip()
            if not pin.isdigit() or len(pin) != 6:
                continue
            conn.execute(
                """
                INSERT OR REPLACE INTO pin_district_mapping
                    (pin_code, district, state, office_name)
                VALUES (?, ?, ?, ?)
                """,
                (
                    pin,
                    rec["district"].strip().upper(),
                    rec["state"].strip().upper(),
                    rec.get("office_name", ""),
                ),
            )
            count += 1
        conn.commit()
    finally:
        conn.close()
    return count


def load_mp_data(records: list[dict[str, Any]]) -> int:
    """Bulk-insert MP info records.

    Each record must have keys: constituency, mp_name, state.
    Optional keys: party, elected_year, source_url.

    Returns the number of rows inserted/replaced.
    """
    if not records:
        return 0

    conn = _conn()
    count = 0
    try:
        for rec in records:
            conn.execute(
                """
                INSERT OR REPLACE INTO mp_info
                    (constituency, mp_name, party, state, elected_year, source_url)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    rec["constituency"].strip().upper(),
                    rec["mp_name"].strip(),
                    rec.get("party", "").strip(),
                    rec["state"].strip().upper(),
                    int(rec.get("elected_year", 2024)),
                    rec.get("source_url", ""),
                ),
            )
            count += 1
        conn.commit()
    finally:
        conn.close()
    return count


def load_from_csv(csv_text: str, table: str) -> int:
    """Load records from a CSV string into pin/constituency/mp tables.

    table must be one of: 'pin', 'constituency', 'mp'.
    Returns number of rows inserted.
    """
    reader = csv.DictReader(io.StringIO(csv_text.strip()))
    records = list(reader)
    if table == "pin":
        return load_pin_data(records)
    if table == "constituency":
        return load_constituency_data(records)
    if table == "mp":
        return load_mp_data(records)
    raise ValueError(f"Unknown table: {table!r}. Must be 'pin', 'constituency', or 'mp'.")
