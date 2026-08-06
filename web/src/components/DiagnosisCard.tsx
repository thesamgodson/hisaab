import type { DiagnosisItem } from "@/lib/action-types";
import SourceLink from "@/components/SourceLink";

/* ---------- severity styling ---------- */

const SEVERITY_BG: Record<DiagnosisItem["severity"], string> = {
  high: "oklch(0.97 0.02 25)",
  medium: "oklch(0.97 0.02 85)",
  low: "oklch(0.97 0.02 145)",
};

const SEVERITY_BORDER: Record<DiagnosisItem["severity"], string> = {
  high: "oklch(0.80 0.12 25)",
  medium: "oklch(0.82 0.10 85)",
  low: "oklch(0.82 0.10 145)",
};

const SEVERITY_TEXT: Record<DiagnosisItem["severity"], string> = {
  high: "oklch(0.40 0.18 25)",
  medium: "oklch(0.40 0.14 85)",
  low: "oklch(0.38 0.14 145)",
};

const SEVERITY_ACCENT: Record<DiagnosisItem["severity"], string> = {
  high: "oklch(0.55 0.20 25)",
  medium: "oklch(0.60 0.16 85)",
  low: "oklch(0.55 0.16 145)",
};

const SEVERITY_LABEL: Record<DiagnosisItem["severity"], string> = {
  high: "High severity",
  medium: "Medium",
  low: "Low",
};

export default function DiagnosisCard({ item }: { item: DiagnosisItem }) {
  return (
    <div
      className="rounded-xl overflow-hidden"
      style={{
        background: SEVERITY_BG[item.severity],
        border: `1px solid ${SEVERITY_BORDER[item.severity]}`,
      }}
    >
      {/* Severity accent bar */}
      <div
        style={{
          height: "3px",
          background: SEVERITY_ACCENT[item.severity],
        }}
      />

      <div className="px-5 py-4">
        <div className="flex items-center justify-between gap-3 mb-2">
          <p
            className="text-sm font-semibold"
            style={{ color: SEVERITY_TEXT[item.severity] }}
          >
            {item.scheme}
          </p>
          <span
            className="inline-block px-2.5 py-0.5 rounded-md text-[11px] font-semibold uppercase tracking-wide text-white"
            style={{ background: SEVERITY_ACCENT[item.severity] }}
          >
            {SEVERITY_LABEL[item.severity]}
          </span>
        </div>

        <p
          className="text-[15px] font-medium mb-1.5 leading-snug"
          style={{ color: "var(--text-primary)" }}
        >
          {item.summary}
        </p>

        <p
          className="text-sm leading-relaxed mb-3"
          style={{ color: "var(--text-secondary)" }}
        >
          {item.detail}
        </p>

        {item.source_url && <SourceLink url={item.source_url} />}
      </div>
    </div>
  );
}
