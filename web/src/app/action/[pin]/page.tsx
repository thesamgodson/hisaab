import { notFound } from "next/navigation";
import Link from "next/link";
import { getBaseUrl } from "@/lib/get-base-url";
import type { ActionBriefResponse, DiagnosisItem } from "@/lib/action-types";
import SourceLink from "@/components/SourceLink";

/* ---------- severity styling ---------- */

const SEVERITY_BG: Record<DiagnosisItem["severity"], string> = {
  high: "oklch(0.95 0.05 25)",
  medium: "oklch(0.95 0.04 85)",
  low: "oklch(0.95 0.04 145)",
};

const SEVERITY_BORDER: Record<DiagnosisItem["severity"], string> = {
  high: "oklch(0.75 0.15 25)",
  medium: "oklch(0.78 0.12 85)",
  low: "oklch(0.78 0.12 145)",
};

const SEVERITY_TEXT: Record<DiagnosisItem["severity"], string> = {
  high: "oklch(0.45 0.18 25)",
  medium: "oklch(0.45 0.14 85)",
  low: "oklch(0.40 0.14 145)",
};

const SEVERITY_BADGE_BG: Record<DiagnosisItem["severity"], string> = {
  high: "oklch(0.55 0.20 25)",
  medium: "oklch(0.60 0.16 85)",
  low: "oklch(0.55 0.16 145)",
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
      <main className="max-w-3xl mx-auto px-4 py-16 text-center">
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
          className="inline-block mt-6 px-5 py-2.5 rounded-xl text-sm font-medium text-white"
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
      <main className="max-w-3xl mx-auto px-4 py-16 text-center">
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
          className="inline-block mt-6 px-5 py-2.5 rounded-xl text-sm font-medium text-white"
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
    <main className="max-w-3xl mx-auto px-4 py-12">
      {/* ---- Section 1: Your Area ---- */}
      <section className="mb-10">
        <h1
          className="text-3xl font-bold mb-2"
          style={{ color: "var(--text-primary)" }}
        >
          {titleCase(data.district)}, {titleCase(data.state)}
        </h1>

        <div
          className="flex flex-wrap gap-x-6 gap-y-1 text-sm mb-2"
          style={{ color: "var(--text-secondary)" }}
        >
          {data.mp && (
            <span>
              <strong>MP:</strong> {data.mp.mp_name}{" "}
              <span style={{ color: "var(--text-muted)" }}>
                ({data.mp.party})
              </span>
            </span>
          )}
          {data.mla && (
            <span>
              <strong>MLA:</strong> {data.mla.mla_name}{" "}
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
      <section className="mb-10">
        <h2
          className="text-xl font-semibold mb-4"
          style={{ color: "var(--text-primary)" }}
        >
          Issues Found
        </h2>

        {data.diagnosis.length === 0 ? (
          <div
            className="rounded-xl px-5 py-4 text-sm font-medium"
            style={{
              background: "oklch(0.95 0.04 145)",
              color: "oklch(0.35 0.14 145)",
              border: "1px solid oklch(0.85 0.08 145)",
            }}
          >
            No major issues flagged for your area. Things look good.
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {data.diagnosis.map((item, i) => (
              <DiagnosisCard key={i} item={item} />
            ))}
          </div>
        )}
      </section>

      {/* ---- Section 3: What You Can Do ---- */}
      {data.actions.length > 0 && (
        <section className="mb-10">
          <h2
            className="text-xl font-semibold mb-4"
            style={{ color: "var(--text-primary)" }}
          >
            What You Can Do
          </h2>

          <div className="flex flex-col gap-3">
            {data.actions.map((action, i) => (
              <div
                key={i}
                className="rounded-xl px-5 py-4"
                style={{
                  background: "var(--surface)",
                  border: "1px solid var(--border)",
                  boxShadow: "var(--shadow-xs)",
                }}
              >
                <p
                  className="text-sm font-bold mb-2"
                  style={{ color: "var(--accent)" }}
                >
                  {action.scheme}
                </p>
                <ol className="list-decimal list-inside flex flex-col gap-1.5">
                  {action.steps.map((step, j) => (
                    <li
                      key={j}
                      className="text-sm"
                      style={{ color: "var(--text-secondary)" }}
                    >
                      {step.action}
                      {step.url && (
                        <a
                          href={step.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="ml-2 text-xs font-medium"
                          style={{ color: "var(--accent)" }}
                        >
                          Visit portal &#x2197;
                        </a>
                      )}
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
        <section className="mb-10">
          <h2
            className="text-xl font-semibold mb-4"
            style={{ color: "var(--text-primary)" }}
          >
            Grievance Portals
          </h2>

          <div className="flex flex-wrap gap-2">
            {data.grievance_channels.map((ch, i) => (
              <a
                key={i}
                href={ch.portal_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-xs font-medium transition-opacity duration-150 hover:opacity-80"
                style={{
                  background: "var(--accent-light)",
                  color: "var(--accent)",
                  border: "1px solid var(--border)",
                }}
              >
                {ch.portal_name}
                {ch.phone && (
                  <span style={{ color: "var(--text-muted)" }}>
                    {" "}
                    | {ch.phone}
                  </span>
                )}
              </a>
            ))}
          </div>
        </section>
      )}

      {/* ---- Footer ---- */}
      <footer
        className="border-t pt-6 mt-6 flex flex-col gap-2"
        style={{ borderColor: "var(--border-subtle)" }}
      >
        <Link
          href={`/district/${districtSlug}`}
          className="text-sm font-medium"
          style={{ color: "var(--accent)" }}
        >
          View full district data for {titleCase(data.district)} &rarr;
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

function DiagnosisCard({ item }: { item: DiagnosisItem }) {
  return (
    <div
      className="rounded-xl px-5 py-4"
      style={{
        background: SEVERITY_BG[item.severity],
        border: `1px solid ${SEVERITY_BORDER[item.severity]}`,
      }}
    >
      <div className="flex items-center justify-between gap-3 mb-1">
        <p
          className="text-sm font-bold"
          style={{ color: SEVERITY_TEXT[item.severity] }}
        >
          {item.scheme}
        </p>
        <span
          className="inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold uppercase tracking-wide text-white"
          style={{ background: SEVERITY_BADGE_BG[item.severity] }}
        >
          {item.severity}
        </span>
      </div>

      <p
        className="text-sm font-medium mb-1"
        style={{ color: "var(--text-primary)" }}
      >
        {item.summary}
      </p>

      <p className="text-xs mb-2" style={{ color: "var(--text-secondary)" }}>
        {item.detail}
      </p>

      {item.source_url && <SourceLink url={item.source_url} />}
    </div>
  );
}

/* ---------- util ---------- */

function titleCase(s: string): string {
  return s
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}
