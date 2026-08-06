import type { DiagnosisItem } from "@/lib/action-types";
import SourceLink from "@/components/SourceLink";
import { schemeDisplay } from "@/lib/scheme-display";

const SEVERITY_LABEL: Record<DiagnosisItem["severity"], string> = {
  high: "High priority",
  medium: "Medium priority",
  low: "Low priority",
};

export default function DiagnosisCard({ item }: { item: DiagnosisItem }) {
  const display = schemeDisplay(item.scheme);

  return (
    <article className={`diagnosis-card diagnosis-card--${item.severity}`}>
      <div className="diagnosis-card__heading">
        <p className="diagnosis-card__scheme">
          {display.need} · {item.scheme}
        </p>
        <span className="diagnosis-card__badge">
          {SEVERITY_LABEL[item.severity]}
        </span>
      </div>
      <h3>{item.summary}</h3>
      <p className="diagnosis-card__detail">{item.detail}</p>
      {item.source_url && <SourceLink url={item.source_url} />}
    </article>
  );
}
