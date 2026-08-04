"""Shared utilities for the query layer."""

from __future__ import annotations

import sqlite3

from db import DB_PATH


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


def list_districts(state: str = "TAMIL NADU", fin_year: str = "2024-2025") -> list[str]:
    """List districts with data across any of the 8 scheme tables."""
    conn = _conn()
    tables_with_fy = [
        "misappropriation",
        "financial_statement",
        "fto_status",
        "pmayg_district",
        "pmkisan_district",
        "jjm_district",
        "pmposhan_district",
        "nsap_district",
        "nfsa_district",
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


def data_quality_warnings() -> dict[str, list[str]]:
    """Return known data quality issues per scheme.

    Mirrors web/src/lib/data-quality.ts — update both together. Every caveat
    also appears in DATA_CLAIMS.md with source and date.

    Updated 2026-08-04: degenerate metrics no longer published as percentages
    (PM POSHAN daily-fed, NFSA active=total); SBM-G / DAY-NRLM / UDISE+ added.
    """
    return {
        "MGNREGA": [
            "Financial amounts are in lakhs (amounts_in_lakhs=1 in financial_statement).",
        ],
        "PMGSY": [
            "Amounts are in crores. Converted to lakhs (*100) in VIEWs.",
        ],
        "PMAY-G": [
            "STATE-LEVEL: Allocation + release + utilization from data.gov.in (2019-2026, pmayg_finance). ~45% of rows have release=0 (allocation present).",
            "DISTRICT-LEVEL: funds_released/utilized remain zero — FinancialProgressRpt.aspx requires login.",
            "Delivery metrics (houses_sanctioned/completed) available at district level.",
        ],
        "PM Kisan": [
            "28 of 36 states have only state-level aggregate records (district='ALL'), not district-level data.",
            "No allocation data — PM Kisan is a direct benefit transfer with no state-level allocation.",
        ],
        "JJM": [
            "STATE-LEVEL: Allocation/release/expenditure from ejalshakti.gov.in (2019-2025, jjm_allocation).",
            "DISTRICT-LEVEL: funds_released/utilized remain zero — API has no financial endpoint.",
            "Delivery metrics (coverage_pct, households_with_tap) available at district level.",
        ],
        "PM POSHAN": [
            "STATE-LEVEL: Real allocation + release + utilization from data.gov.in (2016-2025, pmposhan_finance).",
            "DISTRICT-LEVEL: funds_released/utilized remain zero — portal does not expose district financial data.",
            "children_fed is a DAILY reporting snapshot (CLAIM-2026-0006) — no feeding percentage is published because fed/enrolled is not a delivery rate.",
        ],
        "NSAP": [
            "STATE-LEVEL: Fund release data from data.gov.in (2019-2024, nsap_finance table). ~22% of state×year rows have zero release.",
            "DISTRICT-LEVEL: amount_paid_lakhs is IMPUTED: beneficiaries_paid x GoI pension rate x 12.",
            "Central rates: IGNOAPS Rs 200/mo, IGNWPS Rs 300/mo, IGNDPS Rs 300/mo (central share only).",
            "beneficiaries_eligible is zero for all rows — no coverage percentage or shortfall ranking is published.",
        ],
        "PDS/NFSA": [
            "STATE-LEVEL: Real allocation + offtake in METRIC TONNES from data.gov.in (2019-2023, nfsa_allocation).",
            "DISTRICT-LEVEL: allocation_mt and offtake_mt are zeros — no district breakdown from data.gov.in.",
            "Ration card counts equal 'active' by construction in the source (CLAIM-2026-0008) — no active-percentage is published. Underlying dashboard data is 2021-vintage.",
            "NFSA tracks metric tonnes, not rupees — never compared with other schemes' lakhs columns.",
        ],
        "SBM-G": [
            "Delivery metrics only (ODF Plus villages, star ratings) — SBM-G publishes no district-level financial data.",
        ],
        "DAY-NRLM": [
            "SHG counts at district level; revolving-fund disbursement column present but zero in the current scrape.",
        ],
        "UDISE+": [
            "State-level education indicators only (schools, enrollment, PTR, infrastructure) — no district breakdown, no financial data.",
        ],
    }
