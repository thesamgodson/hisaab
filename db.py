"""
SQLite database schema and loaders for Hisaab — multi-scheme transparency data.

Scheme tables (detailed per-scheme data):
- MGNREGA: misappropriation, fto_status, fto_pendency, issues_reported, financial_statement
- PMGSY: pmgsy_progress, pmgsy_district
- PMAY-G: pmayg_district (rural housing)
- PM Kisan: pmkisan_district (farmer payments)
- Jal Jeevan Mission: jjm_district (rural water)
- PM POSHAN: pmposhan_district (school nutrition)
- NSAP: nsap_district (pensions)
- PDS/NFSA: nfsa_district (ration system)

Unified view:
- money_flow: normalized view across ALL schemes for cross-scheme queries
  (scheme, state, district, fin_year, allocated, released, expended,
   utilization_pct, units_target, units_completed, source_url)

Metadata:
- scrape_runs: metadata for each scrape run
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parent / "data" / "hisaab.db"
CURATED_DIR = Path(__file__).resolve().parent / "data" / "curated"

SCHEMA = """
CREATE TABLE IF NOT EXISTS scrape_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    state TEXT NOT NULL,
    state_code TEXT NOT NULL,
    fin_year TEXT NOT NULL,
    report_name TEXT NOT NULL,
    record_count INTEGER NOT NULL,
    source_url TEXT,
    scraped_at TEXT NOT NULL,
    loaded_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(state, fin_year, report_name, scraped_at)
);

CREATE TABLE IF NOT EXISTS misappropriation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    district TEXT NOT NULL,
    state TEXT NOT NULL,
    state_code TEXT NOT NULL,
    fin_year TEXT NOT NULL,
    cases_reported INTEGER NOT NULL DEFAULT 0,
    amount_reported REAL NOT NULL DEFAULT 0,
    cases_decided INTEGER NOT NULL DEFAULT 0,
    amount_decided REAL NOT NULL DEFAULT 0,
    cases_pending_recovery INTEGER NOT NULL DEFAULT 0,
    amount_to_recover REAL NOT NULL DEFAULT 0,
    cases_recovered INTEGER NOT NULL DEFAULT 0,
    amount_recovered REAL NOT NULL DEFAULT 0,
    amount_unrecovered REAL NOT NULL DEFAULT 0,
    recovery_rate_pct REAL NOT NULL DEFAULT 0,
    source_url TEXT,
    scraped_at TEXT NOT NULL,
    UNIQUE(district, state, fin_year, scraped_at)
);

CREATE TABLE IF NOT EXISTS fto_status (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    district TEXT NOT NULL,
    state TEXT NOT NULL,
    state_code TEXT NOT NULL,
    fin_year TEXT NOT NULL,
    total_fto_generated INTEGER NOT NULL DEFAULT 0,
    first_signatory_signed INTEGER NOT NULL DEFAULT 0,
    first_signatory_pending INTEGER NOT NULL DEFAULT 0,
    second_signatory_signed INTEGER NOT NULL DEFAULT 0,
    second_signatory_pending INTEGER NOT NULL DEFAULT 0,
    fto_sent_to_bank INTEGER NOT NULL DEFAULT 0,
    fto_processed_by_bank INTEGER NOT NULL DEFAULT 0,
    transactions_processed INTEGER NOT NULL DEFAULT 0,
    source_url TEXT,
    scraped_at TEXT NOT NULL,
    UNIQUE(district, state, fin_year, scraped_at)
);

CREATE TABLE IF NOT EXISTS fto_pendency (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bank_name TEXT NOT NULL,
    is_total INTEGER NOT NULL DEFAULT 0,
    state TEXT NOT NULL,
    state_code TEXT NOT NULL,
    fin_year TEXT NOT NULL,
    pending_1_7_days INTEGER NOT NULL DEFAULT 0,
    pending_8_15_days INTEGER NOT NULL DEFAULT 0,
    pending_16_30_days INTEGER NOT NULL DEFAULT 0,
    pending_over_30_days INTEGER NOT NULL DEFAULT 0,
    total_pending INTEGER NOT NULL DEFAULT 0,
    source_url TEXT,
    scraped_at TEXT NOT NULL,
    UNIQUE(bank_name, state, fin_year, scraped_at)
);

CREATE TABLE IF NOT EXISTS issues_reported (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    district TEXT NOT NULL,
    state TEXT NOT NULL,
    state_code TEXT NOT NULL,
    fin_year TEXT NOT NULL,
    total_gps INTEGER NOT NULL DEFAULT 0,
    gps_audited INTEGER NOT NULL DEFAULT 0,
    misappropriation_issues INTEGER NOT NULL DEFAULT 0,
    misappropriation_amount REAL NOT NULL DEFAULT 0,
    financial_deviation_issues INTEGER NOT NULL DEFAULT 0,
    financial_deviation_amount REAL NOT NULL DEFAULT 0,
    process_violation_issues INTEGER NOT NULL DEFAULT 0,
    process_violation_amount REAL NOT NULL DEFAULT 0,
    grievances_issues INTEGER NOT NULL DEFAULT 0,
    grievances_amount REAL NOT NULL DEFAULT 0,
    total_issues INTEGER NOT NULL DEFAULT 0,
    total_amount REAL NOT NULL DEFAULT 0,
    source_url TEXT,
    scraped_at TEXT NOT NULL,
    UNIQUE(district, state, fin_year, scraped_at)
);

CREATE TABLE IF NOT EXISTS financial_statement (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    district TEXT NOT NULL,
    state TEXT NOT NULL,
    state_code TEXT NOT NULL,
    fin_year TEXT NOT NULL,
    opening_balance REAL NOT NULL DEFAULT 0,
    release_last_fy_received REAL NOT NULL DEFAULT 0,
    release_from_state_fund REAL NOT NULL DEFAULT 0,
    authorisation_efms REAL NOT NULL DEFAULT 0,
    misc_receipt REAL NOT NULL DEFAULT 0,
    total_availability REAL NOT NULL DEFAULT 0,
    exp_unskilled_wage REAL NOT NULL DEFAULT 0,
    exp_semiskilled_wage REAL NOT NULL DEFAULT 0,
    exp_material REAL NOT NULL DEFAULT 0,
    exp_tax REAL NOT NULL DEFAULT 0,
    exp_total REAL NOT NULL DEFAULT 0,
    exp_admin_rec REAL NOT NULL DEFAULT 0,
    exp_admin_nonrec REAL NOT NULL DEFAULT 0,
    exp_admin_total REAL NOT NULL DEFAULT 0,
    cumulative_expenditure REAL NOT NULL DEFAULT 0,
    utilization_pct REAL NOT NULL DEFAULT 0,
    balance REAL NOT NULL DEFAULT 0,
    amounts_in_lakhs INTEGER NOT NULL DEFAULT 1,
    source_url TEXT,
    scraped_at TEXT NOT NULL,
    UNIQUE(district, state, fin_year, scraped_at)
);

CREATE TABLE IF NOT EXISTS pmgsy_progress (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    state TEXT NOT NULL,
    state_code TEXT NOT NULL DEFAULT '',
    fin_year TEXT NOT NULL DEFAULT '',
    roads_completed INTEGER NOT NULL DEFAULT 0,
    length_completed_km REAL NOT NULL DEFAULT 0,
    habitations_connected INTEGER NOT NULL DEFAULT 0,
    expenditure_programme_cr REAL NOT NULL DEFAULT 0,
    expenditure_admin_cr REAL NOT NULL DEFAULT 0,
    source_url TEXT,
    scraped_at TEXT NOT NULL,
    UNIQUE(state, fin_year)
);

CREATE TABLE IF NOT EXISTS pmgsy_district (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    district TEXT NOT NULL,
    state TEXT NOT NULL,
    state_code TEXT NOT NULL DEFAULT '',
    fin_year TEXT NOT NULL DEFAULT '',
    scheme TEXT NOT NULL DEFAULT '',
    roads_sanctioned INTEGER NOT NULL DEFAULT 0,
    roads_completed INTEGER NOT NULL DEFAULT 0,
    length_sanctioned_km REAL NOT NULL DEFAULT 0,
    length_completed_km REAL NOT NULL DEFAULT 0,
    habitations_covered INTEGER NOT NULL DEFAULT 0,
    value_of_projects_cr REAL NOT NULL DEFAULT 0,
    expenditure_cr REAL NOT NULL DEFAULT 0,
    source_url TEXT,
    scraped_at TEXT NOT NULL,
    UNIQUE(district, state, fin_year, scheme)
);

CREATE INDEX IF NOT EXISTS idx_misappropriation_state ON misappropriation(state, fin_year);
CREATE INDEX IF NOT EXISTS idx_fto_status_state ON fto_status(state, fin_year);
CREATE INDEX IF NOT EXISTS idx_issues_reported_state ON issues_reported(state, fin_year);
CREATE INDEX IF NOT EXISTS idx_financial_statement_state ON financial_statement(state, fin_year);
CREATE INDEX IF NOT EXISTS idx_pmgsy_progress_state ON pmgsy_progress(state);
CREATE INDEX IF NOT EXISTS idx_pmgsy_district_state ON pmgsy_district(state);
CREATE INDEX IF NOT EXISTS idx_pmgsy_district_district ON pmgsy_district(district, state);

-- =====================================================================
-- New scheme tables (Tier 1)
-- =====================================================================

-- PMAY-G: Pradhan Mantri Awas Yojana Gramin (rural housing)
CREATE TABLE IF NOT EXISTS pmayg_district (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    district TEXT NOT NULL,
    state TEXT NOT NULL,
    state_code TEXT NOT NULL DEFAULT '',
    fin_year TEXT NOT NULL,
    houses_sanctioned INTEGER NOT NULL DEFAULT 0,
    houses_completed INTEGER NOT NULL DEFAULT 0,
    houses_occupied INTEGER NOT NULL DEFAULT 0,
    funds_released_lakhs REAL NOT NULL DEFAULT 0,
    funds_utilized_lakhs REAL NOT NULL DEFAULT 0,
    completion_pct REAL NOT NULL DEFAULT 0,
    source_url TEXT,
    scraped_at TEXT NOT NULL,
    UNIQUE(district, state, fin_year)
);
CREATE INDEX IF NOT EXISTS idx_pmayg_district ON pmayg_district(state, district);

-- PM Kisan Samman Nidhi (farmer direct payments)
CREATE TABLE IF NOT EXISTS pmkisan_district (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    district TEXT NOT NULL,
    state TEXT NOT NULL,
    state_code TEXT NOT NULL DEFAULT '',
    fin_year TEXT NOT NULL,
    beneficiaries_registered INTEGER NOT NULL DEFAULT 0,
    beneficiaries_paid INTEGER NOT NULL DEFAULT 0,
    amount_paid_lakhs REAL NOT NULL DEFAULT 0,
    beneficiaries_rejected INTEGER NOT NULL DEFAULT 0,
    installment TEXT NOT NULL DEFAULT '',
    source_url TEXT,
    scraped_at TEXT NOT NULL,
    UNIQUE(district, state, fin_year, installment)
);
CREATE INDEX IF NOT EXISTS idx_pmkisan_district ON pmkisan_district(state, district);

-- Jal Jeevan Mission (rural water / tap connections)
CREATE TABLE IF NOT EXISTS jjm_district (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    district TEXT NOT NULL,
    state TEXT NOT NULL,
    state_code TEXT NOT NULL DEFAULT '',
    fin_year TEXT NOT NULL DEFAULT 'cumulative',
    total_households INTEGER NOT NULL DEFAULT 0,
    households_with_tap INTEGER NOT NULL DEFAULT 0,
    tap_connections_provided INTEGER NOT NULL DEFAULT 0,
    coverage_pct REAL NOT NULL DEFAULT 0,
    funds_released_lakhs REAL NOT NULL DEFAULT 0,
    funds_utilized_lakhs REAL NOT NULL DEFAULT 0,
    source_url TEXT,
    scraped_at TEXT NOT NULL,
    UNIQUE(district, state, fin_year)
);
CREATE INDEX IF NOT EXISTS idx_jjm_district ON jjm_district(state, district);

-- PM POSHAN / Mid-Day Meal (school nutrition)
CREATE TABLE IF NOT EXISTS pmposhan_district (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    district TEXT NOT NULL,
    state TEXT NOT NULL,
    state_code TEXT NOT NULL DEFAULT '',
    fin_year TEXT NOT NULL,
    schools_covered INTEGER NOT NULL DEFAULT 0,
    children_enrolled INTEGER NOT NULL DEFAULT 0,
    children_fed INTEGER NOT NULL DEFAULT 0,
    funds_released_lakhs REAL NOT NULL DEFAULT 0,
    funds_utilized_lakhs REAL NOT NULL DEFAULT 0,
    utilization_pct REAL NOT NULL DEFAULT 0,
    source_url TEXT,
    scraped_at TEXT NOT NULL,
    UNIQUE(district, state, fin_year)
);
CREATE INDEX IF NOT EXISTS idx_pmposhan_district ON pmposhan_district(state, district);

-- NSAP: National Social Assistance Programme (pensions)
CREATE TABLE IF NOT EXISTS nsap_district (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    district TEXT NOT NULL,
    state TEXT NOT NULL,
    state_code TEXT NOT NULL DEFAULT '',
    fin_year TEXT NOT NULL,
    scheme_type TEXT NOT NULL DEFAULT '',
    beneficiaries_eligible INTEGER NOT NULL DEFAULT 0,
    beneficiaries_paid INTEGER NOT NULL DEFAULT 0,
    amount_paid_lakhs REAL NOT NULL DEFAULT 0,
    pension_per_month REAL NOT NULL DEFAULT 0,
    source_url TEXT,
    scraped_at TEXT NOT NULL,
    UNIQUE(district, state, fin_year, scheme_type)
);
CREATE INDEX IF NOT EXISTS idx_nsap_district ON nsap_district(state, district);

-- PDS / NFSA: National Food Security Act (ration system)
CREATE TABLE IF NOT EXISTS nfsa_district (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    district TEXT NOT NULL,
    state TEXT NOT NULL,
    state_code TEXT NOT NULL DEFAULT '',
    fin_year TEXT NOT NULL,
    ration_cards_total INTEGER NOT NULL DEFAULT 0,
    ration_cards_active INTEGER NOT NULL DEFAULT 0,
    allocation_mt REAL NOT NULL DEFAULT 0,
    offtake_mt REAL NOT NULL DEFAULT 0,
    offtake_pct REAL NOT NULL DEFAULT 0,
    beneficiaries_total INTEGER NOT NULL DEFAULT 0,
    source_url TEXT,
    scraped_at TEXT NOT NULL,
    UNIQUE(district, state, fin_year)
);
CREATE INDEX IF NOT EXISTS idx_nfsa_district ON nfsa_district(state, district);

-- =====================================================================
-- VIEW 1: scheme_finance — Financial flow (rupees in lakhs only)
-- =====================================================================
-- Only schemes with REAL financial data scraped from portals.
-- Excluded: NFSA (metric tons, not rupees), NSAP (all zeros),
--           PMAY-G (financial report behind login/Power BI),
--           JJM (no financial API endpoint),
--           PM POSHAN (funds columns all zeros from portal).

DROP VIEW IF EXISTS scheme_finance;
CREATE VIEW scheme_finance AS
SELECT
    'MGNREGA' as scheme, state, district, fin_year,
    total_availability as allocated_lakhs,
    total_availability as released_lakhs,
    cumulative_expenditure as expended_lakhs,
    utilization_pct, source_url
FROM financial_statement
UNION ALL
SELECT
    'PMGSY' as scheme, state, district, fin_year,
    value_of_projects_cr * 100 as allocated_lakhs,
    value_of_projects_cr * 100 as released_lakhs,
    expenditure_cr * 100 as expended_lakhs,
    CASE WHEN value_of_projects_cr > 0
         THEN (expenditure_cr / value_of_projects_cr * 100)
         ELSE 0 END as utilization_pct,
    source_url
FROM pmgsy_district
UNION ALL
SELECT
    'PM Kisan' as scheme, state, district, fin_year,
    NULL as allocated_lakhs,
    amount_paid_lakhs as released_lakhs,
    amount_paid_lakhs as expended_lakhs,
    CASE WHEN beneficiaries_registered > 0
         THEN (beneficiaries_paid * 100.0 / beneficiaries_registered)
         ELSE 0 END as utilization_pct,
    source_url
FROM pmkisan_district;

-- =====================================================================
-- VIEW 2: scheme_delivery — Service delivery / beneficiary coverage
-- =====================================================================
-- All schemes with units tracking. Each row has a units_label for semantic clarity.

DROP VIEW IF EXISTS scheme_delivery;
CREATE VIEW scheme_delivery AS
SELECT
    'MGNREGA' as scheme, state, district, fin_year,
    NULL as units_target, NULL as units_completed,
    NULL as units_label,
    utilization_pct as delivery_pct, source_url
FROM financial_statement
UNION ALL
SELECT
    'PMGSY' as scheme, state, district, fin_year,
    roads_sanctioned as units_target,
    roads_completed as units_completed,
    'roads' as units_label,
    CASE WHEN roads_sanctioned > 0
         THEN (roads_completed * 100.0 / roads_sanctioned)
         ELSE 0 END as delivery_pct,
    source_url
FROM pmgsy_district
UNION ALL
SELECT
    'PMAY-G' as scheme, state, district, fin_year,
    houses_sanctioned as units_target,
    houses_completed as units_completed,
    'houses' as units_label,
    completion_pct as delivery_pct, source_url
FROM pmayg_district
UNION ALL
SELECT
    'PM Kisan' as scheme, state, district, fin_year,
    beneficiaries_registered as units_target,
    beneficiaries_paid as units_completed,
    'beneficiaries' as units_label,
    CASE WHEN beneficiaries_registered > 0
         THEN (beneficiaries_paid * 100.0 / beneficiaries_registered)
         ELSE 0 END as delivery_pct,
    source_url
FROM pmkisan_district
UNION ALL
SELECT
    'JJM' as scheme, state, district, fin_year,
    total_households as units_target,
    households_with_tap as units_completed,
    'tap connections' as units_label,
    coverage_pct as delivery_pct, source_url
FROM jjm_district
UNION ALL
SELECT
    'PM POSHAN' as scheme, state, district, fin_year,
    children_enrolled as units_target,
    children_fed as units_completed,
    'children fed' as units_label,
    CASE WHEN children_enrolled > 0
         THEN (children_fed * 100.0 / children_enrolled)
         ELSE 0 END as delivery_pct,
    source_url
FROM pmposhan_district
UNION ALL
SELECT
    'NSAP' as scheme, state, district, fin_year,
    beneficiaries_eligible as units_target,
    beneficiaries_paid as units_completed,
    'pensioners' as units_label,
    CASE WHEN beneficiaries_eligible > 0
         THEN (beneficiaries_paid * 100.0 / beneficiaries_eligible)
         ELSE 0 END as delivery_pct,
    source_url
FROM nsap_district
UNION ALL
SELECT
    'PDS/NFSA' as scheme, state, district, fin_year,
    ration_cards_total as units_target,
    ration_cards_active as units_completed,
    'ration cards' as units_label,
    offtake_pct as delivery_pct, source_url
FROM nfsa_district;

-- =====================================================================
-- VIEW 3: money_flow — Backward-compatible combined view
-- =====================================================================
-- Keeps money_flow working for existing code. Adds units_label for clarity.
-- WARNING: Financial columns are HOLLOW (all zeros) for these schemes:
--   PMAY-G, JJM, PM POSHAN — portals don't expose financial data publicly.
--   NSAP — data.gov.in source has all zeros for amount/eligible/pension.
--   NFSA — allocated/expended are metric tons, not lakhs.
-- Use scheme_finance VIEW for clean financial comparisons (MGNREGA, PMGSY, PM Kisan only).

DROP VIEW IF EXISTS money_flow;
CREATE VIEW money_flow AS
SELECT
    'MGNREGA' as scheme, state, district, fin_year,
    total_availability as allocated_lakhs,
    total_availability as released_lakhs,
    cumulative_expenditure as expended_lakhs,
    utilization_pct,
    NULL as units_target, NULL as units_completed,
    NULL as units_label, source_url
FROM financial_statement
UNION ALL
SELECT
    'PMGSY' as scheme, state, district, fin_year,
    value_of_projects_cr * 100 as allocated_lakhs,
    value_of_projects_cr * 100 as released_lakhs,
    expenditure_cr * 100 as expended_lakhs,
    CASE WHEN value_of_projects_cr > 0
         THEN (expenditure_cr / value_of_projects_cr * 100)
         ELSE 0 END as utilization_pct,
    roads_sanctioned as units_target,
    roads_completed as units_completed,
    'roads' as units_label, source_url
FROM pmgsy_district
UNION ALL
SELECT
    'PMAY-G' as scheme, state, district, fin_year,
    funds_released_lakhs as allocated_lakhs,
    funds_released_lakhs as released_lakhs,
    funds_utilized_lakhs as expended_lakhs,
    CASE WHEN funds_released_lakhs > 0
         THEN (funds_utilized_lakhs / funds_released_lakhs * 100)
         ELSE 0 END as utilization_pct,
    houses_sanctioned as units_target,
    houses_completed as units_completed,
    'houses' as units_label, source_url
FROM pmayg_district
UNION ALL
SELECT
    'PM Kisan' as scheme, state, district, fin_year,
    NULL as allocated_lakhs,
    amount_paid_lakhs as released_lakhs,
    amount_paid_lakhs as expended_lakhs,
    CASE WHEN beneficiaries_registered > 0
         THEN (beneficiaries_paid * 100.0 / beneficiaries_registered)
         ELSE 0 END as utilization_pct,
    beneficiaries_registered as units_target,
    beneficiaries_paid as units_completed,
    'beneficiaries' as units_label, source_url
FROM pmkisan_district
UNION ALL
SELECT
    'JJM' as scheme, state, district, fin_year,
    funds_released_lakhs as allocated_lakhs,
    funds_released_lakhs as released_lakhs,
    funds_utilized_lakhs as expended_lakhs,
    CASE WHEN funds_released_lakhs > 0
         THEN (funds_utilized_lakhs / funds_released_lakhs * 100)
         ELSE 0 END as utilization_pct,
    total_households as units_target,
    households_with_tap as units_completed,
    'tap connections' as units_label, source_url
FROM jjm_district
UNION ALL
SELECT
    'PM POSHAN' as scheme, state, district, fin_year,
    funds_released_lakhs as allocated_lakhs,
    funds_released_lakhs as released_lakhs,
    funds_utilized_lakhs as expended_lakhs,
    utilization_pct,
    children_enrolled as units_target,
    children_fed as units_completed,
    'children fed' as units_label, source_url
FROM pmposhan_district
UNION ALL
SELECT
    'NSAP' as scheme, state, district, fin_year,
    NULL as allocated_lakhs,
    amount_paid_lakhs as released_lakhs,
    amount_paid_lakhs as expended_lakhs,
    CASE WHEN beneficiaries_eligible > 0
         THEN (beneficiaries_paid * 100.0 / beneficiaries_eligible)
         ELSE 0 END as utilization_pct,
    beneficiaries_eligible as units_target,
    beneficiaries_paid as units_completed,
    'pensioners' as units_label, source_url
FROM nsap_district
UNION ALL
SELECT
    'PDS/NFSA' as scheme, state, district, fin_year,
    allocation_mt as allocated_lakhs,
    allocation_mt as released_lakhs,
    offtake_mt as expended_lakhs,
    offtake_pct as utilization_pct,
    ration_cards_total as units_target,
    ration_cards_active as units_completed,
    'ration cards' as units_label, source_url
FROM nfsa_district;
"""


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()


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
    """
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
                    r.get("col_2_num", 0),  # Opening Balance (Entered OB)
                    r.get("col_3_num", 0),  # Release of Last FY received in Current FY
                    r.get("col_5_num", 0),  # Release from State Fund (col_4=Centre, col_5=State)
                    r.get("col_6_num", 0),  # Authorisation of EFMS
                    r.get("col_7_num", 0),  # Misc Receipt
                    r.get("col_9_num", 0),  # Total Availability (report col 14)
                    r.get("col_10_num", 0),  # Exp: Unskilled Wage (report col 16)
                    r.get("col_11_num", 0),  # Exp: Semi-skilled Wage (report col 17)
                    r.get("col_12_num", 0),  # Exp: Material (report col 18)
                    r.get("col_13_num", 0),  # Exp: Tax (report col 19)
                    # exp_total = sum of wage+material+tax (no single column in report)
                    r.get("col_10_num", 0) + r.get("col_11_num", 0) + r.get("col_12_num", 0) + r.get("col_13_num", 0),
                    r.get("col_14_num", 0),  # Admin: Rec Exp (report col 20)
                    r.get("col_15_num", 0),  # Admin: Non-Rec Exp (report col 21)
                    r.get("col_16_num", 0),  # Admin: Total (report col 22=20+21)
                    r.get("col_17_num", 0),  # Cumulative Expenditure (report col 23)
                    r.get("col_18_num", 0),  # % Utilization (report col 24)
                    r.get("col_19_num", 0),  # Balance (report col 25)
                    1,  # amounts_in_lakhs
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
    """Impute NSAP financial data from beneficiary counts × central pension rates.

    Formula: amount_paid_lakhs = beneficiaries_paid × pension_rate × 12 / 100000
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


if __name__ == "__main__":
    print("Loading latest scraped data into SQLite...")
    results = load_all_latest()
    print(f"\nDone. Database: {DB_PATH}")
    total = sum(results.values())
    print(f"Total records loaded: {total}")
