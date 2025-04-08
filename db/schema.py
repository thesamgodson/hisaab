"""SQL schema for Hisaab — CREATE TABLE and CREATE VIEW statements.

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
