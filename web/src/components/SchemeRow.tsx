import SourceLink from "@/components/SourceLink";
import { schemeDisplay } from "@/lib/scheme-display";

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

function fmtAmount(lakhs: number): string {
  if (lakhs >= 100) {
    return `₹${(lakhs / 100).toLocaleString("en-IN", {
      maximumFractionDigits: 1,
    })} Cr`;
  }
  return `₹${lakhs.toLocaleString("en-IN", { maximumFractionDigits: 1 })} L`;
}

function fmtNum(value: number): string {
  return value.toLocaleString("en-IN");
}

function periodLabel(finYear: string): string {
  return finYear === "cumulative" ? "Cumulative reporting" : `FY ${finYear}`;
}

function statusInfo(percentage: number | null): {
  tone: "neutral" | "high" | "medium" | "low";
  label: string;
} {
  if (percentage == null) return { tone: "neutral", label: "Reported" };
  const label = `${percentage.toFixed(0)}%`;
  if (percentage >= 75) return { tone: "high", label };
  if (percentage >= 50) return { tone: "medium", label };
  return { tone: "low", label };
}

export default function SchemeRow({ data }: { data: SchemeData }) {
  const display = schemeDisplay(data.scheme);
  const finance = [
    ["Allocated", data.allocated_lakhs],
    ["Released", data.released_lakhs],
    ["Expended", data.expended_lakhs],
  ] as const;
  const hasFinance = finance.some(([, value]) => value != null);
  const hasDelivery = data.units_label != null && data.units_completed != null;
  const deliveryPct =
    data.units_target != null && data.units_target > 0 && data.units_completed != null
      ? (data.units_completed / data.units_target) * 100
      : null;
  const status = statusInfo(deliveryPct ?? data.utilization_pct);

  return (
    <article className={`scheme-card scheme-card--${status.tone}`}>
      <header className="scheme-card__header">
        <div className="scheme-card__title">
          <span className="scheme-card__need">{display.need}</span>
          <span className="scheme-card__scheme">
            {data.scheme} · {periodLabel(data.fin_year)}
          </span>
        </div>
        <span className="scheme-card__badge">{status.label}</span>
      </header>

      {hasFinance && (
        <div className="scheme-card__figures">
          {finance.map(([label, value]) =>
            value != null ? (
              <div key={label}>
                <p className="scheme-card__label">{label}</p>
                <p className="scheme-card__value">{fmtAmount(value)}</p>
              </div>
            ) : null,
          )}
        </div>
      )}

      {hasDelivery && (
        <div className="scheme-card__metric">
          <div className="scheme-card__metric-row">
            <span>{data.units_label}</span>
            <strong>
              {fmtNum(data.units_completed!)}
              {data.units_target != null && data.units_target > 0
                ? ` / ${fmtNum(data.units_target)}`
                : ""}
            </strong>
          </div>
          {deliveryPct != null && (
            <div className="progress-track" aria-hidden="true">
              <div
                className="progress-fill"
                style={{ width: `${Math.min(deliveryPct, 100)}%` }}
              />
            </div>
          )}
        </div>
      )}

      {data.utilization_pct != null && (
        <div className="scheme-card__metric">
          <div className="scheme-card__metric-row">
            <span>Fund utilization</span>
            <strong>{data.utilization_pct.toFixed(1)}%</strong>
          </div>
          {deliveryPct == null && (
            <div className="progress-track" aria-hidden="true">
              <div
                className="progress-fill"
                style={{ width: `${Math.min(data.utilization_pct, 100)}%` }}
              />
            </div>
          )}
        </div>
      )}

      {data.source_url && <SourceLink url={data.source_url} />}
    </article>
  );
}
