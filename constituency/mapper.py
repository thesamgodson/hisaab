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

from db.connection import DB_PATH, get_connection

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _conn():
    return get_connection(DB_PATH)


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
        # Strip reservation suffixes: "GAYA (SC)" → "GAYA"
        import re
        clean_name = re.sub(r"\s*\((?:SC|ST)\)\s*$", "", constituency.strip().upper())
        # Known spelling mismatches between GeoJSON and MP CSV
        _PC_ALIASES = {"PATALIPUTRA": "PATLIPUTRA", "PATLIPUTRA": "PATALIPUTRA"}
        alias = _PC_ALIASES.get(clean_name, clean_name)
        row = conn.execute(
            "SELECT constituency, mp_name, party, state, elected_year, source_url "
            "FROM mp_info WHERE UPPER(constituency) IN (UPPER(?), UPPER(?), UPPER(?))",
            (constituency, clean_name, alias),
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
            margin_raw = rec.get("margin_votes")
            margin_votes = int(margin_raw) if margin_raw is not None else None
            conn.execute(
                """
                INSERT OR REPLACE INTO mp_info
                    (constituency, mp_name, party, state, elected_year, margin_votes, source_url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rec["constituency"].strip().upper(),
                    rec["mp_name"].strip(),
                    rec.get("party", "").strip(),
                    rec["state"].strip().upper(),
                    int(rec.get("elected_year", 2024)),
                    margin_votes,
                    rec.get("source_url", ""),
                ),
            )
            count += 1
        conn.commit()
    finally:
        conn.close()
    return count


def district_to_ac(district: str, state: str) -> list[dict[str, Any]]:
    """Return Assembly Constituencies covering this district.

    Returns list of {ac_name, ac_no, state, district, pc_name}.
    """
    conn = _conn()
    try:
        rows = conn.execute(
            """
            SELECT ac_name, ac_no, state, district, pc_name
            FROM ac_district
            WHERE UPPER(district) = UPPER(?)
              AND UPPER(state) = UPPER(?)
            ORDER BY ac_name
            """,
            (district, state),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_mla_info(ac_name: str, state: str) -> dict[str, Any] | None:
    """Return MLA info for an assembly constituency.

    Lookup is case-insensitive.  Returns None if not found.
    """
    import re

    clean_name = re.sub(r"\s*\((?:SC|ST)\)\s*$", "", ac_name.strip().upper())
    conn = _conn()
    try:
        row = conn.execute(
            """
            SELECT ac_name, ac_no, state, mla_name, party, elected_year, source_url
            FROM mla_info
            WHERE UPPER(state) = UPPER(?)
              AND (UPPER(ac_name) = UPPER(?) OR UPPER(ac_name) = UPPER(?))
            LIMIT 1
            """,
            (state, ac_name.strip(), clean_name),
        ).fetchone()
        return _row_to_dict(row)
    finally:
        conn.close()


def pin_to_full_representatives(pin_code: str) -> dict[str, Any] | None:
    """Full lookup: PIN → district → MP(s) + MLA(s).

    Returns {district, state, mps: [...], mlas: [...]} or None if PIN not found.
    Each MP entry: {constituency, mp_name, party, elected_year}
    Each MLA entry: {ac_name, mla_name, party, elected_year}
    """
    district_info = pin_to_district(pin_code)
    if not district_info:
        return None

    district = district_info["district"]
    state = district_info["state"]

    constituencies = district_to_constituency(district, state)
    mps: list[dict[str, Any]] = []
    for c in constituencies:
        mp = get_mp_info(c["constituency"])
        entry: dict[str, Any] = {
            "type": "LOK_SABHA",
            "constituency": c["constituency"],
        }
        if mp:
            entry["mp_name"] = mp["mp_name"]
            entry["party"] = mp["party"]
            entry["elected_year"] = mp["elected_year"]
        else:
            entry["mp_name"] = None
            entry["party"] = None
            entry["elected_year"] = None
        mps.append(entry)

    acs = district_to_ac(district, state)
    mlas: list[dict[str, Any]] = []
    for ac in acs:
        mla = get_mla_info(ac["ac_name"], state)
        entry = {
            "type": "VIDHAN_SABHA",
            "ac_name": ac["ac_name"],
            "ac_no": ac.get("ac_no"),
        }
        if mla:
            entry["mla_name"] = mla["mla_name"]
            entry["party"] = mla["party"]
            entry["elected_year"] = mla["elected_year"]
        else:
            entry["mla_name"] = None
            entry["party"] = None
            entry["elected_year"] = None
        mlas.append(entry)

    return {
        "district": district,
        "state": state,
        "office_name": district_info.get("office_name"),
        "mps": mps,
        "mlas": mlas,
    }


def load_ac_data(records: list[dict[str, Any]]) -> int:
    """Bulk-insert AC→district mapping records.

    Each record must have keys: ac_name, state, district.
    Optional keys: ac_no, pc_name.

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
                INSERT OR REPLACE INTO ac_district
                    (ac_name, ac_no, state, district, pc_name)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    rec["ac_name"].strip().upper(),
                    rec.get("ac_no"),
                    rec["state"].strip().upper(),
                    rec["district"].strip().upper(),
                    rec.get("pc_name"),
                ),
            )
            count += 1
        conn.commit()
    finally:
        conn.close()
    return count


def load_mla_data(records: list[dict[str, Any]]) -> int:
    """Bulk-insert MLA info records.

    Each record must have keys: ac_name, state, mla_name.
    Optional keys: ac_no, party, elected_year, source_url.

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
                INSERT OR REPLACE INTO mla_info
                    (ac_name, ac_no, state, mla_name, party, elected_year, source_url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    rec["ac_name"].strip().upper(),
                    rec.get("ac_no"),
                    rec["state"].strip().upper(),
                    rec["mla_name"].strip(),
                    rec.get("party", "").strip(),
                    int(rec.get("elected_year", 2024)),
                    rec.get("source_url") or "",
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
    if table == "ac":
        return load_ac_data(records)
    if table == "mla":
        return load_mla_data(records)
    raise ValueError(f"Unknown table: {table!r}. Must be 'pin', 'constituency', 'mp', 'ac', or 'mla'.")
