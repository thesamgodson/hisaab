import { query, queryOne } from "@/lib/db";
import { getStateAccountRecords } from "@/lib/state-account";

export type EvidenceUnit = "count" | "INR lakh" | "INR crore" | "km" | "MT";
export type EvidenceDimension = "money" | "delivery" | "process";

export interface EvidenceMetric {
  label: string;
  value: number;
  unit: EvidenceUnit;
}

export interface EvidenceRecord {
  id: string;
  scheme: string;
  title: string;
  dimension: EvidenceDimension;
  period: string;
  scope: "district" | "state";
  metrics: EvidenceMetric[];
  missingMetrics?: string[];
  sourceUrl: string;
  asOf: string;
  retrievedAt: string;
  claimId: string;
  note?: string;
}

export interface AreaAccount {
  districtRecords: EvidenceRecord[];
  stateRecords: EvidenceRecord[];
  missingDistrictSchemes: string[];
}

interface SourceRow {
  fin_year: string;
  source_url: string;
  scraped_at: string;
}

type FinanceRow = SourceRow & { total_availability: number; cumulative_expenditure: number };
type FtoRow = SourceRow & { total_fto_generated: number; first_signatory_pending: number; second_signatory_pending: number };
type PmgsyRow = SourceRow & { roads_sanctioned: number; roads_completed: number; length_sanctioned_km: number; length_completed_km: number; value_of_projects_cr: number; expenditure_cr: number };
type PmayRow = SourceRow & { houses_sanctioned: number; houses_completed: number };
type PmkisanRow = SourceRow & { installment: string; beneficiaries_paid: number };
type JjmRow = SourceRow & { total_households: number; households_with_tap: number };
type PoshanRow = SourceRow & { children_fed: number };
type NfsaRow = SourceRow & { ration_cards_total: number; beneficiaries_total: number; date_of_data: string | null };
type SbmRow = SourceRow & { total_villages: number; odf_plus_villages: number };
type NrlmRow = SourceRow & {
  state_code: string;
  shgs_total: number;
  rf_shgs_provided: number;
  rf_amount_lakhs: number;
  cif_shgs_provided: number;
  cif_shgs_eligible: number;
  cif_amount_lakhs: number;
};
type UdiseRow = SourceRow & { total_schools: number; total_students: number };
type NsapDistrictRow = SourceRow & { scheme_type: string; beneficiaries_paid: number; source_month: string };

const DISTRICT_SCHEMES = [
  "MGNREGA", "PMGSY", "PMAY-G", "PM Kisan", "JJM",
  "PM POSHAN", "PDS/NFSA", "SBM-G", "DAY-NRLM", "NSAP",
];

const NSAP_TITLES: Record<string, string> = {
  IGNDPS: "Disability pension beneficiaries",
  IGNOAPS: "Old-age pension beneficiaries",
  IGNWPS: "Widow pension beneficiaries",
};

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

function nsapRecordDate(row: NsapDistrictRow): string {
  const month = Number(row.source_month);
  const startYear = Number(row.fin_year.slice(0, 4));
  if (!Number.isInteger(month) || month < 1 || month > 12 || !Number.isInteger(startYear)) {
    return `FY ${row.fin_year}; source month not retained`;
  }
  const year = month >= 4 ? startYear : startYear + 1;
  return `${MONTHS[month - 1]} ${year}`;
}

function yearLabel(value: string): string {
  return value === "cumulative" ? "Cumulative record" : `FY ${value}`;
}

async function latestDistrictRow<T extends SourceRow>(
  table: string,
  columns: string,
  district: string,
  state: string,
  orderBy = "fin_year DESC, scraped_at DESC",
): Promise<T | null> {
  return queryOne<T>(
    `SELECT ${columns}, fin_year, source_url, scraped_at
     FROM ${table}
     WHERE district = ? AND state = ?
     ORDER BY ${orderBy}
     LIMIT 1`,
    [district, state],
  );
}

function record(
  row: SourceRow,
  values: Omit<EvidenceRecord, "period" | "sourceUrl" | "retrievedAt"> & { period?: string },
): EvidenceRecord {
  return {
    ...values,
    period: values.period ?? yearLabel(row.fin_year),
    sourceUrl: row.source_url,
    retrievedAt: row.scraped_at,
  };
}

function mgnregaRecords(
  finance: FinanceRow | null,
  fto: FtoRow | null,
): EvidenceRecord[] {
  const records: EvidenceRecord[] = [];
  if (finance) records.push(record(finance, {
    id: "mgnrega-finance",
    scheme: "MGNREGA",
    title: "Financial statement",
    dimension: "money",
    scope: "district",
    claimId: "CLAIM-2026-0025",
    asOf: `FY ${finance.fin_year}`,
    metrics: [
      { label: "Funds available", value: finance.total_availability, unit: "INR lakh" },
      { label: "Cumulative expenditure", value: finance.cumulative_expenditure, unit: "INR lakh" },
    ],
    note: "Expenditure can exceed funds available because the report carries pending liabilities.",
  }));
  if (fto) records.push(record(fto, {
    id: "mgnrega-fto",
    scheme: "MGNREGA",
    title: "Fund transfer process",
    dimension: "process",
    scope: "district",
    claimId: "CLAIM-2026-0026",
    asOf: `FY ${fto.fin_year}`,
    metrics: [{ label: "FTOs generated", value: fto.total_fto_generated, unit: "count" }],
  }));
  if (fto) records.push(record(fto, {
    id: "mgnrega-signatures",
    scheme: "MGNREGA",
    title: "Signature pendency",
    dimension: "process",
    scope: "district",
    claimId: "CLAIM-2026-0043",
    asOf: `FY ${fto.fin_year}`,
    metrics: [
      { label: "Awaiting first signature", value: fto.first_signatory_pending, unit: "count" },
      { label: "Awaiting second signature", value: fto.second_signatory_pending, unit: "count" },
    ],
    note: "These are district process counts, not the status of an individual wage payment.",
  }));
  return records;
}

function nrlmRecords(row: NrlmRow | null): EvidenceRecord[] {
  if (!row) return [];
  const root = `https://cdn.lokos.in/lokos-in/fdm/prod/${row.state_code}`;
  const common = { scheme: "DAY-NRLM", scope: "district" as const, period: "Cumulative record" };
  return [
    record(row, {
      ...common,
      id: "nrlm-shgs",
      title: "Self-help groups",
      dimension: "delivery",
      claimId: "CLAIM-2026-0027",
      asOf: "9 Jun 2026",
      metrics: [{ label: "SHGs recorded", value: row.shgs_total, unit: "count" }],
    }),
    {
      ...record(row, {
        ...common,
        id: "nrlm-rf",
        title: "Revolving Fund",
        dimension: "money",
        claimId: "CLAIM-2026-0027",
        asOf: "9 Jun 2026",
        metrics: [
          { label: "SHGs receiving fund", value: row.rf_shgs_provided, unit: "count" },
          { label: "Funds received", value: row.rf_amount_lakhs, unit: "INR lakh" },
        ],
        note: "Cumulative money received by SHGs, not expenditure.",
      }),
      sourceUrl: `${root}/DISTRICT_FDM_REVOLVINGFUND.json`,
    },
    {
      ...record(row, {
        ...common,
        id: "nrlm-cif",
        title: "Community Investment Fund",
        dimension: "money",
        claimId: "CLAIM-2026-0033",
        asOf: "9 Jun 2026",
        metrics: [
          { label: "SHGs eligible", value: row.cif_shgs_eligible, unit: "count" },
          { label: "SHGs receiving fund", value: row.cif_shgs_provided, unit: "count" },
          { label: "Funds received", value: row.cif_amount_lakhs, unit: "INR lakh" },
        ],
        note: "Cumulative money received by SHGs, not expenditure.",
      }),
      sourceUrl: `${root}/DISTRICT_FDM_COMMUNITYINVESTMENTFUND.json`,
    },
  ];
}

async function fetchWorkAndDelivery(district: string, state: string) {
  return Promise.all([
    latestDistrictRow<FinanceRow>("financial_statement", "total_availability, cumulative_expenditure", district, state),
    latestDistrictRow<FtoRow>("fto_status", "total_fto_generated, first_signatory_pending, second_signatory_pending", district, state),
    latestDistrictRow<PmgsyRow>("pmgsy_district", "roads_sanctioned, roads_completed, length_sanctioned_km, length_completed_km, value_of_projects_cr, expenditure_cr", district, state),
    latestDistrictRow<PmayRow>("pmayg_district", "houses_sanctioned, houses_completed", district, state),
    queryOne<PmkisanRow>(
      `SELECT installment, beneficiaries_paid, fin_year, source_url, scraped_at
       FROM pmkisan_district
       WHERE district = ? AND state = ? AND installment = '22' AND fin_year = '2025-2026'
       ORDER BY scraped_at DESC LIMIT 1`,
      [district, state],
    ),
    latestDistrictRow<JjmRow>("jjm_district", "total_households, households_with_tap", district, state),
    latestDistrictRow<PoshanRow>("pmposhan_district", "children_fed", district, state),
  ]);
}

async function fetchOtherRecords(district: string, state: string) {
  return Promise.all([
    latestDistrictRow<NfsaRow>("nfsa_district", "ration_cards_total, beneficiaries_total, date_of_data", district, state),
    latestDistrictRow<SbmRow>("sbm_district", "total_villages, odf_plus_villages", district, state),
    latestDistrictRow<NrlmRow>(
      "nrlm_district",
      "state_code, shgs_total, rf_shgs_provided, rf_amount_lakhs, cif_shgs_provided, cif_shgs_eligible, cif_amount_lakhs",
      district,
      state,
    ),
    queryOne<UdiseRow>(
      `SELECT fin_year, total_schools, total_students, source_url, scraped_at
       FROM udise_state WHERE state = ? ORDER BY fin_year DESC, scraped_at DESC LIMIT 1`,
      [state],
    ),
    query<NsapDistrictRow>(
      `SELECT scheme_type, beneficiaries_paid, source_month, fin_year, source_url, scraped_at
       FROM nsap_district
       WHERE district = ? AND state = ?
         AND fin_year = (SELECT MAX(fin_year) FROM nsap_district WHERE district = ? AND state = ?)
       ORDER BY scheme_type`,
      [district, state, district, state],
    ),
  ]);
}

function nsapRecords(rows: NsapDistrictRow[]): EvidenceRecord[] {
  return rows.map((row) => record(row, {
    id: `nsap-${row.scheme_type.toLowerCase()}`,
    scheme: "NSAP",
    title: NSAP_TITLES[row.scheme_type] ?? `${row.scheme_type} beneficiaries`,
    dimension: "delivery",
    scope: "district",
    claimId: "CLAIM-2026-0047",
    asOf: nsapRecordDate(row),
    metrics: [{ label: "Beneficiaries paid", value: row.beneficiaries_paid, unit: "count" }],
    note: "This is a beneficiary count for one pension programme. Hisaab omits the annualized central-share estimate because it is imputed, not reported district spending.",
  }));
}

function pmgsyRecords(row: PmgsyRow | null): EvidenceRecord[] {
  if (!row) return [];
  const common = {
    scheme: "PMGSY",
    scope: "district" as const,
    claimId: "CLAIM-2026-0042",
    asOf: "Programme year 2025",
  };
  return [
    record(row, {
      ...common,
      id: "pmgsy-money",
      title: "Road programme financial record",
      dimension: "money",
      metrics: [
        { label: "Value of projects", value: row.value_of_projects_cr, unit: "INR crore" },
        { label: "Expenditure reported", value: row.expenditure_cr, unit: "INR crore" },
      ],
      note: "Project value and expenditure are not the same as money released.",
    }),
    record(row, {
      ...common,
      id: "pmgsy-delivery",
      title: "Road programme delivery record",
      dimension: "delivery",
      metrics: [
        { label: "Roads sanctioned", value: row.roads_sanctioned, unit: "count" },
        { label: "Roads completed", value: row.roads_completed, unit: "count" },
        { label: "Length sanctioned", value: row.length_sanctioned_km, unit: "km" },
        { label: "Length completed", value: row.length_completed_km, unit: "km" },
      ],
    }),
  ];
}

function pmayRecords(row: PmayRow | null): EvidenceRecord[] {
  if (!row) return [];
  return [record(row, {
    id: "pmay-delivery", scheme: "PMAY-G", title: "Rural housing progress", dimension: "delivery", scope: "district",
    claimId: "CLAIM-2026-0018", asOf: `FY ${row.fin_year}`, metrics: [
      { label: "Houses sanctioned", value: row.houses_sanctioned, unit: "count" },
      { label: "Houses completed", value: row.houses_completed, unit: "count" },
    ], note: "The public district source does not publish usable finance values.",
  })];
}

function simpleDeliveryRecords(pmkisan: PmkisanRow | null, jjm: JjmRow | null, poshan: PoshanRow | null): EvidenceRecord[] {
  const records: EvidenceRecord[] = [];
  if (pmkisan) records.push(record(pmkisan, {
    id: "pmkisan-beneficiaries", scheme: "PM Kisan", title: `Installment ${pmkisan.installment}`, dimension: "delivery", scope: "district",
    claimId: "CLAIM-2026-0044", asOf: "31 Mar 2026",
    metrics: [{ label: "Beneficiaries paid", value: pmkisan.beneficiaries_paid, unit: "count" }],
    note: "This current district source publishes beneficiary counts, not money, and lags the homepage by one installment.",
  }));
  if (jjm) records.push(record(jjm, {
    id: "jjm-delivery", scheme: "JJM", title: "Rural tap-water record", dimension: "delivery", scope: "district",
    claimId: "CLAIM-2026-0045", asOf: "Not published by the retained source", metrics: [
      { label: "Rural households", value: jjm.total_households, unit: "count" },
      { label: "Households with tap connection", value: jjm.households_with_tap, unit: "count" },
    ], note: "The public district source does not publish finance values.",
  }));
  if (poshan) records.push(record(poshan, {
    id: "poshan-snapshot", scheme: "PM POSHAN", title: "Daily meal-reporting snapshot", dimension: "delivery", scope: "district",
    claimId: "CLAIM-2026-0041", asOf: "Source snapshot date not retained",
    metrics: [{ label: "Children reported fed", value: poshan.children_fed, unit: "count" }],
    note: "A daily reporting count, not a coverage rate. Retrieval is shown separately and is not treated as the source reporting date.",
  }));
  return records;
}

function foodAndSanitationRecords(nfsa: NfsaRow | null, sbm: SbmRow | null): EvidenceRecord[] {
  const records: EvidenceRecord[] = [];
  if (nfsa) records.push(record(nfsa, {
    id: "nfsa-stock", scheme: "PDS/NFSA", title: "Ration-card register", dimension: "delivery", scope: "district",
    claimId: "CLAIM-2026-0029", asOf: nfsa.date_of_data ?? "Source reporting date not retained", metrics: [
      { label: "Ration cards recorded", value: nfsa.ration_cards_total, unit: "count" },
      { label: "Members covered", value: nfsa.beneficiaries_total, unit: "count" },
    ], note: "The source reporting date varies by district; retrieval time is shown separately.",
  }));
  if (sbm) records.push(record(sbm, {
    id: "sbm-delivery", scheme: "SBM-G", title: "Village sanitation record", dimension: "delivery", scope: "district",
    claimId: "CLAIM-2026-0046", asOf: "Not published by the retained source", metrics: [
      { label: "Villages recorded", value: sbm.total_villages, unit: "count" },
      { label: "ODF Plus villages", value: sbm.odf_plus_villages, unit: "count" },
    ], note: "This source publishes delivery figures, not district finance.",
  }));
  return records;
}

function udiseRecords(row: UdiseRow | null): EvidenceRecord[] {
  if (!row) return [];
  return [record(row, {
    id: "udise-state", scheme: "UDISE+", title: "State education context", dimension: "delivery", scope: "state",
    claimId: "CLAIM-2026-0020", asOf: `Academic year ${row.fin_year}`, metrics: [
      { label: "Schools recorded in the state", value: row.total_schools, unit: "count" },
      { label: "Students recorded in the state", value: row.total_students, unit: "count" },
    ], note: "UDISE+ data in Hisaab is state-level only. These figures are not district totals.",
  })];
}

export async function getAreaAccount(district: string, state: string): Promise<AreaAccount> {
  const [[finance, fto, pmgsy, pmay, pmkisan, jjm, poshan], [nfsa, sbm, nrlm, udise, nsap], stateRecords] = await Promise.all([
    fetchWorkAndDelivery(district, state),
    fetchOtherRecords(district, state),
    getStateAccountRecords(state),
  ]);
  const districtRecords = [
    ...mgnregaRecords(finance, fto),
    ...pmgsyRecords(pmgsy),
    ...pmayRecords(pmay),
    ...simpleDeliveryRecords(pmkisan, jjm, poshan),
    ...foodAndSanitationRecords(nfsa, sbm),
    ...nrlmRecords(nrlm),
    ...nsapRecords(nsap),
  ];
  const present = new Set(districtRecords.map((item) => item.scheme));
  return {
    districtRecords,
    stateRecords: [...stateRecords, ...udiseRecords(udise)],
    missingDistrictSchemes: DISTRICT_SCHEMES.filter((scheme) => !present.has(scheme)),
  };
}
