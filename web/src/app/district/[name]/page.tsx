import { notFound } from "next/navigation";
import Link from "next/link";
import { query, resolveState } from "@/lib/db";
import SchemeRow, { type SchemeData } from "@/components/SchemeRow";

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
 * fin_year format: "2024-2025" — lexicographic sort works.
 */
function latestPerScheme(rows: MoneyFlowRow[]): SchemeData[] {
  const map = new Map<string, MoneyFlowRow>();
  for (const row of rows) {
    const existing = map.get(row.scheme);
    if (!existing || row.fin_year > existing.fin_year) {
      map.set(row.scheme, row);
    }
  }
  return Array.from(map.values()).sort((a, b) =>
    a.scheme.localeCompare(b.scheme),
  );
}

export default async function DistrictPage(props: {
  params: Promise<{ name: string }>;
  searchParams: Promise<{ state?: string }>;
}) {
  const { name: rawName } = await props.params;
  const searchParams = await props.searchParams;

  const districtName = decodeURIComponent(rawName)
    .toUpperCase()
    .replace(/-/g, " ");

  // Resolve state from query param or DB lookup
  const stateFromParam = searchParams.state?.toUpperCase().replace(/-/g, " ") ?? null;
  const state = stateFromParam ?? (await resolveState(districtName));

  if (!state) {
    notFound();
  }

  // Query money_flow VIEW directly
  const rows = await query<MoneyFlowRow>(
    `SELECT scheme, state, district, fin_year,
            allocated_lakhs, released_lakhs, expended_lakhs,
            utilization_pct, units_target, units_completed,
            units_label, source_url
     FROM money_flow
     WHERE UPPER(district) = UPPER(?)
     ORDER BY scheme, fin_year DESC`,
    [districtName],
  );

  const schemes = latestPerScheme(rows);

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
      {/* Breadcrumb */}
      <nav
        className="text-sm mb-6"
        style={{ color: "var(--text-muted)" }}
        aria-label="Breadcrumb"
      >
        <ol className="flex items-center gap-1.5">
          <li>
            <Link
              href="/"
              className="hover:underline"
              style={{ color: "var(--accent)" }}
            >
              Home
            </Link>
          </li>
          <li aria-hidden="true">/</li>
          <li style={{ color: "var(--text-primary)" }}>{districtName}</li>
        </ol>
      </nav>

      {/* Header */}
      <header className="mb-8">
        <h1
          className="text-2xl sm:text-3xl font-bold mb-1"
          style={{ color: "var(--text-primary)" }}
        >
          {districtName}
        </h1>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          {state}
        </p>
      </header>

      {/* Scheme cards */}
      {schemes.length > 0 ? (
        <div className="grid gap-4 sm:grid-cols-2">
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
          className="text-center py-16 rounded-xl"
          style={{
            background: "var(--surface)",
            border: "1px solid var(--border-subtle)",
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
      <footer className="mt-10 pt-6" style={{ borderTop: "1px solid var(--border-subtle)" }}>
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          Data from official government portals. Financial figures in Indian
          Rupees (lakhs).
        </p>
      </footer>
    </div>
  );
}
