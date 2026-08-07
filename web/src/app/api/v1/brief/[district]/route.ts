import { getLatestFinYear } from "@/lib/fin-year";
import { type NextRequest } from "next/server";
import { queryOne, resolveState } from "@/lib/db";

function fmtRs(amount: number, unit: string = "rupees"): string {
  if (unit === "lakhs") {
    if (Math.abs(amount) >= 100) return `Rs ${(amount / 100).toFixed(2)} Cr`;
    return `Rs ${amount.toFixed(2)} L`;
  }
  if (Math.abs(amount) >= 10000000) return `Rs ${(amount / 10000000).toFixed(2)} Cr`;
  if (Math.abs(amount) >= 100000) return `Rs ${(amount / 100000).toFixed(2)} L`;
  return `Rs ${amount.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ district: string }> },
) {
  const { district: rawDistrict } = await params;
  const district = decodeURIComponent(rawDistrict).toUpperCase().trim().replace(/-/g, " ");
  const searchParams = request.nextUrl.searchParams;
  const finYear = searchParams.get("fin_year") ?? (await getLatestFinYear());

  let state = searchParams.get("state");
  if (!state) {
    state = await resolveState(district);
  }
  if (!state) {
    return Response.json(
      { error: `Could not resolve state for district "${district}"` },
      { status: 404 },
    );
  }

  const args: (string | number)[] = [district, state, finYear];

  const [misappropriation, financial, pmgsy] = await Promise.all([
    queryOne<Record<string, unknown>>(
      `SELECT * FROM misappropriation WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?) AND fin_year = ?`,
      args,
    ),
    queryOne<Record<string, unknown>>(
      `SELECT * FROM financial_statement WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?) AND fin_year = ?`,
      args,
    ),
    queryOne<Record<string, unknown>>(
      `SELECT * FROM pmgsy_district WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?)`,
      [district, state],
    ),
  ]);

  const briefParts: string[] = [
    `HISAAB BRIEF: ${district}, ${state}`,
    `Financial Year: ${finYear}`,
    `Generated: ${new Date().toISOString().slice(0, 10)}`,
    "",
  ];

  // MGNREGA section
  if (misappropriation || financial) {
    briefParts.push("--- MGNREGA ---");

    if (financial) {
      const totalAvail = Number(financial.total_availability ?? 0);
      const totalExpend = Number(financial.cumulative_expenditure ?? 0);
      briefParts.push(`Fund availability: ${fmtRs(totalAvail, "lakhs")}`);
      briefParts.push(`Total expenditure: ${fmtRs(totalExpend, "lakhs")}`);
    }

    if (misappropriation) {
      const amtReported = Number(misappropriation.amount_reported ?? 0);
      const amtRecovered = Number(misappropriation.amount_recovered ?? 0);
      if (amtReported > 0) {
        briefParts.push(`Amount reported: ${fmtRs(amtReported)}`);
        briefParts.push(`Amount recovered: ${fmtRs(amtRecovered)}`);
      }
    }

    briefParts.push("");
  }

  // PMGSY section
  if (pmgsy) {
    briefParts.push("--- PMGSY ---");
    const sanctioned = Number(pmgsy.roads_sanctioned ?? 0);
    const completed = Number(pmgsy.roads_completed ?? 0);
    if (sanctioned > 0) {
      briefParts.push(`Roads sanctioned: ${sanctioned.toLocaleString("en-IN")}`);
      briefParts.push(`Roads completed: ${completed.toLocaleString("en-IN")}`);
    }
    if (pmgsy.expenditure_cr != null) {
      briefParts.push(`Expenditure: ${fmtRs(Number(pmgsy.expenditure_cr) * 100, "lakhs")}`);
    }
    briefParts.push("");
  }

  if (!misappropriation && !financial && !pmgsy) {
    briefParts.push("No key scheme data available for this district in the selected financial year.");
  }

  const brief = briefParts.join("\n");

  return Response.json({
    district,
    state,
    brief,
    format: "plain_text",
  });
}
