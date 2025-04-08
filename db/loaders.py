"""Data loaders for all 8 schemes, NSAP imputation, and bulk load_all_latest."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from db.connection import CURATED_DIR, get_connection, init_db


def _load_json(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_misappropriation(conn: sqlite3.Connection, records: list[dict[str, Any]], fin_year: str) -> int:
    loaded = 0
    for r in records:
        try:
            conn.execute(
                """INSERT OR REPLACE INTO misappropriation
                (district, state, state_code, fin_year, cases_reported, amount_reported,
                 cases_decided, amount_decided, cases_pending_recovery, amount_to_recover,
                 cases_recovered, amount_recovered, amount_unrecovered, recovery_rate_pct,
                 source_url, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    r["district"],
                    r["state"],
                    r["state_code"],
                    fin_year,
                    r["cases_reported"],
                    r["amount_reported"],
                    r["cases_decided"],
                    r["amount_decided"],
                    r["cases_pending_recovery"],
                    r["amount_to_recover"],
                    r["cases_recovered"],
                    r["amount_recovered"],
                    r["amount_unrecovered"],
                    r["recovery_rate_pct"],
                    r["source_url"],
                    r["scraped_at"],
                ),
            )
            loaded += 1
        except sqlite3.IntegrityError:
            pass
    return loaded


def load_fto_status(conn: sqlite3.Connection, records: list[dict[str, Any]], fin_year: str) -> int:
    loaded = 0
    for r in records:
        try:
            conn.execute(
                """INSERT OR REPLACE INTO fto_status
                (district, state, state_code, fin_year, total_fto_generated,
                 first_signatory_signed, first_signatory_pending,
                 second_signatory_signed, second_signatory_pending,
                 fto_sent_to_bank, fto_processed_by_bank, transactions_processed,
                 source_url, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    r["district"],
                    r["state"],
                    r["state_code"],
                    fin_year,
                    r["total_fto_generated"],
                    r["first_signatory_signed"],
                    r["first_signatory_pending"],
                    r["second_signatory_signed"],
                    r["second_signatory_pending"],
                    r["fto_sent_to_bank"],
                    r.get("fto_processed_by_bank", 0),
                    r.get("transactions_processed", 0),
                    r["source_url"],
                    r["scraped_at"],
                ),
            )
            loaded += 1
        except sqlite3.IntegrityError:
            pass
    return loaded


def load_fto_pendency(conn: sqlite3.Connection, records: list[dict[str, Any]], fin_year: str) -> int:
    loaded = 0
    for r in records:
        try:
            conn.execute(
                """INSERT OR REPLACE INTO fto_pendency
                (bank_name, is_total, state, state_code, fin_year,
                 pending_1_7_days, pending_8_15_days, pending_16_30_days,
                 pending_over_30_days, total_pending, source_url, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    r["bank_name"],
                    int(r["is_total"]),
                    r["state"],
                    r["state_code"],
                    fin_year,
                    r.get("pending_1_7_days", 0),
                    r.get("pending_8_15_days", 0),
                    r.get("pending_16_30_days", 0),
                    r.get("pending_over_30_days", 0),
                    r.get("total_pending", 0),
                    r["source_url"],
                    r["scraped_at"],
                ),
            )
            loaded += 1
        except sqlite3.IntegrityError:
            pass
    return loaded


def load_issues_reported(conn: sqlite3.Connection, records: list[dict[str, Any]], fin_year: str) -> int:
    loaded = 0
    for r in records:
        try:
            conn.execute(
                """INSERT OR REPLACE INTO issues_reported
                (district, state, state_code, fin_year, total_gps, gps_audited,
                 misappropriation_issues, misappropriation_amount,
                 financial_deviation_issues, financial_deviation_amount,
                 process_violation_issues, process_violation_amount,
                 grievances_issues, grievances_amount,
                 total_issues, total_amount, source_url, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    r["district"],
                    r["state"],
                    r["state_code"],
                    fin_year,
                    r["total_gps"],
                    r["gps_audited"],
                    r.get("misappropriation_issues", 0),
                    r.get("misappropriation_amount", 0),
                    r.get("financial_deviation_issues", 0),
                    r.get("financial_deviation_amount", 0),
                    r.get("process_violation_issues", 0),
                    r.get("process_violation_amount", 0),
                    r.get("grievances_issues", 0),
                    r.get("grievances_amount", 0),
                    r.get("total_issues", 0),
                    r.get("total_amount", 0),
                    r["source_url"],
                    r["scraped_at"],
                ),
            )
            loaded += 1
        except sqlite3.IntegrityError:
            pass
    return loaded


def load_financial_statement(conn: sqlite3.Connection, records: list[dict[str, Any]], fin_year: str) -> int:
    """Load MGNREGA financial statement records.

    Financial statement columns (from raw HTML headers):
    col_2: Opening Balance (Entered OB)
    col_3: Release of Last FY but Received during Current FY
    col_4/5: Release from Centre/State
    col_6: Authorisation of EFMS
    col_7: Misc Receipt
    col_8: Total Availability = sum of above
    col_9-13: Expenditure breakdown (Unskilled Wage, Semi-skilled, Material, Tax, Total)
    col_14-16: Admin Exp (Rec, Non-Rec, Total Admin)
    col_17: Cumulative Expenditure
    col_18: % Utilization
    col_19: Balance
    """
    loaded = 0
    for r in records:
        try:
            conn.execute(
                """INSERT OR REPLACE INTO financial_statement
                (district, state, state_code, fin_year,
                 opening_balance, release_last_fy_received, release_from_state_fund,
                 authorisation_efms, misc_receipt, total_availability,
                 exp_unskilled_wage, exp_semiskilled_wage, exp_material, exp_tax, exp_total,
                 exp_admin_rec, exp_admin_nonrec, exp_admin_total,
                 cumulative_expenditure, utilization_pct, balance,
                 amounts_in_lakhs, source_url, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    r["district"],
                    r["state"],
                    r["state_code"],
                    fin_year,
                    r.get("col_2_num", 0),
                    r.get("col_3_num", 0),
                    r.get("col_5_num", 0),
                    r.get("col_6_num", 0),
                    r.get("col_7_num", 0),
                    r.get("col_9_num", 0),
                    r.get("col_10_num", 0),
                    r.get("col_11_num", 0),
                    r.get("col_12_num", 0),
                    r.get("col_13_num", 0),
                    r.get("col_10_num", 0) + r.get("col_11_num", 0) + r.get("col_12_num", 0) + r.get("col_13_num", 0),
                    r.get("col_14_num", 0),
                    r.get("col_15_num", 0),
                    r.get("col_16_num", 0),
                    r.get("col_17_num", 0),
                    r.get("col_18_num", 0),
                    r.get("col_19_num", 0),
                    1,
                    r["source_url"],
                    r["scraped_at"],
                ),
            )
            loaded += 1
        except sqlite3.IntegrityError:
            pass
    return loaded


def load_pmgsy_progress(conn: sqlite3.Connection, records: list[dict[str, Any]], fin_year: str) -> int:
    loaded = 0
    for r in records:
        try:
            conn.execute(
                """INSERT OR REPLACE INTO pmgsy_progress
                (state, state_code, fin_year, roads_completed, length_completed_km,
                 habitations_connected, expenditure_programme_cr, expenditure_admin_cr,
                 source_url, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    r.get("state", ""),
                    r.get("state_code", ""),
                    r.get("fin_year_or_scheme", fin_year),
                    r.get("roads_completed", 0),
                    r.get("length_completed_km", 0),
                    r.get("habitations_connected", 0),
                    r.get("expenditure_programme_cr", 0),
                    r.get("expenditure_admin_cr", 0),
                    r.get("source_url", ""),
                    r.get("scraped_at", ""),
                ),
            )
            loaded += 1
        except sqlite3.IntegrityError:
            pass
    return loaded


def load_pmgsy_district(conn: sqlite3.Connection, records: list[dict[str, Any]], fin_year: str) -> int:
    loaded = 0
    for r in records:
        try:
            conn.execute(
                """INSERT OR REPLACE INTO pmgsy_district
                (district, state, state_code, fin_year, scheme,
                 roads_sanctioned, roads_completed, length_sanctioned_km, length_completed_km,
                 habitations_covered, value_of_projects_cr, expenditure_cr,
                 source_url, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    r.get("district", ""),
                    r.get("state", ""),
                    r.get("state_code", ""),
                    fin_year,
                    r.get("scheme", ""),
                    r.get("roads_sanctioned", 0),
                    r.get("roads_completed", 0),
                    r.get("length_sanctioned_km", 0),
                    r.get("length_completed_km", 0),
                    r.get("habitations_covered", 0),
                    r.get("value_of_projects_cr", 0),
                    r.get("expenditure_cr", 0),
                    r.get("source_url", ""),
                    r.get("scraped_at", ""),
                ),
            )
            loaded += 1
        except sqlite3.IntegrityError:
            pass
    return loaded


def load_pmayg_district(conn: sqlite3.Connection, records: list[dict[str, Any]], fin_year: str) -> int:
    loaded = 0
    for r in records:
        try:
            conn.execute(
                """INSERT OR REPLACE INTO pmayg_district
                (district, state, state_code, fin_year, houses_sanctioned, houses_completed,
                 houses_occupied, funds_released_lakhs, funds_utilized_lakhs, completion_pct,
                 source_url, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    r["district"],
                    r["state"],
                    r.get("state_code", ""),
                    fin_year,
                    r.get("houses_sanctioned", 0),
                    r.get("houses_completed", 0),
                    r.get("houses_occupied", 0),
                    r.get("funds_released_lakhs", 0),
                    r.get("funds_utilized_lakhs", 0),
                    r.get("completion_pct", 0),
                    r.get("source_url", ""),
                    r.get("scraped_at", ""),
                ),
            )
            loaded += 1
        except sqlite3.IntegrityError:
            pass
    return loaded


def load_pmkisan_district(conn: sqlite3.Connection, records: list[dict[str, Any]], fin_year: str) -> int:
    loaded = 0
    for r in records:
        try:
            conn.execute(
                """INSERT OR REPLACE INTO pmkisan_district
                (district, state, state_code, fin_year, beneficiaries_registered,
                 beneficiaries_paid, amount_paid_lakhs, beneficiaries_rejected,
                 installment, source_url, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    r["district"],
                    r["state"],
                    r.get("state_code", ""),
                    fin_year,
                    r.get("beneficiaries_registered", 0),
                    r.get("beneficiaries_paid", 0),
                    r.get("amount_paid_lakhs", 0),
                    r.get("beneficiaries_rejected", 0),
                    r.get("installment", ""),
                    r.get("source_url", ""),
                    r.get("scraped_at", ""),
                ),
            )
            loaded += 1
        except sqlite3.IntegrityError:
            pass
    return loaded


def load_jjm_district(conn: sqlite3.Connection, records: list[dict[str, Any]], fin_year: str) -> int:
    loaded = 0
    for r in records:
        try:
            conn.execute(
                """INSERT OR REPLACE INTO jjm_district
                (district, state, state_code, fin_year, total_households,
                 households_with_tap, tap_connections_provided, coverage_pct,
                 funds_released_lakhs, funds_utilized_lakhs, source_url, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    r["district"],
                    r["state"],
                    r.get("state_code", ""),
                    fin_year,
                    r.get("total_households", 0),
                    r.get("households_with_tap", 0),
                    r.get("tap_connections_provided", 0),
                    r.get("coverage_pct", 0),
                    r.get("funds_released_lakhs", 0),
                    r.get("funds_utilized_lakhs", 0),
                    r.get("source_url", ""),
                    r.get("scraped_at", ""),
                ),
            )
            loaded += 1
        except sqlite3.IntegrityError:
            pass
    return loaded


def load_pmposhan_district(conn: sqlite3.Connection, records: list[dict[str, Any]], fin_year: str) -> int:
    loaded = 0
    for r in records:
        try:
            conn.execute(
                """INSERT OR REPLACE INTO pmposhan_district
                (district, state, state_code, fin_year, schools_covered,
                 children_enrolled, children_fed, funds_released_lakhs,
                 funds_utilized_lakhs, utilization_pct, source_url, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    r["district"],
                    r["state"],
                    r.get("state_code", ""),
                    fin_year,
                    r.get("schools_covered", 0),
                    r.get("children_enrolled", 0),
                    r.get("children_fed", 0),
                    r.get("funds_released_lakhs", 0),
                    r.get("funds_utilized_lakhs", 0),
                    r.get("utilization_pct", 0),
                    r.get("source_url", ""),
                    r.get("scraped_at", ""),
                ),
            )
            loaded += 1
        except sqlite3.IntegrityError:
            pass
    return loaded


def load_nsap_district(conn: sqlite3.Connection, records: list[dict[str, Any]], fin_year: str) -> int:
    loaded = 0
    for r in records:
        try:
            conn.execute(
                """INSERT OR REPLACE INTO nsap_district
                (district, state, state_code, fin_year, scheme_type,
                 beneficiaries_eligible, beneficiaries_paid, amount_paid_lakhs,
                 pension_per_month, source_url, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    r["district"],
                    r["state"],
                    r.get("state_code", ""),
                    fin_year,
                    r.get("scheme_type", ""),
                    r.get("beneficiaries_eligible", 0),
                    r.get("beneficiaries_paid", 0),
                    r.get("amount_paid_lakhs", 0),
                    r.get("pension_per_month", 0),
                    r.get("source_url", ""),
                    r.get("scraped_at", ""),
                ),
            )
            loaded += 1
        except sqlite3.IntegrityError:
            pass
    return loaded


def load_nfsa_district(conn: sqlite3.Connection, records: list[dict[str, Any]], fin_year: str) -> int:
    loaded = 0
    for r in records:
        try:
            conn.execute(
                """INSERT OR REPLACE INTO nfsa_district
                (district, state, state_code, fin_year, ration_cards_total,
                 ration_cards_active, allocation_mt, offtake_mt, offtake_pct,
                 beneficiaries_total, source_url, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    r["district"],
                    r["state"],
                    r.get("state_code", ""),
                    fin_year,
                    r.get("ration_cards_total", 0),
                    r.get("ration_cards_active", 0),
                    r.get("allocation_mt", 0),
                    r.get("offtake_mt", 0),
                    r.get("offtake_pct", 0),
                    r.get("beneficiaries_total", 0),
                    r.get("source_url", ""),
                    r.get("scraped_at", ""),
                ),
            )
            loaded += 1
        except sqlite3.IntegrityError:
            pass
    return loaded


# GoI central pension rates (Rs/month) — publicly known, fixed by government order.
# These are the central share only; states may top up independently.
# Source: nsap.nic.in scheme guidelines
NSAP_PENSION_RATES = {
    "IGNOAPS": 200,  # Indira Gandhi National Old Age Pension (60-79 yrs)
    "IGNWPS": 300,  # Indira Gandhi National Widow Pension
    "IGNDPS": 300,  # Indira Gandhi National Disability Pension
}


def impute_nsap_financials(conn: sqlite3.Connection) -> int:
    """Impute NSAP financial data from beneficiary counts x central pension rates.

    Formula: amount_paid_lakhs = beneficiaries_paid x pension_rate x 12 / 100000
    Only updates rows where amount_paid_lakhs is 0 (preserving any real data).
    """
    updated = 0
    for scheme_type, rate in NSAP_PENSION_RATES.items():
        cur = conn.execute(
            """UPDATE nsap_district
            SET amount_paid_lakhs = beneficiaries_paid * ? * 12.0 / 100000,
                pension_per_month = ?
            WHERE scheme_type = ? AND amount_paid_lakhs = 0 AND beneficiaries_paid > 0""",
            (rate, rate, scheme_type),
        )
        updated += cur.rowcount
    conn.commit()
    return updated


LOADERS = {
    "misappropriation": load_misappropriation,
    "fto_status": load_fto_status,
    "fto_pendency": load_fto_pendency,
    "issues_reported": load_issues_reported,
    "financial_statement": load_financial_statement,
    "pmgsy_progress": load_pmgsy_progress,
    "pmgsy_district": load_pmgsy_district,
    "pmayg_district": load_pmayg_district,
    "pmkisan_district": load_pmkisan_district,
    "jjm_district": load_jjm_district,
    "pmposhan_district": load_pmposhan_district,
    "nsap_district": load_nsap_district,
    "nfsa_district": load_nfsa_district,
}


def load_all_latest(fin_year: str = "2024-2025", state_slug: str = "tamil-nadu") -> dict[str, int]:
    """Load all latest curated JSON files into SQLite."""
    conn = get_connection()
    init_db(conn)

    results: dict[str, int] = {}

    for report_name, loader in LOADERS.items():
        path = CURATED_DIR / f"{report_name}_{state_slug}_latest.json"
        if not path.exists():
            print(f"  {report_name}: no data file found")
            results[report_name] = 0
            continue

        records = _load_json(path)
        count = loader(conn, records, fin_year)
        conn.commit()
        print(f"  {report_name}: loaded {count} records")
        results[report_name] = count

        # Log the scrape run
        if records:
            conn.execute(
                """INSERT OR IGNORE INTO scrape_runs
                (state, state_code, fin_year, report_name, record_count, source_url, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    records[0].get("state", ""),
                    records[0].get("state_code", ""),
                    fin_year,
                    report_name,
                    len(records),
                    records[0].get("source_url", ""),
                    records[0].get("scraped_at", ""),
                ),
            )
            conn.commit()

    conn.close()
    return results
