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
  const finYear = request.nextUrl.searchParams.get("fin_year") ?? "2024-2025";

  const mp = await queryOne<MpInfo>(
    `SELECT * FROM mp_info WHERE UPPER(constituency) = UPPER(?)`,
    [constituency],
  );

  const reportCard = await buildConstituencyReportCard(constituency, finYear);

  return Response.json({
    constituency: constituency.toUpperCase(),
    state: mp?.state ?? "Unknown",
    mp_name: mp?.mp_name ?? "Unknown",
    party: mp?.party ?? null,
    elected_year: mp?.elected_year ?? null,
    ...reportCard,
  });
}
