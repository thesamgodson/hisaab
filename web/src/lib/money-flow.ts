/** Shared district scheme-data access: latest money_flow row per scheme. */

import { query } from "@/lib/db";
import type { SchemeData } from "@/components/SchemeRow";

export interface MoneyFlowRow extends SchemeData {
  state: string;
  district: string;
}

/**
 * fin_year is "YYYY-YYYY" or "cumulative" — a real year always beats
 * "cumulative" (which would win a bare lexicographic comparison).
 */
function finYearRank(finYear: string): string {
  return finYear === "cumulative" ? "0000" : finYear;
}

export function latestPerScheme(rows: MoneyFlowRow[]): SchemeData[] {
  const map = new Map<string, MoneyFlowRow>();
  for (const row of rows) {
    const existing = map.get(row.scheme);
    if (!existing || finYearRank(row.fin_year) > finYearRank(existing.fin_year)) {
      map.set(row.scheme, row);
    }
  }
  return Array.from(map.values()).sort((a, b) =>
    a.scheme.localeCompare(b.scheme),
  );
}

/** Latest-per-scheme money/delivery rows for one district (state-scoped —
 *  14 district names exist in two states and must not merge). */
export async function getDistrictSchemeRows(
  district: string,
  state: string,
): Promise<SchemeData[]> {
  const rows = await query<MoneyFlowRow>(
    `SELECT scheme, state, district, fin_year,
            allocated_lakhs, released_lakhs, expended_lakhs,
            utilization_pct, units_target, units_completed,
            units_label, source_url
     FROM money_flow
     WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?)
     ORDER BY scheme, fin_year DESC`,
    [district, state],
  );
  return latestPerScheme(rows);
}
