import { notFound } from "next/navigation";
import Link from "next/link";
import { getBaseUrl } from "@/lib/get-base-url";
import type { ActionBriefResponse, DiagnosisItem } from "@/lib/action-types";
import SourceLink from "@/components/SourceLink";

/* ---------- severity styling ---------- */

const SEVERITY_BG: Record<DiagnosisItem["severity"], string> = {
  high: "oklch(0.97 0.02 25)",
  medium: "oklch(0.97 0.02 85)",
  low: "oklch(0.97 0.02 145)",
};

const SEVERITY_BORDER: Record<DiagnosisItem["severity"], string> = {
  high: "oklch(0.80 0.12 25)",
  medium: "oklch(0.82 0.10 85)",
  low: "oklch(0.82 0.10 145)",
};

const SEVERITY_TEXT: Record<DiagnosisItem["severity"], string> = {
  high: "oklch(0.40 0.18 25)",
  medium: "oklch(0.40 0.14 85)",
  low: "oklch(0.38 0.14 145)",
};

const SEVERITY_ACCENT: Record<DiagnosisItem["severity"], string> = {
  high: "oklch(0.55 0.20 25)",
  medium: "oklch(0.60 0.16 85)",
  low: "oklch(0.55 0.16 145)",
};

const SEVERITY_LABEL: Record<DiagnosisItem["severity"], string> = {
  high: "High severity",
  medium: "Medium",
  low: "Low",
};

/* ---------- page ---------- */

interface PageProps {
  params: Promise<{ pin: string }>;
}

export default async function ActionPage({ params }: PageProps) {
  const { pin } = await params;

  /* Validate PIN format */
  if (!/^\d{6}$/.test(pin)) {
    return (
      <main className="max-w-3xl mx-auto px-4 py-20 text-center">
        <h1
          className="text-2xl font-bold mb-3"
          style={{ color: "var(--text-primary)" }}
        >
          Invalid PIN Code
        </h1>
        <p style={{ color: "var(--text-secondary)" }}>
          &ldquo;{pin}&rdquo; is not a valid 6-digit PIN code.
        </p>
        <Link
          href="/"
          className="inline-block mt-6 px-5 py-2.5 rounded-xl text-sm font-medium text-white transition-opacity duration-150 hover:opacity-90"
          style={{ background: "var(--accent)" }}
        >
          Go back home
        </Link>
      </main>
    );
  }

  /* Fetch data from action API */
  const res = await fetch(`${getBaseUrl()}/api/v1/action/${pin}`, {
    cache: "no-store",
  });

  if (res.status === 404) {
    notFound();
  }

  if (!res.ok) {
    return (
      <main className="max-w-3xl mx-auto px-4 py-20 text-center">
        <h1
          className="text-2xl font-bold mb-3"
          style={{ color: "var(--text-primary)" }}
        >
          Something went wrong
        </h1>
        <p style={{ color: "var(--text-secondary)" }}>
          Could not load data for PIN {pin}. Please try again later.
        </p>
        <Link
          href="/"
          className="inline-block mt-6 px-5 py-2.5 rounded-xl text-sm font-medium text-white transition-opacity duration-150 hover:opacity-90"
          style={{ background: "var(--accent)" }}
        >
          Go back home
        </Link>
      </main>
    );
  }

  const data: ActionBriefResponse = await res.json();

  const generatedDate = new Date(data.generated_at).toLocaleDateString(
    "en-IN",
    { day: "numeric", month: "long", year: "numeric" },
  );

  const districtSlug = data.district.toLowerCase().replace(/\s+/g, "-");

  return (
    <main className="max-w-3xl mx-auto px-4 sm:px-6 py-12">
      {/* ---- Section 1: Your Area ---- */}
      <section className="mb-12 animate-fade-in">
        <nav
          className="text-sm mb-6"
          style={{ color: "var(--text-muted)" }}
          aria-label="Breadcrumb"
        >
          <ol className="flex items-center gap-1.5">
            <li>
              <Link
                href="/"
                className="transition-colors duration-150 hover:underline"
                style={{ color: "var(--accent)" }}
              >
                Home
              </Link>
            </li>
            <li aria-hidden="true" style={{ color: "var(--border)" }}>/</li>
            <li className="font-medium" style={{ color: "var(--text-primary)" }}>
              PIN {pin}
            </li>
          </ol>
        </nav>

        <h1
          className="text-2xl sm:text-3xl font-bold tracking-tight mb-1"
          style={{ color: "var(--text-primary)" }}
        >
          {titleCase(data.district)}, {titleCase(data.state)}
        </h1>

        {data.formerly_part_of && (
          <p className="text-sm mb-3" style={{ color: "var(--text-muted)" }}>
            Formerly part of {titleCase(data.formerly_part_of.parent_district)} district,
            reorganized {data.formerly_part_of.split_year}
          </p>
        )}

        <div
          className="flex flex-wrap gap-x-6 gap-y-1.5 text-sm mb-3"
          style={{ color: "var(--text-secondary)" }}
        >
          {data.mp && (
            <span>
              <span className="font-medium">MP:</span> {data.mp.mp_name}{" "}
              <span style={{ color: "var(--text-muted)" }}>
                ({data.mp.party})
              </span>
            </span>
          )}
          {data.mla && (
            <span>
              <span className="font-medium">MLA:</span> {data.mla.mla_name}{" "}
              <span style={{ color: "var(--text-muted)" }}>
                ({data.mla.party}, {data.mla.ac_name})
              </span>
            </span>
          )}
        </div>

        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          Generated {generatedDate}
        </p>
      </section>

      {/* ---- Section 2: Issues Found ---- */}
      <section className="mb-12">
        <SectionHeader
          title="Issues Found"
          count={data.diagnosis.length}
        />

        {data.diagnosis.length === 0 ? (
          <div
            className="rounded-xl px-5 py-5 text-sm font-medium"
            style={{
              background: "oklch(0.97 0.02 145)",
              color: "oklch(0.35 0.14 145)",
              border: "1px solid oklch(0.88 0.06 145)",
            }}
          >
            No major issues flagged for your area.
          </div>
        ) : (
          <div className="flex flex-col gap-4">
            {data.diagnosis.map((item, i) => (
              <div
                key={i}
                className={`animate-fade-in-up stagger-${Math.min(i + 1, 10)}`}
              >
                <DiagnosisCard item={item} />
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ---- Section 3: What You Can Do ---- */}
      {data.actions.length > 0 && (
        <section className="mb-12">
          <SectionHeader title="What You Can Do" />

          <div className="flex flex-col gap-4">
            {data.actions.map((action, i) => (
              <div
                key={i}
                className={`rounded-xl px-5 py-5 animate-fade-in-up stagger-${Math.min(i + 1, 10)}`}
                style={{
                  background: "var(--elevated)",
                  border: "1px solid var(--border-subtle)",
                  boxShadow: "var(--shadow-sm)",
                }}
              >
                <p
                  className="text-sm font-semibold mb-3"
                  style={{ color: "var(--accent)" }}
                >
                  {action.scheme}
                </p>
                <ol className="flex flex-col gap-2">
                  {action.steps.map((step, j) => (
                    <li
                      key={j}
                      className="flex items-start gap-3 text-sm"
                      style={{ color: "var(--text-secondary)" }}
                    >
                      <span
                        className="flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-[11px] font-semibold mt-0.5"
                        style={{
                          background: "var(--accent-light)",
                          color: "var(--accent)",
                        }}
                      >
                        {j + 1}
                      </span>
                      <span className="flex-1">
                        {step.action}
                        {step.url && (
                          <a
                            href={step.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 ml-2 px-2.5 py-1 rounded-md text-xs font-medium transition-all duration-150 hover:opacity-80"
                            style={{
                              background: "var(--accent-light)",
                              color: "var(--accent)",
                            }}
                          >
                            Visit portal
                            <svg
                              className="w-3 h-3"
                              fill="none"
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                              aria-hidden="true"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                              />
                            </svg>
                          </a>
                        )}
                      </span>
                    </li>
                  ))}
                </ol>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* ---- Section 4: Grievance Portals ---- */}
      {data.grievance_channels && data.grievance_channels.length > 0 && (
        <section className="mb-12">
          <SectionHeader title="Grievance Portals" />

          <div className="grid gap-3 sm:grid-cols-2">
            {data.grievance_channels.map((ch, i) => (
              <a
                key={i}
                href={ch.portal_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-between gap-3 px-4 py-3.5 rounded-xl text-sm transition-all duration-150 card-hover"
                style={{
                  background: "var(--elevated)",
                  border: "1px solid var(--border-subtle)",
                  boxShadow: "var(--shadow-xs)",
                }}
              >
                <div className="min-w-0">
                  <p
                    className="font-medium truncate"
                    style={{ color: "var(--accent)" }}
                  >
                    {ch.portal_name}
                  </p>
                  {ch.phone && (
                    <p
                      className="text-xs mt-0.5"
                      style={{ color: "var(--text-muted)" }}
                    >
                      {ch.phone}
                    </p>
                  )}
                </div>
                <svg
                  className="w-4 h-4 flex-shrink-0"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                  style={{ color: "var(--text-muted)" }}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                  />
                </svg>
              </a>
            ))}
          </div>
        </section>
      )}

      {/* ---- Footer ---- */}
      <footer
        className="pt-8 mt-4 flex flex-col gap-3"
        style={{ borderTop: "1px solid var(--border-subtle)" }}
      >
        <Link
          href={`/district/${districtSlug}`}
          className="inline-flex items-center gap-1.5 text-sm font-medium transition-opacity duration-150 hover:opacity-80"
          style={{ color: "var(--accent)" }}
        >
          View full district data for {titleCase(data.district)}
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9 5l7 7-7 7"
            />
          </svg>
        </Link>
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          Data from official government portals. Source links provided per
          finding.
        </p>
      </footer>
    </main>
  );
}

/* ---------- sub-components ---------- */

function SectionHeader({ title, count }: { title: string; count?: number }) {
  return (
    <div className="flex items-center gap-3 mb-5">
      <h2
        className="text-lg font-semibold"
        style={{ color: "var(--text-primary)" }}
      >
        {title}
      </h2>
      {count != null && count > 0 && (
        <span
          className="inline-flex items-center justify-center w-6 h-6 rounded-full text-[11px] font-semibold"
          style={{
            background: "var(--accent-light)",
            color: "var(--accent)",
          }}
        >
          {count}
        </span>
      )}
      <div
        className="flex-1 h-px"
        style={{ background: "var(--border-subtle)" }}
      />
    </div>
  );
}

function DiagnosisCard({ item }: { item: DiagnosisItem }) {
  return (
    <div
      className="rounded-xl overflow-hidden"
      style={{
        background: SEVERITY_BG[item.severity],
        border: `1px solid ${SEVERITY_BORDER[item.severity]}`,
      }}
    >
      {/* Severity accent bar */}
      <div
        style={{
          height: "3px",
          background: SEVERITY_ACCENT[item.severity],
        }}
      />

      <div className="px-5 py-4">
        <div className="flex items-center justify-between gap-3 mb-2">
          <p
            className="text-sm font-semibold"
            style={{ color: SEVERITY_TEXT[item.severity] }}
          >
            {item.scheme}
          </p>
          <span
            className="inline-block px-2.5 py-0.5 rounded-md text-[11px] font-semibold uppercase tracking-wide text-white"
            style={{ background: SEVERITY_ACCENT[item.severity] }}
          >
            {SEVERITY_LABEL[item.severity]}
          </span>
        </div>

        <p
          className="text-[15px] font-medium mb-1.5 leading-snug"
          style={{ color: "var(--text-primary)" }}
        >
          {item.summary}
        </p>

        <p
          className="text-sm leading-relaxed mb-3"
          style={{ color: "var(--text-secondary)" }}
        >
          {item.detail}
        </p>

        {item.source_url && <SourceLink url={item.source_url} />}
      </div>
    </div>
  );
}

/* ---------- util ---------- */

function titleCase(s: string): string {
  return s
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
