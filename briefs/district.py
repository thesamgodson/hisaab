"""District-level journalist brief generation."""

from __future__ import annotations

import difflib
import sqlite3
from datetime import datetime

from briefs import sections
from briefs.formatting import FIN_YEAR, get_conn
from briefs.red_flags import detect_flags

# ---------------------------------------------------------------------------
# Fuzzy district matching
# ---------------------------------------------------------------------------
_DISTRICT_TABLES = (
    "misappropriation",
    "financial_statement",
    "pmgsy_district",
    "pmayg_district",
    "pmkisan_district",
    "jjm_district",
    "pmposhan_district",
    "nsap_district",
    "nfsa_district",
)


def _all_districts(conn: sqlite3.Connection) -> list[dict[str, str]]:
    """Return all (district, state) pairs from all scheme tables."""
    seen: set[tuple[str, str]] = set()
    result: list[dict[str, str]] = []
    for table in _DISTRICT_TABLES:
        try:
            rows = conn.execute(f"SELECT DISTINCT district, state FROM {table} ORDER BY state, district").fetchall()
            for r in rows:
                key = (r["district"].upper(), r["state"].upper())
                if key not in seen:
                    seen.add(key)
                    result.append({"district": r["district"], "state": r["state"]})
        except Exception:
            pass
    return sorted(result, key=lambda d: (d["state"], d["district"]))


def resolve_district(query: str) -> dict[str, str] | None:
    """Fuzzy-match a district name. Returns {district, state} or None."""
    conn = get_conn()
    all_d = _all_districts(conn)
    conn.close()

    query_upper = query.strip().upper()

    # Exact match
    for d in all_d:
        if d["district"].upper() == query_upper:
            return d

    # Prefix match
    for d in all_d:
        if d["district"].upper().startswith(query_upper):
            return d

    # Fuzzy match via difflib
    names = [d["district"] for d in all_d]
    upper_names = [n.upper() for n in names]
    matches = difflib.get_close_matches(query_upper, upper_names, n=1, cutoff=0.5)
    if matches:
        idx = upper_names.index(matches[0])
        return all_d[idx]

    return None


# ---------------------------------------------------------------------------
# Ranking queries
# ---------------------------------------------------------------------------
def _state_rank_unrecovered(conn: sqlite3.Connection, district: str, state: str) -> tuple[int, int]:
    """Rank within state by unrecovered amount. Returns (rank, total)."""
    rows = conn.execute(
        """SELECT district, (amount_reported - amount_recovered) as unrecovered
           FROM misappropriation WHERE UPPER(state) = UPPER(?)
           ORDER BY unrecovered DESC""",
        (state,),
    ).fetchall()
    total = len(rows)
    for i, r in enumerate(rows, 1):
        if r["district"].upper() == district.upper():
            return i, total
    return 0, total


def _national_rank_unrecovered(conn: sqlite3.Connection, district: str, state: str) -> tuple[int, int]:
    """Rank nationally by unrecovered amount. Returns (rank, total)."""
    rows = conn.execute(
        """SELECT district, state, (amount_reported - amount_recovered) as unrecovered
           FROM misappropriation ORDER BY unrecovered DESC"""
    ).fetchall()
    total = len(rows)
    for i, r in enumerate(rows, 1):
        if r["district"].upper() == district.upper() and r["state"].upper() == state.upper():
            return i, total
    return 0, total


# ---------------------------------------------------------------------------
# Main brief generator
# ---------------------------------------------------------------------------
def brief(district_query: str) -> str:
    """Generate a journalist briefing for a district. Accepts fuzzy names."""
    match = resolve_district(district_query)
    if not match:
        return f"ERROR: Could not find district matching '{district_query}'.\nTry an exact name or longer prefix."

    district = match["district"]
    state = match["state"]
    conn = get_conn()

    generated = datetime.now().strftime("%d %b %Y")
    lines = [
        "HISAAB DISTRICT BRIEF",
        f"{district}, {state}",
        f"Generated: {generated} | Source: Government of India, MoRD MGNREGA MIS",
        f"Financial Year: {FIN_YEAR}",
        "",
    ]

    section_fns = [
        sections.misappropriation,
        sections.fund_utilization,
        sections.fto,
        sections.social_audit,
        sections.pmgsy,
        sections.pmayg,
        sections.pmkisan,
        sections.jjm,
        sections.poshan,
        sections.nsap,
        sections.nfsa,
    ]
    for section_fn in section_fns:
        lines.extend(section_fn(conn, district, state))

    # Red flags
    flags = detect_flags(conn, district, state, verbose=True)
    if flags:
        lines.append("RED FLAGS")
        for flag in flags:
            lines.append(f"  \u26a0 {flag}")
        lines.append("")

    # Context rankings
    lines.append("CONTEXT")
    state_rank, state_total = _state_rank_unrecovered(conn, district, state)
    national_rank, national_total = _national_rank_unrecovered(conn, district, state)
    if state_rank > 0:
        lines.append(
            f"  {district} ranks #{state_rank} out of {state_total} {state} districts for unrecovered misappropriation."
        )
    if national_rank > 0:
        lines.append(f"  Nationally, it ranks #{national_rank} out of {national_total} districts.")

    conn.close()
    return "\n".join(lines)
