import { query } from "@/lib/db";

export const dynamic = "force-dynamic";

/** Every dataset the product serves — the freshness surface must cover ALL
 *  of them, including finance/allocation tables. An accountability site
 *  whose own transparency endpoint omits schemes is lying by omission. */
const SCHEME_TABLES: Record<string, string[]> = {
  MGNREGA: [
    "misappropriation",
    "financial_statement",
    "fto_status",
    "fto_pendency",
    "issues_reported",
  ],
  PMGSY: ["pmgsy_progress", "pmgsy_district"],
  "PMAY-G": ["pmayg_district", "pmayg_finance"],
  "PM Kisan": ["pmkisan_district"],
  JJM: ["jjm_district", "jjm_allocation"],
  "PM POSHAN": ["pmposhan_district", "pmposhan_finance"],
  NSAP: ["nsap_district", "nsap_finance"],
  "PDS/NFSA": ["nfsa_district", "nfsa_allocation"],
  "SBM-G": ["sbm_district"],
  "DAY-NRLM": ["nrlm_district"],
  "UDISE+": ["udise_state"],
};

const SCHEME_SOURCES: Record<string, string> = {
  MGNREGA: "nrega.nic.in",
  PMGSY: "pmgsy.dord.gov.in",
  "PMAY-G": "report.pmayg.dord.gov.in / data.gov.in",
  "PM Kisan": "data.gov.in",
  JJM: "ejalshakti.gov.in",
  "PM POSHAN": "pmposhan-ams.education.gov.in / data.gov.in",
  NSAP: "nsap.nic.in / data.gov.in",
  "PDS/NFSA": "nfsa.gov.in / data.gov.in",
  "SBM-G": "sbm.gov.in",
  "DAY-NRLM": "nrlm.gov.in",
  "UDISE+": "api.udiseplus.gov.in",
};

interface TableStats {
  table_name: string;
  cnt: number;
  states: number;
  latest: string | null;
}

export async function GET() {
  // One UNION ALL round-trip for all tables instead of 20 serial queries.
  const allTables = Object.values(SCHEME_TABLES).flat();
  const sql = allTables
    .map(
      (t) =>
        `SELECT '${t}' AS table_name, COUNT(*) AS cnt,
                COUNT(DISTINCT state) AS states, MAX(scraped_at) AS latest
         FROM ${t}`,
    )
    .join("\nUNION ALL\n");
  const rows = await query<TableStats>(sql);
  const byTable = new Map(rows.map((r) => [r.table_name, r]));

  let totalRecords = 0;
  const freshness = Object.entries(SCHEME_TABLES).map(([scheme, tables]) => {
    let records = 0;
    let states = 0;
    let latestScraped: string | null = null;
    for (const table of tables) {
      const row = byTable.get(table);
      if (!row) continue;
      records += Number(row.cnt);
      states = Math.max(states, Number(row.states));
      if (row.latest && (latestScraped === null || row.latest > latestScraped)) {
        latestScraped = row.latest;
      }
    }
    totalRecords += records;
    return {
      scheme,
      source: SCHEME_SOURCES[scheme] ?? "unknown",
      latest_scraped: latestScraped?.slice(0, 10) ?? null,
      records,
      states,
    };
  });

  return Response.json({ freshness, total_records: totalRecords });
}
