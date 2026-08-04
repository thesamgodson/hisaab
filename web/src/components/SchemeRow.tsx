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

/** Status color and label based on best available percentage.
 *
 * "Reported" (neutral) means figures exist but no percentage can honestly be
 * computed (no target, or the source metric is not a completion rate) — it is
 * NOT a judgment. Never label a card "No data" while rendering data on it.
 */
function statusInfo(row: SchemeData): { color: string; label: string } {
  const deliveryPct =
    row.units_target && row.units_target > 0 && row.units_completed != null
      ? (row.units_completed / row.units_target) * 100
      : null;
  const pct = deliveryPct ?? row.utilization_pct;
  if (pct == null) return { color: "oklch(0.60 0 0)", label: "Reported" };
  if (pct >= 75) return { color: "oklch(0.55 0.18 145)", label: "Good" };
  if (pct >= 50) return { color: "oklch(0.62 0.16 75)", label: "Fair" };
  return { color: "oklch(0.55 0.20 25)", label: "Poor" };
}

export default function SchemeRow({ data }: { data: SchemeData }) {
  const hasFinance =
    (data.allocated_lakhs ?? 0) > 0 ||
    (data.released_lakhs ?? 0) > 0 ||
    (data.expended_lakhs ?? 0) > 0;

  const hasDelivery =
    data.units_label != null && data.units_completed != null;

  const deliveryPct =
    data.units_target && data.units_target > 0 && data.units_completed != null
      ? (data.units_completed / data.units_target) * 100
      : null;

  const showUtilization =
    data.utilization_pct != null &&
    (data.utilization_pct > 0 || hasFinance);

  const status = statusInfo(data);

  return (
    <div
      className="rounded-xl p-5 card-hover status-border-left flex flex-col"
      style={{
        background: "var(--elevated)",
        border: "1px solid var(--border-subtle)",
        boxShadow: "var(--shadow-sm)",
        ["--card-accent" as string]: status.color,
      }}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="min-w-0">
          <h3
            className="text-[15px] font-semibold leading-tight"
            style={{ color: "var(--text-primary)" }}
          >
            {data.scheme}
          </h3>
          <span
            className="text-xs mt-0.5 inline-block"
            style={{ color: "var(--text-muted)" }}
          >
            {data.fin_year}
          </span>
        </div>
        <span
          className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md text-[11px] font-semibold flex-shrink-0"
          style={{
            background: status.color,
            color: "white",
          }}
        >
          {status.label}
        </span>
      </div>

      {/* Finance figures — tabular layout */}
      {hasFinance && (
        <div
          className="grid grid-cols-3 gap-3 mb-3 pb-3"
          style={{ borderBottom: "1px solid var(--border-subtle)" }}
        >
          {data.allocated_lakhs != null && data.allocated_lakhs > 0 && (
            <div>
              <p
                className="text-[11px] uppercase tracking-wide font-medium mb-0.5"
                style={{ color: "var(--text-muted)" }}
              >
                Allocated
              </p>
              <p
                className="text-sm font-semibold tabular-nums"
                style={{ color: "var(--text-primary)" }}
              >
                {fmtAmount(data.allocated_lakhs)}
              </p>
            </div>
          )}
          {data.released_lakhs != null && data.released_lakhs > 0 && (
            <div>
              <p
                className="text-[11px] uppercase tracking-wide font-medium mb-0.5"
                style={{ color: "var(--text-muted)" }}
              >
                Released
              </p>
              <p
                className="text-sm font-semibold tabular-nums"
                style={{ color: "var(--text-primary)" }}
              >
                {fmtAmount(data.released_lakhs)}
              </p>
            </div>
          )}
          {data.expended_lakhs != null && data.expended_lakhs > 0 && (
            <div>
              <p
                className="text-[11px] uppercase tracking-wide font-medium mb-0.5"
                style={{ color: "var(--text-muted)" }}
              >
                Expended
              </p>
              <p
                className="text-sm font-semibold tabular-nums"
                style={{ color: "var(--text-primary)" }}
              >
                {fmtAmount(data.expended_lakhs)}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Delivery with progress bar */}
      {hasDelivery && (
        <div className="mb-3">
          <div className="flex items-baseline justify-between mb-1.5">
            <p className="text-xs" style={{ color: "var(--text-secondary)" }}>
              {data.units_label}
            </p>
            <p
              className="text-xs font-medium tabular-nums"
              style={{ color: "var(--text-primary)" }}
            >
              {fmtNum(data.units_completed!)}
              {data.units_target && data.units_target > 0
                ? ` / ${fmtNum(data.units_target)}`
                : ""}
              {deliveryPct != null && (
                <span style={{ color: "var(--text-muted)" }}>
                  {" "}
                  ({deliveryPct.toFixed(1)}%)
                </span>
              )}
            </p>
          </div>
          {deliveryPct != null && (
            <div className="progress-track">
              <div
                className="progress-fill"
                style={{
                  width: `${Math.min(deliveryPct, 100)}%`,
                  background: status.color,
                }}
              />
            </div>
          )}
        </div>
      )}

      {/* Utilization */}
      {showUtilization && !deliveryPct && (
        <div className="mb-3">
          <div className="flex items-baseline justify-between mb-1.5">
            <p className="text-xs" style={{ color: "var(--text-secondary)" }}>
              Utilization
            </p>
            <p
              className="text-xs font-medium tabular-nums"
              style={{ color: "var(--text-primary)" }}
            >
              {data.utilization_pct!.toFixed(1)}%
            </p>
          </div>
          <div className="progress-track">
            <div
              className="progress-fill"
              style={{
                width: `${Math.min(data.utilization_pct!, 100)}%`,
                background: status.color,
              }}
            />
          </div>
        </div>
      )}

      {showUtilization && deliveryPct && (
        <p className="text-xs mb-3 tabular-nums" style={{ color: "var(--text-muted)" }}>
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
