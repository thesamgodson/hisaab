import { ALL_SCHEME_NAMES, dataQualityWarnings } from "@/lib/data-quality";

export const revalidate = 3600;

export async function GET() {
  const warnings = dataQualityWarnings();

  const schemes = ALL_SCHEME_NAMES.map((name) => ({
    name,
    warnings: warnings[name] ?? [],
  }));

  return Response.json({ schemes, count: schemes.length });
}
