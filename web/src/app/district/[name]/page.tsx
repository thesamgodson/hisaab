import { cache } from "react";
import { notFound } from "next/navigation";
import Link from "next/link";
import { resolveState } from "@/lib/db";
import { buildDistrictBrief } from "@/lib/action-brief";
import { getDistrictSchemeRows } from "@/lib/money-flow";
import {
  displayPersonName,
  formatDistrictLabel,
  titleCasePlace,
} from "@/lib/format-place";
import ComplaintKitSection from "@/components/ComplaintKit";
import DiagnosisCard from "@/components/DiagnosisCard";
import SchemeDataSection from "@/components/SchemeDataSection";
import SectionHeader from "@/components/SectionHeader";

interface DistrictPageProps {
  params: Promise<{ name: string }>;
  searchParams: Promise<{ state?: string }>;
}

/* generateMetadata and the page resolve the same district — cache() keeps the
   state lookup to a single query per request. */
const getState = cache(resolveState);

async function resolveDistrict(props: DistrictPageProps) {
  const [{ name: rawName }, searchParams] = await Promise.all([
    props.params,
    props.searchParams,
  ]);

  // Canonical form — this feeds the query, never the display.
  const districtName = decodeURIComponent(rawName)
    .toUpperCase()
    .replace(/-/g, " ");

  // Resolve state from query param or DB lookup
  const stateFromParam = searchParams.state?.toUpperCase().replace(/-/g, " ") ?? null;
  const state = stateFromParam ?? (await getState(districtName));

  return { districtName, state };
}

export async function generateMetadata(props: DistrictPageProps) {
  const { districtName, state } = await resolveDistrict(props);
  // The root layout's title template appends "| Hisaab".
  const label = state
    ? formatDistrictLabel(districtName, state)
    : titleCasePlace(districtName);
  return {
    title: label,
    description: `Scheme shortfalls, how to complain, who is accountable, and fund-flow data for ${label} — from official government sources.`,
  };
}

/**
 * The district page IS the accountability brief at district grain — the same
 * sections the PIN page serves (issues, complaint kits, scheme data), with
 * honestly-plural representatives: a district commonly spans 2-3 Lok Sabha
 * constituencies, so naming "your MP" needs a PIN. Map clicks and PIN entry
 * must never net different products.
 */
export default async function DistrictPage(props: DistrictPageProps) {
  const { districtName, state } = await resolveDistrict(props);

  if (!state) {
    notFound();
  }

  const districtLabel = formatDistrictLabel(districtName, state);
  const [brief, schemes] = await Promise.all([
    buildDistrictBrief(districtName, state),
    getDistrictSchemeRows(districtName, state),
  ]);

  const nothingChecked =
    brief.diagnosis.length === 0 && brief.schemes_checked.length === 0;
  const representatives = brief.mps.map(
    (mp) => `MP ${displayPersonName(mp.mp_name)} (${mp.party})`,
  );

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10">
      {/* Breadcrumb */}
      <nav
        className="text-sm mb-8"
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
            {districtLabel}
          </li>
        </ol>
      </nav>

      {/* Header */}
      <header className="mb-10">
        <h1
          className="text-2xl sm:text-3xl font-bold tracking-tight mb-1"
          style={{ color: "var(--text-primary)" }}
        >
          {districtLabel}
        </h1>
        <p className="text-sm mb-3" style={{ color: "var(--text-muted)" }}>
          {titleCasePlace(state)} · {schemes.length} scheme
          {schemes.length !== 1 ? "s" : ""} with data
        </p>

        {brief.formerly_part_of && (
          <p className="text-sm mb-3" style={{ color: "var(--text-muted)" }}>
            Formerly part of{" "}
            {titleCasePlace(brief.formerly_part_of.parent_district)} district,
            reorganized {brief.formerly_part_of.split_year}
          </p>
        )}

        {brief.mps.length > 0 && (
          <div
            className="flex flex-col gap-1 text-sm"
            style={{ color: "var(--text-secondary)" }}
          >
            {brief.mps.map((mp) => (
              <span key={mp.constituency}>
                <span className="font-medium">
                  MP ({titleCasePlace(mp.constituency)}):
                </span>{" "}
                {displayPersonName(mp.mp_name)}{" "}
                <span style={{ color: "var(--text-muted)" }}>({mp.party})</span>
              </span>
            ))}
            <span className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
              {brief.ac_count > 0
                ? `${brief.ac_count} assembly seats cover this district — `
                : ""}
              <Link
                href="/"
                className="underline underline-offset-2"
                style={{ color: "var(--accent)" }}
              >
                enter your PIN
              </Link>{" "}
              for your exact MP and MLA.
            </span>
          </div>
        )}
      </header>

      {/* Issues Found — same section the PIN page serves */}
      <section className="mb-12">
        <SectionHeader title="Issues Found" count={brief.diagnosis.length} />
        {brief.diagnosis.length === 0 ? (
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
                (MGNREGA, PMAY-G, JJM, PMGSY) don&apos;t report district data
                for {districtLabel}. That&apos;s common in urban districts —
                the scheme data below is what we track here.
              </p>
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
              No shortfalls flagged in the data we can check for this district.
            </div>
          )
        ) : (
          <div className="flex flex-col gap-4">
            {brief.diagnosis.map((item, i) => (
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

      {/* How to Complain — same kits the PIN page serves */}
      <ComplaintKitSection
        kits={brief.complaint_kits}
        universal={brief.universal_channels}
        representatives={representatives}
      />

      {/* Scheme evidence cards */}
      <SchemeDataSection schemes={schemes} />

      {schemes.length === 0 && (
        <div
          className="text-center py-16 rounded-xl mb-12"
          style={{
            background: "var(--surface)",
            border: "1px solid var(--border-subtle)",
            boxShadow: "var(--shadow-sm)",
          }}
        >
          <p
            className="text-lg font-medium mb-1"
            style={{ color: "var(--text-primary)" }}
          >
            No scheme data found
          </p>
          <p className="text-sm" style={{ color: "var(--text-muted)" }}>
            We don&apos;t have data for this district yet.
          </p>
        </div>
      )}

      {/* Footer note */}
      <footer
        className="mt-4 pt-6"
        style={{ borderTop: "1px solid var(--border-subtle)" }}
      >
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          Data from official government portals. Financial figures in Indian
          Rupees (lakhs). All numbers use the latest available financial year.
        </p>
      </footer>
    </div>
  );
}
