/** Card showing one scheme's data for a district. */

import DataQuality, { qualityFromWarnings } from "./DataQuality";
import RedFlagBadge from "./RedFlagBadge";
import SourceLink from "./SourceLink";
import { SCHEME_META } from "@/lib/types";

interface SchemeCardProps {
  schemeName: string;
  answer: string;
  data: Record<string, unknown> | Record<string, unknown>[] | null;
  sourceUrl?: string;
  warnings: string[];
}

/** Extract red flags from the data based on known thresholds. */
function detectRedFlags(
  schemeName: string,
  data: Record<string, unknown> | Record<string, unknown>[] | null,
): string[] {
  if (!data) return [];
  const flags: string[] = [];
  const d = Array.isArray(data) ? data[0] : data;
  if (!d) return flags;

  if (schemeName === "MGNREGA") {
    const rate = d["recovery_rate_pct"] as number | undefined;
    if (rate !== undefined && rate < 20) {
      flags.push(`Recovery rate only ${rate.toFixed(0)}%`);
    }
    const cases = d["cases_reported"] as number | undefined;
    if (cases !== undefined && cases > 100) {
      flags.push(`${cases.toLocaleString()} cases reported`);
    }
  }

  if (schemeName === "PMGSY") {
    const items = Array.isArray(data) ? data : [d];
    const totalSanctioned = items.reduce(
      (s, r) => s + ((r["roads_sanctioned"] as number) || 0),
      0,
    );
    const totalCompleted = items.reduce(
      (s, r) => s + ((r["roads_completed"] as number) || 0),
      0,
    );
    if (totalSanctioned > 0) {
      const pct = (totalCompleted / totalSanctioned) * 100;
      if (pct < 50) flags.push(`Only ${pct.toFixed(0)}% roads completed`);
    }
  }

  if (schemeName === "PMAY-G") {
    const pct = d["completion_pct"] as number | undefined;
    if (pct !== undefined && pct < 50) {
      flags.push(`Only ${pct.toFixed(0)}% houses completed`);
    }
  }

  if (schemeName === "JJM") {
    const pct = d["coverage_pct"] as number | undefined;
    if (pct !== undefined && pct < 50) {
      flags.push(`Only ${pct.toFixed(0)}% tap water coverage`);
    }
  }

  const utilPct = d["utilization_pct"] as number | undefined;
  if (utilPct !== undefined && utilPct < 40 && utilPct > 0) {
    flags.push(`Low utilization: ${utilPct.toFixed(0)}%`);
  }

  return flags;
}

/** Format scheme answer into structured lines for display. */
function formatAnswer(answer: string): string[] {
  return answer
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

export default function SchemeCard({
  schemeName,
  answer,
  data,
  sourceUrl,
  warnings,
}: SchemeCardProps) {
  const meta = SCHEME_META[schemeName];
  const quality = qualityFromWarnings(schemeName, warnings);
  const redFlags = detectRedFlags(schemeName, data);
  const lines = formatAnswer(answer);
  const headerLine = lines[0] ?? schemeName;
  const detailLines = lines.slice(1);

  return (
    <div
      className={`rounded-2xl border border-gray-100 shadow-sm overflow-hidden ${meta?.bg ?? "bg-gray-50"}`}
    >
      <div className="px-5 py-4">
        {/* Header */}
        <div className="flex items-start justify-between gap-2 mb-3">
          <div>
            <h3
              className={`text-base font-semibold ${meta?.color ?? "text-gray-800"}`}
            >
              {meta?.shortName ?? schemeName}
            </h3>
            <p className="text-xs text-gray-500 mt-0.5">{headerLine}</p>
          </div>
          <DataQuality quality={quality} detail={warnings.join(" | ")} />
        </div>

        {/* Red flags */}
        {redFlags.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-3">
            {redFlags.map((flag) => (
              <RedFlagBadge key={flag} label={flag} />
            ))}
          </div>
        )}

        {/* Data lines */}
        {data ? (
          <div className="space-y-1">
            {detailLines.map((line, i) => (
              <p
                key={i}
                className="text-sm text-gray-700 font-mono leading-relaxed"
              >
                {line}
              </p>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-400 italic">
            No data available for this district.
          </p>
        )}

        {/* Warnings tooltip area */}
        {warnings.length > 0 && (
          <details className="mt-3">
            <summary className="text-xs text-gray-400 cursor-pointer hover:text-gray-600">
              {warnings.length} data quality{" "}
              {warnings.length === 1 ? "note" : "notes"}
            </summary>
            <ul className="mt-1 space-y-1">
              {warnings.map((w, i) => (
                <li
                  key={i}
                  className="text-xs text-gray-500 pl-3 relative before:content-[''] before:absolute before:left-0 before:top-1.5 before:w-1 before:h-1 before:bg-gray-300 before:rounded-full"
                >
                  {w}
                </li>
              ))}
            </ul>
          </details>
        )}

        {/* Source link */}
        {sourceUrl && (
          <div className="mt-3 pt-3 border-t border-gray-200/50">
            <SourceLink url={sourceUrl} />
          </div>
        )}
      </div>
    </div>
  );
}
