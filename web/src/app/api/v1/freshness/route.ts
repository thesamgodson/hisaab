import { type NextRequest } from "next/server";
import { query } from "@/lib/db";

const SCHEME_TABLES: Record<string, string[]> = {
  MGNREGA: [
    "misappropriation",
    "financial_statement",
    "fto_status",
    "fto_pendency",
    "issues_reported",
  ],
  PMGSY: ["pmgsy_progress", "pmgsy_district"],
  "PMAY-G": ["pmayg_district"],
  "PM Kisan": ["pmkisan_district"],
  JJM: ["jjm_district"],
  "PM POSHAN": ["pmposhan_district"],
  NSAP: ["nsap_district"],
  "PDS/NFSA": ["nfsa_district"],
};

const SCHEME_SOURCES: Record<string, string> = {
  MGNREGA: "nrega.nic.in",
  PMGSY: "pmgsy.dord.gov.in",
  "PMAY-G": "report.pmayg.dord.gov.in",
  "PM Kisan": "data.gov.in",
  JJM: "ejalshakti.gov.in",
  "PM POSHAN": "pmposhan-ams.education.gov.in",
  NSAP: "nsap.nic.in / data.gov.in",
  "PDS/NFSA": "nfsa.gov.in",
};

interface TableStats {
  cnt: number;
  states: number;
  latest: string | null;
}

export async function GET(_request: NextRequest) {
  const freshness: {
    scheme: string;
    source: string;
    latest_scraped: string | null;
    records: number;
    states: number;
  }[] = [];

  let totalRecords = 0;

  for (const [scheme, tables] of Object.entries(SCHEME_TABLES)) {
    let records = 0;
    let states = 0;
    let latestScraped: string | null = null;

    for (const table of tables) {
      try {
        const rows = await query<TableStats>(
          `SELECT COUNT(*) as cnt, COUNT(DISTINCT state) as states, MAX(scraped_at) as latest FROM ${table}`,
        );
        const row = rows[0];
        if (row) {
          records += row.cnt;
          states = Math.max(states, row.states);
          if (
            row.latest &&
            (latestScraped === null || row.latest > latestScraped)
          ) {
            latestScraped = row.latest;
          }
        }
      } catch {
        // Table may not exist — skip
      }
    }

    totalRecords += records;

    freshness.push({
      scheme,
      source: SCHEME_SOURCES[scheme] ?? "unknown",
      latest_scraped: latestScraped?.slice(0, 10) ?? null,
      records,
      states,
    });
  }

  return Response.json({ freshness, total_records: totalRecords });
}
