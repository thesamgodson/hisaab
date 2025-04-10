import Link from "next/link";
import { Suspense } from "react";
import BriefButton from "@/components/BriefButton";
import SchemeCard from "@/components/SchemeCard";
import SearchBar from "@/components/SearchBar";
import type { DataQualityResponse, SchemeData } from "@/lib/types";

const API_BASE = process.env.API_BASE_URL ?? "http://localhost:8000";

const SCHEME_KEYS = [
  { key: "mgnrega", name: "MGNREGA" },
  { key: "funds", name: "MGNREGA Funds" },
  { key: "fto", name: "MGNREGA FTO" },
  { key: "pmgsy", name: "PMGSY" },
  { key: "pmayg", name: "PMAY-G" },
  { key: "pmkisan", name: "PM Kisan" },
  { key: "jjm", name: "JJM" },
  { key: "pmposhan", name: "PM POSHAN" },
  { key: "nsap", name: "NSAP" },
  { key: "nfsa", name: "PDS/NFSA" },
];

async function fetchSchemeData(
  district: string,
  schemeKey: string,
): Promise<SchemeData | null> {
  try {
    const res = await fetch(
      `${API_BASE}/api/v1/district/${encodeURIComponent(district)}/${encodeURIComponent(schemeKey)}`,
      { cache: "no-store" },
    );
    if (!res.ok) return null;
    return (await res.json()) as SchemeData;
  } catch {
    return null;
  }
}

async function fetchDistrictInfo(district: string): Promise<SchemeData | null> {
  try {
    const res = await fetch(
      `${API_BASE}/api/v1/district/${encodeURIComponent(district)}`,
      { cache: "no-store" },
    );
    if (!res.ok) return null;
    return (await res.json()) as SchemeData;
  } catch {
    return null;
  }
}

async function fetchQuality(): Promise<DataQualityResponse> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/data-quality`, {
      cache: "no-store",
    });
    if (!res.ok) return {};
    return (await res.json()) as DataQualityResponse;
  } catch {
    return {};
  }
}

async function fetchMoneyFlow(district: string): Promise<SchemeData | null> {
  try {
    const res = await fetch(
      `${API_BASE}/api/v1/district/${encodeURIComponent(district)}/money-flow`,
      { cache: "no-store" },
    );
    if (!res.ok) return null;
    return (await res.json()) as SchemeData;
  } catch {
    return null;
  }
}

/** Resolve the state name for display from the district overview response. */
function extractState(overview: SchemeData | null): string | null {
  if (!overview) return null;
  const answer = overview.answer ?? "";
  // The overview answer contains lines like "VILLUPURAM, TAMIL NADU (FY 2024-2025):"
  const match = answer.match(/,\s*([A-Z\s]+?)\s*\(/);
  return match ? match[1].trim() : null;
}

async function DistrictContent({ district }: { district: string }) {
  const [overview, quality, moneyFlow, ...schemeResults] = await Promise.all([
    fetchDistrictInfo(district),
    fetchQuality(),
    fetchMoneyFlow(district),
    ...SCHEME_KEYS.map((s) => fetchSchemeData(district, s.key)),
  ]);

  const state = extractState(overview);
  const hasAnyData = schemeResults.some(
    (r) => r?.data !== null && r?.data !== undefined,
  );

  if (!hasAnyData && !overview?.data) {
    return (
      <div className="text-center py-16">
        <p className="text-xl text-gray-500">No data found for {district}</p>
        <p className="text-sm text-gray-400 mt-2">
          Try checking the spelling or searching for another district.
        </p>
      </div>
    );
  }

  // Build scheme cards: pair each SCHEME_KEYS entry with its result
  const schemeCards = SCHEME_KEYS.map((s, i) => ({
    ...s,
    result: schemeResults[i],
  })).filter((s) => s.result?.data !== null && s.result?.data !== undefined);

  // Determine display name mapping for warnings lookup
  const warningNameMap: Record<string, string> = {
    mgnrega: "MGNREGA",
    funds: "MGNREGA",
    fto: "MGNREGA",
    pmgsy: "PMGSY",
    pmayg: "PMAY-G",
    pmkisan: "PM Kisan",
    jjm: "JJM",
    pmposhan: "PM POSHAN",
    nsap: "NSAP",
    nfsa: "PDS/NFSA",
  };

  return (
    <>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">{district}</h1>
        {state && <p className="text-lg text-gray-500 mt-1">{state}</p>}
        <div className="flex items-center gap-3 mt-4">
          <BriefButton district={district} />
          <span className="text-xs text-gray-400">
            {schemeCards.length} of 8 schemes with data
          </span>
        </div>
      </div>

      {/* Money flow summary */}
      {moneyFlow?.data && (
        <div className="mb-8 rounded-2xl border border-indigo-100 bg-indigo-50/30 p-5">
          <h2 className="text-sm font-semibold text-indigo-800 mb-3">
            Cross-Scheme Money Flow
          </h2>
          <div className="space-y-1">
            {moneyFlow.answer
              .split("\n")
              .map((l) => l.trim())
              .filter(Boolean)
              .map((line, i) => (
                <p
                  key={i}
                  className="text-sm text-gray-700 font-mono leading-relaxed"
                >
                  {line}
                </p>
              ))}
          </div>
        </div>
      )}

      {/* Scheme cards */}
      <div className="grid gap-4 sm:grid-cols-2">
        {schemeCards.map((s) => {
          const result = s.result!;
          const qualityKey = warningNameMap[s.key] ?? s.name;
          const warnings = quality[qualityKey] ?? [];

          return (
            <SchemeCard
              key={s.key}
              schemeName={qualityKey}
              answer={result.answer}
              data={result.data}
              sourceUrl={result.source_url}
              warnings={warnings}
            />
          );
        })}
      </div>
    </>
  );
}

function LoadingSkeleton() {
  return (
    <div className="animate-pulse space-y-6">
      <div className="h-10 w-64 bg-gray-200 rounded-lg" />
      <div className="h-6 w-40 bg-gray-100 rounded-lg" />
      <div className="grid gap-4 sm:grid-cols-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-48 bg-gray-100 rounded-2xl" />
        ))}
      </div>
    </div>
  );
}

export default async function DistrictPage({
  params,
}: {
  params: Promise<{ name: string }>;
}) {
  const { name } = await params;
  const district = decodeURIComponent(name).toUpperCase();

  return (
    <div className="min-h-screen">
      {/* Navigation bar */}
      <nav className="border-b border-gray-100 bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center gap-4">
          <Link
            href="/"
            className="text-lg font-bold text-gray-900 hover:text-indigo-600 transition-colors shrink-0"
          >
            Hisaab
          </Link>
          <div className="flex-1 max-w-md">
            <SearchBar />
          </div>
        </div>
      </nav>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-4 py-8">
        <Suspense fallback={<LoadingSkeleton />}>
          <DistrictContent district={district} />
        </Suspense>
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-100 mt-16">
        <div className="max-w-4xl mx-auto px-4 py-6 text-center text-xs text-gray-400">
          Data sourced from official government portals. Hisaab is open-source
          public infrastructure.
        </div>
      </footer>
    </div>
  );
}
