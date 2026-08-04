import { getLatestFinYear } from "@/lib/fin-year";
import { type NextRequest } from "next/server";
import { getStateRankings } from "@/lib/scores";

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const finYear = searchParams.get("fin_year") ?? (await getLatestFinYear());

  const rankings = await getStateRankings(finYear);

  return Response.json({
    fin_year: finYear,
    count: rankings.length,
    rankings,
  });
}
