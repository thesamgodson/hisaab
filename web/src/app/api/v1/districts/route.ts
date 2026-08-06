import { getLatestFinYear } from "@/lib/fin-year";
import { type NextRequest } from "next/server";
import { query } from "@/lib/db";

interface DistrictRow {
  district: string;
  state: string;
}

/** All districts with any scheme data, from the canonical registry
 *  (district_scores, written at load time — 'ALL' state-rows excluded). */
export async function GET(request: NextRequest) {
  const state = request.nextUrl.searchParams.get("state");
  const finYear = request.nextUrl.searchParams.get("fin_year") ?? (await getLatestFinYear());

  const rows = state
    ? await query<DistrictRow>(
        `SELECT district, state FROM district_scores
         WHERE fin_year = ? AND UPPER(state) = UPPER(?) ORDER BY district`,
        [finYear, state],
      )
    : await query<DistrictRow>(
        `SELECT district, state FROM district_scores
         WHERE fin_year = ? ORDER BY district`,
        [finYear],
      );

  return Response.json({
    districts: rows.map((r) => r.district),
    items: rows,
    count: rows.length,
  });
}
