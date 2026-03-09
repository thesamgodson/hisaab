import { type NextRequest } from "next/server";

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => null);
  const text = body?.query ?? body?.text ?? "";

  return Response.json({
    query: text,
    intent: "unsupported",
    district: null,
    answer:
      "Natural language queries are not yet supported in the web version.",
    lang: "en",
  });
}
