/** Data quality indicator -- shows whether financial/delivery data is real, imputed, or hollow. */

type Quality = "real" | "imputed" | "hollow";

interface DataQualityProps {
  quality: Quality;
  detail?: string;
}

const QUALITY_STYLES: Record<
  Quality,
  { bg: string; color: string; dot: string; label: string }
> = {
  real: {
    bg: "oklch(0.95 0.03 145)",
    color: "oklch(0.40 0.12 145)",
    dot: "oklch(0.55 0.17 145)",
    label: "Verified",
  },
  imputed: {
    bg: "oklch(0.95 0.03 80)",
    color: "oklch(0.45 0.12 80)",
    dot: "oklch(0.60 0.16 80)",
    label: "Imputed",
  },
  hollow: {
    bg: "var(--border-subtle)",
    color: "var(--text-muted)",
    dot: "var(--border)",
    label: "No Data",
  },
};

export default function DataQuality({ quality, detail }: DataQualityProps) {
  const style = QUALITY_STYLES[quality];

  return (
    <span
      className="inline-flex items-center gap-1.5 px-2 py-0.5 text-xs font-medium rounded-md"
      style={{
        background: style.bg,
        color: style.color,
      }}
      title={detail}
    >
      <span
        className="w-1.5 h-1.5 rounded-full"
        style={{ backgroundColor: style.dot }}
      />
      {style.label}
    </span>
  );
}

/** Determine quality level from scheme warnings. */
export function qualityFromWarnings(
  scheme: string,
  warnings: string[],
): Quality {
  if (!warnings || warnings.length === 0) return "real";

  const hasHollow = warnings.some(
    (w) =>
      w.includes("ALL zeros") ||
      w.includes("still zero") ||
      w.includes("not publicly accessible"),
  );
  if (hasHollow) return "hollow";

  const hasImputed = warnings.some(
    (w) => w.includes("IMPUTED") || w.includes("imputed"),
  );
  if (hasImputed) return "imputed";

  // Schemes with minor notes are still "real"
  if (scheme === "MGNREGA" || scheme === "PMGSY") return "real";

  return "real";
}
