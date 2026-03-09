import { type NextRequest } from "next/server";
import { query, resolveState } from "@/lib/db";

function fmtRs(amount: number): string {
  if (Math.abs(amount) >= 100) return `Rs ${(amount / 100).toFixed(2)} Cr`;
  return `Rs ${amount.toFixed(2)} L`;
}

interface MoneyFlowRow {
  scheme: string;
  fin_year: string;
  allocated_lakhs: number | null;
  released_lakhs: number | null;
  expended_lakhs: number | null;
  utilization_pct: number | null;
  units_target: number | null;
  units_completed: number | null;
  units_label: string | null;
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ name: string }> },
) {
  const { name } = await params;
  const district = decodeURIComponent(name);
  const searchParams = request.nextUrl.searchParams;

  let state = searchParams.get("state");
  if (!state) {
    state = await resolveState(district);
  }

  let rows: MoneyFlowRow[];

  if (state) {
    rows = await query<MoneyFlowRow>(
      `SELECT scheme, fin_year, allocated_lakhs, released_lakhs, expended_lakhs,
              utilization_pct, units_target, units_completed, units_label
       FROM money_flow
       WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?)
       ORDER BY scheme, fin_year`,
      [district, state],
    );
  } else {
    rows = await query<MoneyFlowRow>(
      `SELECT scheme, fin_year, allocated_lakhs, released_lakhs, expended_lakhs,
              utilization_pct, units_target, units_completed, units_label
       FROM money_flow
       WHERE UPPER(district) = UPPER(?)
       ORDER BY scheme, fin_year`,
      [district],
    );
  }

  if (rows.length === 0) {
    return Response.json({
      answer: `No money flow data found for district "${district}".`,
      data: [],
    });
  }

  // Group by scheme for summary
  const byScheme = new Map<string, MoneyFlowRow[]>();
  for (const row of rows) {
    const existing = byScheme.get(row.scheme) ?? [];
    existing.push(row);
    byScheme.set(row.scheme, existing);
  }

  const summaryParts: string[] = [];
  for (const [scheme, schemeRows] of byScheme) {
    const latest = schemeRows[schemeRows.length - 1];
    const parts = [`${scheme} (${latest.fin_year}):`];

    if (latest.allocated_lakhs != null && latest.allocated_lakhs > 0)
      parts.push(`  Allocated: ${fmtRs(latest.allocated_lakhs)}`);
    if (latest.released_lakhs != null && latest.released_lakhs > 0)
      parts.push(`  Released: ${fmtRs(latest.released_lakhs)}`);
    if (latest.expended_lakhs != null && latest.expended_lakhs > 0)
      parts.push(`  Expended: ${fmtRs(latest.expended_lakhs)}`);
    if (latest.utilization_pct != null)
      parts.push(`  Utilization: ${latest.utilization_pct.toFixed(1)}%`);
    if (latest.units_target != null && latest.units_completed != null)
      parts.push(
        `  Delivery: ${latest.units_completed.toLocaleString("en-IN")} / ${latest.units_target.toLocaleString("en-IN")} ${latest.units_label ?? "units"}`,
      );

    summaryParts.push(parts.join("\n"));
  }

  const answer = `Money flow for ${district}${state ? `, ${state}` : ""} (${byScheme.size} schemes, ${rows.length} records):\n\n${summaryParts.join("\n\n")}`;

  return Response.json({ answer, data: rows });
}
