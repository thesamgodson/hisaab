import { type NextRequest } from "next/server";
import { query } from "@/lib/db";

interface SearchResult {
  constituency: string;
  state: string;
}

export async function GET(request: NextRequest) {
  const q = request.nextUrl.searchParams.get("q");

  if (!q || q.trim().length === 0) {
    return Response.json(
      { error: "Query parameter 'q' is required." },
      { status: 400 },
    );
  }

  const searchTerm = q.trim();

  const results = await query<SearchResult>(
    `SELECT constituency, state FROM constituency_district
     WHERE UPPER(constituency) LIKE '%' || UPPER(?) || '%'
     UNION
     SELECT constituency, state FROM mp_info
     WHERE UPPER(mp_name) LIKE '%' || UPPER(?) || '%'
        OR UPPER(constituency) LIKE '%' || UPPER(?) || '%'`,
    [searchTerm, searchTerm, searchTerm],
  );

  return Response.json({
    query: searchTerm,
    results,
    count: results.length,
  });
}
