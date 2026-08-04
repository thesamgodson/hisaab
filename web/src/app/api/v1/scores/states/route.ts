import { type NextRequest } from "next/server";
import { getStateRankings } from "@/lib/scores";

export const revalidate = 3600;

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const finYear = searchParams.get("fin_year") ?? "2024-2025";

  const rankings = await getStateRankings(finYear);

  return Response.json({
    fin_year: finYear,
    count: rankings.length,
    rankings,
  });
}
