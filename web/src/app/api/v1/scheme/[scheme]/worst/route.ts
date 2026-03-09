import { type NextRequest } from "next/server";
import { query } from "@/lib/db";

type SchemeKey =
  | "MGNREGA"
  | "PMGSY"
  | "PMAY-G"
  | "PM Kisan"
  | "JJM"
  | "PM POSHAN"
  | "NSAP"
  | "PDS/NFSA";

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
    case "PM POSHAN":
      return {
        sql: `SELECT district, state, children_enrolled, children_fed,
              CASE WHEN children_enrolled > 0
                THEN ROUND(children_fed * 100.0 / children_enrolled, 1)
                ELSE 0 END as feeding_pct, fin_year
              FROM pmposhan_district
              WHERE UPPER(state) = UPPER(?)
              ORDER BY feeding_pct ASC
              LIMIT ?`,
        args: [state, limit],
        describe: (rows) =>
          `Top ${rows.length} worst PM POSHAN districts in ${state} by feeding percentage.`,
      };
    case "NSAP":
      return {
        sql: `SELECT district, state, beneficiaries_paid, amount_paid_lakhs, fin_year
              FROM nsap_district
              WHERE UPPER(state) = UPPER(?)
              ORDER BY beneficiaries_paid ASC
              LIMIT ?`,
        args: [state, limit],
        describe: (rows) =>
          `Top ${rows.length} worst NSAP districts in ${state} by beneficiaries paid.`,
      };
    case "PDS/NFSA":
      return {
        sql: `SELECT district, state, ration_cards_total, ration_cards_active,
              CASE WHEN ration_cards_total > 0
                THEN ROUND(ration_cards_active * 100.0 / ration_cards_total, 1)
                ELSE 0 END as active_pct, fin_year
              FROM nfsa_district
              WHERE UPPER(state) = UPPER(?)
              ORDER BY active_pct ASC
              LIMIT ?`,
        args: [state, limit],
        describe: (rows) =>
          `Top ${rows.length} worst PDS/NFSA districts in ${state} by active ration card percentage.`,
      };
    default:
      return null;
  }
}

const VALID_SCHEMES: SchemeKey[] = [
  "MGNREGA",
  "PMGSY",
  "PMAY-G",
  "PM Kisan",
  "JJM",
  "PM POSHAN",
  "NSAP",
  "PDS/NFSA",
];

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ scheme: string }> },
) {
  const { scheme: rawScheme } = await params;
  const scheme = decodeURIComponent(rawScheme) as SchemeKey;
  const searchParams = request.nextUrl.searchParams;
  const state = searchParams.get("state") ?? "TAMIL NADU";
  const limitParam = Number(searchParams.get("limit") ?? 10);
  const limit = Math.min(Math.max(1, limitParam), 100);

  if (!VALID_SCHEMES.includes(scheme)) {
    return Response.json(
      {
        error: `Unknown scheme "${scheme}". Valid schemes: ${VALID_SCHEMES.join(", ")}`,
      },
      { status: 404 },
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
