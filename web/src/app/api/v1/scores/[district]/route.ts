import { getLatestFinYear } from "@/lib/fin-year";
import { type NextRequest } from "next/server";
import { getDistrictScore } from "@/lib/scores";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ district: string }> },
) {
  const { district: rawDistrict } = await params;
  const district = decodeURIComponent(rawDistrict).toUpperCase();
  const searchParams = request.nextUrl.searchParams;
  const finYear = searchParams.get("fin_year") ?? (await getLatestFinYear());
  const state = searchParams.get("state")?.toUpperCase() ?? null;

  const match = await getDistrictScore(district, state, finYear);

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
