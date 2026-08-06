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

function amount(lakhs: number): string {
  if (lakhs >= 100) {
    return `₹${(lakhs / 100).toLocaleString("en-IN", { maximumFractionDigits: 1 })} crore`;
  }
  return `₹${lakhs.toLocaleString("en-IN", { maximumFractionDigits: 1 })} lakh`;
}

function period(finYear: string): string {
  return finYear === "cumulative" ? "Cumulative report" : `FY ${finYear}`;
}

export default function SchemeRow({ data }: { data: SchemeData }) {
  const display = schemeDisplay(data.scheme);
  const indicator = data.utilization_pct;
  const finance = [
    ["Allocated", data.allocated_lakhs],
    ["Released", data.released_lakhs],
    ["Expended", data.expended_lakhs],
  ] as const;

  return (
    <details className="evidence-row">
      <summary>
        <strong>{display.need}</strong>
        <span className="evidence-row__indicator">
          {indicator != null ? `${indicator.toFixed(1)}% funds` : "View"}
        </span>
      </summary>
      <div className="evidence-row__body">
        <p className="evidence-row__meta">{data.scheme} · {period(data.fin_year)}</p>
        <dl>
          {finance.map(([label, value]) => value != null && (
            <div key={label}><dt>{label}</dt><dd>{amount(value)}</dd></div>
          ))}
          {data.units_label && data.units_completed != null && (
            <div>
              <dt>{data.units_label}</dt>
              <dd>
                {data.units_completed.toLocaleString("en-IN")}
                {data.units_target != null && data.units_target > 0
                  ? ` of ${data.units_target.toLocaleString("en-IN")}`
                  : ""}
              </dd>
            </div>
          )}
          {data.utilization_pct != null && (
            <div><dt>Fund utilization</dt><dd>{data.utilization_pct.toFixed(1)}%</dd></div>
          )}
        </dl>
        {data.source_url && <SourceLink url={data.source_url} />}
      </div>
    </details>
  );
}
