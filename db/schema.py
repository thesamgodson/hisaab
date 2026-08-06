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
- SBM-G: sbm_district (ODF Plus village sanitation)
- DAY-NRLM: nrlm_district (SHG formation + revolving fund)

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
    release_from_centre REAL NOT NULL DEFAULT 0,
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
CREATE INDEX IF NOT EXISTS idx_fto_pendency_state ON fto_pendency(state, fin_year);
CREATE INDEX IF NOT EXISTS idx_scrape_runs_lookup ON scrape_runs(state, fin_year, report_name);

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
-- SBM-G: Swachh Bharat Mission - Gramin (ODF Plus village sanitation)
-- =====================================================================
CREATE TABLE IF NOT EXISTS sbm_district (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    district TEXT NOT NULL,
    state TEXT NOT NULL,
    state_code TEXT NOT NULL DEFAULT '',
    fin_year TEXT NOT NULL DEFAULT 'cumulative',
    total_villages INTEGER NOT NULL DEFAULT 0,
    odf_plus_villages INTEGER NOT NULL DEFAULT 0,
    odf_plus_pct REAL NOT NULL DEFAULT 0,
    one_star_villages INTEGER NOT NULL DEFAULT 0,
    three_star_villages INTEGER NOT NULL DEFAULT 0,
    five_star_villages INTEGER NOT NULL DEFAULT 0,
    model_village_pct REAL NOT NULL DEFAULT 0,
    source_url TEXT,
    scraped_at TEXT NOT NULL,
    UNIQUE(district, state, fin_year)
);
CREATE INDEX IF NOT EXISTS idx_sbm_district ON sbm_district(state, district);

-- DAY-NRLM: National Rural Livelihoods Mission (SHG formation + revolving fund)
CREATE TABLE IF NOT EXISTS nrlm_district (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    district TEXT NOT NULL,
    state TEXT NOT NULL,
    state_code TEXT NOT NULL DEFAULT '',
    fin_year TEXT NOT NULL DEFAULT 'cumulative',
    shgs_total INTEGER NOT NULL DEFAULT 0,
    shgs_new INTEGER NOT NULL DEFAULT 0,
    shgs_revived INTEGER NOT NULL DEFAULT 0,
    shgs_pre_nrlm INTEGER NOT NULL DEFAULT 0,
    members_total INTEGER NOT NULL DEFAULT 0,
    rf_shgs_provided INTEGER NOT NULL DEFAULT 0,
    rf_amount_lakhs REAL NOT NULL DEFAULT 0,
    cif_shgs_provided INTEGER NOT NULL DEFAULT 0,
    cif_shgs_eligible INTEGER NOT NULL DEFAULT 0,
    cif_amount_lakhs REAL NOT NULL DEFAULT 0,
    source_url TEXT,
    scraped_at TEXT NOT NULL,
    UNIQUE(district, state, fin_year)
);
CREATE INDEX IF NOT EXISTS idx_nrlm_district ON nrlm_district(state, district);

-- =====================================================================
-- UDISE+: Unified District Information System for Education (state-level)
-- =====================================================================
CREATE TABLE IF NOT EXISTS udise_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    state TEXT NOT NULL,
    fin_year TEXT NOT NULL,
    total_schools INTEGER NOT NULL DEFAULT 0,
    schools_govt INTEGER NOT NULL DEFAULT 0,
    schools_pvt INTEGER NOT NULL DEFAULT 0,
    schools_rural INTEGER NOT NULL DEFAULT 0,
    schools_urban INTEGER NOT NULL DEFAULT 0,
    total_students INTEGER NOT NULL DEFAULT 0,
    total_teachers INTEGER NOT NULL DEFAULT 0,
    ptr_primary REAL NOT NULL DEFAULT 0,
    ptr_secondary REAL NOT NULL DEFAULT 0,
    ger_primary REAL NOT NULL DEFAULT 0,
    ger_secondary REAL NOT NULL DEFAULT 0,
    dropout_primary REAL NOT NULL DEFAULT 0,
    dropout_secondary REAL NOT NULL DEFAULT 0,
    schools_electricity_pct REAL NOT NULL DEFAULT 0,
    schools_drinkwater_pct REAL NOT NULL DEFAULT 0,
    schools_girls_toilet_pct REAL NOT NULL DEFAULT 0,
    schools_library_pct REAL NOT NULL DEFAULT 0,
    source_url TEXT,
    scraped_at TEXT NOT NULL,
    UNIQUE(state, fin_year)
);
CREATE INDEX IF NOT EXISTS idx_udise_state ON udise_state(state);

-- =====================================================================
-- Phase 6: State-level financial tables (from data.gov.in + dashboards)
-- =====================================================================

-- PM POSHAN state-level financial data (data.gov.in, 2016-2025)
CREATE TABLE IF NOT EXISTS pmposhan_finance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    state TEXT NOT NULL,
    fin_year TEXT NOT NULL,
    allocated_lakhs REAL NOT NULL DEFAULT 0,
    released_lakhs REAL NOT NULL DEFAULT 0,
    utilized_lakhs REAL NOT NULL DEFAULT 0,
    source_url TEXT,
    scraped_at TEXT NOT NULL,
    UNIQUE(state, fin_year)
);
CREATE INDEX IF NOT EXISTS idx_pmposhan_finance ON pmposhan_finance(state);

-- NSAP state-level real release data (replaces imputation at state level)
CREATE TABLE IF NOT EXISTS nsap_finance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    state TEXT NOT NULL,
    fin_year TEXT NOT NULL,
    released_lakhs REAL NOT NULL DEFAULT 0,
    beneficiaries INTEGER NOT NULL DEFAULT 0,
    source_url TEXT,
    scraped_at TEXT NOT NULL,
    UNIQUE(state, fin_year)
);
CREATE INDEX IF NOT EXISTS idx_nsap_finance ON nsap_finance(state);

-- NFSA state-level allocation + offtake in metric tonnes
CREATE TABLE IF NOT EXISTS nfsa_allocation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    state TEXT NOT NULL,
    fin_year TEXT NOT NULL,
    grain_type TEXT NOT NULL DEFAULT 'total',
    allocation_mt REAL NOT NULL DEFAULT 0,
    offtake_mt REAL NOT NULL DEFAULT 0,
    source_url TEXT,
    scraped_at TEXT NOT NULL,
    UNIQUE(state, fin_year, grain_type)
);
CREATE INDEX IF NOT EXISTS idx_nfsa_allocation ON nfsa_allocation(state);

-- JJM state-level allocation (data.gov.in, allocation only — no release/utilization)
CREATE TABLE IF NOT EXISTS jjm_allocation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    state TEXT NOT NULL,
    fin_year TEXT NOT NULL,
    allocated_crores REAL NOT NULL DEFAULT 0,
    released_crores REAL NOT NULL DEFAULT 0,
    expended_crores REAL NOT NULL DEFAULT 0,
    source_url TEXT,
    scraped_at TEXT NOT NULL,
    UNIQUE(state, fin_year)
);
CREATE INDEX IF NOT EXISTS idx_jjm_allocation ON jjm_allocation(state);

-- PMAY-G state-level financial data (dashboard.dord.gov.in)
CREATE TABLE IF NOT EXISTS pmayg_finance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    state TEXT NOT NULL,
    fin_year TEXT NOT NULL,
    allocated_lakhs REAL NOT NULL DEFAULT 0,
    released_lakhs REAL NOT NULL DEFAULT 0,
    utilized_lakhs REAL NOT NULL DEFAULT 0,
    source_url TEXT,
    scraped_at TEXT NOT NULL,
    UNIQUE(state, fin_year)
);
CREATE INDEX IF NOT EXISTS idx_pmayg_finance ON pmayg_finance(state);

-- =====================================================================
-- VIEW 1: scheme_finance — Financial flow (rupees in lakhs only)
-- =====================================================================
-- Schemes with financial data: MGNREGA, PMGSY, PM Kisan (district-level),
-- PM POSHAN, NSAP, PMAY-G, JJM (state-level from data.gov.in/dashboards).
-- NFSA excluded: metric tons, not rupees.
--
-- Every utilization_pct CASE falls back to NULL, never 0: a missing
-- denominator means "not reported", and a fabricated 0% renders as a real
-- "Poor" score on the public pages. Scoring already skips non-positive
-- utilization (queries/composite.py), so NULL is the honest encoding.

DROP VIEW IF EXISTS scheme_finance;
CREATE VIEW scheme_finance AS
SELECT
    'MGNREGA' as scheme, state, district, fin_year,
    NULL as allocated_lakhs,
    total_availability as released_lakhs,
    cumulative_expenditure as expended_lakhs,
    utilization_pct, source_url
FROM financial_statement
UNION ALL
SELECT
    'PMGSY' as scheme, state, district, fin_year,
    NULL as allocated_lakhs,
    value_of_projects_cr * 100 as released_lakhs,
    expenditure_cr * 100 as expended_lakhs,
    CASE WHEN value_of_projects_cr > 0
         THEN (expenditure_cr / value_of_projects_cr * 100)
         ELSE NULL END as utilization_pct,
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
         ELSE NULL END as utilization_pct,
    source_url
FROM pmkisan_district
UNION ALL
SELECT
    'PM POSHAN' as scheme, state, 'ALL' as district, fin_year,
    allocated_lakhs, released_lakhs, utilized_lakhs as expended_lakhs,
    CASE WHEN released_lakhs > 0
         THEN (utilized_lakhs / released_lakhs * 100)
         ELSE NULL END as utilization_pct,
    source_url
FROM pmposhan_finance
UNION ALL
SELECT
    'NSAP' as scheme, state, 'ALL' as district, fin_year,
    NULL as allocated_lakhs,
    released_lakhs,
    released_lakhs as expended_lakhs,
    NULL as utilization_pct,
    source_url
FROM nsap_finance
UNION ALL
SELECT
    'PMAY-G' as scheme, state, 'ALL' as district, fin_year,
    allocated_lakhs, released_lakhs, utilized_lakhs as expended_lakhs,
    CASE WHEN released_lakhs > 0
         THEN (utilized_lakhs / released_lakhs * 100)
         ELSE NULL END as utilization_pct,
    source_url
FROM pmayg_finance
UNION ALL
SELECT
    'JJM' as scheme, state, 'ALL' as district, fin_year,
    allocated_crores * 100 as allocated_lakhs,
    CASE WHEN released_crores > 0 THEN released_crores * 100 ELSE NULL END as released_lakhs,
    CASE WHEN expended_crores > 0 THEN expended_crores * 100 ELSE NULL END as expended_lakhs,
    CASE WHEN released_crores > 0 AND expended_crores > 0
         THEN (expended_crores / released_crores * 100)
         ELSE NULL END as utilization_pct,
    source_url
FROM jjm_allocation
UNION ALL
-- DAY-NRLM district-level SHG community funds: Revolving Fund + Community
-- Investment Fund (both cumulative, rupees/1e5 from the LokOS FDM feed) — a
-- district money metric almost no other scheme provides. utilization_pct is
-- NULL: LokOS publishes no allocated/utilized split, and composite scoring
-- only counts scheme_finance rows with a non-null utilization_pct, so exposing
-- NRLM money here does not perturb any district score.
SELECT
    'DAY-NRLM' as scheme, state, district, fin_year,
    NULL as allocated_lakhs,
    (rf_amount_lakhs + cif_amount_lakhs) as released_lakhs,
    (rf_amount_lakhs + cif_amount_lakhs) as expended_lakhs,
    NULL as utilization_pct,
    source_url
FROM nrlm_district;

-- =====================================================================
-- VIEW 2: scheme_delivery — Service delivery / beneficiary coverage
-- =====================================================================
-- All schemes with units tracking. Each row has a units_label for semantic clarity.

DROP VIEW IF EXISTS scheme_delivery;
CREATE VIEW scheme_delivery AS
SELECT
    'PMGSY' as scheme, state, district, fin_year,
    roads_sanctioned as units_target,
    roads_completed as units_completed,
    'roads' as units_label,
    CASE WHEN roads_sanctioned > 0
         THEN (roads_completed * 100.0 / roads_sanctioned)
         ELSE NULL END as delivery_pct,
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
         ELSE NULL END as delivery_pct,
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
    -- children_fed is a DAILY reporting snapshot (CLAIM-2026-0006); dividing
    -- it by total enrollment is not a delivery rate. No percentage published.
    'PM POSHAN' as scheme, state, district, fin_year,
    NULL as units_target,
    children_fed as units_completed,
    'children fed (daily snapshot)' as units_label,
    NULL as delivery_pct,
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
         ELSE NULL END as delivery_pct,
    source_url
FROM nsap_district
UNION ALL
SELECT
    -- active = total by construction in the source (CLAIM-2026-0008) — an
    -- active/total ratio would always read 100%. Card counts published as a
    -- stock figure, not a delivery rate.
    'PDS/NFSA' as scheme, state, district, fin_year,
    NULL as units_target,
    ration_cards_total as units_completed,
    'ration cards' as units_label,
    NULL as delivery_pct,
    source_url
FROM nfsa_district
UNION ALL
SELECT
    'SBM-G' as scheme, state, district, fin_year,
    total_villages as units_target,
    odf_plus_villages as units_completed,
    'ODF+ villages' as units_label,
    odf_plus_pct as delivery_pct, source_url
FROM sbm_district
UNION ALL
SELECT
    'DAY-NRLM' as scheme, state, district, fin_year,
    NULL as units_target,
    shgs_total as units_completed,
    'SHGs' as units_label,
    NULL as delivery_pct, source_url
FROM nrlm_district
UNION ALL
SELECT
    'UDISE+' as scheme, state, 'ALL' as district, fin_year,
    NULL as units_target,
    total_schools as units_completed,
    'schools' as units_label,
    NULL as delivery_pct, source_url
FROM udise_state;

-- =====================================================================
-- VIEW 3: money_flow — Backward-compatible combined view
-- =====================================================================
-- Includes both district-level data (from _district tables, may be hollow)
-- and state-level finance data (from _finance/_allocation tables, real data).
-- NFSA district rows still use MT (not lakhs) — use scheme_finance for clean comparisons.

-- =====================================================================
-- Telegram subscriber table — stores chat IDs for alert delivery
-- =====================================================================
CREATE TABLE IF NOT EXISTS telegram_subscribers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER UNIQUE NOT NULL,
    username TEXT,
    subscribed_states TEXT DEFAULT 'ALL',
    subscribed_at TEXT NOT NULL DEFAULT (datetime('now')),
    active INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_telegram_subscribers_active
    ON telegram_subscribers(active, subscribed_states);

-- =====================================================================
-- Constituency mapping tables (PIN → District → Constituency → MP)
-- =====================================================================

CREATE TABLE IF NOT EXISTS pin_district_mapping (
    pin_code TEXT PRIMARY KEY,
    district TEXT NOT NULL,
    state TEXT NOT NULL,
    office_name TEXT
);
CREATE INDEX IF NOT EXISTS idx_pin_district ON pin_district_mapping(district, state);

CREATE TABLE IF NOT EXISTS pin_constituency (
    pin_code TEXT PRIMARY KEY,
    constituency TEXT NOT NULL,
    state TEXT NOT NULL,
    method TEXT NOT NULL DEFAULT 'spatial_join'
);
CREATE INDEX IF NOT EXISTS idx_pin_constituency ON pin_constituency(constituency, state);

-- PIN centroids from GeoNames postal localities (CC BY 4.0) — powers the
-- "use my location" nearest-PIN lookup. lat/lng are the MEDIAN of the PIN's
-- locality coordinates (robust to bad geocodes); spread_km records how far
-- the localities scatter, as a per-PIN quality signal (CLAIM-2026-0038).
CREATE TABLE IF NOT EXISTS pin_geo (
    pin_code TEXT PRIMARY KEY,
    lat REAL NOT NULL,
    lng REAL NOT NULL,
    locality_count INTEGER,
    spread_km REAL,
    source TEXT,
    scraped_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_pin_geo_latlng ON pin_geo(lat, lng);

-- India reuses PC names across states, and two states can even share a PC
-- name AND a district name (HAMIRPUR/HAMIRPUR in UP and HP) — uniqueness
-- must include state or one state's row silently vanishes at ingest.
CREATE TABLE IF NOT EXISTS constituency_district (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    constituency TEXT NOT NULL,
    state TEXT NOT NULL,
    district TEXT NOT NULL,
    constituency_type TEXT NOT NULL DEFAULT 'LOK_SABHA',
    UNIQUE(constituency, state, district)
);
CREATE INDEX IF NOT EXISTS idx_constituency_district ON constituency_district(constituency, state);
CREATE INDEX IF NOT EXISTS idx_constituency_district_district ON constituency_district(district, state);

-- India reuses PC names across states (AURANGABAD is a Bihar seat and a
-- Maharashtra seat), so uniqueness must be per (constituency, state).
CREATE TABLE IF NOT EXISTS mp_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    constituency TEXT NOT NULL,
    mp_name TEXT NOT NULL,
    party TEXT NOT NULL DEFAULT '',
    state TEXT NOT NULL,
    elected_year INTEGER NOT NULL DEFAULT 2024,
    margin_votes INTEGER,
    source_url TEXT,
    UNIQUE(constituency, state)
);
CREATE INDEX IF NOT EXISTS idx_mp_info_constituency ON mp_info(constituency, state);

-- Assembly Constituency → District mapping
CREATE TABLE IF NOT EXISTS ac_district (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ac_name TEXT NOT NULL,
    ac_no INTEGER,
    state TEXT NOT NULL,
    district TEXT NOT NULL,
    pc_name TEXT,
    UNIQUE(ac_name, state, district)
);
CREATE INDEX IF NOT EXISTS idx_ac_district ON ac_district(district, state);
CREATE INDEX IF NOT EXISTS idx_ac_name ON ac_district(ac_name, state);

-- MLA info (similar to mp_info)
CREATE TABLE IF NOT EXISTS mla_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ac_name TEXT NOT NULL,
    ac_no INTEGER,
    state TEXT NOT NULL,
    mla_name TEXT NOT NULL,
    party TEXT NOT NULL DEFAULT '',
    elected_year INTEGER NOT NULL DEFAULT 2024,
    source_url TEXT,
    UNIQUE(ac_name, state)
);
CREATE INDEX IF NOT EXISTS idx_mla_info ON mla_info(ac_name, state);

-- District officials (Collector, DM, SP, CDO, etc.) for citizen action briefs
CREATE TABLE IF NOT EXISTS district_officials (
    state           TEXT NOT NULL,
    district        TEXT NOT NULL,
    role            TEXT NOT NULL,
    name            TEXT NOT NULL,
    phone           TEXT,
    email           TEXT,
    office_address  TEXT,
    source_url      TEXT NOT NULL,
    scraped_at      TEXT NOT NULL,
    PRIMARY KEY (state, district, role)
);
CREATE INDEX IF NOT EXISTS idx_officials_district ON district_officials(district, state);

-- Grievance channels per scheme — portals, helplines, escalation paths
CREATE TABLE IF NOT EXISTS grievance_channels (
    scheme              TEXT NOT NULL,  -- scheme name, or 'ALL' for universal channels (CPGRAMS, RTI)
    level               TEXT NOT NULL,  -- local | district | state | national
    authority           TEXT,           -- WHO hears this rung (Programme Officer, Collector, Ombudsperson…)
    portal_name         TEXT NOT NULL,
    portal_url          TEXT NOT NULL,
    phone               TEXT,           -- only if printed on an official page
    description         TEXT,           -- HOW: what to do at this rung, one sentence
    escalation_scheme   TEXT,
    source_url          TEXT NOT NULL,
    scraped_at          TEXT NOT NULL,
    PRIMARY KEY (scheme, level, portal_name)
);
CREATE INDEX IF NOT EXISTS idx_grievance_scheme ON grievance_channels(scheme);

-- WHY a citizen should complain: the legal entitlement per scheme, in plain
-- language, with its statutory basis. Curated from acts/guidelines — every
-- row carries the official source it was verified against.
CREATE TABLE IF NOT EXISTS scheme_entitlements (
    scheme          TEXT PRIMARY KEY,
    entitlement     TEXT NOT NULL,  -- what the citizen is owed, one sentence
    legal_basis     TEXT NOT NULL,  -- act + section / guideline + clause
    complain_when   TEXT,           -- JSON array of concrete trigger conditions
    source_url      TEXT NOT NULL,
    scraped_at      TEXT NOT NULL
);

-- District lineage — tracks district splits/reorganizations so the UI
-- can show "formerly part of <parent>" when a new district was carved out.
CREATE TABLE IF NOT EXISTS district_lineage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    new_district TEXT NOT NULL,
    parent_district TEXT NOT NULL,
    state TEXT NOT NULL,
    split_year INTEGER NOT NULL,
    UNIQUE(new_district, state)
);
CREATE INDEX IF NOT EXISTS idx_lineage_lookup ON district_lineage(new_district, state);

-- =====================================================================
-- Temporal snapshot table — weekly metric captures for trend analysis
-- =====================================================================
CREATE TABLE IF NOT EXISTS metrics_snapshot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_date TEXT NOT NULL,
    scheme TEXT NOT NULL,
    state TEXT NOT NULL,
    district TEXT NOT NULL,
    fin_year TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL,
    source_url TEXT,
    UNIQUE(snapshot_date, scheme, state, district, fin_year, metric_name)
);
CREATE INDEX IF NOT EXISTS idx_snapshot_lookup
    ON metrics_snapshot(scheme, state, district, metric_name);

-- =====================================================================
-- Precomputed composite accountability scores — written at load time by
-- queries/composite.py:persist_district_scores(). Every serving surface
-- (web, CLI, briefs) reads this table; nothing recomputes the formula.
-- =====================================================================
CREATE TABLE IF NOT EXISTS district_scores (
    district            TEXT NOT NULL,
    state               TEXT NOT NULL,
    fin_year            TEXT NOT NULL,
    score               REAL,               -- NULL when schemes_count < minimum
    grade               TEXT,
    schemes_count       INTEGER NOT NULL DEFAULT 0,
    schemes_with_data   TEXT NOT NULL DEFAULT '[]',   -- JSON array
    red_flags           TEXT NOT NULL DEFAULT '[]',   -- JSON array
    delivery_avg        REAL,
    delivery_schemes    TEXT NOT NULL DEFAULT '[]',   -- JSON array
    finance_avg         REAL,
    finance_schemes     TEXT NOT NULL DEFAULT '[]',   -- JSON array
    governance_score    REAL,
    computed_at         TEXT NOT NULL,
    PRIMARY KEY (district, state, fin_year)
);
CREATE INDEX IF NOT EXISTS idx_district_scores_state ON district_scores(state, fin_year);
CREATE INDEX IF NOT EXISTS idx_district_scores_score ON district_scores(fin_year, score);

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
         ELSE NULL END as utilization_pct,
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
         ELSE NULL END as utilization_pct,
    houses_sanctioned as units_target,
    houses_completed as units_completed,
    'houses' as units_label, source_url
FROM pmayg_district
UNION ALL
SELECT
    'PMAY-G' as scheme, state, 'ALL' as district, fin_year,
    allocated_lakhs, released_lakhs,
    utilized_lakhs as expended_lakhs,
    CASE WHEN released_lakhs > 0
         THEN (utilized_lakhs / released_lakhs * 100)
         ELSE NULL END as utilization_pct,
    NULL as units_target, NULL as units_completed,
    NULL as units_label, source_url
FROM pmayg_finance
UNION ALL
SELECT
    'PM Kisan' as scheme, state, district, fin_year,
    NULL as allocated_lakhs,
    amount_paid_lakhs as released_lakhs,
    amount_paid_lakhs as expended_lakhs,
    CASE WHEN beneficiaries_registered > 0
         THEN (beneficiaries_paid * 100.0 / beneficiaries_registered)
         ELSE NULL END as utilization_pct,
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
         ELSE NULL END as utilization_pct,
    total_households as units_target,
    households_with_tap as units_completed,
    'tap connections' as units_label, source_url
FROM jjm_district
UNION ALL
SELECT
    'JJM' as scheme, state, 'ALL' as district, fin_year,
    allocated_crores * 100 as allocated_lakhs,
    CASE WHEN released_crores > 0 THEN released_crores * 100 ELSE NULL END as released_lakhs,
    CASE WHEN expended_crores > 0 THEN expended_crores * 100 ELSE NULL END as expended_lakhs,
    CASE WHEN released_crores > 0 AND expended_crores > 0
         THEN (expended_crores / released_crores * 100)
         ELSE NULL END as utilization_pct,
    NULL as units_target, NULL as units_completed,
    NULL as units_label, source_url
FROM jjm_allocation
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
    'PM POSHAN' as scheme, state, 'ALL' as district, fin_year,
    allocated_lakhs, released_lakhs,
    utilized_lakhs as expended_lakhs,
    CASE WHEN released_lakhs > 0
         THEN (utilized_lakhs / released_lakhs * 100)
         ELSE NULL END as utilization_pct,
    NULL as units_target, NULL as units_completed,
    NULL as units_label, source_url
FROM pmposhan_finance
UNION ALL
SELECT
    -- NSAP is three pension sub-schemes (IGNOAPS/IGNWPS/IGNDPS) stored as
    -- three rows per district-year. Emitted un-aggregated they are
    -- indistinguishable here (no scheme_type column), so a consumer picking
    -- "the NSAP row" showed one arbitrary sub-scheme as the district's whole
    -- pension picture. The district total is the only honest single row.
    'NSAP' as scheme, state, district, fin_year,
    NULL as allocated_lakhs,
    SUM(amount_paid_lakhs) as released_lakhs,
    SUM(amount_paid_lakhs) as expended_lakhs,
    CASE WHEN SUM(beneficiaries_eligible) > 0
         THEN (SUM(beneficiaries_paid) * 100.0 / SUM(beneficiaries_eligible))
         ELSE NULL END as utilization_pct,
    NULLIF(SUM(beneficiaries_eligible), 0) as units_target,
    SUM(beneficiaries_paid) as units_completed,
    'pensioners' as units_label, MAX(source_url) as source_url
FROM nsap_district
GROUP BY state, district, fin_year
UNION ALL
SELECT
    'NSAP' as scheme, state, 'ALL' as district, fin_year,
    NULL as allocated_lakhs,
    released_lakhs,
    released_lakhs as expended_lakhs,
    NULL as utilization_pct,
    NULL as units_target,
    beneficiaries as units_completed,
    'pensioners' as units_label, source_url
FROM nsap_finance
UNION ALL
SELECT
    -- allocation/offtake are METRIC TONNES, never rupees — they must not
    -- flow into *_lakhs columns. Card counts are a stock, not delivery.
    -- offtake_pct is 0 for every district row (no district-level offtake is
    -- published at all), so surfacing it read as a real 0% utilization.
    'PDS/NFSA' as scheme, state, district, fin_year,
    NULL as allocated_lakhs,
    NULL as released_lakhs,
    NULL as expended_lakhs,
    NULL as utilization_pct,
    NULL as units_target,
    ration_cards_total as units_completed,
    'ration cards' as units_label, source_url
FROM nfsa_district
UNION ALL
SELECT
    -- released/expended = Revolving Fund + Community Investment Fund, the two
    -- district-level SHG money streams the LokOS FDM feed publishes (both
    -- cumulative, rupees/1e5). rf_amount_lakhs alone was CLAIM-2026-0027's basis;
    -- the combined figure is CLAIM-2026-0033.
    'DAY-NRLM' as scheme, state, district, fin_year,
    NULL as allocated_lakhs,
    (rf_amount_lakhs + cif_amount_lakhs) as released_lakhs,
    (rf_amount_lakhs + cif_amount_lakhs) as expended_lakhs,
    NULL as utilization_pct,
    NULL as units_target,
    shgs_total as units_completed,
    'SHGs' as units_label, source_url
FROM nrlm_district;
"""
