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
      <div className="text-center py-24">
        <div
          className="w-16 h-16 mx-auto mb-4 rounded-2xl flex items-center justify-center"
          style={{ background: "var(--accent-light)" }}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: "var(--accent)" }} aria-hidden="true">
            <circle cx="11" cy="11" r="8" />
            <path d="M21 21l-4.35-4.35" />
          </svg>
        </div>
        <p className="text-xl font-semibold" style={{ color: "var(--text-primary)" }}>
          No data found for {district}
        </p>
        <p className="text-sm mt-2" style={{ color: "var(--text-muted)" }}>
          Try checking the spelling or searching for another district.
        </p>
      </div>
    );
  }

  const schemeCards = SCHEME_KEYS.map((s, i) => ({
    ...s,
    result: schemeResults[i],
  })).filter((s) => s.result?.data !== null && s.result?.data !== undefined);

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
      <div className="mb-8 animate-fade-in-up">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 mb-4 text-sm" style={{ color: "var(--text-muted)" }}>
          <Link href="/" className="transition-colors duration-150 hover:text-[var(--accent)]">
            Home
          </Link>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <path d="M9 18l6-6-6-6" />
          </svg>
          <span style={{ color: "var(--text-secondary)" }}>{district}</span>
        </div>

        <h1
          className="text-3xl sm:text-4xl font-bold"
          style={{ color: "var(--text-primary)" }}
        >
          {district}
        </h1>
        {state && (
          <p className="text-lg mt-1" style={{ color: "var(--text-secondary)" }}>
            {state}
          </p>
        )}
        <div className="flex items-center gap-3 mt-4">
          <BriefButton district={district} />
          <span className="text-xs" style={{ color: "var(--text-muted)" }}>
            {schemeCards.length} of 8 schemes with data
          </span>
        </div>
      </div>

      {/* Money flow summary */}
      {moneyFlow?.data && (
        <div
          className="mb-8 rounded-xl p-5 animate-fade-in-up stagger-1"
          style={{
            background: "var(--surface-tinted)",
            border: "1px solid var(--border)",
          }}
        >
          <h2
            className="text-xs font-semibold uppercase tracking-widest mb-3"
            style={{ color: "var(--accent)" }}
          >
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
                  className="text-sm font-mono leading-relaxed"
                  style={{ color: "var(--text-secondary)" }}
                >
                  {line}
                </p>
              ))}
          </div>
        </div>
      )}

      {/* Scheme cards */}
      <div className="grid gap-4 sm:grid-cols-2">
        {schemeCards.map((s, i) => {
          const result = s.result!;
          const qualityKey = warningNameMap[s.key] ?? s.name;
          const warnings = quality[qualityKey] ?? [];

          return (
            <div
              key={s.key}
              className={`animate-fade-in-up stagger-${Math.min(i + 2, 10)}`}
            >
              <SchemeCard
                schemeName={qualityKey}
                answer={result.answer}
                data={result.data}
                sourceUrl={result.source_url}
                warnings={warnings}
              />
            </div>
          );
        })}
      </div>
    </>
  );
}

function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      <div className="space-y-3">
        <div className="h-4 w-32 rounded-lg shimmer" style={{ background: "var(--border)" }} />
        <div className="h-10 w-64 rounded-lg shimmer" style={{ background: "var(--border)" }} />
        <div className="h-5 w-40 rounded-lg shimmer" style={{ background: "var(--border-subtle)" }} />
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <div
            key={i}
            className="h-48 rounded-xl shimmer"
            style={{ background: "var(--border-subtle)" }}
          />
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
    <div className="flex-1">
      {/* Secondary nav with search */}
      <div
        className="border-b"
        style={{
          borderColor: "var(--border-subtle)",
          background: "var(--surface)",
        }}
      >
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-3">
          <div className="max-w-md">
            <SearchBar />
          </div>
        </div>
      </div>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 py-8">
        <Suspense fallback={<LoadingSkeleton />}>
          <DistrictContent district={district} />
        </Suspense>
      </main>
    </div>
  );
}
