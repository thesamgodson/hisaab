import { query, queryOne } from "@/lib/db";

export const dynamic = "force-dynamic";

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

interface StatRow {
  cnt: number;
  latest: string | null;
}

export async function GET() {
  // One UNION ALL statement instead of 42 serial round-trips.
  const perTableSql = MAJOR_TABLES.map(
    (t) => `SELECT COUNT(*) AS cnt, MAX(scraped_at) AS latest FROM ${t}`,
  ).join("\nUNION ALL\n");

  const [schemeRow, districtRow, tableStats] = await Promise.all([
    queryOne<CountRow>("SELECT COUNT(DISTINCT scheme) as cnt FROM money_flow"),
    queryOne<CountRow>(
      "SELECT COUNT(DISTINCT district) as cnt FROM money_flow WHERE district != 'ALL'",
    ),
    query<StatRow>(perTableSql),
  ]);

  const totalRecords = tableStats.reduce((sum, r) => sum + Number(r.cnt), 0);
  const lastUpdated = tableStats.reduce<string | null>(
    (latest, r) =>
      r.latest && (latest === null || r.latest > latest) ? r.latest : latest,
    null,
  );

  return Response.json({
    scheme_count: schemeRow?.cnt ?? 0,
    district_count: districtRow?.cnt ?? 0,
    total_records: totalRecords,
    last_updated: lastUpdated?.slice(0, 10) ?? null,
  });
}
