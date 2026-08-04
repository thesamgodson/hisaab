/**
 * Per-scheme data-quality caveats — the manifesto-critical provenance text.
 *
 * SINGLE SOURCE for the web app (served by /api/v1/schemes and
 * /api/v1/data-quality). Mirrors queries/common.py:data_quality_warnings();
 * update both together when a caveat changes.
 */

export const ALL_SCHEME_NAMES = [
  "MGNREGA",
  "PMGSY",
  "PMAY-G",
  "PM Kisan",
  "JJM",
  "PM POSHAN",
  "NSAP",
  "PDS/NFSA",
  "SBM-G",
  "DAY-NRLM",
  "UDISE+",
];

export function dataQualityWarnings(): Record<string, string[]> {
  return {
    MGNREGA: [
      "Financial amounts are in lakhs (amounts_in_lakhs=1 in financial_statement).",
    ],
    PMGSY: ["Amounts are in crores. Converted to lakhs (*100) in VIEWs."],
    "PMAY-G": [
      "STATE-LEVEL: Allocation + release + utilization from data.gov.in (2019-2026, pmayg_finance). ~45% of rows have release=0 (allocation present).",
      "DISTRICT-LEVEL: funds_released/utilized remain zero — FinancialProgressRpt.aspx requires login.",
      "Delivery metrics (houses_sanctioned/completed) available at district level.",
    ],
    "PM Kisan": [
      "28 of 36 states have only state-level aggregate records (district='ALL'), not district-level data.",
      "No allocation data — PM Kisan is a direct benefit transfer with no state-level allocation.",
    ],
    JJM: [
      "STATE-LEVEL: Allocation/release/expenditure from ejalshakti.gov.in (2019-2025, jjm_allocation).",
      "DISTRICT-LEVEL: funds_released/utilized remain zero — API has no financial endpoint.",
      "Delivery metrics (coverage_pct, households_with_tap) available at district level.",
    ],
    "PM POSHAN": [
      "STATE-LEVEL: Real allocation + release + utilization from data.gov.in (2016-2025, pmposhan_finance).",
      "DISTRICT-LEVEL: funds_released/utilized remain zero — portal does not expose district financial data.",
      "children_fed is a DAILY reporting snapshot (CLAIM-2026-0006) — no feeding percentage is published because fed/enrolled is not a delivery rate.",
    ],
    NSAP: [
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
  };
}
