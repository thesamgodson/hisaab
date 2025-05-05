/**
 * Constituency detail page — full MP Report Card.
 *
 * Shareable via OG tags.  Links to district detail pages.
 * Includes a link to the SVG share image.
 */

import type { Metadata } from "next";
import Link from "next/link";
import type { ConstituencyReport, SchemePerf } from "@/lib/constituency-types";

const API_BASE = process.env.API_BASE_URL ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// Data fetching
// ---------------------------------------------------------------------------

async function fetchReport(name: string, fin_year: string): Promise<ConstituencyReport | null> {
  try {
    const url = `${API_BASE}/api/v1/constituency/${encodeURIComponent(name)}?fin_year=${encodeURIComponent(fin_year)}`;
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as ConstituencyReport;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Metadata (OG tags for sharing)
// ---------------------------------------------------------------------------

export async function generateMetadata({
  params,
}: {
  params: Promise<{ name: string }>;
}): Promise<Metadata> {
  const { name } = await params;
  const constituency = decodeURIComponent(name).toUpperCase();
  const report = await fetchReport(constituency, "2024-2025");

  const title = report?.mp_name
    ? `${report.mp_name} (${constituency}) — Hisaab Report Card`
    : `${constituency} — Hisaab Report Card`;

  const scoreText =
    report?.composite_score != null
      ? `Score: ${report.composite_score}/100 (Grade ${report.composite_grade})`
      : "Welfare scheme performance data";

  const cardUrl = `${API_BASE}/api/v1/constituency/${encodeURIComponent(constituency)}/card?fmt=landscape`;

  return {
    title,
    description: `${constituency} Lok Sabha constituency. ${scoreText}. 11 government welfare schemes tracked by Hisaab.`,
    openGraph: {
      title,
      description: `${scoreText} across 11 welfare schemes.`,
      images: [{ url: cardUrl, width: 1200, height: 630 }],
      siteName: "Hisaab",
    },
    twitter: {
      card: "summary_large_image",
      title,
      images: [cardUrl],
    },
  };
}

// ---------------------------------------------------------------------------
// UI helpers
// ---------------------------------------------------------------------------

function gradeColor(grade: string | null | undefined): string {
  return (
    {
      A: "text-green-600 bg-green-50 border-green-200",
      B: "text-blue-600 bg-blue-50 border-blue-200",
      C: "text-amber-600 bg-amber-50 border-amber-200",
      D: "text-orange-600 bg-orange-50 border-orange-200",
      F: "text-red-600 bg-red-50 border-red-200",
    }[grade ?? ""] ?? "text-gray-500 bg-gray-50 border-gray-200"
  );
}

function statusDot(status: string): string {
  return (
    {
      green: "bg-green-500",
      yellow: "bg-amber-500",
      orange: "bg-orange-500",
      red: "bg-red-500",
      no_data: "bg-gray-300",
    }[status] ?? "bg-gray-300"
  );
}

function SchemeRow({ sp }: { sp: SchemePerf }) {
  const dot = statusDot(sp.status);
  const scoreLabel =
    sp.score != null ? `${sp.score.toFixed(0)}%` : "No data";
  return (
    <div className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
      <div className="flex items-center gap-3">
        <span className={`w-2.5 h-2.5 rounded-full shrink-0 ${dot}`} />
        <span className="text-sm text-gray-700">{sp.scheme}</span>
      </div>
      <div className="flex items-center gap-4 text-right">
        {sp.delivery_pct != null && (
          <span className="text-xs text-gray-400 hidden sm:inline">
            Delivery {sp.delivery_pct.toFixed(0)}%
          </span>
        )}
        {sp.utilization_pct != null && (
          <span className="text-xs text-gray-400 hidden sm:inline">
            Util {sp.utilization_pct.toFixed(0)}%
          </span>
        )}
        <span className="text-sm font-medium text-gray-800 w-16 text-right">
          {scoreLabel}
        </span>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default async function ConstituencyDetailPage({
  params,
}: {
  params: Promise<{ name: string }>;
}) {
  const { name } = await params;
  const constituency = decodeURIComponent(name).toUpperCase();
  const report = await fetchReport(constituency, "2024-2025");

  if (!report) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center px-4">
        <p className="text-xl text-gray-500">Constituency not found: {constituency}</p>
        <p className="text-sm text-gray-400 mt-2">
          Use{" "}
          <Link href="/constituency" className="text-indigo-600 underline">
            PIN code lookup
          </Link>{" "}
          or check the spelling.
        </p>
      </div>
    );
  }

  const scoreGradeClass = gradeColor(report.composite_grade);
  const noData = report.composite_score == null;
  const cardSvgUrl = `/api/v1/constituency/${encodeURIComponent(constituency)}/card?fmt=portrait`;

  return (
    <div className="min-h-screen flex flex-col">
      {/* Nav */}
      <nav className="border-b border-gray-100 bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-2xl mx-auto px-4 py-3 flex items-center gap-4">
          <Link
            href="/"
            className="text-lg font-bold text-gray-900 hover:text-indigo-600 transition-colors shrink-0"
          >
            Hisaab
          </Link>
          <Link
            href="/constituency"
            className="text-sm text-gray-500 hover:text-indigo-600 transition-colors"
          >
            ← Constituencies
          </Link>
        </div>
      </nav>

      <main className="flex-1 max-w-2xl mx-auto w-full px-4 py-8">
        {/* Header card */}
        <div className="rounded-2xl border border-gray-100 bg-white shadow-sm p-6 mb-6">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <h1 className="text-2xl font-bold text-gray-900 leading-tight">
                {report.mp_name === "Unknown" ? constituency : report.mp_name}
              </h1>
              {report.mp_name !== "Unknown" && (
                <p className="text-gray-500 mt-1">
                  {report.party && (
                    <span className="font-medium text-gray-700">{report.party} · </span>
                  )}
                  {report.constituency}
                </p>
              )}
              <p className="text-sm text-gray-400 mt-1">
                {report.state} · Elected {report.elected_year} · Lok Sabha
              </p>
            </div>

            {/* Score badge */}
            {!noData && (
              <div
                className={`shrink-0 flex flex-col items-center justify-center w-20 h-20 rounded-2xl border-2 ${scoreGradeClass}`}
              >
                <span className="text-2xl font-bold leading-none">
                  {report.composite_score!.toFixed(0)}
                </span>
                <span className="text-xs font-medium mt-1">
                  Grade {report.composite_grade}
                </span>
              </div>
            )}
          </div>

          {/* National comparison */}
          {report.national_avg_score != null && report.composite_score != null && (
            <p className="text-sm text-gray-500 mt-4 pt-4 border-t border-gray-50">
              {report.composite_score >= report.national_avg_score
                ? "▲ Above"
                : "▼ Below"}{" "}
              national average by{" "}
              <strong>
                {Math.abs(report.composite_score - report.national_avg_score).toFixed(0)} pts
              </strong>{" "}
              (national avg: {report.national_avg_score.toFixed(0)})
            </p>
          )}
        </div>

        {/* Districts */}
        {report.districts.length > 0 && (
          <div className="rounded-2xl border border-gray-100 bg-white shadow-sm p-5 mb-6">
            <h2 className="text-sm font-semibold text-gray-600 uppercase tracking-wide mb-3">
              Districts in Constituency
            </h2>
            <div className="flex flex-wrap gap-2">
              {report.districts.map((d) => (
                <Link
                  key={d}
                  href={`/district/${encodeURIComponent(d)}`}
                  className="px-3 py-1.5 rounded-lg bg-indigo-50 text-indigo-700 text-sm font-medium hover:bg-indigo-100 transition-colors"
                >
                  {d}
                </Link>
              ))}
            </div>
          </div>
        )}

        {/* Red flags */}
        {report.red_flags.length > 0 && (
          <div className="rounded-2xl border border-red-100 bg-red-50/50 p-5 mb-6">
            <h2 className="text-sm font-semibold text-red-700 uppercase tracking-wide mb-3">
              🚩 Red Flags
            </h2>
            <ul className="space-y-1">
              {report.red_flags.map((flag, i) => (
                <li key={i} className="text-sm text-red-800">
                  • {flag}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Scheme performance */}
        <div className="rounded-2xl border border-gray-100 bg-white shadow-sm p-5 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-gray-600 uppercase tracking-wide">
              Scheme Performance
            </h2>
            <div className="flex items-center gap-3 text-xs text-gray-400">
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-green-500 inline-block" />
                75%+
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-amber-500 inline-block" />
                50%+
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-red-500 inline-block" />
                Below 50%
              </span>
            </div>
          </div>

          {noData ? (
            <p className="text-sm text-gray-400 py-4 text-center">
              No scheme data available for this constituency yet.
              {report.districts.length === 0 && (
                <span> District mapping may not be loaded — see constituency/seed_data.py.</span>
              )}
            </p>
          ) : (
            <div>
              {report.schemes.map((sp) => (
                <SchemeRow key={sp.scheme} sp={sp} />
              ))}
            </div>
          )}

          {report.districts.length > 0 && (
            <p className="text-xs text-gray-400 mt-4">
              Averaged across {report.districts.length} district
              {report.districts.length !== 1 ? "s" : ""}: {report.districts.join(", ")}
            </p>
          )}
        </div>

        {/* Share card */}
        <div className="rounded-2xl border border-indigo-100 bg-indigo-50/30 p-5 mb-6">
          <h2 className="text-sm font-semibold text-indigo-800 mb-3">Share this Report Card</h2>
          <div className="flex flex-wrap gap-3">
            <a
              href={`${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"}${cardSvgUrl}`}
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 transition-colors"
            >
              Download SVG Card (WhatsApp)
            </a>
            <a
              href={`${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"}/api/v1/constituency/${encodeURIComponent(constituency)}/card?fmt=landscape`}
              target="_blank"
              rel="noopener noreferrer"
              className="px-4 py-2 rounded-lg border border-indigo-200 text-indigo-700 text-sm font-medium hover:bg-indigo-50 transition-colors"
            >
              OG Card (Twitter / Facebook)
            </a>
          </div>
        </div>

        {/* Source note */}
        <p className="text-xs text-gray-400 text-center">{report.source_note}</p>
      </main>

      <footer className="border-t border-gray-100 py-6">
        <p className="text-center text-xs text-gray-400">
          Hisaab is open-source public infrastructure. Not affiliated with any
          government body.
        </p>
      </footer>
    </div>
  );
}
