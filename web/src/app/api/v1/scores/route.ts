import { type NextRequest } from "next/server";
import { computeDistrictScores } from "@/lib/scores";

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const finYear = searchParams.get("fin_year") ?? "2024-2025";

  const scores = await computeDistrictScores(finYear);
  const scoredCount = scores.filter((s) => s.score !== null).length;

  return Response.json({
    fin_year: finYear,
    count: scores.length,
    scored_count: scoredCount,
    scores,
  });
}
