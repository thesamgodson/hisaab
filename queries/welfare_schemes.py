"""Queries for PM POSHAN, NSAP, and PDS/NFSA."""

from __future__ import annotations

from typing import Any

import queries.common as _common

_fmt_rs = _common._fmt_rs


# ---------------------------------------------------------------------------
# PM POSHAN queries (school nutrition)
# ---------------------------------------------------------------------------
def pmposhan_by_district(
    district: str,
    state: str = "TAMIL NADU",
    fin_year: str = "2024-2025",
) -> dict[str, Any]:
    conn = _common._conn()
    row = conn.execute(
        """SELECT * FROM pmposhan_district
        WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?) AND fin_year = ?""",
        (district, state, fin_year),
    ).fetchone()
    conn.close()

    if not row:
        return {"answer": f"No PM POSHAN data for {district}, {state} ({fin_year}).", "data": None}

    r = dict(row)
    feeding_pct = (r["children_fed"] / r["children_enrolled"] * 100) if r["children_enrolled"] > 0 else 0
    return {
        "answer": (
            f"{r['district']}, {r['state']} — PM POSHAN (FY {fin_year}):\n"
            f"  Schools covered: {r['schools_covered']:,}\n"
            f"  Children enrolled: {r['children_enrolled']:,} | fed: {r['children_fed']:,} ({feeding_pct:.0f}%)\n"
            f"  Funds released: {_fmt_rs(r['funds_released_lakhs'], 'lakhs')} | utilized: {_fmt_rs(r['funds_utilized_lakhs'], 'lakhs')} ({r['utilization_pct']:.0f}%)"
        ),
        "data": r,
        "source_url": r.get("source_url"),
    }


def pmposhan_state_summary(
    state: str = "TAMIL NADU",
    fin_year: str = "2024-2025",
) -> dict[str, Any]:
    conn = _common._conn()
    row = conn.execute(
        """SELECT COUNT(DISTINCT district) as districts,
                  SUM(schools_covered) as schools, SUM(children_enrolled) as enrolled,
                  SUM(children_fed) as fed,
                  SUM(funds_released_lakhs) as released, SUM(funds_utilized_lakhs) as utilized,
                  AVG(utilization_pct) as avg_util
           FROM pmposhan_district WHERE UPPER(state) = UPPER(?) AND fin_year = ?""",
        (state, fin_year),
    ).fetchone()
    conn.close()

    if not row or row["districts"] == 0:
        return {"answer": f"No PM POSHAN data for {state} ({fin_year}).", "data": None}

    r = dict(row)
    feeding_pct = (r["fed"] / r["enrolled"] * 100) if r["enrolled"] > 0 else 0
    return {
        "answer": (
            f"{state} PM POSHAN summary (FY {fin_year}):\n"
            f"  Districts: {r['districts']} | Schools: {r['schools']:,}\n"
            f"  Children enrolled: {r['enrolled']:,} | fed: {r['fed']:,} ({feeding_pct:.0f}%)\n"
            f"  Funds released: {_fmt_rs(r['released'], 'lakhs')} | utilized: {_fmt_rs(r['utilized'], 'lakhs')}"
        ),
        "data": r,
    }


def pmposhan_worst_feeding(
    state: str = "TAMIL NADU",
    fin_year: str = "2024-2025",
    limit: int = 5,
) -> dict[str, Any]:
    conn = _common._conn()
    rows = conn.execute(
        """SELECT district, children_enrolled, children_fed,
                  CASE WHEN children_enrolled > 0
                       THEN (children_fed * 100.0 / children_enrolled)
                       ELSE 0 END as feeding_pct,
                  source_url
           FROM pmposhan_district
           WHERE UPPER(state) = UPPER(?) AND fin_year = ? AND children_enrolled > 0
           ORDER BY feeding_pct ASC LIMIT ?""",
        (state, fin_year, limit),
    ).fetchall()
    conn.close()

    if not rows:
        return {"answer": f"No PM POSHAN data for {state} ({fin_year}).", "data": None}

    lines = [f"Worst {limit} districts by meal coverage ({state}, PM POSHAN, FY {fin_year}):"]
    data = []
    for i, row in enumerate(rows, 1):
        r = dict(row)
        lines.append(
            f"  {i}. {r['district']}: {r['feeding_pct']:.0f}% "
            f"({r['children_fed']:,}/{r['children_enrolled']:,} children)"
        )
        data.append(r)
    return {"answer": "\n".join(lines), "data": data}


# ---------------------------------------------------------------------------
# NSAP queries (pensions)
# ---------------------------------------------------------------------------
def nsap_by_district(
    district: str,
    state: str = "TAMIL NADU",
    fin_year: str = "2024-2025",
) -> dict[str, Any]:
    conn = _common._conn()
    rows = conn.execute(
        """SELECT * FROM nsap_district
        WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?) AND fin_year = ?
        ORDER BY scheme_type""",
        (district, state, fin_year),
    ).fetchall()
    conn.close()

    if not rows:
        return {"answer": f"No NSAP data for {district}, {state} ({fin_year}).", "data": None}

    data = [dict(r) for r in rows]
    total_paid = sum(r["beneficiaries_paid"] for r in data)
    total_eligible = sum(r["beneficiaries_eligible"] for r in data)
    total_amount = sum(r["amount_paid_lakhs"] for r in data)

    lines = [f"{district}, {state} — NSAP Pensions (FY {fin_year}):"]
    lines.append(f"  Total beneficiaries paid: {total_paid:,}")
    if total_eligible > 0:
        lines.append(f"  Eligible: {total_eligible:,} ({total_paid / total_eligible * 100:.0f}% coverage)")
    lines.append(f"  Amount paid: {_fmt_rs(total_amount, 'lakhs')}")
    for r in data:
        if r["scheme_type"]:
            lines.append(f"    {r['scheme_type']}: {r['beneficiaries_paid']:,} paid")

    return {
        "answer": "\n".join(lines),
        "data": data,
        "source_url": data[0].get("source_url"),
    }


def nsap_state_summary(
    state: str = "TAMIL NADU",
    fin_year: str = "2024-2025",
) -> dict[str, Any]:
    conn = _common._conn()
    row = conn.execute(
        """SELECT COUNT(DISTINCT district) as districts,
                  SUM(beneficiaries_paid) as total_paid,
                  SUM(beneficiaries_eligible) as total_eligible,
                  SUM(amount_paid_lakhs) as total_amount
           FROM nsap_district WHERE UPPER(state) = UPPER(?) AND fin_year = ?""",
        (state, fin_year),
    ).fetchone()
    conn.close()

    if not row or row["districts"] == 0:
        return {"answer": f"No NSAP data for {state} ({fin_year}).", "data": None}

    r = dict(row)
    coverage = (r["total_paid"] / r["total_eligible"] * 100) if r["total_eligible"] > 0 else 0
    return {
        "answer": (
            f"{state} NSAP summary (FY {fin_year}):\n"
            f"  Districts: {r['districts']}\n"
            f"  Beneficiaries paid: {r['total_paid']:,}"
            + (f" ({coverage:.0f}% of {r['total_eligible']:,} eligible)" if r["total_eligible"] > 0 else "")
            + f"\n  Amount paid: {_fmt_rs(r['total_amount'], 'lakhs')}"
        ),
        "data": r,
    }


def nsap_worst_coverage(
    state: str = "TAMIL NADU",
    fin_year: str = "2024-2025",
    limit: int = 5,
) -> dict[str, Any]:
    conn = _common._conn()
    rows = conn.execute(
        """SELECT district,
                  SUM(beneficiaries_eligible) as eligible,
                  SUM(beneficiaries_paid) as paid,
                  CASE WHEN SUM(beneficiaries_eligible) > 0
                       THEN (SUM(beneficiaries_paid) * 100.0 / SUM(beneficiaries_eligible))
                       ELSE 0 END as coverage_pct
           FROM nsap_district
           WHERE UPPER(state) = UPPER(?) AND fin_year = ? AND beneficiaries_eligible > 0
           GROUP BY district
           ORDER BY coverage_pct ASC LIMIT ?""",
        (state, fin_year, limit),
    ).fetchall()
    conn.close()

    if not rows:
        return {"answer": f"No NSAP data for {state} ({fin_year}).", "data": None}

    lines = [f"Worst {limit} districts by pension coverage ({state}, NSAP, FY {fin_year}):"]
    data = []
    for i, row in enumerate(rows, 1):
        r = dict(row)
        lines.append(f"  {i}. {r['district']}: {r['coverage_pct']:.0f}% ({r['paid']:,}/{r['eligible']:,} pensioners)")
        data.append(r)
    return {"answer": "\n".join(lines), "data": data}


# ---------------------------------------------------------------------------
# NFSA queries (PDS / ration system)
# ---------------------------------------------------------------------------
def nfsa_by_district(
    district: str,
    state: str = "TAMIL NADU",
    fin_year: str = "2024-2025",
) -> dict[str, Any]:
    conn = _common._conn()
    row = conn.execute(
        """SELECT * FROM nfsa_district
        WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?) AND fin_year = ?""",
        (district, state, fin_year),
    ).fetchone()
    conn.close()

    if not row:
        return {"answer": f"No NFSA data for {district}, {state} ({fin_year}).", "data": None}

    r = dict(row)
    active_pct = (r["ration_cards_active"] / r["ration_cards_total"] * 100) if r["ration_cards_total"] > 0 else 0
    return {
        "answer": (
            f"{r['district']}, {r['state']} — PDS/NFSA (FY {fin_year}):\n"
            f"  Ration cards: {r['ration_cards_active']:,} active / {r['ration_cards_total']:,} total ({active_pct:.0f}%)\n"
            f"  Allocation: {r['allocation_mt']:,.1f} MT | Offtake: {r['offtake_mt']:,.1f} MT ({r['offtake_pct']:.0f}%)\n"
            f"  Beneficiaries: {r['beneficiaries_total']:,}"
        ),
        "data": r,
        "source_url": r.get("source_url"),
    }


def nfsa_state_summary(
    state: str = "TAMIL NADU",
    fin_year: str = "2024-2025",
) -> dict[str, Any]:
    conn = _common._conn()
    row = conn.execute(
        """SELECT COUNT(DISTINCT district) as districts,
                  SUM(ration_cards_total) as total_cards, SUM(ration_cards_active) as active_cards,
                  SUM(allocation_mt) as allocation, SUM(offtake_mt) as offtake,
                  SUM(beneficiaries_total) as beneficiaries
           FROM nfsa_district WHERE UPPER(state) = UPPER(?) AND fin_year = ?""",
        (state, fin_year),
    ).fetchone()
    conn.close()

    if not row or row["districts"] == 0:
        return {"answer": f"No NFSA data for {state} ({fin_year}).", "data": None}

    r = dict(row)
    offtake_pct = (r["offtake"] / r["allocation"] * 100) if r["allocation"] > 0 else 0
    return {
        "answer": (
            f"{state} PDS/NFSA summary (FY {fin_year}):\n"
            f"  Districts: {r['districts']}\n"
            f"  Ration cards: {r['active_cards']:,} active / {r['total_cards']:,} total\n"
            f"  Allocation: {r['allocation']:,.1f} MT | Offtake: {r['offtake']:,.1f} MT ({offtake_pct:.0f}%)\n"
            f"  Total beneficiaries: {r['beneficiaries']:,}"
        ),
        "data": r,
    }


def nfsa_worst_coverage(
    state: str = "TAMIL NADU",
    fin_year: str = "2024-2025",
    limit: int = 5,
) -> dict[str, Any]:
    conn = _common._conn()
    rows = conn.execute(
        """SELECT district, ration_cards_total, ration_cards_active,
                  offtake_pct, source_url
           FROM nfsa_district
           WHERE UPPER(state) = UPPER(?) AND fin_year = ? AND ration_cards_total > 0
           ORDER BY offtake_pct ASC LIMIT ?""",
        (state, fin_year, limit),
    ).fetchall()
    conn.close()

    if not rows:
        return {"answer": f"No NFSA data for {state} ({fin_year}).", "data": None}

    lines = [f"Worst {limit} districts by ration offtake ({state}, NFSA, FY {fin_year}):"]
    data = []
    for i, row in enumerate(rows, 1):
        r = dict(row)
        lines.append(
            f"  {i}. {r['district']}: {r['offtake_pct']:.0f}% offtake "
            f"({r['ration_cards_active']:,}/{r['ration_cards_total']:,} active cards)"
        )
        data.append(r)
    return {"answer": "\n".join(lines), "data": data}
