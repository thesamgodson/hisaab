/**
 * Composite accountability score computation for districts.
 *
 * Scoring methodology (0-100):
 *   - Delivery metrics (60%): average delivery_pct across all schemes with data
 *   - Financial utilization (30%): average utilization_pct from scheme_finance VIEW
 *   - Governance / recovery (10%): MGNREGA recovery_rate_pct (if available)
 *
 * Grades: A=80+, B=60-80, C=40-60, D=20-40, F=<20
 */

import { query } from "@/lib/db";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const GRADE_THRESHOLDS: [number, string][] = [
  [80.0, "A"],
  [60.0, "B"],
  [40.0, "C"],
  [20.0, "D"],
  [0.0, "F"],
];

const DELIVERY_WEIGHT = 0.60;
const FINANCE_WEIGHT = 0.30;
const GOVERNANCE_WEIGHT = 0.10;

const DISTRICT_TABLES = [
  "misappropriation",
  "financial_statement",
  "pmgsy_district",
  "pmayg_district",
  "pmkisan_district",
  "jjm_district",
  "pmposhan_district",
  "nsap_district",
  "nfsa_district",
  "sbm_district",
  "nrlm_district",
] as const;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ScoreBreakdown {
  delivery_avg: number | null;
  delivery_schemes: string[];
  finance_avg: number | null;
  finance_schemes: string[];
  governance_score: number | null;
}

export interface DistrictScore {
  district: string;
  state: string;
  score: number | null;
  grade: string | null;
  schemes_with_data: string[];
  schemes_count: number;
  red_flags: string[];
  breakdown: ScoreBreakdown;
}

export interface StateRanking {
  state: string;
  avg_score: number;
  grade: string;
  district_count: number;
  best_district_score: number;
  worst_district_score: number;
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

function grade(score: number): string {
  for (const [threshold, letter] of GRADE_THRESHOLDS) {
    if (score >= threshold) return letter;
  }
  return "F";
}

function avg(values: number[]): number | null {
  const valid = values.filter((v) => v >= 0 && v <= 100);
  if (valid.length === 0) return null;
  return valid.reduce((a, b) => a + b, 0) / valid.length;
}

function round1(v: number): number {
  return Math.round(v * 10) / 10;
}

// ---------------------------------------------------------------------------
// Data fetching
// ---------------------------------------------------------------------------

interface DeliveryRow {
  scheme: string;
  state: string;
  district: string;
  delivery_pct: number;
}

interface FinanceRow {
  scheme: string;
  state: string;
  district: string;
  utilization_pct: number;
}

interface RecoveryRow {
  district: string;
  state: string;
  recovery_rate_pct: number;
}

interface DistrictPair {
  d: string;
  s: string;
}

type SchemeMap = Map<string, Map<string, number>>;
// outer key = "DISTRICT|STATE", inner key = scheme name

function districtKey(district: string, state: string): string {
  return `${district.toUpperCase()}|${state.toUpperCase()}`;
}

function parseKey(key: string): [string, string] {
  const idx = key.indexOf("|");
  return [key.slice(0, idx), key.slice(idx + 1)];
}

async function fetchDeliveryScores(finYear: string): Promise<SchemeMap> {
  const rows = await query<DeliveryRow>(
    `SELECT scheme, state, district, delivery_pct
     FROM scheme_delivery
     WHERE delivery_pct IS NOT NULL
       AND district != 'ALL'
       AND fin_year = ?`,
    [finYear],
  );

  const result: SchemeMap = new Map();
  for (const row of rows) {
    const key = districtKey(row.district, row.state);
    if (!result.has(key)) result.set(key, new Map());
    const schemes = result.get(key)!;
    const existing = schemes.get(row.scheme);
    if (existing === undefined || row.delivery_pct > existing) {
      schemes.set(row.scheme, row.delivery_pct);
    }
  }
  return result;
}

async function fetchFinanceScores(finYear: string): Promise<SchemeMap> {
  const rows = await query<FinanceRow>(
    `SELECT scheme, state, district, utilization_pct
     FROM scheme_finance
     WHERE utilization_pct IS NOT NULL
       AND utilization_pct > 0
       AND utilization_pct <= 150
       AND fin_year = ?`,
    [finYear],
  );

  const result: SchemeMap = new Map();
  for (const row of rows) {
    const key = districtKey(row.district, row.state);
    if (!result.has(key)) result.set(key, new Map());
    const schemes = result.get(key)!;
    const existing = schemes.get(row.scheme);
    const capped = Math.min(100.0, row.utilization_pct);
    if (existing === undefined || capped > existing) {
      schemes.set(row.scheme, capped);
    }
  }
  return result;
}

async function fetchRecoveryRates(
  finYear: string,
): Promise<Map<string, number>> {
  const rows = await query<RecoveryRow>(
    `SELECT district, state, recovery_rate_pct
     FROM misappropriation
     WHERE fin_year = ?
       AND recovery_rate_pct IS NOT NULL`,
    [finYear],
  );

  const result = new Map<string, number>();
  for (const row of rows) {
    const key = districtKey(row.district, row.state);
    const existing = result.get(key);
    if (existing === undefined || row.recovery_rate_pct > existing) {
      result.set(key, row.recovery_rate_pct);
    }
  }
  return result;
}

async function fetchAllDistricts(): Promise<Set<string>> {
  const pairs = new Set<string>();

  const queries = DISTRICT_TABLES.map((table) =>
    query<DistrictPair>(
      `SELECT DISTINCT UPPER(district) as d, UPPER(state) as s FROM ${table} WHERE district != 'ALL'`,
    ).catch(() => [] as DistrictPair[]),
  );

  const results = await Promise.all(queries);
  for (const rows of results) {
    for (const row of rows) {
      pairs.add(districtKey(row.d, row.s));
    }
  }
  return pairs;
}

// ---------------------------------------------------------------------------
// Red flags
// ---------------------------------------------------------------------------

function computeRedFlags(
  delivery: Map<string, number>,
  finance: Map<string, number>,
  recoveryRate: number | undefined,
): string[] {
  const flags: string[] = [];

  for (const [scheme, pct] of delivery) {
    if (pct < 40) {
      flags.push(`${scheme} delivery only ${Math.round(pct)}%`);
    }
  }

  for (const [scheme, pct] of finance) {
    if (pct < 30) {
      flags.push(`${scheme} utilization only ${Math.round(pct)}%`);
    }
  }

  if (recoveryRate !== undefined && recoveryRate < 20) {
    flags.push(`MGNREGA recovery rate ${Math.round(recoveryRate)}%`);
  }

  return flags.slice(0, 5);
}

// ---------------------------------------------------------------------------
// Score computation
// ---------------------------------------------------------------------------

function buildScoreRecord(
  district: string,
  state: string,
  delivery: Map<string, number>,
  finance: Map<string, number>,
  recoveryRate: number | undefined,
): DistrictScore {
  const deliveryAvg = avg([...delivery.values()]);
  const financeAvg = avg([...finance.values()]);
  const governanceScore =
    recoveryRate !== undefined ? Math.min(100.0, recoveryRate) : null;

  const components: [number, number][] = [];
  if (deliveryAvg !== null) components.push([DELIVERY_WEIGHT, deliveryAvg]);
  if (financeAvg !== null) components.push([FINANCE_WEIGHT, financeAvg]);
  if (governanceScore !== null)
    components.push([GOVERNANCE_WEIGHT, governanceScore]);

  if (components.length === 0) {
    return nullScoreRecord(district, state);
  }

  const totalWeight = components.reduce((sum, [w]) => sum + w, 0);
  const raw = components.reduce(
    (sum, [w, v]) => sum + (w / totalWeight) * v,
    0,
  );
  const score = round1(Math.min(100.0, Math.max(0.0, raw)));

  const schemesWithData = [
    ...new Set([...delivery.keys(), ...finance.keys()]),
  ].sort();
  const redFlags = computeRedFlags(delivery, finance, recoveryRate);

  return {
    district,
    state,
    score,
    grade: grade(score),
    schemes_with_data: schemesWithData,
    schemes_count: schemesWithData.length,
    red_flags: redFlags,
    breakdown: {
      delivery_avg: deliveryAvg !== null ? round1(deliveryAvg) : null,
      delivery_schemes: [...delivery.keys()].sort(),
      finance_avg: financeAvg !== null ? round1(financeAvg) : null,
      finance_schemes: [...finance.keys()].sort(),
      governance_score:
        governanceScore !== null ? round1(governanceScore) : null,
    },
  };
}

function nullScoreRecord(district: string, state: string): DistrictScore {
  return {
    district,
    state,
    score: null,
    grade: null,
    schemes_with_data: [],
    schemes_count: 0,
    red_flags: [],
    breakdown: {
      delivery_avg: null,
      delivery_schemes: [],
      finance_avg: null,
      finance_schemes: [],
      governance_score: null,
    },
  };
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Compute composite accountability scores for all districts.
 *
 * Returns scored districts descending by score, then unscored at the end.
 */
export async function computeDistrictScores(
  finYear: string = "2024-2025",
): Promise<DistrictScore[]> {
  const [allDistricts, deliveryMap, financeMap, recoveryMap] =
    await Promise.all([
      fetchAllDistricts(),
      fetchDeliveryScores(finYear),
      fetchFinanceScores(finYear),
      fetchRecoveryRates(finYear),
    ]);

  const records: DistrictScore[] = [];
  const sortedKeys = [...allDistricts].sort();

  for (const key of sortedKeys) {
    const [district, state] = parseKey(key);
    const delivery = deliveryMap.get(key) ?? new Map();
    const finance = financeMap.get(key) ?? new Map();
    const recovery = recoveryMap.get(key);
    records.push(
      buildScoreRecord(district, state, delivery, finance, recovery),
    );
  }

  const scored = records
    .filter((r) => r.score !== null)
    .sort((a, b) => (b.score as number) - (a.score as number));
  const unscored = records.filter((r) => r.score === null);
  return [...scored, ...unscored];
}

/**
 * Compute state rankings by averaging district scores.
 */
export async function getStateRankings(
  finYear: string = "2024-2025",
): Promise<StateRanking[]> {
  const allScores = await computeDistrictScores(finYear);
  const scored = allScores.filter((r) => r.score !== null);

  const buckets = new Map<string, number[]>();
  for (const record of scored) {
    if (!buckets.has(record.state)) buckets.set(record.state, []);
    buckets.get(record.state)!.push(record.score as number);
  }

  const rankings: StateRanking[] = [];
  for (const [state, scores] of buckets) {
    const avgScore = round1(
      scores.reduce((a, b) => a + b, 0) / scores.length,
    );
    rankings.push({
      state,
      avg_score: avgScore,
      grade: grade(avgScore),
      district_count: scores.length,
      best_district_score: round1(Math.max(...scores)),
      worst_district_score: round1(Math.min(...scores)),
    });
  }

  return rankings.sort((a, b) => b.avg_score - a.avg_score);
}

/**
 * Return the bottom N districts by composite score.
 */
export async function getWorstDistricts(
  n: number = 50,
  finYear: string = "2024-2025",
): Promise<DistrictScore[]> {
  const allScores = await computeDistrictScores(finYear);
  const scored = allScores.filter((r) => r.score !== null);
  return scored.slice(-n).reverse();
}
