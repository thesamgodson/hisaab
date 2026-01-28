import type { DiagnosisItem } from "@/lib/action-types";

const SEVERITY_COLORS: Record<DiagnosisItem["severity"], string> = {
  high: "oklch(0.55 0.22 25)",
  medium: "oklch(0.65 0.18 65)",
  low: "oklch(0.55 0.10 250)",
};

const SEVERITY_BG: Record<DiagnosisItem["severity"], string> = {
  high: "oklch(0.97 0.04 25)",
  medium: "oklch(0.98 0.03 65)",
  low: "oklch(0.97 0.02 250)",
};

const SEVERITY_LABEL: Record<DiagnosisItem["severity"], string> = {
  high: "High",
  medium: "Medium",
  low: "Low",
};

interface DiagnosisCardProps {
  item: DiagnosisItem;
}

export default function DiagnosisCard({ item }: DiagnosisCardProps) {
  const dotColor = SEVERITY_COLORS[item.severity];
  const bgColor = SEVERITY_BG[item.severity];

  return (
    <div
      className="rounded-xl p-5 card-hover"
      style={{
        background: "var(--elevated)",
        border: "1px solid var(--border)",
        boxShadow: "var(--shadow-sm)",
      }}
    >
      {/* Header row */}
      <div className="flex items-start gap-3 mb-3">
        {/* Severity dot */}
        <span
          className="mt-0.5 flex-shrink-0 w-3 h-3 rounded-full"
          style={{ background: dotColor }}
          aria-hidden="true"
        />

        <div className="flex-1 min-w-0">
          {/* Scheme + severity badge */}
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <span
              className="text-xs font-semibold uppercase tracking-wider"
              style={{ color: "var(--accent)" }}
            >
              {item.scheme}
            </span>
            <span
              className="text-xs font-medium px-2 py-0.5 rounded-full"
              style={{ background: bgColor, color: dotColor }}
            >
              {SEVERITY_LABEL[item.severity]} severity
            </span>
            {item.amount && (
              <span
                className="text-xs font-mono px-2 py-0.5 rounded-full"
                style={{
                  background: "var(--surface-tinted)",
                  color: "var(--text-secondary)",
                }}
              >
                {item.amount}
              </span>
            )}
          </div>

          {/* Summary */}
          <p
            className="text-sm font-semibold leading-snug"
            style={{ color: "var(--text-primary)" }}
          >
            {item.summary}
          </p>
        </div>
      </div>

      {/* Detail */}
      <p
        className="text-sm leading-relaxed mb-3 pl-6"
        style={{ color: "var(--text-secondary)" }}
      >
        {item.detail}
      </p>

      {/* Source link */}
      <div className="pl-6">
        <a
          href={item.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-xs font-medium transition-colors duration-150 hover:underline"
          style={{ color: "var(--accent)" }}
        >
          View source data
          <svg
            width="10"
            height="10"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M7 17L17 7M17 7H7M17 7v10" />
          </svg>
        </a>
      </div>
    </div>
  );
}
