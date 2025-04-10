"""Queries for PMAY-G, PM Kisan, JJM, PM POSHAN, NSAP, and NFSA."""

from __future__ import annotations

from typing import Any

import queries.common as _common

_fmt_rs = _common._fmt_rs


# ---------------------------------------------------------------------------
# PMAY-G queries (rural housing)
# ---------------------------------------------------------------------------
def pmayg_by_district(
    district: str,
    state: str = "TAMIL NADU",
    fin_year: str = "2024-2025",
) -> dict[str, Any]:
    conn = _common._conn()
    row = conn.execute(
        """SELECT * FROM pmayg_district
        WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?) AND fin_year = ?""",
        (district, state, fin_year),
    ).fetchone()
    conn.close()

    if not row:
        return {"answer": f"No PMAY-G data for {district}, {state} ({fin_year}).", "data": None}

    r = dict(row)
    occupied_pct = (r["houses_occupied"] / r["houses_completed"] * 100) if r["houses_completed"] > 0 else 0
    return {
        "answer": (
            f"{r['district']}, {r['state']} — PMAY-G Rural Housing (FY {fin_year}):\n"
            f"  Houses sanctioned: {r['houses_sanctioned']:,} | completed: {r['houses_completed']:,} ({r['completion_pct']:.0f}%)\n"
            f"  Houses occupied: {r['houses_occupied']:,} ({occupied_pct:.0f}% of completed)\n"
            f"  Funds released: {_fmt_rs(r['funds_released_lakhs'], 'lakhs')} | utilized: {_fmt_rs(r['funds_utilized_lakhs'], 'lakhs')}"
        ),
        "data": r,
        "source_url": r.get("source_url"),
    }


def pmayg_state_summary(
    state: str = "TAMIL NADU",
    fin_year: str = "2024-2025",
) -> dict[str, Any]:
    conn = _common._conn()
    row = conn.execute(
        """SELECT COUNT(DISTINCT district) as districts,
                  SUM(houses_sanctioned) as sanctioned, SUM(houses_completed) as completed,
                  SUM(houses_occupied) as occupied,
                  SUM(funds_released_lakhs) as released, SUM(funds_utilized_lakhs) as utilized
           FROM pmayg_district WHERE UPPER(state) = UPPER(?) AND fin_year = ?""",
        (state, fin_year),
    ).fetchone()
    conn.close()

    if not row or row["districts"] == 0:
        return {"answer": f"No PMAY-G data for {state} ({fin_year}).", "data": None}

    r = dict(row)
    completion_pct = (r["completed"] / r["sanctioned"] * 100) if r["sanctioned"] > 0 else 0
    return {
        "answer": (
            f"{state} PMAY-G summary (FY {fin_year}):\n"
            f"  Districts: {r['districts']}\n"
            f"  Houses sanctioned: {r['sanctioned']:,} | completed: {r['completed']:,} ({completion_pct:.0f}%)\n"
            f"  Occupied: {r['occupied']:,}\n"
            f"  Funds released: {_fmt_rs(r['released'], 'lakhs')} | utilized: {_fmt_rs(r['utilized'], 'lakhs')}"
        ),
        "data": r,
    }


def pmayg_worst_completion(
    state: str = "TAMIL NADU",
    fin_year: str = "2024-2025",
    limit: int = 5,
) -> dict[str, Any]:
    conn = _common._conn()
    rows = conn.execute(
        """SELECT district, houses_sanctioned, houses_completed, houses_occupied,
                  completion_pct, source_url
           FROM pmayg_district
           WHERE UPPER(state) = UPPER(?) AND fin_year = ? AND houses_sanctioned > 0
           ORDER BY completion_pct ASC LIMIT ?""",
        (state, fin_year, limit),
    ).fetchall()
    conn.close()

    if not rows:
        return {"answer": f"No PMAY-G data for {state} ({fin_year}).", "data": None}

    lines = [f"Worst {limit} districts by housing completion ({state}, PMAY-G, FY {fin_year}):"]
    data = []
    for i, row in enumerate(rows, 1):
        r = dict(row)
        lines.append(
            f"  {i}. {r['district']}: {r['completion_pct']:.0f}% "
            f"({r['houses_completed']:,}/{r['houses_sanctioned']:,} houses)"
        )
        data.append(r)
    return {"answer": "\n".join(lines), "data": data}


# ---------------------------------------------------------------------------
# PM Kisan queries (farmer payments)
# ---------------------------------------------------------------------------
def pmkisan_by_district(
    district: str,
    state: str = "TAMIL NADU",
    fin_year: str = "2024-2025",
) -> dict[str, Any]:
    conn = _common._conn()
    rows = conn.execute(
        """SELECT * FROM pmkisan_district
        WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?) AND fin_year = ?
        ORDER BY installment""",
        (district, state, fin_year),
    ).fetchall()
    conn.close()

    if not rows:
        return {"answer": f"No PM Kisan data for {district}, {state} ({fin_year}).", "data": None}

    data = [dict(r) for r in rows]
    total_paid = sum(r["beneficiaries_paid"] for r in data)
    total_amount = sum(r["amount_paid_lakhs"] for r in data)
    max_registered = max(r["beneficiaries_registered"] for r in data)
    coverage_pct = (total_paid / max_registered * 100) if max_registered > 0 else 0

    return {
        "answer": (
            f"{district}, {state} — PM Kisan (FY {fin_year}):\n"
            f"  Beneficiaries registered: {max_registered:,}\n"
            f"  Total paid: {total_paid:,} ({coverage_pct:.0f}% coverage)\n"
            f"  Amount disbursed: {_fmt_rs(total_amount, 'lakhs')}\n"
            f"  Installments: {len(data)}"
        ),
        "data": data,
        "source_url": data[0].get("source_url"),
    }


def pmkisan_state_summary(
    state: str = "TAMIL NADU",
    fin_year: str = "2024-2025",
) -> dict[str, Any]:
    conn = _common._conn()
    row = conn.execute(
        """SELECT COUNT(DISTINCT district) as districts,
                  SUM(beneficiaries_paid) as total_paid,
                  SUM(amount_paid_lakhs) as total_amount,
                  MAX(beneficiaries_registered) as max_registered
           FROM pmkisan_district WHERE UPPER(state) = UPPER(?) AND fin_year = ?""",
        (state, fin_year),
    ).fetchone()
    conn.close()

    if not row or row["districts"] == 0:
        return {"answer": f"No PM Kisan data for {state} ({fin_year}).", "data": None}

    r = dict(row)
    return {
        "answer": (
            f"{state} PM Kisan summary (FY {fin_year}):\n"
            f"  Districts: {r['districts']}\n"
            f"  Total beneficiaries paid: {r['total_paid']:,}\n"
            f"  Total disbursed: {_fmt_rs(r['total_amount'], 'lakhs')}"
        ),
        "data": r,
    }


def pmkisan_worst_coverage(
    state: str = "TAMIL NADU",
    fin_year: str = "2024-2025",
    limit: int = 5,
) -> dict[str, Any]:
    conn = _common._conn()
    rows = conn.execute(
        """SELECT district,
                  MAX(beneficiaries_registered) as registered,
                  SUM(beneficiaries_paid) as paid,
                  SUM(amount_paid_lakhs) as amount,
                  CASE WHEN MAX(beneficiaries_registered) > 0
                       THEN (SUM(beneficiaries_paid) * 100.0 / MAX(beneficiaries_registered))
                       ELSE 0 END as coverage_pct
           FROM pmkisan_district
           WHERE UPPER(state) = UPPER(?) AND fin_year = ?
                 AND UPPER(district) != 'ALL' AND beneficiaries_registered > 0
           GROUP BY district
           ORDER BY coverage_pct ASC LIMIT ?""",
        (state, fin_year, limit),
    ).fetchall()
    conn.close()

    if not rows:
        return {"answer": f"No PM Kisan data for {state} ({fin_year}).", "data": None}

    lines = [f"Worst {limit} districts by PM Kisan coverage ({state}, FY {fin_year}):"]
    data = []
    for i, row in enumerate(rows, 1):
        r = dict(row)
        lines.append(
            f"  {i}. {r['district']}: {r['coverage_pct']:.0f}% ({r['paid']:,}/{r['registered']:,} beneficiaries)"
        )
        data.append(r)
    return {"answer": "\n".join(lines), "data": data}


# ---------------------------------------------------------------------------
# JJM queries (Jal Jeevan Mission — rural water)
# ---------------------------------------------------------------------------
def jjm_by_district(
    district: str,
    state: str = "TAMIL NADU",
    fin_year: str = "cumulative",
) -> dict[str, Any]:
    conn = _common._conn()
    row = conn.execute(
        """SELECT * FROM jjm_district
        WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?) AND fin_year = ?""",
        (district, state, fin_year),
    ).fetchone()
    conn.close()

    if not row:
        return {"answer": f"No JJM data for {district}, {state} ({fin_year}).", "data": None}

    r = dict(row)
    util_pct = (r["funds_utilized_lakhs"] / r["funds_released_lakhs"] * 100) if r["funds_released_lakhs"] > 0 else 0
    return {
        "answer": (
            f"{r['district']}, {r['state']} — Jal Jeevan Mission ({fin_year}):\n"
            f"  Households: {r['total_households']:,} total | {r['households_with_tap']:,} with tap ({r['coverage_pct']:.0f}%)\n"
            f"  Funds released: {_fmt_rs(r['funds_released_lakhs'], 'lakhs')} | utilized: {_fmt_rs(r['funds_utilized_lakhs'], 'lakhs')} ({util_pct:.0f}%)"
        ),
        "data": r,
        "source_url": r.get("source_url"),
    }


def jjm_state_summary(
    state: str = "TAMIL NADU",
    fin_year: str = "cumulative",
) -> dict[str, Any]:
    conn = _common._conn()
    row = conn.execute(
        """SELECT COUNT(DISTINCT district) as districts,
                  SUM(total_households) as total_hh, SUM(households_with_tap) as tapped,
                  AVG(coverage_pct) as avg_coverage,
                  SUM(funds_released_lakhs) as released, SUM(funds_utilized_lakhs) as utilized
           FROM jjm_district WHERE UPPER(state) = UPPER(?) AND fin_year = ?""",
        (state, fin_year),
    ).fetchone()
    conn.close()

    if not row or row["districts"] == 0:
        return {"answer": f"No JJM data for {state} ({fin_year}).", "data": None}

    r = dict(row)
    overall_coverage = (r["tapped"] / r["total_hh"] * 100) if r["total_hh"] > 0 else 0
    return {
        "answer": (
            f"{state} JJM summary ({fin_year}):\n"
            f"  Districts: {r['districts']}\n"
            f"  Households: {r['total_hh']:,} total | {r['tapped']:,} with tap ({overall_coverage:.0f}%)\n"
            f"  Funds released: {_fmt_rs(r['released'], 'lakhs')} | utilized: {_fmt_rs(r['utilized'], 'lakhs')}"
        ),
        "data": r,
    }


def jjm_worst_coverage(
    state: str = "TAMIL NADU",
    fin_year: str = "cumulative",
    limit: int = 5,
) -> dict[str, Any]:
    conn = _common._conn()
    rows = conn.execute(
        """SELECT district, total_households, households_with_tap, coverage_pct, source_url
           FROM jjm_district
           WHERE UPPER(state) = UPPER(?) AND fin_year = ? AND total_households > 0
           ORDER BY coverage_pct ASC LIMIT ?""",
        (state, fin_year, limit),
    ).fetchall()
    conn.close()

    if not rows:
        return {"answer": f"No JJM data for {state} ({fin_year}).", "data": None}

    lines = [f"Worst {limit} districts by tap water coverage ({state}, JJM):"]
    data = []
    for i, row in enumerate(rows, 1):
        r = dict(row)
        lines.append(
            f"  {i}. {r['district']}: {r['coverage_pct']:.0f}% "
            f"({r['households_with_tap']:,}/{r['total_households']:,} households)"
        )
        data.append(r)
    return {"answer": "\n".join(lines), "data": data}
