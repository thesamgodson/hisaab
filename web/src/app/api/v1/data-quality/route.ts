import { dataQualityWarnings } from "@/lib/data-quality";

export const revalidate = 3600;

export async function GET() {
  const warnings = dataQualityWarnings();
  return Response.json({
    warnings,
    note: "Every caveat here also appears in DATA_CLAIMS.md with source and date.",
  });
}
