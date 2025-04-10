"""Red flag detection and district scanning for journalist story-finding."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any

from briefs.flag_checks import (
    cross_scheme_flags,
    jjm_flags,
    mgnrega_flags,
    nfsa_flags,
    nsap_flags,
    pmayg_flags,
    pmgsy_flags,
    pmkisan_flags,
    poshan_flags,
)
from briefs.formatting import FIN_YEAR, fmt_inr, get_conn


def detect_flags(
    conn: sqlite3.Connection,
    district: str,
    state: str,
    verbose: bool = False,
) -> list[str]:
    """Return list of red flag strings for a district.

    verbose=True gives detailed explanations (for briefs).
    verbose=False gives compact labels (for scan tables).
    """
    mis = conn.execute(
        "SELECT * FROM misappropriation WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchone()

    fin = conn.execute(
        "SELECT * FROM financial_statement WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchone()

    aud = conn.execute(
        "SELECT * FROM issues_reported WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchone()

    fto = conn.execute(
        "SELECT * FROM fto_status WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchone()

    flags: list[str] = []
    flags.extend(mgnrega_flags(mis, fin, aud, fto, verbose))

    pmgsy_rows = conn.execute(
        "SELECT * FROM pmgsy_district WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?)",
        (district, state),
    ).fetchall()
    flags.extend(pmgsy_flags(conn, pmgsy_rows, state, verbose))

    pmayg = conn.execute(
        "SELECT * FROM pmayg_district WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchone()
    flags.extend(pmayg_flags(pmayg, verbose))

    pmkisan_rows = conn.execute(
        "SELECT * FROM pmkisan_district WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchall()
    flags.extend(pmkisan_flags(pmkisan_rows, verbose))

    jjm = conn.execute(
        "SELECT * FROM jjm_district WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?)",
        (district, state),
    ).fetchone()
    flags.extend(jjm_flags(jjm, verbose))

    poshan = conn.execute(
        "SELECT * FROM pmposhan_district WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchone()
    flags.extend(poshan_flags(poshan, verbose))

    nsap_rows = conn.execute(
        "SELECT * FROM nsap_district WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchall()
    flags.extend(nsap_flags(nsap_rows, verbose))

    nfsa = conn.execute(
        "SELECT * FROM nfsa_district WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchone()
    flags.extend(nfsa_flags(nfsa, verbose))

    # Cross-scheme flags
    total_sanctioned = 0
    total_completed = 0
    if pmgsy_rows:
        pm = [dict(r) for r in pmgsy_rows]
        total_sanctioned = sum(r.get("roads_sanctioned", 0) for r in pm)
        total_completed = sum(r.get("roads_completed", 0) for r in pm)

    flags.extend(
        cross_scheme_flags(fin, pmgsy_rows, pmayg, jjm, poshan, nfsa, total_sanctioned, total_completed, verbose)
    )

    return flags


# ---------------------------------------------------------------------------
# Scan all districts for red flags
# ---------------------------------------------------------------------------
_TABLES_WITH_FY = [
    "misappropriation",
    "financial_statement",
    "fto_status",
    "pmayg_district",
    "pmkisan_district",
    "pmposhan_district",
    "nsap_district",
    "nfsa_district",
]
_TABLES_WITHOUT_FY = ["pmgsy_district", "jjm_district"]


def _gather_districts(conn: sqlite3.Connection, state_filter: str | None) -> list[tuple[str, str]]:
    """Collect all (district, state) pairs across scheme tables."""
    all_districts: set[tuple[str, str]] = set()

    for table in _TABLES_WITH_FY:
        try:
            where = "WHERE fin_year=?"
            params: list[Any] = [FIN_YEAR]
            if state_filter:
                where += " AND UPPER(state)=UPPER(?)"
                params.append(state_filter)
            for r in conn.execute(f"SELECT DISTINCT district, state FROM {table} {where}", params).fetchall():
                all_districts.add((r["district"], r["state"]))
        except Exception:
            pass

    for table in _TABLES_WITHOUT_FY:
        try:
            where = "WHERE 1=1"
            params_nfy: list[Any] = []
            if state_filter:
                where += " AND UPPER(state)=UPPER(?)"
                params_nfy.append(state_filter)
            for r in conn.execute(f"SELECT DISTINCT district, state FROM {table} {where}", params_nfy).fetchall():
                all_districts.add((r["district"], r["state"]))
        except Exception:
            pass

    return sorted(all_districts, key=lambda x: (x[1], x[0]))


def scan_red_flags(limit: int = 25, state_filter: str | None = None) -> str:
    """Scan all districts and rank by number of red flags. Story finder for journalists."""
    conn = get_conn()
    rows = _gather_districts(conn, state_filter)

    flagged: list[tuple[str, str, list[str], float]] = []
    for d, s in rows:
        flags = detect_flags(conn, d, s)
        if flags:
            mis = conn.execute(
                "SELECT amount_reported, amount_recovered FROM misappropriation WHERE district=? AND state=? AND fin_year=?",
                (d, s, FIN_YEAR),
            ).fetchone()
            unrecovered = (mis["amount_reported"] - mis["amount_recovered"]) if mis else 0
            flagged.append((d, s, flags, unrecovered))

    flagged.sort(key=lambda x: (-len(x[2]), -x[3]))

    scope = state_filter if state_filter else "INDIA"
    generated = datetime.now().strftime("%d %b %Y")
    lines = [
        "HISAAB RED FLAG SCAN",
        f"Scope: {scope} | Generated: {generated}",
        f"Financial Year: {FIN_YEAR}",
        f"Scanned {len(rows)} districts, {len(flagged)} have red flags",
        "",
    ]

    for i, (d, s, flags, unrec) in enumerate(flagged[:limit], 1):
        lines.append(f"{i}. {d}, {s} \u2014 {len(flags)} flags | {fmt_inr(unrec)} unrecovered")
        for flag in flags:
            lines.append(f"     {flag}")
        lines.append("")

    if len(flagged) > limit:
        lines.append(f"... and {len(flagged) - limit} more districts with red flags.")

    conn.close()
    return "\n".join(lines)
