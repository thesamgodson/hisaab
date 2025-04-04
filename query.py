"""
Query layer for multi-scheme government transparency data.

Schemes: MGNREGA, PMGSY, PMAY-G, PM Kisan, JJM, PM POSHAN, NSAP, PDS/NFSA.

Cross-scheme queries use the unified money_flow VIEW.

Each function returns a dict with 'answer' (human-readable), 'data' (raw), and 'source_url'.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parent / "data" / "hisaab.db"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _fmt_rs(amount: float, unit: str = "rupees") -> str:
    """Format rupee amounts in human-readable form.

    unit: 'rupees' for raw rupee amounts, 'lakhs' for amounts already in lakhs.
    """
    if unit == "lakhs":
        # Input is in lakhs, convert to crores if large
        if abs(amount) >= 100:
            return f"Rs {amount / 100:.2f} Cr"
        return f"Rs {amount:.2f} L"
    # Input is in rupees
    if abs(amount) >= 10000000:
        return f"Rs {amount / 10000000:.2f} Cr"
    if abs(amount) >= 100000:
        return f"Rs {amount / 100000:.2f} L"
    return f"Rs {amount:,.0f}"


# ---------------------------------------------------------------------------
# Misappropriation queries
# ---------------------------------------------------------------------------
def misappropriation_by_district(
    district: str, state: str = "TAMIL NADU", fin_year: str = "2024-2025"
) -> dict[str, Any]:
    conn = _conn()
    row = conn.execute(
        """SELECT * FROM misappropriation
        WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?) AND fin_year = ?""",
        (district, state, fin_year),
    ).fetchone()
    conn.close()

    if not row:
        return {"answer": f"No misappropriation data found for {district}, {state} ({fin_year}).", "data": None}

    r = dict(row)
    return {
        "answer": (
            f"{r['district']}, {r['state']} (FY {fin_year}):\n"
            f"  Cases reported: {r['cases_reported']:,}\n"
            f"  Amount reported: {_fmt_rs(r['amount_reported'])}\n"
            f"  Amount recovered: {_fmt_rs(r['amount_recovered'])}\n"
            f"  Recovery rate: {r['recovery_rate_pct']:.1f}%\n"
            f"  Pending recovery: {_fmt_rs(r['amount_to_recover'] - r['amount_recovered'])}"
        ),
        "data": r,
        "source_url": r["source_url"],
    }


def misappropriation_state_summary(
    state: str = "TAMIL NADU", fin_year: str = "2024-2025"
) -> dict[str, Any]:
    conn = _conn()
    row = conn.execute(
        """SELECT COUNT(*) as districts,
                  SUM(cases_reported) as total_cases,
                  SUM(amount_reported) as total_reported,
                  SUM(amount_recovered) as total_recovered,
                  SUM(amount_to_recover) as total_to_recover
           FROM misappropriation
           WHERE UPPER(state) = UPPER(?) AND fin_year = ?""",
        (state, fin_year),
    ).fetchone()
    conn.close()

    if not row or row["districts"] == 0:
        return {"answer": f"No misappropriation data for {state} ({fin_year}).", "data": None}

    r = dict(row)
    recovery_pct = (r["total_recovered"] / r["total_to_recover"] * 100) if r["total_to_recover"] > 0 else 0
    return {
        "answer": (
            f"{state} misappropriation summary (FY {fin_year}):\n"
            f"  Districts: {r['districts']}\n"
            f"  Total cases: {r['total_cases']:,}\n"
            f"  Amount reported: {_fmt_rs(r['total_reported'])}\n"
            f"  Amount recovered: {_fmt_rs(r['total_recovered'])}\n"
            f"  Recovery rate: {recovery_pct:.1f}%"
        ),
        "data": r,
    }


def worst_misappropriation_districts(
    state: str = "TAMIL NADU", fin_year: str = "2024-2025", limit: int = 5
) -> dict[str, Any]:
    conn = _conn()
    rows = conn.execute(
        """SELECT district, cases_reported, amount_reported, recovery_rate_pct, source_url
           FROM misappropriation
           WHERE UPPER(state) = UPPER(?) AND fin_year = ?
           ORDER BY amount_reported DESC LIMIT ?""",
        (state, fin_year, limit),
    ).fetchall()
    conn.close()

    if not rows:
        return {"answer": f"No data for {state} ({fin_year}).", "data": None}

    lines = [f"Top {limit} districts by misappropriation amount ({state}, FY {fin_year}):"]
    data = []
    for i, row in enumerate(rows, 1):
        r = dict(row)
        lines.append(f"  {i}. {r['district']}: {_fmt_rs(r['amount_reported'])} ({r['cases_reported']:,} cases, {r['recovery_rate_pct']:.0f}% recovered)")
        data.append(r)

    return {"answer": "\n".join(lines), "data": data, "source_url": data[0]["source_url"]}


# ---------------------------------------------------------------------------
# Financial queries
# ---------------------------------------------------------------------------
def fund_utilization_by_district(
    district: str, state: str = "TAMIL NADU", fin_year: str = "2024-2025"
) -> dict[str, Any]:
    conn = _conn()
    row = conn.execute(
        """SELECT * FROM financial_statement
        WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?) AND fin_year = ?""",
        (district, state, fin_year),
    ).fetchone()
    conn.close()

    if not row:
        return {"answer": f"No financial data for {district}, {state} ({fin_year}).", "data": None}

    r = dict(row)
    return {
        "answer": (
            f"{r['district']}, {r['state']} (FY {fin_year}) — amounts in Lakhs:\n"
            f"  Total funds available: {_fmt_rs(r['total_availability'], 'lakhs')}\n"
            f"  Cumulative expenditure: {_fmt_rs(r['cumulative_expenditure'], 'lakhs')}\n"
            f"  Utilization: {r['utilization_pct']:.1f}%\n"
            f"  Balance: {_fmt_rs(r['balance'], 'lakhs')}\n"
            f"  Wage expenditure: {_fmt_rs(r['exp_unskilled_wage'], 'lakhs')} (unskilled)"
        ),
        "data": r,
        "source_url": r["source_url"],
    }


def fund_utilization_state_summary(
    state: str = "TAMIL NADU", fin_year: str = "2024-2025"
) -> dict[str, Any]:
    conn = _conn()
    row = conn.execute(
        """SELECT COUNT(*) as districts,
                  SUM(total_availability) as total_funds,
                  SUM(cumulative_expenditure) as total_exp,
                  AVG(utilization_pct) as avg_util,
                  SUM(exp_unskilled_wage) as total_wage
           FROM financial_statement
           WHERE UPPER(state) = UPPER(?) AND fin_year = ?""",
        (state, fin_year),
    ).fetchone()
    conn.close()

    if not row or row["districts"] == 0:
        return {"answer": f"No financial data for {state} ({fin_year}).", "data": None}

    r = dict(row)
    return {
        "answer": (
            f"{state} financial summary (FY {fin_year}) — amounts in Lakhs:\n"
            f"  Districts: {r['districts']}\n"
            f"  Total funds: {_fmt_rs(r['total_funds'], 'lakhs')}\n"
            f"  Total expenditure: {_fmt_rs(r['total_exp'], 'lakhs')}\n"
            f"  Avg utilization: {r['avg_util']:.1f}%\n"
            f"  Wage payments: {_fmt_rs(r['total_wage'], 'lakhs')}"
        ),
        "data": r,
    }


# ---------------------------------------------------------------------------
# Social audit queries
# ---------------------------------------------------------------------------
def social_audit_by_district(
    district: str, state: str = "TAMIL NADU", fin_year: str = "2024-2025"
) -> dict[str, Any]:
    conn = _conn()
    row = conn.execute(
        """SELECT * FROM issues_reported
        WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?) AND fin_year = ?""",
        (district, state, fin_year),
    ).fetchone()
    conn.close()

    if not row:
        return {"answer": f"No social audit data for {district}, {state} ({fin_year}).", "data": None}

    r = dict(row)
    audit_coverage = (r["gps_audited"] / r["total_gps"] * 100) if r["total_gps"] > 0 else 0
    return {
        "answer": (
            f"{r['district']}, {r['state']} social audit (FY {fin_year}):\n"
            f"  GPs audited: {r['gps_audited']}/{r['total_gps']} ({audit_coverage:.0f}%)\n"
            f"  Total issues: {r['total_issues']:,}\n"
            f"  Misappropriation: {r['misappropriation_issues']:,} issues\n"
            f"  Financial deviation: {r['financial_deviation_issues']:,} issues\n"
            f"  Process violations: {r['process_violation_issues']:,} issues\n"
            f"  Grievances: {r['grievances_issues']:,} issues"
        ),
        "data": r,
        "source_url": r["source_url"],
    }


# ---------------------------------------------------------------------------
# FTO queries
# ---------------------------------------------------------------------------
def fto_status_by_district(
    district: str, state: str = "TAMIL NADU", fin_year: str = "2024-2025"
) -> dict[str, Any]:
    conn = _conn()
    row = conn.execute(
        """SELECT * FROM fto_status
        WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?) AND fin_year = ?""",
        (district, state, fin_year),
    ).fetchone()
    conn.close()

    if not row:
        return {"answer": f"No FTO data for {district}, {state} ({fin_year}).", "data": None}

    r = dict(row)
    return {
        "answer": (
            f"{r['district']}, {r['state']} FTO status (FY {fin_year}):\n"
            f"  Total FTOs generated: {r['total_fto_generated']:,}\n"
            f"  1st signatory: {r['first_signatory_signed']:,} signed, {r['first_signatory_pending']:,} pending\n"
            f"  2nd signatory: {r['second_signatory_signed']:,} signed, {r['second_signatory_pending']:,} pending\n"
            f"  Sent to bank: {r['fto_sent_to_bank']:,}\n"
            f"  Processed by bank: {r['fto_processed_by_bank']:,}"
        ),
        "data": r,
        "source_url": r["source_url"],
    }


def fto_pendency_summary(
    state: str = "TAMIL NADU", fin_year: str = "2024-2025"
) -> dict[str, Any]:
    conn = _conn()
    row = conn.execute(
        """SELECT * FROM fto_pendency
        WHERE UPPER(state) = UPPER(?) AND fin_year = ? AND bank_name = 'Grand Total'""",
        (state, fin_year),
    ).fetchone()
    conn.close()

    if not row:
        return {"answer": f"No FTO pendency data for {state} ({fin_year}).", "data": None}

    r = dict(row)
    if r["total_pending"] == 0:
        answer = f"{state} FTO pendency (FY {fin_year}): No pending FTOs. All payments processed."
    else:
        answer = (
            f"{state} FTO pendency (FY {fin_year}):\n"
            f"  1-7 days: {r['pending_1_7_days']:,}\n"
            f"  8-15 days: {r['pending_8_15_days']:,}\n"
            f"  16-30 days: {r['pending_16_30_days']:,}\n"
            f"  >30 days: {r['pending_over_30_days']:,}\n"
            f"  Total pending: {r['total_pending']:,}"
        )
    return {"answer": answer, "data": r, "source_url": r["source_url"]}


# ---------------------------------------------------------------------------
# District overview (combines all reports)
# ---------------------------------------------------------------------------
def district_overview(
    district: str, state: str = "TAMIL NADU", fin_year: str = "2024-2025"
) -> dict[str, Any]:
    parts = []
    sources = []

    mis = misappropriation_by_district(district, state, fin_year)
    if mis["data"]:
        parts.append(mis["answer"])
        sources.append(mis.get("source_url", ""))

    fin = fund_utilization_by_district(district, state, fin_year)
    if fin["data"]:
        parts.append(fin["answer"])
        sources.append(fin.get("source_url", ""))

    audit = social_audit_by_district(district, state, fin_year)
    if audit["data"]:
        parts.append(audit["answer"])
        sources.append(audit.get("source_url", ""))

    fto = fto_status_by_district(district, state, fin_year)
    if fto["data"]:
        parts.append(fto["answer"])
        sources.append(fto.get("source_url", ""))

    if not parts:
        return {"answer": f"No data found for {district}, {state} ({fin_year}).", "data": None}

    return {
        "answer": f"\n\n".join(parts),
        "source_urls": [s for s in sources if s],
    }


# ---------------------------------------------------------------------------
# List available districts
# ---------------------------------------------------------------------------
def list_districts(state: str = "TAMIL NADU", fin_year: str = "2024-2025") -> list[str]:
    """List districts with data across any of the 8 scheme tables."""
    conn = _conn()
    tables_with_fy = [
        "misappropriation", "financial_statement", "fto_status",
        "pmayg_district", "pmkisan_district", "jjm_district",
        "pmposhan_district", "nsap_district", "nfsa_district",
    ]
    tables_without_fy = ["pmgsy_district"]

    districts: set[str] = set()
    for table in tables_with_fy:
        try:
            rows = conn.execute(
                f"SELECT DISTINCT district FROM {table} WHERE UPPER(state) = UPPER(?) AND fin_year = ?",
                (state, fin_year),
            ).fetchall()
            districts.update(r["district"] for r in rows)
        except Exception:
            pass
    for table in tables_without_fy:
        try:
            rows = conn.execute(
                f"SELECT DISTINCT district FROM {table} WHERE UPPER(state) = UPPER(?)",
                (state,),
            ).fetchall()
            districts.update(r["district"] for r in rows)
        except Exception:
            pass
    conn.close()
    return sorted(districts)


# ---------------------------------------------------------------------------
# PMGSY queries
# ---------------------------------------------------------------------------
def pmgsy_district_summary(
    district: str, state: str = "TAMIL NADU",
) -> dict[str, Any]:
    conn = _conn()
    rows = conn.execute(
        """SELECT * FROM pmgsy_district
        WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?)
        ORDER BY fin_year DESC""",
        (district, state),
    ).fetchall()
    conn.close()

    if not rows:
        return {"answer": f"No PMGSY data found for {district}, {state}.", "data": None}

    data = [dict(r) for r in rows]
    total_sanctioned = sum(r.get("roads_sanctioned", 0) for r in data)
    total_completed = sum(r.get("roads_completed", 0) for r in data)
    total_length_s = sum(r.get("length_sanctioned_km", 0) for r in data)
    total_length_c = sum(r.get("length_completed_km", 0) for r in data)
    total_expenditure = sum(r.get("expenditure_cr", 0) for r in data)
    completion_rate = (total_completed / total_sanctioned * 100) if total_sanctioned > 0 else 0
    cost_per_km = (total_expenditure / total_length_c) if total_length_c > 0 else 0

    return {
        "answer": (
            f"{district}, {state} — PMGSY Rural Roads:\n"
            f"  Roads sanctioned: {total_sanctioned:,} | completed: {total_completed:,} ({completion_rate:.0f}%)\n"
            f"  Length sanctioned: {total_length_s:,.1f} km | completed: {total_length_c:,.1f} km\n"
            f"  Total expenditure: {_fmt_rs(total_expenditure * 10000000)}\n"
            f"  Cost per km: {_fmt_rs(cost_per_km * 10000000)}"
        ),
        "data": data,
        "source_url": data[0].get("source_url"),
    }


def pmgsy_state_summary(
    state: str = "TAMIL NADU",
) -> dict[str, Any]:
    conn = _conn()
    row = conn.execute(
        """SELECT COUNT(DISTINCT district) as districts,
                  SUM(roads_sanctioned) as total_sanctioned,
                  SUM(roads_completed) as total_completed,
                  SUM(length_sanctioned_km) as total_length_s,
                  SUM(length_completed_km) as total_length_c,
                  SUM(expenditure_cr) as total_expenditure
           FROM pmgsy_district
           WHERE UPPER(state) = UPPER(?)""",
        (state,),
    ).fetchone()
    conn.close()

    if not row or row["districts"] == 0:
        return {"answer": f"No PMGSY data for {state}.", "data": None}

    r = dict(row)
    completion_rate = (r["total_completed"] / r["total_sanctioned"] * 100) if r["total_sanctioned"] > 0 else 0

    return {
        "answer": (
            f"{state} PMGSY summary:\n"
            f"  Districts: {r['districts']}\n"
            f"  Roads sanctioned: {r['total_sanctioned']:,} | completed: {r['total_completed']:,} ({completion_rate:.0f}%)\n"
            f"  Length: {r['total_length_s']:,.1f} km sanctioned | {r['total_length_c']:,.1f} km completed\n"
            f"  Total expenditure: {_fmt_rs(r['total_expenditure'] * 10000000)}"
        ),
        "data": r,
    }


def pmgsy_worst_completion(
    state: str = "TAMIL NADU", limit: int = 5,
) -> dict[str, Any]:
    conn = _conn()
    rows = conn.execute(
        """SELECT district,
                  SUM(roads_sanctioned) as sanctioned,
                  SUM(roads_completed) as completed,
                  SUM(length_sanctioned_km) as len_s,
                  SUM(length_completed_km) as len_c,
                  SUM(expenditure_cr) as exp,
                  CASE WHEN SUM(roads_sanctioned) > 0
                       THEN (SUM(roads_completed) * 100.0 / SUM(roads_sanctioned))
                       ELSE 0 END as completion_pct
           FROM pmgsy_district
           WHERE UPPER(state) = UPPER(?) AND roads_sanctioned > 0
           GROUP BY district
           ORDER BY completion_pct ASC LIMIT ?""",
        (state, limit),
    ).fetchall()
    conn.close()

    if not rows:
        return {"answer": f"No PMGSY data for {state}.", "data": None}

    lines = [f"Worst {limit} districts by road completion rate ({state}, PMGSY):"]
    data = []
    for i, row in enumerate(rows, 1):
        r = dict(row)
        lines.append(
            f"  {i}. {r['district']}: {r['completion_pct']:.0f}% "
            f"({r['completed']:,}/{r['sanctioned']:,} roads, "
            f"{r['len_c']:,.1f}/{r['len_s']:,.1f} km)"
        )
        data.append(r)

    return {"answer": "\n".join(lines), "data": data}


# ---------------------------------------------------------------------------
# PMAY-G queries (rural housing)
# ---------------------------------------------------------------------------
def pmayg_by_district(
    district: str, state: str = "TAMIL NADU", fin_year: str = "2024-2025",
) -> dict[str, Any]:
    conn = _conn()
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
    state: str = "TAMIL NADU", fin_year: str = "2024-2025",
) -> dict[str, Any]:
    conn = _conn()
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
    state: str = "TAMIL NADU", fin_year: str = "2024-2025", limit: int = 5,
) -> dict[str, Any]:
    conn = _conn()
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
    district: str, state: str = "TAMIL NADU", fin_year: str = "2024-2025",
) -> dict[str, Any]:
    conn = _conn()
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
    state: str = "TAMIL NADU", fin_year: str = "2024-2025",
) -> dict[str, Any]:
    conn = _conn()
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
    state: str = "TAMIL NADU", fin_year: str = "2024-2025", limit: int = 5,
) -> dict[str, Any]:
    conn = _conn()
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
            f"  {i}. {r['district']}: {r['coverage_pct']:.0f}% "
            f"({r['paid']:,}/{r['registered']:,} beneficiaries)"
        )
        data.append(r)
    return {"answer": "\n".join(lines), "data": data}


# ---------------------------------------------------------------------------
# JJM queries (Jal Jeevan Mission — rural water)
# ---------------------------------------------------------------------------
def jjm_by_district(
    district: str, state: str = "TAMIL NADU", fin_year: str = "cumulative",
) -> dict[str, Any]:
    conn = _conn()
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
    state: str = "TAMIL NADU", fin_year: str = "cumulative",
) -> dict[str, Any]:
    conn = _conn()
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
    state: str = "TAMIL NADU", fin_year: str = "cumulative", limit: int = 5,
) -> dict[str, Any]:
    conn = _conn()
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


# ---------------------------------------------------------------------------
# PM POSHAN queries (school nutrition)
# ---------------------------------------------------------------------------
def pmposhan_by_district(
    district: str, state: str = "TAMIL NADU", fin_year: str = "2024-2025",
) -> dict[str, Any]:
    conn = _conn()
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
    state: str = "TAMIL NADU", fin_year: str = "2024-2025",
) -> dict[str, Any]:
    conn = _conn()
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
    state: str = "TAMIL NADU", fin_year: str = "2024-2025", limit: int = 5,
) -> dict[str, Any]:
    conn = _conn()
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
    district: str, state: str = "TAMIL NADU", fin_year: str = "2024-2025",
) -> dict[str, Any]:
    conn = _conn()
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
    state: str = "TAMIL NADU", fin_year: str = "2024-2025",
) -> dict[str, Any]:
    conn = _conn()
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
    state: str = "TAMIL NADU", fin_year: str = "2024-2025", limit: int = 5,
) -> dict[str, Any]:
    conn = _conn()
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
        lines.append(
            f"  {i}. {r['district']}: {r['coverage_pct']:.0f}% "
            f"({r['paid']:,}/{r['eligible']:,} pensioners)"
        )
        data.append(r)
    return {"answer": "\n".join(lines), "data": data}


# ---------------------------------------------------------------------------
# NFSA queries (PDS / ration system)
# ---------------------------------------------------------------------------
def nfsa_by_district(
    district: str, state: str = "TAMIL NADU", fin_year: str = "2024-2025",
) -> dict[str, Any]:
    conn = _conn()
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
    state: str = "TAMIL NADU", fin_year: str = "2024-2025",
) -> dict[str, Any]:
    conn = _conn()
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
    state: str = "TAMIL NADU", fin_year: str = "2024-2025", limit: int = 5,
) -> dict[str, Any]:
    conn = _conn()
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


# ---------------------------------------------------------------------------
# Data quality warnings
# ---------------------------------------------------------------------------
def data_quality_warnings() -> dict[str, list[str]]:
    """Return known data quality issues per scheme.

    Updated 2026-03: Investigated scraper sources and government portals.
    Financial data for PMAY-G, JJM, and PM POSHAN is NOT publicly accessible
    via API — portals require login or use Power BI embeds.
    """
    return {
        "PM Kisan": [
            "28 of 36 states have only state-level aggregate records (district='ALL'), not district-level data.",
            "No allocation data — PM Kisan is a direct benefit transfer with no state-level allocation.",
        ],
        "NSAP": [
            "amount_paid_lakhs, beneficiaries_eligible, and pension_per_month are all zeros — data.gov.in API only has beneficiary counts.",
            "Only beneficiaries_paid has meaningful data. Coverage percentages cannot be computed.",
            "API scraper (scrape_nsap_api.py) fetches IGNOAPS/IGNWPS/IGNDPS from data.gov.in automatically.",
            "State-level funds released data exists on data.gov.in (dataset ebb775b3) but no district breakdown.",
        ],
        "PDS/NFSA": [
            "allocation_mt and offtake_mt are ALL zeros — nfsa.gov.in dashboard data is stale (Jul 2021).",
            "Ration card counts (total, active, AAY, PHH) and beneficiary counts are populated.",
            "data.gov.in has state-level allocation/offtake only (dataset 84bb8521), no district breakdown.",
            "Do not compare NFSA MT columns with other schemes' rupee columns.",
        ],
        "PM POSHAN": [
            "funds_released_lakhs and funds_utilized_lakhs are ALL zeros — portal does not expose financial data.",
            "Rely on children_fed vs children_enrolled for meaningful delivery metrics.",
            "Excluded from scheme_finance VIEW to prevent misleading zero aggregations.",
        ],
        "PMAY-G": [
            "funds_released_lakhs and funds_utilized_lakhs are ALL zeros — financial report is behind login/Power BI.",
            "PhysicalProgressRpt.aspx only has housing counts; FinancialProgressRpt.aspx returns 404.",
            "Excluded from scheme_finance VIEW. Use houses_sanctioned/completed for delivery metrics.",
        ],
        "JJM": [
            "funds_released_lakhs and funds_utilized_lakhs are ALL zeros — ejalshakti.gov.in API has no financial endpoint.",
            "Tested Param values 1-34 and alternate endpoints (JJMFinancialView, etc.) — all return 401 or same schema.",
            "Excluded from scheme_finance VIEW. Use coverage_pct for delivery metrics.",
        ],
        "MGNREGA": [
            "Financial amounts are in lakhs (amounts_in_lakhs=1 in financial_statement).",
        ],
        "PMGSY": [
            "Amounts are in crores. Converted to lakhs (*100) in VIEWs.",
        ],
    }


# ---------------------------------------------------------------------------
# Cross-scheme queries (money_flow VIEW)
# ---------------------------------------------------------------------------
def money_flow_by_district(
    district: str, state: str | None = None,
) -> dict[str, Any]:
    """Total money flow across all schemes for a district."""
    conn = _conn()
    if state:
        rows = conn.execute(
            """SELECT scheme, fin_year,
                      COALESCE(allocated_lakhs, 0) as allocated,
                      COALESCE(released_lakhs, 0) as released,
                      COALESCE(expended_lakhs, 0) as expended,
                      utilization_pct,
                      units_target, units_completed, units_label
               FROM money_flow
               WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?)
               ORDER BY scheme, fin_year""",
            (district, state),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT scheme, fin_year,
                      COALESCE(allocated_lakhs, 0) as allocated,
                      COALESCE(released_lakhs, 0) as released,
                      COALESCE(expended_lakhs, 0) as expended,
                      utilization_pct,
                      units_target, units_completed, units_label
               FROM money_flow
               WHERE UPPER(district) = UPPER(?)
               ORDER BY scheme, fin_year""",
            (district,),
        ).fetchall()
    conn.close()

    if not rows:
        return {"answer": f"No data found for {district} across any scheme.", "data": None}

    data = [dict(r) for r in rows]
    total_expended = sum(r["expended"] for r in data)
    schemes_present = sorted(set(r["scheme"] for r in data))

    lines = [f"{district} — Money flow across {len(schemes_present)} schemes:"]
    for scheme in schemes_present:
        scheme_rows = [r for r in data if r["scheme"] == scheme]
        exp = sum(r["expended"] for r in scheme_rows)
        lines.append(f"  {scheme}: {_fmt_rs(exp, 'lakhs')}")
        if scheme_rows[0]["units_label"] and scheme_rows[0]["units_target"]:
            target = sum(r["units_target"] or 0 for r in scheme_rows)
            done = sum(r["units_completed"] or 0 for r in scheme_rows)
            lines.append(f"    {scheme_rows[0]['units_label']}: {done:,}/{target:,}")

    lines.append(f"  TOTAL: {_fmt_rs(total_expended, 'lakhs')}")

    return {"answer": "\n".join(lines), "data": data}


def money_flow_state_summary(
    state: str = "TAMIL NADU",
) -> dict[str, Any]:
    """Aggregated money flow across all schemes for a state."""
    conn = _conn()
    rows = conn.execute(
        """SELECT scheme,
                  COUNT(DISTINCT district) as districts,
                  SUM(COALESCE(expended_lakhs, 0)) as total_expended,
                  AVG(utilization_pct) as avg_util
           FROM money_flow
           WHERE UPPER(state) = UPPER(?)
           GROUP BY scheme
           ORDER BY total_expended DESC""",
        (state,),
    ).fetchall()
    conn.close()

    if not rows:
        return {"answer": f"No data found for {state} across any scheme.", "data": None}

    data = [dict(r) for r in rows]
    total = sum(r["total_expended"] for r in data)

    lines = [f"{state} — Money flow across all schemes:"]
    for r in data:
        util_str = f", {r['avg_util']:.0f}% util" if r["avg_util"] else ""
        lines.append(f"  {r['scheme']}: {_fmt_rs(r['total_expended'], 'lakhs')} ({r['districts']} districts{util_str})")
    lines.append(f"  TOTAL: {_fmt_rs(total, 'lakhs')}")

    return {"answer": "\n".join(lines), "data": data}


def schemes_in_district(district: str) -> dict[str, Any]:
    """List which schemes have data for a district."""
    conn = _conn()
    rows = conn.execute(
        """SELECT DISTINCT scheme FROM money_flow
           WHERE UPPER(district) = UPPER(?)
           ORDER BY scheme""",
        (district,),
    ).fetchall()
    conn.close()

    schemes = [r["scheme"] for r in rows]
    if not schemes:
        return {"answer": f"No scheme data found for {district}.", "data": []}
    return {
        "answer": f"{district} has data for: {', '.join(schemes)}",
        "data": schemes,
    }


if __name__ == "__main__":
    print("Available districts:", list_districts())
    print()

    # Demo queries
    print("=" * 60)
    print(misappropriation_state_summary()["answer"])
    print()
    print(worst_misappropriation_districts()["answer"])
    print()
    print(fund_utilization_state_summary()["answer"])
    print()
    print(fto_pendency_summary()["answer"])
    print()
    print("=" * 60)
    print("\nDistrict deep dive: VILLUPURAM")
    print(district_overview("VILLUPURAM")["answer"])
