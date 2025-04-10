/** Data quality indicator — shows whether financial/delivery data is real, imputed, or hollow. */

type Quality = "real" | "imputed" | "hollow";

interface DataQualityProps {
  quality: Quality;
  detail?: string;
}

const QUALITY_STYLES: Record<
  Quality,
  { bg: string; text: string; label: string }
> = {
  real: { bg: "bg-green-50", text: "text-green-700", label: "Verified" },
  imputed: { bg: "bg-yellow-50", text: "text-yellow-700", label: "Imputed" },
  hollow: { bg: "bg-gray-100", text: "text-gray-500", label: "No Data" },
};

export default function DataQuality({ quality, detail }: DataQualityProps) {
  const style = QUALITY_STYLES[quality];

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-md border ${style.bg} ${style.text} border-current/20`}
      title={detail}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${
          quality === "real"
            ? "bg-green-500"
            : quality === "imputed"
              ? "bg-yellow-500"
              : "bg-gray-400"
        }`}
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
