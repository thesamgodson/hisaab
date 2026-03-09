import { type NextRequest } from "next/server";
import { computeDistrictScores } from "@/lib/scores";
import { resolveState } from "@/lib/db";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ district: string }> },
) {
  const { district: rawDistrict } = await params;
  const district = decodeURIComponent(rawDistrict).toUpperCase();
  const searchParams = request.nextUrl.searchParams;
  const finYear = searchParams.get("fin_year") ?? "2024-2025";

  let state = searchParams.get("state")?.toUpperCase() ?? null;
  if (!state) {
    state = await resolveState(district);
    if (state) state = state.toUpperCase();
  }

  const allScores = await computeDistrictScores(finYear);

  const match = allScores.find((s) => {
    if (s.district !== district) return false;
    if (state && s.state !== state) return false;
    return true;
  });

  if (!match) {
    return Response.json(
      {
        error: `No data found for district "${district}"${state ? ` in state "${state}"` : ""}`,
      },
      { status: 404 },
    );
  }

  return Response.json(match);
}
