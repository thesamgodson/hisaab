"use client";

/**
 * IndiaMap — State-level choropleth map for accountability scores.
 *
 * Renders a simplified inline SVG of India's states coloured by average
 * composite accountability score. Hover shows state name + avg score.
 * Click navigates to the first matched district page for that state.
 *
 * Data source: /api/v1/scores/states (aggregated from district scores).
 *
 * NOTE: This is a state-level map using hand-simplified SVG paths.
 * For full district-level choropleth, replace `loadDistrictBoundaries()` in
 * `@/lib/geodata.ts` with district GeoJSON from datameet/maps and project
 * with d3-geo. The SVG viewport (800×900) and state id convention remain
 * the same, so only the path data needs updating.
 */

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { fetchStateRankings } from "@/lib/api";
import { type StateRanking } from "@/lib/types";
import { loadDistrictBoundaries, type StateBoundary } from "@/lib/geodata";

// ---------------------------------------------------------------------------
// Score → colour mapping
// ---------------------------------------------------------------------------

type ScoreBand = "high" | "medium-high" | "medium" | "low" | "none";

function scoreBand(score: number | undefined): ScoreBand {
  if (score === undefined) return "none";
  if (score >= 80) return "high";
  if (score >= 60) return "medium-high";
  if (score >= 40) return "medium";
  return "low";
}

const BAND_FILL: Record<ScoreBand, string> = {
  high: "#16a34a",          // green-600
  "medium-high": "#ca8a04", // yellow-600
  medium: "#ea580c",        // orange-600
  low: "#dc2626",           // red-600
  none: "#d1d5db",          // gray-300
};

const BAND_LABEL: Record<ScoreBand, string> = {
  high: "80+ (Good)",
  "medium-high": "60–80 (Fair)",
  medium: "40–60 (Weak)",
  low: "<40 (Poor)",
  none: "No data",
};

// ---------------------------------------------------------------------------
// Tooltip component
// ---------------------------------------------------------------------------

interface TooltipState {
  x: number;
  y: number;
  state: string;
  score: number | undefined;
  grade: string | undefined;
  districtCount: number | undefined;
}

function Tooltip({ tip }: { tip: TooltipState }) {
  const band = scoreBand(tip.score);
  return (
    <div
      className="pointer-events-none absolute z-20 rounded-xl border border-gray-200 bg-white
                 px-3 py-2 shadow-lg text-xs leading-snug"
      style={{ left: tip.x + 12, top: tip.y - 10 }}
    >
      <p className="font-semibold text-gray-900 text-sm">{tip.state}</p>
      {tip.score !== undefined ? (
        <>
          <p className="mt-0.5" style={{ color: BAND_FILL[band] }}>
            Score: {tip.score.toFixed(1)} — Grade {tip.grade}
          </p>
          <p className="text-gray-400">{tip.districtCount} districts</p>
        </>
      ) : (
        <p className="text-gray-400">No score data</p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Legend component
// ---------------------------------------------------------------------------

function Legend() {
  const bands: ScoreBand[] = ["high", "medium-high", "medium", "low", "none"];
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1 mt-3 justify-center">
      {bands.map((band) => (
        <div key={band} className="flex items-center gap-1.5">
          <span
            className="inline-block w-3 h-3 rounded-sm flex-shrink-0"
            style={{ backgroundColor: BAND_FILL[band] }}
          />
          <span className="text-xs text-gray-500">{BAND_LABEL[band]}</span>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main map component
// ---------------------------------------------------------------------------

export default function IndiaMap() {
  const router = useRouter();
  const svgRef = useRef<SVGSVGElement>(null);

  const [rankingsByState, setRankingsByState] = useState<
    Record<string, StateRanking>
  >({});
  const [loading, setLoading] = useState(true);
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);

  const boundaries: StateBoundary[] = loadDistrictBoundaries();

  useEffect(() => {
    fetchStateRankings()
      .then((res) => {
        const map: Record<string, StateRanking> = {};
        for (const r of res.rankings) {
          map[r.state.toUpperCase()] = r;
        }
        setRankingsByState(map);
      })
      .catch(() => {
        // Backend not running — map renders with grey states
      })
      .finally(() => setLoading(false));
  }, []);

  function handleMouseMove(
    e: React.MouseEvent<SVGPathElement>,
    boundary: StateBoundary,
  ) {
    const rect = svgRef.current?.getBoundingClientRect();
    if (!rect) return;
    const ranking = rankingsByState[boundary.id.toUpperCase()];
    setTooltip({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
      state: boundary.label,
      score: ranking?.avg_score,
      grade: ranking?.grade,
      districtCount: ranking?.district_count,
    });
  }

  function handleClick(boundary: StateBoundary) {
    // Navigate to the first known district for this state.
    // The district page will show state context in its header.
    const ranking = rankingsByState[boundary.id.toUpperCase()];
    if (!ranking) return;
    // Encode state name as a search query so SearchBar picks it up.
    // Fallback: navigate to the state name directly — district route handles
    // the lookup via _resolve_state in the API.
    router.push(
      `/district/${encodeURIComponent(boundary.id)}?state=${encodeURIComponent(boundary.id)}`,
    );
  }

  return (
    <div className="w-full max-w-2xl mx-auto">
      <div className="relative rounded-2xl border border-gray-100 bg-white shadow-sm overflow-hidden px-4 pt-4 pb-2">
        {/* Header */}
        <div className="mb-3 flex items-baseline justify-between">
          <h2 className="text-sm font-semibold text-gray-700">
            Accountability Map
          </h2>
          <span className="text-xs text-gray-400">
            {loading ? "Loading scores…" : `${Object.keys(rankingsByState).length} states scored`}
          </span>
        </div>

        {/* SVG map — relative container for tooltip positioning */}
        <div className="relative">
          <svg
            ref={svgRef}
            viewBox="80 20 510 420"
            className="w-full h-auto"
            aria-label="India state accountability map"
            role="img"
            onMouseLeave={() => setTooltip(null)}
          >
            {boundaries.map((boundary) => {
              const ranking = rankingsByState[boundary.id.toUpperCase()];
              const band = scoreBand(ranking?.avg_score);
              const fill = BAND_FILL[band];
              return (
                <g key={boundary.id}>
                  <path
                    d={boundary.path}
                    fill={fill}
                    stroke="#fff"
                    strokeWidth={1.5}
                    strokeLinejoin="round"
                    className="transition-opacity duration-150 cursor-pointer hover:opacity-80"
                    onMouseMove={(e) => handleMouseMove(e, boundary)}
                    onClick={() => handleClick(boundary)}
                    aria-label={`${boundary.label}${ranking ? `: score ${ranking.avg_score}` : ": no data"}`}
                  />
                  {/* Abbreviated label inside state */}
                  <text
                    x={boundary.labelX}
                    y={boundary.labelY}
                    fontSize={7}
                    fill="white"
                    textAnchor="middle"
                    dominantBaseline="middle"
                    className="pointer-events-none select-none font-medium"
                    style={{ fontFamily: "var(--font-geist-sans, system-ui)" }}
                  >
                    {boundary.label}
                  </text>
                </g>
              );
            })}
          </svg>

          {/* Floating tooltip */}
          {tooltip && <Tooltip tip={tooltip} />}
        </div>

        <Legend />
      </div>
    </div>
  );
}
