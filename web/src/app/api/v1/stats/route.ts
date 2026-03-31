import { type NextRequest } from "next/server";
import { query, queryOne } from "@/lib/db";

const MAJOR_TABLES = [
  "misappropriation",
  "financial_statement",
  "fto_status",
  "fto_pendency",
  "issues_reported",
  "pmgsy_progress",
  "pmgsy_district",
  "pmayg_district",
  "pmayg_finance",
  "pmkisan_district",
  "jjm_district",
  "jjm_allocation",
  "pmposhan_district",
  "pmposhan_finance",
  "nsap_district",
  "nsap_finance",
  "nfsa_district",
  "nfsa_allocation",
  "sbm_district",
  "nrlm_district",
  "udise_state",
];

interface CountRow {
  cnt: number;
}

interface MaxRow {
  latest: string | null;
}

export async function GET(_request: NextRequest) {
  try {
    // Scheme count from money_flow view
    const schemeRow = await queryOne<CountRow>(
      "SELECT COUNT(DISTINCT scheme) as cnt FROM money_flow",
    );
    const schemeCount = schemeRow?.cnt ?? 0;

    // District count (exclude state-level 'ALL' rows)
    const districtRow = await queryOne<CountRow>(
      "SELECT COUNT(DISTINCT district) as cnt FROM money_flow WHERE district != 'ALL'",
    );
    const districtCount = districtRow?.cnt ?? 0;

    // Total records across all major tables
    let totalRecords = 0;
    for (const table of MAJOR_TABLES) {
      try {
        const row = await queryOne<CountRow>(
          `SELECT COUNT(*) as cnt FROM ${table}`,
        );
        totalRecords += row?.cnt ?? 0;
      } catch {
        // Table may not exist — skip
      }
    }

    // Last updated: MAX(scraped_at) across tables
    let lastUpdated: string | null = null;
    for (const table of MAJOR_TABLES) {
      try {
        const row = await queryOne<MaxRow>(
          `SELECT MAX(scraped_at) as latest FROM ${table}`,
        );
        if (row?.latest && (lastUpdated === null || row.latest > lastUpdated)) {
          lastUpdated = row.latest;
        }
      } catch {
        // Table may not exist — skip
      }
    }

    return Response.json({
      scheme_count: schemeCount,
      district_count: districtCount,
      total_records: totalRecords,
      last_updated: lastUpdated?.slice(0, 10) ?? null,
    });
  } catch (error) {
    return Response.json(
      { error: "Failed to fetch stats" },
      { status: 500 },
    );
  }
}
