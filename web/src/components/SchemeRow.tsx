import Link from "next/link";
import SourceLink from "@/components/SourceLink";
import type { EvidenceMetric, EvidenceRecord } from "@/lib/area-account";
import { schemeDisplay } from "@/lib/scheme-display";

function displayDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(date);
}

function displayMetric(metric: EvidenceMetric): string {
  const value = metric.value.toLocaleString("en-IN", { maximumFractionDigits: 2 });
  if (metric.unit === "count") return value;
  if (metric.unit === "INR lakh") return `₹${value} lakh`;
  if (metric.unit === "INR crore") return `₹${value} crore`;
  if (metric.unit === "MT") return `${value} MT`;
  return `${value} km`;
}

function sourceMeta(record: EvidenceRecord) {
  const scope = record.scope === "district" ? "District record" : "State context";
  return `${scope} · ${record.period}`;
}

export default function SchemeRow({
  scheme,
  records,
  actionHref,
}: {
  scheme: string;
  records: EvidenceRecord[];
  actionHref: string;
}) {
  const display = schemeDisplay(scheme);
  return (
    <details className="ledger-scheme" id={`scheme-${scheme.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}>
      <summary className="ledger-scheme__summary">
        <span className="ledger-scheme__identity">
          <strong>{display.shortNeed}</strong>
          <small>{scheme}</small>
        </span>
        <span className="ledger-scheme__count">
          {records.length} {records.length === 1 ? "record" : "records"}
        </span>
      </summary>
      <div className="ledger-scheme__body">
        <Link className="ledger-scheme__action no-print" href={actionHref}
          aria-label={`Get help with ${display.shortNeed}`}>Get help with this</Link>
        <div className="ledger-records">
          {records.map((record) => (
            <section className="ledger-record" key={record.id} aria-labelledby={`${record.id}-heading`}>
              <header className="ledger-record__header">
                <h3 id={`${record.id}-heading`}>{record.title}</h3>
                <p>{sourceMeta(record)}</p>
              </header>
              <dl className="ledger-metrics">
                {record.metrics.map((metric) => (
                  <div key={metric.label}>
                    <dt>{metric.label}</dt>
                    <dd>{displayMetric(metric)}</dd>
                  </div>
                ))}
              </dl>
              {record.missingMetrics && record.missingMetrics.length > 0 && (
                <ul className="ledger-record__gaps" aria-label="Source values Hisaab cannot interpret">
                  {record.missingMetrics.map((item) => <li key={item}>{item}</li>)}
                </ul>
              )}
              {record.note && <p className="ledger-record__note">{record.note}</p>}
              <footer className="ledger-record__provenance">
                <SourceLink
                  url={record.sourceUrl}
                  label="Data source"
                  accessibleLabel={`Data source for ${scheme}: ${record.title}`}
                />
                <span>Record date: {record.asOf}</span>
                <span>Retrieved {displayDate(record.retrievedAt)}</span>
                <span className="claim-id">{record.claimId}</span>
              </footer>
            </section>
          ))}
        </div>
      </div>
    </details>
  );
}
