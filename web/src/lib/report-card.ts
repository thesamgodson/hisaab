/**
 * Constituency report card, shared by /api/v1/mp/[name] and
 * /api/v1/constituency/[name].
 *
 * The composite score is the mean of the PRECOMPUTED district scores
 * (district_scores table — methodology DERIVED-2026-0001 in DATA_CLAIMS.md).
 * No scoring formula lives here; per-scheme delivery/utilization figures are
 * plain averages across the constituency's districts, published as facts.
 */

import { query } from "@/lib/db";

export const REPORT_CARD_SOURCE_NOTE =
  "Composite = mean of district accountability scores (precomputed; " +
  "methodology DERIVED-2026-0001 in DATA_CLAIMS.md). Per-scheme figures are " +
  "delivery/utilization averages across the constituency's districts.";

interface DistrictRow {
  district: string;
  state: string;
}

interface SchemeAggRow {
  scheme: string;
  delivery_pct: number | null;
  utilization_pct: number | null;
}

export interface SchemeReportRow {
  scheme: string;
  delivery_pct: number | null;
  utilization_pct: number | null;
  status: "good" | "fair" | "needs_attention" | "critical" | "no_data";
}

export interface ConstituencyReportCard {
  districts: string[];
  fin_year: string;
  composite_score: number | null;
  composite_grade: string | null;
  scored_district_count: number;
  national_avg_score: number | null;
  red_flags: string[];
  schemes: SchemeReportRow[];
  source_note: string;
}

// Presentation banding only — mirrors _GRADE_THRESHOLDS in queries/composite.py.
function gradeForAverage(score: number): string {
  if (score >= 80) return "A";
  if (score >= 60) return "B";
  if (score >= 40) return "C";
  if (score >= 20) return "D";
  return "F";
}

function statusBand(pct: number | null): SchemeReportRow["status"] {
  if (pct == null) return "no_data";
  if (pct >= 80) return "good";
  if (pct >= 60) return "fair";
  if (pct >= 40) return "needs_attention";
  return "critical";
}

function round1(v: number): number {
  return Math.round(v * 10) / 10;
}

export async function buildConstituencyReportCard(
  constituency: string,
  finYear: string,
): Promise<ConstituencyReportCard> {
  const districtRows = await query<DistrictRow>(
    `SELECT DISTINCT district, state FROM constituency_district
     WHERE UPPER(constituency) = UPPER(?)`,
    [constituency],
  );

  if (districtRows.length === 0) {
    return {
      districts: [],
      fin_year: finYear,
      composite_score: null,
      composite_grade: null,
      scored_district_count: 0,
      national_avg_score: null,
      red_flags: [],
      schemes: [],
      source_note: REPORT_CARD_SOURCE_NOTE,
    };
  }

  const pairPlaceholders = districtRows
    .map(() => "(UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?))")
    .join(" OR ");
  const pairArgs = districtRows.flatMap((r) => [r.district, r.state]);

  const [scoreRows, schemeRows, nationalRow] = await Promise.all([
    query<{ score: number | null; red_flags: string }>(
      `SELECT score, red_flags FROM district_scores
       WHERE fin_year = ? AND (${pairPlaceholders})`,
      [finYear, ...pairArgs],
    ),
    query<SchemeAggRow>(
      `SELECT scheme,
              ROUND(AVG(CASE WHEN delivery_pct BETWEEN 0 AND 100 THEN delivery_pct END), 1) AS delivery_pct,
              NULL AS utilization_pct
       FROM scheme_delivery
       WHERE fin_year = ? AND delivery_pct IS NOT NULL AND (${pairPlaceholders})
       GROUP BY scheme
       UNION ALL
       SELECT scheme,
              NULL AS delivery_pct,
              ROUND(AVG(MIN(utilization_pct, 100)), 1) AS utilization_pct
       FROM scheme_finance
       WHERE fin_year = ? AND utilization_pct > 0 AND utilization_pct <= 150
         AND (${pairPlaceholders})
       GROUP BY scheme`,
      [finYear, ...pairArgs, finYear, ...pairArgs],
    ),
    query<{ avg_score: number | null }>(
      `SELECT ROUND(AVG(score), 1) AS avg_score FROM district_scores
       WHERE fin_year = ? AND score IS NOT NULL`,
      [finYear],
    ),
  ]);

  // Merge the delivery / utilization halves of the UNION per scheme
  const bySchemes = new Map<string, SchemeReportRow>();
  for (const row of schemeRows) {
    const entry = bySchemes.get(row.scheme) ?? {
      scheme: row.scheme,
      delivery_pct: null,
      utilization_pct: null,
      status: "no_data" as const,
    };
    if (row.delivery_pct != null) entry.delivery_pct = Number(row.delivery_pct);
    if (row.utilization_pct != null)
      entry.utilization_pct = Number(row.utilization_pct);
    bySchemes.set(row.scheme, entry);
  }
  const schemes = [...bySchemes.values()]
    .map((s) => ({
      ...s,
      status: statusBand(s.delivery_pct ?? s.utilization_pct),
    }))
    .sort((a, b) => a.scheme.localeCompare(b.scheme));

  const scored = scoreRows
    .map((r) => r.score)
    .filter((s): s is number => s != null);
  const compositeScore =
    scored.length > 0
      ? round1(scored.reduce((a, b) => a + b, 0) / scored.length)
      : null;

  const redFlags = [
    ...new Set(
      scoreRows.flatMap((r) => {
        try {
          const parsed = JSON.parse(r.red_flags);
          return Array.isArray(parsed) ? parsed : [];
        } catch {
          return [];
        }
      }),
    ),
  ].slice(0, 5);

  return {
    districts: districtRows.map((r) => r.district),
    fin_year: finYear,
    composite_score: compositeScore,
    composite_grade:
      compositeScore != null ? gradeForAverage(compositeScore) : null,
    scored_district_count: scored.length,
    national_avg_score: nationalRow[0]?.avg_score ?? null,
    red_flags: redFlags,
    schemes,
    source_note: REPORT_CARD_SOURCE_NOTE,
  };
}
