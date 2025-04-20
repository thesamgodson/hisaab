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

    Updated 2026-03-21: Phase 6 added real financial data for 5 previously-hollow schemes
    via data.gov.in API and MoRD dashboard. State-level financial data now available for
    PM POSHAN, NSAP, PMAY-G, JJM, and NFSA. District-level financial columns remain zero.
    """
    return {
        "PM Kisan": [
            "28 of 36 states have only state-level aggregate records (district='ALL'), not district-level data.",
            "No allocation data — PM Kisan is a direct benefit transfer with no state-level allocation.",
        ],
        "NSAP": [
            "STATE-LEVEL: Fund release data from data.gov.in (2019-2024, nsap_finance table). ~22% of state×year rows have zero release.",
            "DISTRICT-LEVEL: amount_paid_lakhs is IMPUTED: beneficiaries_paid x GoI pension rate x 12.",
            "Central rates: IGNOAPS Rs 200/mo, IGNWPS Rs 300/mo, IGNDPS Rs 300/mo (central share only).",
            "beneficiaries_eligible is still zero — data.gov.in API does not provide eligibility counts.",
        ],
        "PDS/NFSA": [
            "STATE-LEVEL: Real allocation + offtake in MT from data.gov.in (2019-2025, nfsa_allocation table).",
            "DISTRICT-LEVEL: allocation_mt and offtake_mt are zeros — no district breakdown from data.gov.in.",
            "Ration card counts (total, active, AAY, PHH) and beneficiary counts are populated at district level.",
            "NFSA tracks metric tonnes, not rupees — do not compare with other schemes' lakhs columns.",
        ],
        "PM POSHAN": [
            "STATE-LEVEL: Real allocation + release + utilization from data.gov.in (2016-2025, pmposhan_finance).",
            "DISTRICT-LEVEL: funds_released/utilized remain zero — portal does not expose district financial data.",
            "Delivery metrics (children_fed vs children_enrolled) available at district level.",
        ],
        "PMAY-G": [
            "STATE-LEVEL: Allocation + release + utilization from data.gov.in (2020-22, pmayg_finance). ~45% of rows have release=0 (allocation present).",
            "DISTRICT-LEVEL: funds_released/utilized remain zero — FinancialProgressRpt.aspx requires login.",
            "Delivery metrics (houses_sanctioned/completed) available at district level.",
        ],
        "JJM": [
            "STATE-LEVEL: Allocation data from data.gov.in (2019-2023, jjm_allocation). Allocation only.",
            "No release/utilization data available publicly — ejalshakti.gov.in financial page uses JS rendering.",
            "DISTRICT-LEVEL: funds_released/utilized remain zero — API has no financial endpoint.",
            "Delivery metrics (coverage_pct, households_with_tap) available at district level.",
        ],
        "MGNREGA": [
            "Financial amounts are in lakhs (amounts_in_lakhs=1 in financial_statement).",
        ],
        "PMGSY": [
            "Amounts are in crores. Converted to lakhs (*100) in VIEWs.",
        ],
    }
