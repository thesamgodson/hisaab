import { type NextRequest } from "next/server";
import { query } from "@/lib/db";
import {
  resolveSchemeParam,
  VALID_SCHEME_SLUGS,
  type SchemeKey,
} from "@/lib/schemes";

interface WorstQuery {
  sql: string;
  args: (string | number | null)[];
  describe: (rows: Record<string, unknown>[]) => string;
}

function buildWorstQuery(
  scheme: SchemeKey,
  state: string,
  limit: number,
): WorstQuery | null {
  switch (scheme) {
    case "MGNREGA":
      return {
        sql: `SELECT district, state, cases_reported, amount_reported, amount_recovered, recovery_rate_pct, fin_year
              FROM misappropriation
              WHERE UPPER(state) = UPPER(?)
              ORDER BY amount_reported DESC
              LIMIT ?`,
        args: [state, limit],
        describe: (rows) =>
          `Top ${rows.length} worst MGNREGA districts in ${state} by misappropriation amount.`,
      };
    case "PMGSY":
      return {
        sql: `SELECT district, state, length_sanctioned_km, length_completed_km,
              CASE WHEN length_sanctioned_km > 0
                THEN ROUND(length_completed_km * 100.0 / length_sanctioned_km, 1)
                ELSE 0 END as completion_pct
              FROM pmgsy_district
              WHERE UPPER(state) = UPPER(?)
              ORDER BY completion_pct ASC
              LIMIT ?`,
        args: [state, limit],
        describe: (rows) =>
          `Top ${rows.length} worst PMGSY districts in ${state} by road completion percentage.`,
      };
    case "PMAY-G":
      return {
        sql: `SELECT district, state, houses_sanctioned, houses_completed,
              CASE WHEN houses_sanctioned > 0
                THEN ROUND(houses_completed * 100.0 / houses_sanctioned, 1)
                ELSE 0 END as completion_pct, fin_year
              FROM pmayg_district
              WHERE UPPER(state) = UPPER(?)
              ORDER BY completion_pct ASC
              LIMIT ?`,
        args: [state, limit],
        describe: (rows) =>
          `Top ${rows.length} worst PMAY-G districts in ${state} by house completion percentage.`,
      };
    case "PM Kisan":
      return {
        sql: `SELECT district, state, beneficiaries_paid, amount_paid_lakhs, fin_year
              FROM pmkisan_district
              WHERE UPPER(state) = UPPER(?)
              ORDER BY beneficiaries_paid ASC
              LIMIT ?`,
        args: [state, limit],
        describe: (rows) =>
          `Top ${rows.length} worst PM Kisan districts in ${state} by beneficiaries paid.`,
      };
    case "JJM":
      return {
        sql: `SELECT district, state, coverage_pct, households_with_tap, fin_year
              FROM jjm_district
              WHERE UPPER(state) = UPPER(?)
              ORDER BY coverage_pct ASC
              LIMIT ?`,
        args: [state, limit],
        describe: (rows) =>
          `Top ${rows.length} worst JJM districts in ${state} by tap water coverage.`,
      };
    // PM POSHAN, NSAP, and PDS/NFSA have no honest district-level shortfall
    // metric to rank by (daily-snapshot feeding, no eligibility target,
    // active=total by construction — see DATA_CLAIMS.md). Ranking them would
    // publish a false claim, so they are not rankable here.
    default:
      return null;
  }
}

const NOT_RANKABLE_REASON: Partial<Record<SchemeKey, string>> = {
  "PM POSHAN":
    "children_fed is a daily reporting snapshot, not a completion rate (CLAIM-2026-0006).",
  NSAP: "No eligibility target is published at district level; beneficiary count is not a shortfall metric.",
  "PDS/NFSA":
    "Active ration cards equal total by construction in the source (CLAIM-2026-0008).",
};

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ scheme: string }> },
) {
  const { scheme: rawScheme } = await params;
  const scheme = resolveSchemeParam(rawScheme);
  const searchParams = request.nextUrl.searchParams;
  const state = searchParams.get("state");
  const limitParam = Number(searchParams.get("limit") ?? 10);
  const limit = Math.min(Math.max(1, limitParam), 100);

  if (!scheme) {
    return Response.json(
      {
        error: `Unknown scheme "${decodeURIComponent(rawScheme)}". Valid slugs: ${VALID_SCHEME_SLUGS.join(", ")}`,
      },
      { status: 404 },
    );
  }

  if (!state) {
    return Response.json(
      { error: "Query parameter 'state' is required (e.g. ?state=BIHAR)." },
      { status: 400 },
    );
  }

  const notRankable = NOT_RANKABLE_REASON[scheme];
  if (notRankable) {
    return Response.json(
      {
        error: `${scheme} has no honest district-level ranking metric: ${notRankable}`,
      },
      { status: 422 },
    );
  }

  const worstQuery = buildWorstQuery(scheme, state, limit);
  if (!worstQuery) {
    return Response.json(
      { error: `No query configured for scheme "${scheme}".` },
      { status: 500 },
    );
  }

  const rows = await query<Record<string, unknown>>(
    worstQuery.sql,
    worstQuery.args,
  );

  if (rows.length === 0) {
    return Response.json({
      answer: `No data found for ${scheme} in ${state}.`,
      data: [],
    });
  }

  return Response.json({
    answer: worstQuery.describe(rows),
    data: rows,
  });
}
