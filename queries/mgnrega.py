"""MGNREGA queries: misappropriation, fund utilization, social audit, FTO, district overview."""

from __future__ import annotations

from typing import Any

import queries.common as _common

_fmt_rs = _common._fmt_rs


# ---------------------------------------------------------------------------
# Misappropriation queries
# ---------------------------------------------------------------------------
def misappropriation_by_district(
    district: str, state: str = "TAMIL NADU", fin_year: str = "2024-2025"
) -> dict[str, Any]:
    conn = _common._conn()
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


def misappropriation_state_summary(state: str = "TAMIL NADU", fin_year: str = "2024-2025") -> dict[str, Any]:
    conn = _common._conn()
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
    conn = _common._conn()
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
        lines.append(
            f"  {i}. {r['district']}: {_fmt_rs(r['amount_reported'])} ({r['cases_reported']:,} cases, {r['recovery_rate_pct']:.0f}% recovered)"
        )
        data.append(r)

    return {"answer": "\n".join(lines), "data": data, "source_url": data[0]["source_url"]}


# ---------------------------------------------------------------------------
# Financial queries
# ---------------------------------------------------------------------------
def fund_utilization_by_district(
    district: str, state: str = "TAMIL NADU", fin_year: str = "2024-2025"
) -> dict[str, Any]:
    conn = _common._conn()
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


def fund_utilization_state_summary(state: str = "TAMIL NADU", fin_year: str = "2024-2025") -> dict[str, Any]:
    conn = _common._conn()
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
def social_audit_by_district(district: str, state: str = "TAMIL NADU", fin_year: str = "2024-2025") -> dict[str, Any]:
    conn = _common._conn()
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
def fto_status_by_district(district: str, state: str = "TAMIL NADU", fin_year: str = "2024-2025") -> dict[str, Any]:
    conn = _common._conn()
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


def fto_pendency_summary(state: str = "TAMIL NADU", fin_year: str = "2024-2025") -> dict[str, Any]:
    conn = _common._conn()
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
def district_overview(district: str, state: str = "TAMIL NADU", fin_year: str = "2024-2025") -> dict[str, Any]:
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
        "answer": "\n\n".join(parts),
        "source_urls": [s for s in sources if s],
    }
