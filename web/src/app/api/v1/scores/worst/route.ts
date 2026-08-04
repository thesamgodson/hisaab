import { type NextRequest } from "next/server";
import { getWorstDistricts } from "@/lib/scores";

export const revalidate = 3600;

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const n = Math.min(200, Math.max(1, Number(searchParams.get("n") ?? 50)));
  const finYear = searchParams.get("fin_year") ?? "2024-2025";

  const districts = await getWorstDistricts(n, finYear);

  return Response.json({
    fin_year: finYear,
    count: districts.length,
    districts,
  });
}
