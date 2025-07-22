import type { Metadata } from "next";
import Link from "next/link";
import type { ConstituencyReport, SchemePerf } from "@/lib/constituency-types";

const API_BASE = process.env.API_BASE_URL ?? "http://localhost:8000";

async function fetchReport(name: string, fin_year: string): Promise<ConstituencyReport | null> {
  try {
    const url = `${API_BASE}/api/v1/constituency/${encodeURIComponent(name)}?fin_year=${encodeURIComponent(fin_year)}`;
    const res = await fetch(url, { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as ConstituencyReport;
  } catch { return null; }
}

export async function generateMetadata({ params }: { params: Promise<{ name: string }> }): Promise<Metadata> {
  const { name } = await params;
  const constituency = decodeURIComponent(name).toUpperCase();
  const report = await fetchReport(constituency, "2024-2025");
  const title = report?.mp_name
    ? `${report.mp_name} (${constituency}) -- Hisaab Report Card`
    : `${constituency} -- Hisaab Report Card`;
  const scoreText = report?.composite_score != null
    ? `Score: ${report.composite_score}/100 (Grade ${report.composite_grade})`
    : "Welfare scheme performance data";
  const cardUrl = `${API_BASE}/api/v1/constituency/${encodeURIComponent(constituency)}/card?fmt=landscape`;
  return {
    title,
    description: `${constituency} Lok Sabha constituency. ${scoreText}. 11 schemes tracked.`,
    openGraph: { title, description: `${scoreText} across 11 welfare schemes.`, images: [{ url: cardUrl, width: 1200, height: 630 }], siteName: "Hisaab" },
    twitter: { card: "summary_large_image", title, images: [cardUrl] },
  };
}

const GRADE_COLOR: Record<string, string> = { A: "oklch(0.45 0.15 145)", B: "oklch(0.45 0.15 240)", C: "oklch(0.50 0.15 80)", D: "oklch(0.50 0.16 45)", F: "oklch(0.50 0.18 25)" };
const GRADE_BG: Record<string, string> = { A: "oklch(0.95 0.03 145)", B: "oklch(0.95 0.03 240)", C: "oklch(0.95 0.03 80)", D: "oklch(0.95 0.03 45)", F: "oklch(0.95 0.03 25)" };
const STATUS_DOT: Record<string, string> = { green: "oklch(0.55 0.17 145)", yellow: "oklch(0.65 0.16 80)", orange: "oklch(0.60 0.16 50)", red: "oklch(0.55 0.20 25)", no_data: "oklch(0.80 0 0)" };

function SchemeRow({ sp }: { sp: SchemePerf }) {
  const dot = STATUS_DOT[sp.status] ?? "oklch(0.80 0 0)";
  const scoreLabel = sp.score != null ? `${sp.score.toFixed(0)}%` : "No data";
  return (
    <div className="flex items-center justify-between py-3 last:border-0" style={{ borderBottom: "1px solid var(--border-subtle)" }}>
      <div className="flex items-center gap-3">
        <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: dot }} />
        <span className="text-sm" style={{ color: "var(--text-primary)" }}>{sp.scheme}</span>
      </div>
      <div className="flex items-center gap-4 text-right">
        {sp.delivery_pct != null && <span className="text-xs hidden sm:inline" style={{ color: "var(--text-muted)" }}>Delivery {sp.delivery_pct.toFixed(0)}%</span>}
        {sp.utilization_pct != null && <span className="text-xs hidden sm:inline" style={{ color: "var(--text-muted)" }}>Util {sp.utilization_pct.toFixed(0)}%</span>}
        <span className="text-sm font-semibold w-16 text-right tabular-nums" style={{ color: "var(--text-primary)" }}>{scoreLabel}</span>
      </div>
    </div>
  );
}

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
      <div className="flex-1 flex flex-col items-center justify-center px-4 py-24">
        <div
          className="w-16 h-16 mx-auto mb-4 rounded-2xl flex items-center justify-center"
          style={{ background: "var(--accent-light)" }}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ color: "var(--accent)" }} aria-hidden="true">
            <circle cx="12" cy="12" r="10" />
            <path d="M12 16v-4M12 8h.01" />
          </svg>
        </div>
        <p className="text-xl font-semibold" style={{ color: "var(--text-primary)" }}>
          Constituency not found
        </p>
        <p className="text-sm mt-2" style={{ color: "var(--text-muted)" }}>
          {constituency} is not in our database yet. Use{" "}
          <Link href="/constituency" className="underline" style={{ color: "var(--accent)" }}>
            PIN code lookup
          </Link>{" "}
          or check the spelling.
        </p>
      </div>
    );
  }

  const noData = report.composite_score == null;
  const gradeColor = GRADE_COLOR[report.composite_grade ?? ""] ?? "var(--text-muted)";
  const gradeBg = GRADE_BG[report.composite_grade ?? ""] ?? "var(--border-subtle)";
  const cardSvgUrl = `/api/v1/constituency/${encodeURIComponent(constituency)}/card?fmt=portrait`;

  return (
    <main className="flex-1 max-w-2xl mx-auto w-full px-4 sm:px-6 py-8">
      {/* Breadcrumb */}
      <div
        className="flex items-center gap-2 mb-6 text-sm animate-fade-in-up"
        style={{ color: "var(--text-muted)" }}
      >
        <Link href="/" className="transition-colors duration-150 hover:text-[var(--accent)]">
          Home
        </Link>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
          <path d="M9 18l6-6-6-6" />
        </svg>
        <Link href="/constituency" className="transition-colors duration-150 hover:text-[var(--accent)]">
          Constituencies
        </Link>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
          <path d="M9 18l6-6-6-6" />
        </svg>
        <span style={{ color: "var(--text-secondary)" }}>{constituency}</span>
      </div>

      {/* Header card */}
      <div
        className="rounded-xl p-6 mb-6 animate-fade-in-up stagger-1"
        style={{
          background: "var(--surface)",
          boxShadow: "var(--shadow-md)",
          border: "1px solid var(--border-subtle)",
        }}
      >
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <h1
              className="text-2xl sm:text-3xl font-bold leading-tight"
              style={{ color: "var(--text-primary)" }}
            >
              {report.mp_name === "Unknown" ? constituency : report.mp_name}
            </h1>
            {report.mp_name !== "Unknown" && (
              <p className="mt-1" style={{ color: "var(--text-secondary)" }}>
                {report.party && (
                  <span className="font-medium" style={{ color: "var(--text-primary)" }}>
                    {report.party}
                  </span>
                )}
                {report.party && " \u00B7 "}
                {report.constituency}
              </p>
            )}
            <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
              {report.state} · Elected {report.elected_year} · Lok Sabha
            </p>
          </div>

          {/* Score badge */}
          {!noData && (
            <div
              className="shrink-0 flex flex-col items-center justify-center w-20 h-20 rounded-xl"
              style={{
                background: gradeBg,
                border: `2px solid ${gradeColor}`,
                color: gradeColor,
              }}
            >
              <span className="text-2xl font-bold leading-none tabular-nums">
                {report.composite_score!.toFixed(0)}
              </span>
              <span className="text-xs font-semibold mt-1">
                Grade {report.composite_grade}
              </span>
            </div>
          )}
        </div>

        {/* National comparison */}
        {report.national_avg_score != null && report.composite_score != null && (
          <p
            className="text-sm mt-4 pt-4"
            style={{
              color: "var(--text-secondary)",
              borderTop: "1px solid var(--border-subtle)",
            }}
          >
            {report.composite_score >= report.national_avg_score
              ? "\u25B2 Above"
              : "\u25BC Below"}{" "}
            national average by{" "}
            <strong style={{ color: "var(--text-primary)" }}>
              {Math.abs(report.composite_score - report.national_avg_score).toFixed(0)} pts
            </strong>{" "}
            (national avg: {report.national_avg_score.toFixed(0)})
          </p>
        )}
      </div>

      {/* Districts */}
      {report.districts.length > 0 && (
        <div
          className="rounded-xl p-5 mb-6 animate-fade-in-up stagger-2"
          style={{
            background: "var(--surface)",
            boxShadow: "var(--shadow-sm)",
            border: "1px solid var(--border-subtle)",
          }}
        >
          <h2
            className="text-xs font-semibold uppercase tracking-widest mb-3"
            style={{ color: "var(--text-muted)" }}
          >
            Districts in Constituency
          </h2>
          <div className="flex flex-wrap gap-2">
            {report.districts.map((d) => (
              <Link
                key={d}
                href={`/district/${encodeURIComponent(d)}`}
                className="px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-150"
                style={{
                  background: "var(--accent-light)",
                  color: "var(--accent)",
                }}
              >
                {d}
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Red flags */}
      {report.red_flags.length > 0 && (
        <div
          className="rounded-xl p-5 mb-6 animate-fade-in-up stagger-3"
          style={{
            background: "oklch(0.97 0.02 25)",
            border: "1px solid oklch(0.90 0.06 25)",
          }}
        >
          <h2
            className="text-xs font-semibold uppercase tracking-widest mb-3"
            style={{ color: "oklch(0.45 0.18 25)" }}
          >
            Red Flags
          </h2>
          <ul className="space-y-1.5">
            {report.red_flags.map((flag, i) => (
              <li
                key={i}
                className="text-sm flex items-start gap-2"
                style={{ color: "oklch(0.35 0.10 25)" }}
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" className="shrink-0 mt-0.5" aria-hidden="true">
                  <path fillRule="evenodd" d="M8.485 2.495c.673-1.167 2.357-1.167 3.03 0l6.28 10.875c.673 1.167-.168 2.625-1.516 2.625H3.72c-1.347 0-2.189-1.458-1.515-2.625L8.485 2.495zM10 5a.75.75 0 01.75.75v3.5a.75.75 0 01-1.5 0v-3.5A.75.75 0 0110 5zm0 9a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
                </svg>
                {flag}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Scheme performance */}
      <div
        className="rounded-xl p-5 mb-6 animate-fade-in-up stagger-4"
        style={{
          background: "var(--surface)",
          boxShadow: "var(--shadow-sm)",
          border: "1px solid var(--border-subtle)",
        }}
      >
        <div className="flex items-center justify-between mb-4">
          <h2
            className="text-xs font-semibold uppercase tracking-widest"
            style={{ color: "var(--text-muted)" }}
          >
            Scheme Performance
          </h2>
          <div className="flex items-center gap-3 text-xs" style={{ color: "var(--text-muted)" }}>
            {[
              { color: "oklch(0.55 0.17 145)", label: "75%+" },
              { color: "oklch(0.65 0.16 80)", label: "50%+" },
              { color: "oklch(0.55 0.20 25)", label: "<50%" },
            ].map((legend) => (
              <span key={legend.label} className="flex items-center gap-1">
                <span
                  className="w-2 h-2 rounded-full inline-block"
                  style={{ backgroundColor: legend.color }}
                />
                {legend.label}
              </span>
            ))}
          </div>
        </div>

        {noData ? (
          <p className="text-sm py-4 text-center" style={{ color: "var(--text-muted)" }}>
            No scheme data available for this constituency yet.
            {report.districts.length === 0 && (
              <span> District mapping may not be loaded.</span>
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
          <p className="text-xs mt-4" style={{ color: "var(--text-muted)" }}>
            Averaged across {report.districts.length} district
            {report.districts.length !== 1 ? "s" : ""}: {report.districts.join(", ")}
          </p>
        )}
      </div>

      {/* Share card */}
      <div
        className="rounded-xl p-5 mb-6 animate-fade-in-up stagger-5"
        style={{
          background: "var(--surface-tinted)",
          border: "1px solid var(--border)",
        }}
      >
        <h2
          className="text-xs font-semibold uppercase tracking-widest mb-3"
          style={{ color: "var(--accent)" }}
        >
          Share this Report Card
        </h2>
        <div className="flex flex-wrap gap-3">
          <a
            href={`${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"}${cardSvgUrl}`}
            target="_blank"
            rel="noopener noreferrer"
            className="px-5 py-2.5 rounded-xl text-white text-sm font-semibold transition-opacity duration-150 hover:opacity-90"
            style={{ background: "var(--accent-gradient)" }}
          >
            Download SVG Card
          </a>
          <a
            href={`${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"}/api/v1/constituency/${encodeURIComponent(constituency)}/card?fmt=landscape`}
            target="_blank"
            rel="noopener noreferrer"
            className="px-5 py-2.5 rounded-xl text-sm font-semibold transition-all duration-150"
            style={{
              color: "var(--accent)",
              border: "1px solid var(--accent)",
              background: "transparent",
            }}
          >
            OG Card (Social)
          </a>
        </div>
      </div>

      {/* Source note */}
      <p className="text-xs text-center" style={{ color: "var(--text-muted)" }}>
        {report.source_note}
      </p>
    </main>
  );
}
