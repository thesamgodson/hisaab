import { getLatestFinYear } from "@/lib/fin-year";
import { type NextRequest } from "next/server";
import { queryOne } from "@/lib/db";
import { buildConstituencyReportCard } from "@/lib/report-card";

interface MpInfo {
  mp_name: string;
  party: string;
  constituency: string;
  state: string;
  elected_year: number;
  source_url: string;
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ name: string }> },
) {
  const { name } = await params;
  const constituency = decodeURIComponent(name);
  const finYear = request.nextUrl.searchParams.get("fin_year") ?? (await getLatestFinYear());

  const mp = await queryOne<MpInfo>(
    `SELECT * FROM mp_info WHERE UPPER(constituency) = UPPER(?)`,
    [constituency],
  );

  if (!mp) {
    return Response.json(
      {
        error: `No MP found for constituency "${constituency}". Use /api/v1/constituency/search to find valid constituency names.`,
      },
      { status: 404 },
    );
  }

  const reportCard = await buildConstituencyReportCard(mp.constituency, finYear);

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
