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
            "Social audit tables (misappropriation, issues_reported) are FROZEN at FY2024-25: "
            "their only source, the national MIS index, went captcha-gated in Aug 2026. "
            "Cite those figures as FY2024-25, never as current. See DATA_CLAIMS.md CLAIM-2026-0001.",
        ],
        "PMGSY": [
            "Amounts are in crores. Converted to lakhs (*100) in VIEWs.",
        ],
        "PMAY-G": [
            "STATE-LEVEL: Allocation + release + utilization from the un-gated B.3 High Level Financial Progress report (report.pmayg.dord.gov.in, 2019-2026, pmayg_finance; captcha removed 2026-08-04). ~45% of rows have release=0 (allocation present).",
            "DISTRICT-LEVEL: funds_released/utilized remain zero — FinancialProgressRpt.aspx requires login.",
            "Delivery metrics (houses_sanctioned/completed) available at district level.",
        ],
        "PM Kisan": [
            "DISTRICT-LEVEL: beneficiaries paid per installment, aggregated from the data.gov.in village dataset (CLAIM-2026-0031). Counts only — the dataset publishes no money; district data lags the homepage by one installment.",
            "STATE-LEVEL: current-period eligible vs transferred from the pmkisan.gov.in homepage (district='ALL' rows, CLAIM-2026-0030) — mid-cycle numbers while an installment is still being paid out.",
            "amount_paid_lakhs is zero everywhere except 8 states' frozen FY2024-25 district rows (Rajya Sabha resources, last updated 2023) — never rank districts by PM Kisan money.",
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
            "Ration card counts equal 'active' by construction in the source (CLAIM-2026-0029) — no active-percentage is published. Reporting vintage varies by state (per-row date_of_data): half the districts report 2025-26 dates, a long tail still cites 2019-2021.",
            "NFSA tracks metric tonnes, not rupees — never compared with other schemes' lakhs columns.",
        ],
        "SBM-G": [
            "Delivery metrics only (ODF Plus villages, star ratings) — SBM-G publishes no district-level financial data.",
        ],
        "DAY-NRLM": [
            "District-level SHG counts plus two real money streams — Revolving Fund and Community Investment Fund (both cumulative, from the LokOS FDM feed, which lags real time by ~2 months).",
            "The served CIF figure is money received; the eligible-vs-received gap travels in the data (cif_shgs_eligible vs cif_shgs_provided) and only a minority of eligible SHGs have received CIF nationally.",
        ],
        "UDISE+": [
            "State-level education indicators only (schools, enrollment, PTR, infrastructure) — no district breakdown, no financial data.",
        ],
    }
