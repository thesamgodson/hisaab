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
    conn = _conn()
    rows = conn.execute(
        """SELECT DISTINCT district FROM misappropriation
        WHERE UPPER(state) = UPPER(?) AND fin_year = ? ORDER BY district""",
        (state, fin_year),
    ).fetchall()
    conn.close()
    return [r["district"] for r in rows]


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
