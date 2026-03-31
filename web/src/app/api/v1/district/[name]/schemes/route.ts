import { type NextRequest } from "next/server";
import { query } from "@/lib/db";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ name: string }> },
) {
  const { name } = await params;
  const district = decodeURIComponent(name).toUpperCase().trim().replace(/-/g, " ");

  const rows = await query<{ scheme: string }>(
    `SELECT DISTINCT scheme FROM money_flow WHERE UPPER(district) = UPPER(?) ORDER BY scheme`,
    [district],
  );

  const schemes = rows.map((r) => r.scheme);

  if (schemes.length === 0) {
    return Response.json({
      answer: `No scheme data found for district "${district}".`,
      data: [],
    });
  }

  return Response.json({
    answer: `Schemes with data for ${district}: ${schemes.join(", ")}.`,
    data: schemes,
  });
}
