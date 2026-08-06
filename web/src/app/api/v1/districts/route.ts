import { type NextRequest } from "next/server";
import { query } from "@/lib/db";

interface DistrictRow {
  district: string;
  state: string;
}

const DISTRICT_REGISTRY_SQL = `
  SELECT DISTINCT district, state FROM (
    SELECT district, state FROM district_scores
    UNION
    SELECT district, state FROM pin_district_mapping
  )
  WHERE UPPER(district) <> 'ALL'
`;

/** Canonical citizen district registry. PIN coverage can exceed current-year
 * performance-data coverage, so complaint access cannot query scores alone. */
export async function GET(request: NextRequest) {
  const state = request.nextUrl.searchParams.get("state");

  const rows = state
    ? await query<DistrictRow>(
        `SELECT district, state FROM (${DISTRICT_REGISTRY_SQL})
         WHERE UPPER(state) = UPPER(?) ORDER BY district`,
        [state],
      )
    : await query<DistrictRow>(
        `SELECT district, state FROM (${DISTRICT_REGISTRY_SQL}) ORDER BY state, district`,
        [],
      );

  return Response.json({
    districts: rows.map((r) => r.district),
    items: rows,
    count: rows.length,
  });
}
