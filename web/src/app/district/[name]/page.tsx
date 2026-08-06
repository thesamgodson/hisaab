import { cache } from "react";
import { notFound } from "next/navigation";
import Link from "next/link";
import { query, resolveState } from "@/lib/db";
import { formatDistrictLabel, titleCasePlace } from "@/lib/format-place";
import SchemeRow, { type SchemeData } from "@/components/SchemeRow";

interface DistrictPageProps {
  params: Promise<{ name: string }>;
  searchParams: Promise<{ state?: string }>;
}

interface MoneyFlowRow {
  scheme: string;
  state: string;
  district: string;
  fin_year: string;
  allocated_lakhs: number | null;
  released_lakhs: number | null;
  expended_lakhs: number | null;
  utilization_pct: number | null;
  units_target: number | null;
  units_completed: number | null;
  units_label: string | null;
  source_url: string | null;
}

/**
 * Group rows by scheme and pick the latest fin_year for each.
 * fin_year is "YYYY-YYYY" or "cumulative" — a real year always beats
 * "cumulative" (which would win a bare lexicographic comparison).
 */
function finYearRank(finYear: string): string {
  return finYear === "cumulative" ? "0000" : finYear;
}

function latestPerScheme(rows: MoneyFlowRow[]): SchemeData[] {
  const map = new Map<string, MoneyFlowRow>();
  for (const row of rows) {
    const existing = map.get(row.scheme);
    if (!existing || finYearRank(row.fin_year) > finYearRank(existing.fin_year)) {
      map.set(row.scheme, row);
    }
  }
  return Array.from(map.values()).sort((a, b) =>
    a.scheme.localeCompare(b.scheme),
  );
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
    description: `Government welfare scheme delivery and fund flow for ${label}, from official portals.`,
  };
}

export default async function DistrictPage(props: DistrictPageProps) {
  const { districtName, state } = await resolveDistrict(props);

  if (!state) {
    notFound();
  }

  const districtLabel = formatDistrictLabel(districtName, state);

  // Query money_flow VIEW directly. The state predicate matters: 14 district
  // names exist in two states (AURANGABAD, BILASPUR, …) and must not merge.
  const rows = await query<MoneyFlowRow>(
    `SELECT scheme, state, district, fin_year,
            allocated_lakhs, released_lakhs, expended_lakhs,
            utilization_pct, units_target, units_completed,
            units_label, source_url
     FROM money_flow
     WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?)
     ORDER BY scheme, fin_year DESC`,
    [districtName, state],
  );

  const schemes = latestPerScheme(rows);

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-10">
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
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          {titleCasePlace(state)} · {schemes.length} scheme
          {schemes.length !== 1 ? "s" : ""} with data
        </p>
      </header>

      {/* Scheme cards */}
      {schemes.length > 0 ? (
        <div className="grid gap-5 sm:grid-cols-2">
          {schemes.map((s, i) => (
            <div
              key={s.scheme}
              className={`animate-fade-in-up stagger-${Math.min(i + 1, 10)}`}
            >
              <SchemeRow data={s} />
            </div>
          ))}
        </div>
      ) : (
        <div
          className="text-center py-20 rounded-xl"
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
        className="mt-12 pt-6"
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
