import { getLatestFinYear } from "@/lib/fin-year";
import { type NextRequest } from "next/server";
import { query } from "@/lib/db";
import {
  resolveSchemeParam,
  VALID_SCHEME_SLUGS,
  type SchemeKey,
} from "@/lib/schemes";

interface SchemeQuery {
  sql: string;
  args: (string | number | null)[];
  describe: (row: Record<string, unknown>) => string;
}

function formatRupees(amount: unknown): string {
  const value = Number(amount ?? 0);
  if (Math.abs(value) >= 10000000) return `Rs ${(value / 10000000).toFixed(2)} Cr`;
  if (Math.abs(value) >= 100000) return `Rs ${(value / 100000).toFixed(2)} L`;
  return `Rs ${value.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

function buildQuery(
  scheme: SchemeKey,
  state: string,
  finYear: string,
): SchemeQuery | null {
  switch (scheme) {
    case "MGNREGA":
      return {
        sql: `SELECT COUNT(*) as districts, SUM(cases_reported) as total_cases,
              SUM(amount_reported) as total_reported, SUM(amount_recovered) as total_recovered,
              SUM(amount_to_recover) as total_to_recover
              FROM misappropriation WHERE UPPER(state) = UPPER(?) AND fin_year = ?`,
        args: [state, finYear],
        describe: (r) =>
          `MGNREGA in ${state} (${finYear}): ${r.districts} districts, ${r.total_cases} cases reported, ${formatRupees(r.total_reported)} reported, ${formatRupees(r.total_recovered)} recovered.`,
      };
    case "PMGSY":
      return {
        sql: `SELECT COUNT(*) as districts, SUM(length_sanctioned_km) as total_sanctioned,
              SUM(length_completed_km) as total_completed
              FROM pmgsy_district WHERE UPPER(state) = UPPER(?)`,
        args: [state],
        describe: (r) =>
          `PMGSY in ${state}: ${r.districts} districts, ${Number(r.total_sanctioned ?? 0).toFixed(1)} km sanctioned, ${Number(r.total_completed ?? 0).toFixed(1)} km completed.`,
      };
    case "PMAY-G":
      return {
        sql: `SELECT COUNT(*) as districts, SUM(houses_sanctioned) as total_sanctioned,
              SUM(houses_completed) as total_completed
              FROM pmayg_district WHERE UPPER(state) = UPPER(?) AND fin_year = ?`,
        args: [state, finYear],
        describe: (r) =>
          `PMAY-G in ${state} (${finYear}): ${r.districts} districts, ${Number(r.total_sanctioned ?? 0).toLocaleString("en-IN")} sanctioned, ${Number(r.total_completed ?? 0).toLocaleString("en-IN")} completed.`,
      };
    case "PM Kisan":
      return {
        sql: `SELECT COUNT(*) as districts, SUM(beneficiaries_paid) as total_paid,
              NULL as total_amount
              FROM pmkisan_district WHERE UPPER(state) = UPPER(?) AND fin_year = ?`,
        args: [state, finYear],
        describe: (r) =>
          `PM Kisan in ${state} (${finYear}): ${r.districts} districts, ${Number(r.total_paid ?? 0).toLocaleString("en-IN")} farmers recorded as paid. This district source does not publish money.`,
      };
    case "JJM":
      return {
        sql: `SELECT COUNT(*) as districts, AVG(coverage_pct) as avg_coverage,
              SUM(households_with_tap) as total_tap
              FROM jjm_district WHERE UPPER(state) = UPPER(?) AND fin_year = ?`,
        args: [state, finYear],
        describe: (r) =>
          `JJM in ${state} (${finYear}): ${r.districts} districts, ${Number(r.avg_coverage ?? 0).toFixed(1)}% avg coverage, ${Number(r.total_tap ?? 0).toLocaleString("en-IN")} households with tap.`,
      };
    case "PM POSHAN":
      return {
        sql: `SELECT COUNT(*) as districts, SUM(children_enrolled) as total_enrolled,
              SUM(children_fed) as total_fed
              FROM pmposhan_district WHERE UPPER(state) = UPPER(?) AND fin_year = ?`,
        args: [state, finYear],
        describe: (r) =>
          `PM POSHAN in ${state} (${finYear}): ${r.districts} districts, ${Number(r.total_fed ?? 0).toLocaleString("en-IN")} children reported fed in a daily meal snapshot. ${Number(r.total_enrolled ?? 0).toLocaleString("en-IN")} enrolled is context, not a coverage denominator.`,
      };
    case "NSAP":
      return {
        sql: `SELECT COUNT(DISTINCT UPPER(district)) as districts,
              SUM(beneficiaries_paid) as total_paid, NULL as total_amount
              FROM nsap_district WHERE UPPER(state) = UPPER(?) AND fin_year = ?`,
        args: [state, finYear],
        describe: (r) =>
          `NSAP in ${state} (${finYear}): ${r.districts} distinct districts, ${Number(r.total_paid ?? 0).toLocaleString("en-IN")} beneficiaries recorded as paid. District spending is not published.`,
      };
    case "PDS/NFSA":
      return {
        sql: `SELECT COUNT(*) as districts, SUM(ration_cards_total) as total_cards,
              NULL as active_cards
              FROM nfsa_district WHERE UPPER(state) = UPPER(?) AND fin_year = ?`,
        args: [state, finYear],
        describe: (r) =>
          `PDS/NFSA in ${state} (${finYear}): ${r.districts} districts, ${Number(r.total_cards ?? 0).toLocaleString("en-IN")} ration cards recorded. Active-card status is not separately published.`,
      };
    default:
      return null;
  }
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ scheme: string }> },
) {
  const { scheme: rawScheme } = await params;
  const scheme = resolveSchemeParam(rawScheme);
  const searchParams = request.nextUrl.searchParams;
  const state = searchParams.get("state");
  const finYear = searchParams.get("fin_year") ?? (await getLatestFinYear());

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

  const schemeQuery = buildQuery(scheme, state, finYear);
  if (!schemeQuery) {
    return Response.json(
      { error: `No query configured for scheme "${scheme}".` },
      { status: 500 },
    );
  }

  const rows = await query<Record<string, unknown>>(
    schemeQuery.sql,
    schemeQuery.args,
  );

  const data = rows[0] ?? null;

  if (!data || Number(data.districts ?? 0) === 0) {
    return Response.json({
      answer: `No data found for ${scheme} in ${state} (${finYear}).`,
      data: null,
    });
  }

  return Response.json({
    answer: schemeQuery.describe(data),
    data,
  });
}
