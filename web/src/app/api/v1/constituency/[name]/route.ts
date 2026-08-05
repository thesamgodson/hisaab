import { getLatestFinYear } from "@/lib/fin-year";
import { type NextRequest } from "next/server";
import { query, queryOne } from "@/lib/db";
import { buildConstituencyReportCard } from "@/lib/report-card";
import {
  candidateStates,
  pcNameNorm,
  stripReservation,
} from "@/lib/vintage-states";

interface MpInfo {
  mp_name: string;
  party: string;
  constituency: string;
  state: string;
  elected_year: number;
  source_url: string;
}

// India reuses PC names across states (AURANGABAD is a Bihar seat and a
// Maharashtra seat). Without ?state= an ambiguous name answers 300 with the
// candidates — a report card must never merge two states' districts.
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ name: string }> },
) {
  const { name } = await params;
  const constituency = decodeURIComponent(name);
  const finYear =
    request.nextUrl.searchParams.get("fin_year") ?? (await getLatestFinYear());
  const stateParam = request.nextUrl.searchParams.get("state");
  const cleanName = stripReservation(constituency);

  // Where can this name legitimately live? constituency_district (datameet,
  // internally-consistent vintage labels) is the primary registry; names it
  // doesn't know fall back to mp_info's (today's) labels. Never union the
  // two vocabularies — a vintage seat would look falsely ambiguous.
  const cdStates = await query<{ state: string }>(
    `SELECT DISTINCT state FROM constituency_district
     WHERE ${pcNameNorm("constituency")} = ? ORDER BY state`,
    [cleanName],
  );
  const mpStates = cdStates.length
    ? []
    : await query<{ state: string }>(
        `SELECT DISTINCT state FROM mp_info
         WHERE ${pcNameNorm("constituency")} = ? ORDER BY state`,
        [cleanName],
      );
  const scopes = (cdStates.length ? cdStates : mpStates).map((r) =>
    r.state.toUpperCase(),
  );

  if (!stateParam && scopes.length > 1) {
    return Response.json(
      {
        error: `Constituency "${constituency}" exists in more than one state.`,
        candidates: scopes.map((state) => ({ constituency: cleanName, state })),
        hint: "Retry with ?state=<STATE>.",
      },
      { status: 300 },
    );
  }
  const scope = stateParam?.toUpperCase() ?? scopes[0] ?? null;

  let mp: MpInfo | null = null;
  if (scope) {
    for (const st of candidateStates(scope)) {
      mp = await queryOne<MpInfo>(
        `SELECT * FROM mp_info
         WHERE ${pcNameNorm("constituency")} = ? AND UPPER(state) = ?`,
        [cleanName, st],
      );
      if (mp) break;
    }
  }

  const reportCard = await buildConstituencyReportCard(
    constituency,
    finYear,
    scope ?? undefined,
  );

  return Response.json({
    constituency: constituency.toUpperCase(),
    state: mp?.state ?? scope ?? "Unknown",
    mp_name: mp?.mp_name ?? "Unknown",
    party: mp?.party ?? null,
    elected_year: mp?.elected_year ?? null,
    ...reportCard,
  });
}
