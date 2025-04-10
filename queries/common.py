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
            "amount_paid_lakhs is IMPUTED: beneficiaries_paid x GoI central pension rate x 12 months.",
            "Central rates: IGNOAPS Rs 200/mo, IGNWPS Rs 300/mo, IGNDPS Rs 300/mo (central share only, states may top up).",
            "beneficiaries_eligible is still zero — data.gov.in API does not provide eligibility counts.",
            "API scraper (scrape_nsap_api.py) fetches IGNOAPS/IGNWPS/IGNDPS from data.gov.in automatically.",
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
