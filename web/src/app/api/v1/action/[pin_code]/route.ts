import { type NextRequest } from "next/server";
import { buildActionBrief } from "@/lib/action-brief";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ pin_code: string }> },
) {
  const { pin_code } = await params;

  if (!/^\d{6}$/.test(pin_code)) {
    return Response.json(
      { error: "Invalid PIN code. Must be a 6-digit number." },
      { status: 400 },
    );
  }

  const brief = await buildActionBrief(pin_code);

  if (!brief) {
    return Response.json(
      {
        error: `PIN code ${pin_code} not found. Ensure this is a valid Indian postal code.`,
      },
      { status: 404 },
    );
  }

  return Response.json(brief);
}
