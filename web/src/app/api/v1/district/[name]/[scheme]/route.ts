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

interface SchemeConfig {
  table: string;
  useFinYear: boolean;
  summarize: (row: Record<string, unknown>, finYear: string) => string;
}

const SCHEME_MAP: Record<string, SchemeConfig> = {
  mgnrega: {
    table: "misappropriation",
    useFinYear: true,
    summarize: (row, fy) => {
      const parts = [`MGNREGA Misappropriation for ${row.district}, ${row.state} (${fy}):`];
      if (row.cases_reported != null)
        parts.push(`Cases reported: ${Number(row.cases_reported).toLocaleString("en-IN")}`);
      if (row.cases_decided != null)
        parts.push(`Cases decided: ${Number(row.cases_decided).toLocaleString("en-IN")}`);
      if (row.amount_reported != null)
        parts.push(`Amount reported: ${fmtRs(Number(row.amount_reported), "lakhs")}`);
      if (row.amount_recovered != null)
        parts.push(`Amount recovered: ${fmtRs(Number(row.amount_recovered), "lakhs")}`);
      return parts.join("\n");
    },
  },
  misappropriation: {
    table: "misappropriation",
    useFinYear: true,
    summarize: (row, fy) => SCHEME_MAP.mgnrega.summarize(row, fy),
  },
  funds: {
    table: "financial_statement",
    useFinYear: true,
    summarize: (row, fy) => {
      const parts = [`MGNREGA Financial Statement for ${row.district}, ${row.state} (${fy}):`];
      if (row.total_availability != null)
        parts.push(`Total fund availability: ${fmtRs(Number(row.total_availability), "lakhs")}`);
      if (row.cumulative_expenditure != null)
        parts.push(`Total expenditure: ${fmtRs(Number(row.cumulative_expenditure), "lakhs")}`);
      if (row.exp_unskilled_wage != null)
        parts.push(`Wage expenditure: ${fmtRs(Number(row.exp_unskilled_wage), "lakhs")}`);
      if (row.exp_material != null)
        parts.push(`Material expenditure: ${fmtRs(Number(row.exp_material), "lakhs")}`);
      return parts.join("\n");
    },
  },
  audit: {
    table: "issues_reported",
    useFinYear: true,
    summarize: (row, fy) => {
      const parts = [`MGNREGA Social Audit for ${row.district}, ${row.state} (${fy}):`];
      if (row.total_issues != null)
        parts.push(`Total issues: ${Number(row.total_issues).toLocaleString("en-IN")}`);
      if (row.total_amount != null)
        parts.push(`Total amount: ${fmtRs(Number(row.total_amount), "lakhs")}`);
      return parts.join("\n");
    },
  },
  fto: {
    table: "fto_status",
    useFinYear: true,
    summarize: (row, fy) => {
      const parts = [`MGNREGA FTO Status for ${row.district}, ${row.state} (${fy}):`];
      if (row.total_fto_generated != null)
        parts.push(`Total FTOs generated: ${Number(row.total_fto_generated).toLocaleString("en-IN")}`);
      if (row.first_signatory_pending != null)
        parts.push(`First signatory pending: ${Number(row.first_signatory_pending).toLocaleString("en-IN")}`);
      return parts.join("\n");
    },
  },
  pmgsy: {
    table: "pmgsy_district",
    useFinYear: false,
    summarize: (row) => {
      const parts = [`PMGSY for ${row.district}, ${row.state}:`];
      if (row.roads_sanctioned != null)
        parts.push(`Roads sanctioned: ${Number(row.roads_sanctioned).toLocaleString("en-IN")}`);
      if (row.roads_completed != null)
        parts.push(`Roads completed: ${Number(row.roads_completed).toLocaleString("en-IN")}`);
      if (row.length_sanctioned_km != null)
        parts.push(`Length sanctioned: ${Number(row.length_sanctioned_km).toFixed(2)} km`);
      if (row.length_completed_km != null)
        parts.push(`Length completed: ${Number(row.length_completed_km).toFixed(2)} km`);
      if (row.expenditure_cr != null)
        parts.push(`Expenditure: ${fmtRs(Number(row.expenditure_cr) * 100, "lakhs")}`);
      return parts.join("\n");
    },
  },
  pmayg: {
    table: "pmayg_district",
    useFinYear: true,
    summarize: (row, fy) => {
      const parts = [`PMAY-G for ${row.district}, ${row.state} (${fy}):`];
      if (row.houses_sanctioned != null)
        parts.push(`Houses sanctioned: ${Number(row.houses_sanctioned).toLocaleString("en-IN")}`);
      if (row.houses_completed != null)
        parts.push(`Houses completed: ${Number(row.houses_completed).toLocaleString("en-IN")}`);
      if (row.houses_sanctioned != null && row.houses_completed != null && Number(row.houses_sanctioned) > 0) {
        const pct = ((Number(row.houses_completed) / Number(row.houses_sanctioned)) * 100).toFixed(1);
        parts.push(`Completion rate: ${pct}%`);
      }
      return parts.join("\n");
    },
  },
  pmkisan: {
    table: "pmkisan_district",
    useFinYear: true,
    summarize: (row, fy) => {
      const parts = [`PM Kisan for ${row.district}, ${row.state} (${fy}):`];
      if (row.beneficiaries_paid != null)
        parts.push(`Beneficiaries paid: ${Number(row.beneficiaries_paid).toLocaleString("en-IN")}`);
      if (row.amount_paid_lakhs != null)
        parts.push(`Amount paid: ${fmtRs(Number(row.amount_paid_lakhs), "lakhs")}`);
      return parts.join("\n");
    },
  },
  jjm: {
    table: "jjm_district",
    useFinYear: true,
    summarize: (row, fy) => {
      const parts = [`JJM for ${row.district}, ${row.state} (${fy}):`];
      if (row.coverage_pct != null)
        parts.push(`Coverage: ${Number(row.coverage_pct).toFixed(1)}%`);
      if (row.households_with_tap != null)
        parts.push(`Households with tap: ${Number(row.households_with_tap).toLocaleString("en-IN")}`);
      if (row.total_households != null)
        parts.push(`Total households: ${Number(row.total_households).toLocaleString("en-IN")}`);
      return parts.join("\n");
    },
  },
  pmposhan: {
    table: "pmposhan_district",
    useFinYear: true,
    summarize: (row, fy) => {
      const parts = [`PM POSHAN for ${row.district}, ${row.state} (${fy}):`];
      if (row.children_enrolled != null)
        parts.push(`Children enrolled: ${Number(row.children_enrolled).toLocaleString("en-IN")}`);
      if (row.children_fed != null)
        parts.push(`Children fed: ${Number(row.children_fed).toLocaleString("en-IN")}`);
      if (row.children_enrolled != null && row.children_fed != null && Number(row.children_enrolled) > 0) {
        const pct = ((Number(row.children_fed) / Number(row.children_enrolled)) * 100).toFixed(1);
        parts.push(`Feeding coverage: ${pct}%`);
      }
      return parts.join("\n");
    },
  },
  nsap: {
    table: "nsap_district",
    useFinYear: true,
    summarize: (row, fy) => {
      const parts = [`NSAP for ${row.district}, ${row.state} (${fy}):`];
      if (row.beneficiaries_paid != null)
        parts.push(`Beneficiaries paid: ${Number(row.beneficiaries_paid).toLocaleString("en-IN")}`);
      if (row.amount_paid_lakhs != null)
        parts.push(`Amount paid: ${fmtRs(Number(row.amount_paid_lakhs), "lakhs")}`);
      if (row.scheme_type != null)
        parts.push(`Sub-scheme: ${row.scheme_type}`);
      return parts.join("\n");
    },
  },
  nfsa: {
    table: "nfsa_district",
    useFinYear: true,
    summarize: (row, fy) => {
      const parts = [`NFSA/PDS for ${row.district}, ${row.state} (${fy}):`];
      if (row.ration_cards_total != null)
        parts.push(`Total ration cards: ${Number(row.ration_cards_total).toLocaleString("en-IN")}`);
      if (row.ration_cards_active != null)
        parts.push(`Active ration cards: ${Number(row.ration_cards_active).toLocaleString("en-IN")}`);
      if (row.beneficiaries_total != null)
        parts.push(`Total beneficiaries: ${Number(row.beneficiaries_total).toLocaleString("en-IN")}`);
      return parts.join("\n");
    },
  },
};

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ name: string; scheme: string }> },
) {
  const { name, scheme } = await params;
  const district = decodeURIComponent(name).toUpperCase().trim().replace(/-/g, " ");
  const schemeSlug = decodeURIComponent(scheme).toLowerCase();
  const searchParams = request.nextUrl.searchParams;
  const finYear = searchParams.get("fin_year") ?? (await getLatestFinYear());

  const config = SCHEME_MAP[schemeSlug];
  if (!config) {
    return Response.json(
      { error: `Unknown scheme "${scheme}". Valid: ${Object.keys(SCHEME_MAP).join(", ")}` },
      { status: 404 },
    );
  }

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

  let row: Record<string, unknown> | null;

  if (config.useFinYear) {
    row = await queryOne(
      `SELECT * FROM ${config.table} WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?) AND fin_year = ?`,
      [district, state, finYear],
    );
  } else {
    row = await queryOne(
      `SELECT * FROM ${config.table} WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?)`,
      [district, state],
    );
  }

  if (!row) {
    return Response.json({
      answer: `No ${schemeSlug} data found for ${district}, ${state}${config.useFinYear ? ` in ${finYear}` : ""}.`,
      data: null,
    });
  }

  const answer = config.summarize(row, finYear);
  const sourceUrl = row.source_url ? String(row.source_url) : undefined;

  return Response.json({
    answer,
    data: row,
    ...(sourceUrl && { source_url: sourceUrl }),
  });
}
