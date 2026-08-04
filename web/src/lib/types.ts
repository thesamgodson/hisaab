/** Client-safe response types for /api/v1/scores (consumed by IndiaMap).
 *
 * Server code reads scores via lib/scores.ts; these mirror its shapes without
 * importing the server-only DB module into client components.
 */

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

export interface ScoresResponse {
  fin_year: string;
  count: number;
  scored_count: number;
  scores: DistrictScore[];
}
