import { type NextRequest } from "next/server";
import { query } from "@/lib/db";
import { getLatestFinYear } from "@/lib/fin-year";

interface MisappropriationRow {
  district: string;
  cases_reported: number;
  amount_reported: number;
  recovery_rate_pct: number;
  source_url: string | null;
}

interface PmgsyRow {
  district: string;
  length_sanctioned_km: number;
  length_completed_km: number;
  completion_pct: number;
}

interface JjmRow {
  district: string;
  coverage_pct: number;
}

function formatRupees(amount: number): string {
  if (Math.abs(amount) >= 10000000) return `Rs ${(amount / 10000000).toFixed(2)} Cr`;
  if (Math.abs(amount) >= 100000) return `Rs ${(amount / 100000).toFixed(2)} L`;
  return `Rs ${amount.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

export async function GET(request: NextRequest) {
  const state = request.nextUrl.searchParams.get("state");
  if (!state) {
    // A national API must never silently answer for one state.
    return Response.json(
      {
        error:
          "Query parameter 'state' is required. For national worst districts use /api/v1/scores/worst.",
      },
      { status: 400 },
    );
  }
  const limitParam = request.nextUrl.searchParams.get("limit");
  const limit = Math.min(
    Math.max(parseInt(limitParam ?? "10", 10) || 10, 1),
    50,
  );
  const finYear =
    request.nextUrl.searchParams.get("fin_year") ?? (await getLatestFinYear());

  // Misappropriation
  let misappropriation: {
    answer: string;
    data: MisappropriationRow[];
    source_url: string | null;
  } = { answer: "No misappropriation data available.", data: [], source_url: null };

  try {
    const rows = await query<MisappropriationRow>(
      `SELECT district, cases_reported, amount_reported, recovery_rate_pct, source_url
       FROM misappropriation
       WHERE UPPER(state) = UPPER(?) AND fin_year = ?
       ORDER BY amount_reported DESC
       LIMIT ?`,
      [state, finYear, limit],
    );

    if (rows.length > 0) {
      const top = rows[0];
      const sourceUrl = top.source_url ?? null;
      const answer =
        rows.length === 1
          ? `${top.district}: ${top.cases_reported} cases, ${formatRupees(top.amount_reported)} reported, ${top.recovery_rate_pct}% recovered.`
          : `Top ${rows.length} districts by reported misappropriation amount: ${rows.map((r) => `${r.district} (${formatRupees(r.amount_reported)})`).join(", ")}.`;
      misappropriation = { answer, data: rows, source_url: sourceUrl };
    }
  } catch {
    // Table may not exist
  }

  // PMGSY completion
  let pmgsyCompletion: {
    answer: string;
    data: PmgsyRow[];
  } = { answer: "No PMGSY data available.", data: [] };

  try {
    const rows = await query<PmgsyRow>(
      `SELECT district, length_sanctioned_km, length_completed_km,
              CASE WHEN length_sanctioned_km > 0
                   THEN ROUND(length_completed_km * 100.0 / length_sanctioned_km, 1)
                   ELSE 0
              END as completion_pct
       FROM pmgsy_district
       WHERE UPPER(state) = UPPER(?)
       ORDER BY completion_pct ASC
       LIMIT ?`,
      [state, limit],
    );

    if (rows.length > 0) {
      const answer = `Lowest PMGSY completion: ${rows.map((r) => `${r.district} (${r.completion_pct}%)`).join(", ")}.`;
      pmgsyCompletion = { answer, data: rows };
    }
  } catch {
    // Table may not exist
  }

  // JJM coverage
  let jjmCoverage: {
    answer: string;
    data: JjmRow[];
  } = { answer: "No JJM data available.", data: [] };

  try {
    const rows = await query<JjmRow>(
      `SELECT district, coverage_pct
       FROM jjm_district
       WHERE UPPER(state) = UPPER(?) AND fin_year = ?
       ORDER BY coverage_pct ASC
       LIMIT ?`,
      [state, finYear, limit],
    );

    if (rows.length > 0) {
      const answer = `Lowest JJM tap water coverage: ${rows.map((r) => `${r.district} (${r.coverage_pct}%)`).join(", ")}.`;
      jjmCoverage = { answer, data: rows };
    }
  } catch {
    // Table may not exist
  }

  return Response.json({
    misappropriation,
    pmgsy_completion: pmgsyCompletion,
    jjm_coverage: jjmCoverage,
  });
}
