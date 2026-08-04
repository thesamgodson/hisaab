/** Latest financial year the pipeline has published scores for.
 *
 * The serving default everywhere — never hardcode a year in a route. Falls
 * back to 2024-2025 (the last known-good year) if the table is unreachable.
 */

import { queryOne } from "@/lib/db";

const FALLBACK_FIN_YEAR = "2024-2025";

let _cached: { value: string; at: number } | null = null;
const TTL_MS = 10 * 60 * 1000;

export async function getLatestFinYear(): Promise<string> {
  if (_cached && Date.now() - _cached.at < TTL_MS) return _cached.value;
  try {
    const row = await queryOne<{ fy: string | null }>(
      `SELECT MAX(fin_year) AS fy FROM district_scores`,
    );
    const value = row?.fy ?? FALLBACK_FIN_YEAR;
    _cached = { value, at: Date.now() };
    return value;
  } catch {
    return FALLBACK_FIN_YEAR;
  }
}
