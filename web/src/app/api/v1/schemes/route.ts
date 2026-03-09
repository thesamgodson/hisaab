import { type NextRequest } from "next/server";

const SCHEME_NAMES = [
  "MGNREGA",
  "PMGSY",
  "PMAY-G",
  "PM Kisan",
  "JJM",
  "PM POSHAN",
  "NSAP",
  "PDS/NFSA",
];

function dataQualityWarnings(): Record<string, string[]> {
  return {
    "PM Kisan": [
      "28 of 36 states have only state-level aggregate records (district='ALL'), not district-level data.",
      "No allocation data — PM Kisan is a direct benefit transfer with no state-level allocation.",
    ],
    NSAP: [
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
    JJM: [
      "STATE-LEVEL: Allocation data from data.gov.in (2019-2023, jjm_allocation). Allocation only.",
      "No release/utilization data available publicly — ejalshakti.gov.in financial page uses JS rendering.",
      "DISTRICT-LEVEL: funds_released/utilized remain zero — API has no financial endpoint.",
      "Delivery metrics (coverage_pct, households_with_tap) available at district level.",
    ],
    MGNREGA: [
      "Financial amounts are in lakhs (amounts_in_lakhs=1 in financial_statement).",
    ],
    PMGSY: [
      "Amounts are in crores. Converted to lakhs (*100) in VIEWs.",
    ],
  };
}

export async function GET(_request: NextRequest) {
  const warnings = dataQualityWarnings();

  const schemes = SCHEME_NAMES.map((name) => ({
    name,
    warnings: warnings[name] ?? [],
  }));

  return Response.json({ schemes, count: schemes.length });
}
