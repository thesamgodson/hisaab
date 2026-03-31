/** Card for one scheme showing finance, delivery, and source link. */

import SourceLink from "@/components/SourceLink";

export interface SchemeData {
  scheme: string;
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

/** Format lakhs: >=100 as "X.X Cr", else "X.X L". */
function fmtAmount(lakhs: number): string {
  if (lakhs >= 100) {
    const cr = lakhs / 100;
    return `\u20B9${cr.toLocaleString("en-IN", { maximumFractionDigits: 1 })} Cr`;
  }
  return `\u20B9${lakhs.toLocaleString("en-IN", { maximumFractionDigits: 1 })} L`;
}

/** Indian number format. */
function fmtNum(n: number): string {
  return n.toLocaleString("en-IN");
}

/** Determine status color based on best available percentage. */
function statusColor(row: SchemeData): string {
  const deliveryPct =
    row.units_target && row.units_target > 0 && row.units_completed != null
      ? (row.units_completed / row.units_target) * 100
      : null;
  const pct = deliveryPct ?? row.utilization_pct;
  if (pct == null) return "#9ca3af"; // gray
  if (pct >= 75) return "#22c55e"; // green
  if (pct >= 50) return "#f59e0b"; // amber
  return "#ef4444"; // red
}

export default function SchemeRow({ data }: { data: SchemeData }) {
  const hasFinance =
    (data.allocated_lakhs ?? 0) > 0 ||
    (data.released_lakhs ?? 0) > 0 ||
    (data.expended_lakhs ?? 0) > 0;

  const financeParts: string[] = [];
  if (data.allocated_lakhs && data.allocated_lakhs > 0)
    financeParts.push(`Allocated ${fmtAmount(data.allocated_lakhs)}`);
  if (data.released_lakhs && data.released_lakhs > 0)
    financeParts.push(`Released ${fmtAmount(data.released_lakhs)}`);
  if (data.expended_lakhs && data.expended_lakhs > 0)
    financeParts.push(`Expended ${fmtAmount(data.expended_lakhs)}`);

  const hasDelivery =
    data.units_label != null && data.units_completed != null;

  const deliveryPct =
    data.units_target && data.units_target > 0 && data.units_completed != null
      ? (data.units_completed / data.units_target) * 100
      : null;

  const showUtilization =
    data.utilization_pct != null &&
    (data.utilization_pct > 0 || hasFinance);

  return (
    <div
      className="rounded-xl p-5 card-hover gradient-border-top"
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border-subtle)",
      }}
    >
      {/* Header */}
      <div className="flex items-center gap-2.5 mb-3">
        <span
          className="inline-block w-2.5 h-2.5 rounded-full flex-shrink-0"
          style={{ background: statusColor(data) }}
          aria-hidden="true"
        />
        <h3
          className="text-base font-semibold leading-tight"
          style={{ color: "var(--text-primary)" }}
        >
          {data.scheme}
        </h3>
        <span
          className="ml-auto text-xs font-medium"
          style={{ color: "var(--text-muted)" }}
        >
          {data.fin_year}
        </span>
      </div>

      {/* Finance line */}
      {financeParts.length > 0 && (
        <p
          className="text-sm mb-1.5"
          style={{ color: "var(--text-secondary)" }}
        >
          {financeParts.join(" \u00B7 ")}
        </p>
      )}

      {/* Delivery line */}
      {hasDelivery && (
        <p
          className="text-sm mb-1.5"
          style={{ color: "var(--text-secondary)" }}
        >
          {data.units_label}:{" "}
          <span className="font-medium" style={{ color: "var(--text-primary)" }}>
            {fmtNum(data.units_completed!)}
            {data.units_target && data.units_target > 0
              ? ` / ${fmtNum(data.units_target)}`
              : ""}
          </span>
          {deliveryPct != null && (
            <span style={{ color: "var(--text-muted)" }}>
              {" "}
              ({deliveryPct.toFixed(1)}%)
            </span>
          )}
        </p>
      )}

      {/* Utilization */}
      {showUtilization && (
        <p className="text-xs mb-3" style={{ color: "var(--text-muted)" }}>
          Utilization: {data.utilization_pct!.toFixed(1)}%
        </p>
      )}

      {/* Source link */}
      {data.source_url && (
        <div className="mt-auto pt-2">
          <SourceLink url={data.source_url} />
        </div>
      )}
    </div>
  );
}
