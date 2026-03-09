import { type NextRequest } from "next/server";
import { query } from "@/lib/db";

const TABLES_WITH_FIN_YEAR = [
  "misappropriation",
  "financial_statement",
  "fto_status",
  "pmayg_district",
  "pmkisan_district",
  "jjm_district",
  "pmposhan_district",
  "nsap_district",
  "nfsa_district",
];

const TABLES_WITHOUT_FIN_YEAR = ["pmgsy_district"];

interface DistrictRow {
  district: string;
}

export async function GET(request: NextRequest) {
  const state = request.nextUrl.searchParams.get("state");
  const finYear = "2024-2025";

  const districts = new Set<string>();

  for (const table of TABLES_WITH_FIN_YEAR) {
    try {
      const sql = state
        ? `SELECT DISTINCT UPPER(district) as district FROM ${table} WHERE UPPER(state) = UPPER(?) AND fin_year = ?`
        : `SELECT DISTINCT UPPER(district) as district FROM ${table} WHERE fin_year = ?`;
      const args = state ? [state, finYear] : [finYear];
      const rows = await query<DistrictRow>(sql, args);
      for (const row of rows) {
        if (row.district) districts.add(row.district);
      }
    } catch {
      // Table may not exist — skip
    }
  }

  for (const table of TABLES_WITHOUT_FIN_YEAR) {
    try {
      const sql = state
        ? `SELECT DISTINCT UPPER(district) as district FROM ${table} WHERE UPPER(state) = UPPER(?)`
        : `SELECT DISTINCT UPPER(district) as district FROM ${table}`;
      const args = state ? [state] : [];
      const rows = await query<DistrictRow>(sql, args);
      for (const row of rows) {
        if (row.district) districts.add(row.district);
      }
    } catch {
      // Table may not exist — skip
    }
  }

  const sorted = [...districts].sort();

  return Response.json({ districts: sorted, count: sorted.length });
}
