import { cache } from "react";
import type { Metadata } from "next";
import Link from "next/link";
import { buildActionBrief } from "@/lib/action-brief";
import { getDistrictSchemeRows } from "@/lib/money-flow";
import {
  displayPersonName,
  formatDistrictLabel,
  titleCasePlace,
} from "@/lib/format-place";
import ComplaintKitSection from "@/components/ComplaintKit";
import SchemeDataSection from "@/components/SchemeDataSection";
import DiagnosisCard from "@/components/DiagnosisCard";
import PinNotice from "@/components/PinNotice";
import SectionHeader from "@/components/SectionHeader";

/* generateMetadata and the page both need the brief — cache() collapses them
   into a single build per request. */
const getBrief = cache(buildActionBrief);

/* ---------- page ---------- */

interface PageProps {
  params: Promise<{ pin: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { pin } = await params;
  if (!/^\d{6}$/.test(pin)) return { title: "Invalid PIN code" };

  const data = await getBrief(pin);
  if (!data) return { title: `PIN ${pin}` };

  return {
    title: `PIN ${pin} · ${formatDistrictLabel(data.district, data.state)}`,
    description: `Welfare scheme shortfalls, who is accountable, and what you can do about them for PIN ${pin}.`,
  };
}

export default async function ActionPage({ params }: PageProps) {
  const { pin } = await params;

  /* Validate PIN format */
  if (!/^\d{6}$/.test(pin)) {
    return (
      <PinNotice heading="Invalid PIN Code">
        &ldquo;{pin}&rdquo; is not a valid 6-digit PIN code.
      </PinNotice>
    );
  }

  /* Build the brief in-process — same code path the public API serves */
  const data = await getBrief(pin);

  /* A well-formed PIN we don't serve is a typo, not a missing page — the 404
     shell ("does not exist or has been moved") tells the user nothing. */
  if (!data) {
    return (
      <PinNotice heading={`PIN ${pin} not found`}>
        This PIN isn&apos;t in the postal directory we serve. Double-check the
        code, or try a nearby PIN.
      </PinNotice>
    );
  }

  const generatedDate = new Date(data.generated_at).toLocaleDateString(
    "en-IN",
    { day: "numeric", month: "long", year: "numeric" },
  );

  const schemes = await getDistrictSchemeRows(data.district, data.state);
  const districtSlug = data.district.toLowerCase().replace(/\s+/g, "-");
  const districtHref = `/district/${districtSlug}?state=${encodeURIComponent(data.state)}`;
  const districtLabel = formatDistrictLabel(data.district, data.state);
  // Nothing flagged AND nothing checked: the honest answer is "no district
  // data", not a green all-clear.
  const nothingChecked =
    data.diagnosis.length === 0 && data.schemes_checked.length === 0;
  // Curated complaint routing supersedes the legacy hardcoded actions the
  // moment its data is published; until then the old sections still render.
  const hasKits =
    data.complaint_kits.length > 0 || data.universal_channels.length > 0;
  const representatives = [
    data.mp && `MP ${displayPersonName(data.mp.mp_name)} (${data.mp.party})`,
    data.mla && `MLA ${displayPersonName(data.mla.mla_name)} (${data.mla.party})`,
  ].filter((r): r is string => Boolean(r));

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-12">
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
          {districtLabel}
        </h1>

        {data.formerly_part_of && (
          <p className="text-sm mb-3" style={{ color: "var(--text-muted)" }}>
            Formerly part of {titleCasePlace(data.formerly_part_of.parent_district)} district,
            reorganized {data.formerly_part_of.split_year}
          </p>
        )}

        <div
          className="flex flex-wrap gap-x-6 gap-y-1.5 text-sm mb-3"
          style={{ color: "var(--text-secondary)" }}
        >
          {data.mp && (
            <span>
              <span className="font-medium">MP:</span> {displayPersonName(data.mp.mp_name)}{" "}
              <span style={{ color: "var(--text-muted)" }}>
                ({data.mp.party})
              </span>
            </span>
          )}
          {data.mla && (
            <span>
              <span className="font-medium">MLA:</span> {displayPersonName(data.mla.mla_name)}{" "}
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
          nothingChecked ? (
            <div
              className="rounded-xl px-5 py-5"
              style={{
                background: "var(--surface)",
                border: "1px solid var(--border-subtle)",
              }}
            >
              <p
                className="text-sm leading-relaxed"
                style={{ color: "var(--text-secondary)" }}
              >
                The schemes we can check for shortfalls at district level
                (MGNREGA, PMAY-G, JJM, PMGSY) don&apos;t report district data for{" "}
                {districtLabel}. That&apos;s common in urban districts.
              </p>
              <Link
                href={districtHref}
                className="inline-flex items-center gap-1.5 mt-4 px-5 py-2.5 rounded-xl text-sm font-semibold text-white transition-opacity duration-150 hover:opacity-90"
                style={{ background: "var(--accent)" }}
              >
                View full district data for {titleCasePlace(data.district)}
                <ArrowRightIcon />
              </Link>
            </div>
          ) : (
            <div
              className="rounded-xl px-5 py-5 text-sm font-medium"
              style={{
                background: "oklch(0.97 0.02 145)",
                color: "oklch(0.35 0.14 145)",
                border: "1px solid oklch(0.88 0.06 145)",
              }}
            >
              No shortfalls flagged in {formatSchemeList(data.schemes_checked)}{" "}
              data for your area.
            </div>
          )
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

      {/* ---- Section 3: How to Complain (curated) / legacy actions ---- */}
      {hasKits && (
        <ComplaintKitSection
          kits={data.complaint_kits}
          universal={data.universal_channels}
          representatives={representatives}
        />
      )}

      {!hasKits && data.actions.length > 0 && (
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

      {/* ---- Section 4: Grievance Portals (legacy — superseded by kits) ---- */}
      {!hasKits && data.grievance_channels && data.grievance_channels.length > 0 && (
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

      {/* ---- Scheme evidence cards (same section the district page serves) ---- */}
      <SchemeDataSection schemes={schemes} />

      {/* ---- Footer ---- */}
      <footer
        className="pt-8 mt-4 flex flex-col gap-3"
        style={{ borderTop: "1px solid var(--border-subtle)" }}
      >
        {/* Promoted into the diagnosis section when it is the primary action. */}
        {!nothingChecked && (
          <Link
            href={districtHref}
            className="inline-flex items-center gap-1.5 text-sm font-medium transition-opacity duration-150 hover:opacity-80"
            style={{ color: "var(--accent)" }}
          >
            View full district data for {titleCasePlace(data.district)}
            <ArrowRightIcon />
          </Link>
        )}
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          Data from official government portals. Source links provided per
          finding.
        </p>
      </footer>
    </div>
  );
}

/* ---------- sub-components ---------- */

function ArrowRightIcon() {
  return (
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
  );
}

/* ---------- util ---------- */

const SCHEME_LIST_FORMAT = new Intl.ListFormat("en", { type: "conjunction" });

function formatSchemeList(schemes: string[]): string {
  return SCHEME_LIST_FORMAT.format(schemes);
}
