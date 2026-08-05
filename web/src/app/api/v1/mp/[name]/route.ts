import { getLatestFinYear } from "@/lib/fin-year";
import { type NextRequest } from "next/server";
import { query, queryOne } from "@/lib/db";
import { buildConstituencyReportCard } from "@/lib/report-card";
import {
  candidateStates,
  pcNameLookupCandidates,
  pcNameNorm,
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
// candidates — never another state's MP. Legacy/variant names expand through
// the PC-name registry (PONDICHERRY resolves to PUDUCHERRY's MP).
export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ name: string }> },
) {
  const { name } = await params;
  const constituency = decodeURIComponent(name);
  const finYear =
    request.nextUrl.searchParams.get("fin_year") ?? (await getLatestFinYear());
  const stateParam = request.nextUrl.searchParams.get("state");

  let mp: MpInfo | null = null;
  if (stateParam) {
    const names = pcNameLookupCandidates(constituency, stateParam);
    const nameSlots = names.map(() => "?").join(", ");
    for (const st of candidateStates(stateParam)) {
      mp = await queryOne<MpInfo>(
        `SELECT * FROM mp_info
         WHERE ${pcNameNorm("constituency")} IN (${nameSlots}) AND UPPER(state) = ?`,
        [...names, st],
      );
      if (mp) break;
    }
  } else {
    const names = pcNameLookupCandidates(constituency);
    const nameSlots = names.map(() => "?").join(", ");
    const matches = await query<MpInfo>(
      `SELECT * FROM mp_info
       WHERE ${pcNameNorm("constituency")} IN (${nameSlots}) ORDER BY state`,
      names,
    );
    if (matches.length > 1) {
      return Response.json(
        {
          error: `Constituency "${constituency}" exists in more than one state.`,
          candidates: matches.map((m) => ({
            constituency: m.constituency,
            state: m.state,
            mp_name: m.mp_name,
          })),
          hint: "Retry with ?state=<STATE>.",
        },
        { status: 300 },
      );
    }
    mp = matches[0] ?? null;
  }

  if (!mp) {
    const scopeNote = stateParam ? ` in ${stateParam.toUpperCase()}` : "";
    return Response.json(
      {
        error: `No MP found for constituency "${constituency}"${scopeNote}. Use /api/v1/constituency/search to find valid constituency names.`,
      },
      { status: 404 },
    );
  }

  const reportCard = await buildConstituencyReportCard(
    mp.constituency,
    finYear,
    mp.state,
  );

  return Response.json({
    mp_name: mp.mp_name,
    party: mp.party,
    constituency: mp.constituency,
    state: mp.state,
    elected_year: mp.elected_year,
    source_url: mp.source_url,
    report_card: reportCard,
  });
}
