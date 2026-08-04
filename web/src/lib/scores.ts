/**
 * District accountability scores — READ-ONLY access to the precomputed
 * district_scores table.
 *
 * The scoring formula runs in exactly one place: queries/composite.py
 * (persist_district_scores), at data load time. This module never computes
 * scores; it only reads what the pipeline published. Methodology is
 * documented in DATA_CLAIMS.md (DERIVED-2026-0001).
 */

import { query, queryOne } from "@/lib/db";

// ---------------------------------------------------------------------------
// Types (response shapes are unchanged from the legacy compute-in-TS version)
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

interface ScoreRow {
  district: string;
  state: string;
  score: number | null;
  grade: string | null;
  schemes_count: number;
  schemes_with_data: string;
  red_flags: string;
  delivery_avg: number | null;
  delivery_schemes: string;
  finance_avg: number | null;
  finance_schemes: string;
  governance_score: number | null;
}

// Presentation banding only — mirrors _GRADE_THRESHOLDS in queries/composite.py.
// Used solely to label state AVERAGES; district grades come from the table.
function gradeForAverage(score: number): string {
  if (score >= 80) return "A";
  if (score >= 60) return "B";
  if (score >= 40) return "C";
  if (score >= 20) return "D";
  return "F";
}

function parseJsonArray(raw: string): string[] {
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function toRecord(row: ScoreRow): DistrictScore {
  return {
    district: row.district,
    state: row.state,
    score: row.score,
    grade: row.grade,
    schemes_with_data: parseJsonArray(row.schemes_with_data),
    schemes_count: Number(row.schemes_count),
    red_flags: parseJsonArray(row.red_flags),
    breakdown: {
      delivery_avg: row.delivery_avg,
      delivery_schemes: parseJsonArray(row.delivery_schemes),
      finance_avg: row.finance_avg,
      finance_schemes: parseJsonArray(row.finance_schemes),
      governance_score: row.governance_score,
    },
  };
}

const SCORE_COLUMNS = `district, state, score, grade, schemes_count,
  schemes_with_data, red_flags, delivery_avg, delivery_schemes,
  finance_avg, finance_schemes, governance_score`;

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/** All district scores, scored first (descending), unscored at the end. */
export async function computeDistrictScores(
  finYear: string = "2024-2025",
): Promise<DistrictScore[]> {
  const rows = await query<ScoreRow>(
    `SELECT ${SCORE_COLUMNS} FROM district_scores
     WHERE fin_year = ?
     ORDER BY score IS NULL, score DESC, district`,
    [finYear],
  );
  return rows.map(toRecord);
}

/** Score record for one district (state narrows homonyms like BILASPUR). */
export async function getDistrictScore(
  district: string,
  state: string | null,
  finYear: string = "2024-2025",
): Promise<DistrictScore | null> {
  const row = state
    ? await queryOne<ScoreRow>(
        `SELECT ${SCORE_COLUMNS} FROM district_scores
         WHERE fin_year = ? AND UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?)`,
        [finYear, district, state],
      )
    : await queryOne<ScoreRow>(
        `SELECT ${SCORE_COLUMNS} FROM district_scores
         WHERE fin_year = ? AND UPPER(district) = UPPER(?)`,
        [finYear, district],
      );
  return row ? toRecord(row) : null;
}

/** Average district score per state, descending. */
export async function getStateRankings(
  finYear: string = "2024-2025",
): Promise<StateRanking[]> {
  const rows = await query<{
    state: string;
    avg_score: number;
    district_count: number;
    best: number;
    worst: number;
  }>(
    `SELECT state,
            ROUND(AVG(score), 1) AS avg_score,
            COUNT(score)        AS district_count,
            ROUND(MAX(score),1) AS best,
            ROUND(MIN(score),1) AS worst
     FROM district_scores
     WHERE fin_year = ? AND score IS NOT NULL
     GROUP BY state
     ORDER BY avg_score DESC`,
    [finYear],
  );
  return rows.map((r) => ({
    state: r.state,
    avg_score: r.avg_score,
    grade: gradeForAverage(r.avg_score),
    district_count: Number(r.district_count),
    best_district_score: r.best,
    worst_district_score: r.worst,
  }));
}

/** Bottom N districts by score (worst first). */
export async function getWorstDistricts(
  n: number = 50,
  finYear: string = "2024-2025",
): Promise<DistrictScore[]> {
  const rows = await query<ScoreRow>(
    `SELECT ${SCORE_COLUMNS} FROM district_scores
     WHERE fin_year = ? AND score IS NOT NULL
     ORDER BY score ASC, district
     LIMIT ?`,
    [finYear, n],
  );
  return rows.map(toRecord);
}
