import { type NextRequest } from "next/server";
import { query, resolveState } from "@/lib/db";

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
  { params }: { params: Promise<{ name: string }> },
) {
  const { name } = await params;
  // Normalize: hyphens → spaces to match DB convention (TopoJSON uses hyphens)
  const district = decodeURIComponent(name).toUpperCase().trim().replace(/-/g, " ");
  const searchParams = request.nextUrl.searchParams;
  const finYear = searchParams.get("fin_year") ?? "2024-2025";

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

  const [misappropriation, financial, issues, fto] = await Promise.all([
    query(
      `SELECT * FROM misappropriation WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?) AND fin_year = ?`,
      args,
    ),
    query(
      `SELECT * FROM financial_statement WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?) AND fin_year = ?`,
      args,
    ),
    query(
      `SELECT * FROM issues_reported WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?) AND fin_year = ?`,
      args,
    ),
    query(
      `SELECT * FROM fto_status WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?) AND fin_year = ?`,
      args,
    ),
  ]);

  const sections: string[] = [];
  const sourceUrls: string[] = [];

  if (misappropriation.length > 0) {
    const row = misappropriation[0] as Record<string, unknown>;
    const parts = [`MGNREGA Misappropriation (${finYear}):`];
    if (row.cases_reported != null)
      parts.push(`  Cases reported: ${Number(row.cases_reported).toLocaleString("en-IN")}`);
    if (row.cases_decided != null)
      parts.push(`  Cases decided: ${Number(row.cases_decided).toLocaleString("en-IN")}`);
    if (row.amount_reported != null)
      parts.push(`  Amount reported: ${fmtRs(Number(row.amount_reported), "lakhs")}`);
    if (row.amount_recovered != null)
      parts.push(`  Amount recovered: ${fmtRs(Number(row.amount_recovered), "lakhs")}`);
    sections.push(parts.join("\n"));
    if (row.source_url) sourceUrls.push(String(row.source_url));
  }

  if (financial.length > 0) {
    const row = financial[0] as Record<string, unknown>;
    const parts = [`MGNREGA Financial Statement (${finYear}):`];
    if (row.total_availability != null)
      parts.push(`  Total fund availability: ${fmtRs(Number(row.total_availability), "lakhs")}`);
    if (row.cumulative_expenditure != null)
      parts.push(`  Total expenditure: ${fmtRs(Number(row.cumulative_expenditure), "lakhs")}`);
    if (row.exp_unskilled_wage != null)
      parts.push(`  Wage expenditure: ${fmtRs(Number(row.exp_unskilled_wage), "lakhs")}`);
    if (row.exp_material != null)
      parts.push(`  Material expenditure: ${fmtRs(Number(row.exp_material), "lakhs")}`);
    sections.push(parts.join("\n"));
    if (row.source_url) sourceUrls.push(String(row.source_url));
  }

  if (issues.length > 0) {
    const row = issues[0] as Record<string, unknown>;
    const parts = [`MGNREGA Social Audit Issues (${finYear}):`];
    if (row.total_issues != null)
      parts.push(`  Total issues reported: ${Number(row.total_issues).toLocaleString("en-IN")}`);
    if (row.total_amount != null)
      parts.push(`  Total amount: ${fmtRs(Number(row.total_amount), "lakhs")}`);
    sections.push(parts.join("\n"));
    if (row.source_url) sourceUrls.push(String(row.source_url));
  }

  if (fto.length > 0) {
    const row = fto[0] as Record<string, unknown>;
    const parts = [`MGNREGA FTO Status (${finYear}):`];
    if (row.total_fto_generated != null)
      parts.push(`  Total FTOs generated: ${Number(row.total_fto_generated).toLocaleString("en-IN")}`);
    if (row.first_signatory_pending != null)
      parts.push(`  First signatory pending: ${Number(row.first_signatory_pending).toLocaleString("en-IN")}`);
    sections.push(parts.join("\n"));
    if (row.source_url) sourceUrls.push(String(row.source_url));
  }

  if (sections.length === 0) {
    return Response.json({
      answer: `No data found for district "${district}" (${state}) in ${finYear}.`,
      source_urls: [],
    });
  }

  const answer = `District overview for ${district}, ${state} (${finYear}):\n\n${sections.join("\n\n")}`;

  return Response.json({
    answer,
    source_urls: [...new Set(sourceUrls)],
  });
}
