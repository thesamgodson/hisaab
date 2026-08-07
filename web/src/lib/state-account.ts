import { query, queryOne } from "@/lib/db";
import type { EvidenceMetric, EvidenceRecord } from "@/lib/area-account";

interface StateRow {
  fin_year: string;
  source_url: string;
  scraped_at: string;
}

type MoneyRow = StateRow & { allocated_lakhs: number; released_lakhs: number; utilized_lakhs: number };
type NsapRow = StateRow & { released_lakhs: number };
type JjmRow = StateRow & { allocated_crores: number; released_crores: number; expended_crores: number };
type PmkisanRow = StateRow & { beneficiaries_registered: number; beneficiaries_paid: number; installment: string };
type GrainRow = StateRow & { grain_type: string; allocation_mt: number; offtake_mt: number };

function sourceMetrics(metrics: EvidenceMetric[]): {
  metrics: EvidenceMetric[];
  missingMetrics: string[];
} {
  return {
    metrics: metrics.filter((metric) => metric.value > 0),
    missingMetrics: metrics
      .filter((metric) => metric.value === 0)
      .map((metric) => `${metric.label}: the source value is 0; none and not reported cannot be distinguished.`),
  };
}

async function latestStateRow<T extends StateRow>(
  table: string,
  columns: string,
  state: string,
): Promise<T | null> {
  return queryOne<T>(
    `SELECT ${columns}, fin_year, source_url, scraped_at FROM ${table}
     WHERE state = ? ORDER BY fin_year DESC, scraped_at DESC LIMIT 1`,
    [state],
  );
}

function stateRecord(
  row: StateRow,
  values: Omit<EvidenceRecord, "period" | "sourceUrl" | "retrievedAt" | "scope">,
): EvidenceRecord {
  return {
    ...values,
    scope: "state",
    period: `FY ${row.fin_year}`,
    sourceUrl: row.source_url,
    retrievedAt: row.scraped_at,
  };
}

function moneyRecord(
  row: MoneyRow | null,
  scheme: "PM POSHAN" | "PMAY-G",
  claimId: string,
): EvidenceRecord[] {
  if (!row) return [];
  const { metrics, missingMetrics } = sourceMetrics([
    { label: "Funds allocated", value: row.allocated_lakhs, unit: "INR lakh" },
    { label: "Funds released", value: row.released_lakhs, unit: "INR lakh" },
    { label: "Funds utilized", value: row.utilized_lakhs, unit: "INR lakh" },
  ]);
  return [stateRecord(row, {
    id: `${scheme.toLowerCase().replace(/[^a-z0-9]+/g, "-")}-state-finance`,
    scheme,
    title: "State financial record",
    dimension: "money",
    claimId,
    asOf: `FY ${row.fin_year}`,
    metrics,
    missingMetrics,
    note: "State total, not money assigned to the selected district.",
  })];
}

function otherStateRecords(nsap: NsapRow | null, jjm: JjmRow | null, pmkisan: PmkisanRow | null) {
  const records: EvidenceRecord[] = [];
  if (nsap) {
    const { metrics, missingMetrics } = sourceMetrics([
      { label: "Funds released", value: nsap.released_lakhs, unit: "INR lakh" },
    ]);
    records.push(stateRecord(nsap, {
    id: "nsap-state-release", scheme: "NSAP", title: "State fund release", dimension: "money",
    claimId: "CLAIM-2026-0013", asOf: `FY ${nsap.fin_year}`,
    metrics, missingMetrics,
    note: "This is a state release, not district expenditure.",
    }));
  }
  const jjmMetrics = jjm ? sourceMetrics([
    { label: "Funds allocated", value: jjm.allocated_crores, unit: "INR crore" },
    { label: "Funds released", value: jjm.released_crores, unit: "INR crore" },
    { label: "Expenditure reported", value: jjm.expended_crores, unit: "INR crore" },
  ]) : null;
  if (jjm && jjmMetrics) records.push(stateRecord(jjm, {
    id: "jjm-state-finance", scheme: "JJM", title: "State financial record", dimension: "money",
    claimId: "CLAIM-2026-0015", asOf: `FY ${jjm.fin_year}`,
    metrics: jjmMetrics.metrics, missingMetrics: jjmMetrics.missingMetrics,
    note: "State total, not money assigned to the selected district.",
  }));
  if (pmkisan) records.push(stateRecord(pmkisan, {
    id: "pmkisan-state-period", scheme: "PM Kisan", title: pmkisan.installment, dimension: "delivery",
    claimId: "CLAIM-2026-0030", asOf: "28 Jun 2026", metrics: [
      { label: "Farmers eligible in the state", value: pmkisan.beneficiaries_registered, unit: "count" },
      { label: "Farmers transferred to", value: pmkisan.beneficiaries_paid, unit: "count" },
    ], note: "Mid-cycle state count. The source does not publish money on this surface.",
  }));
  return records;
}

function grainRecords(rows: GrainRow[]): EvidenceRecord[] {
  return rows.flatMap((row) => {
    const { metrics, missingMetrics } = sourceMetrics([
      { label: "Foodgrain allocated", value: row.allocation_mt, unit: "MT" },
      { label: "Foodgrain offtake", value: row.offtake_mt, unit: "MT" },
    ]);
    return [stateRecord(row, {
      id: `nfsa-state-${row.grain_type}`, scheme: "PDS/NFSA",
      title: `${row.grain_type[0].toUpperCase()}${row.grain_type.slice(1)} allocation and offtake`,
      dimension: "delivery", claimId: "CLAIM-2026-0014", asOf: `FY ${row.fin_year}`,
      metrics, missingMetrics,
      note: "State quantity in metric tonnes, never rupees or district money.",
    })];
  });
}

async function latestGrainRows(state: string): Promise<GrainRow[]> {
  return query<GrainRow>(
    `SELECT fin_year, grain_type, allocation_mt, offtake_mt, source_url, scraped_at
     FROM nfsa_allocation
     WHERE state = ?
       AND fin_year = (SELECT MAX(fin_year) FROM nfsa_allocation WHERE state = ?)
       AND (
         grain_type IN ('rice', 'wheat')
         OR (grain_type = 'total' AND NOT EXISTS (
           SELECT 1 FROM nfsa_allocation components
           WHERE components.state = ?
             AND components.fin_year = nfsa_allocation.fin_year
             AND components.grain_type IN ('rice', 'wheat')
         ))
       )
     ORDER BY grain_type`,
    [state, state, state],
  );
}

export async function getStateAccountRecords(state: string): Promise<EvidenceRecord[]> {
  const [poshan, nsap, jjm, pmay, pmkisan, grain] = await Promise.all([
    latestStateRow<MoneyRow>("pmposhan_finance", "allocated_lakhs, released_lakhs, utilized_lakhs", state),
    latestStateRow<NsapRow>("nsap_finance", "released_lakhs", state),
    latestStateRow<JjmRow>("jjm_allocation", "allocated_crores, released_crores, expended_crores", state),
    latestStateRow<MoneyRow>("pmayg_finance", "allocated_lakhs, released_lakhs, utilized_lakhs", state),
    queryOne<PmkisanRow>(
      `SELECT beneficiaries_registered, beneficiaries_paid, installment, fin_year, source_url, scraped_at
       FROM pmkisan_district
       WHERE state = ? AND district = 'ALL' AND installment = 'April-July' AND fin_year = '2026-2027'
       ORDER BY scraped_at DESC LIMIT 1`,
      [state],
    ),
    latestGrainRows(state),
  ]);
  return [
    ...moneyRecord(poshan, "PM POSHAN", "CLAIM-2026-0012"),
    ...otherStateRecords(nsap, jjm, pmkisan),
    ...moneyRecord(pmay, "PMAY-G", "CLAIM-2026-0034"),
    ...grainRecords(grain),
  ];
}
