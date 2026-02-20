"use client";

/**
 * IndiaMap -- 820-district choropleth of accountability scores.
 *
 * Uses d3-geo + TopoJSON for real district boundaries. Each district is
 * coloured by composite accountability score. Hover shows tooltip with
 * district name, state, score, and grade. Click navigates to district page.
 *
 * Performance: React.memo on DistrictPath, useMemo on projection/pathGen.
 * Renders 820 SVG <path> elements with smooth interaction.
 */

import { useRouter } from "next/navigation";
import {
  memo,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { geoMercator, geoPath } from "d3-geo";
import type { GeoPermissibleObjects } from "d3-geo";
import { fetchScores } from "@/lib/api";
import { loadDistrictBoundaries, type DistrictFeature } from "@/lib/geodata";
import type { DistrictScore } from "@/lib/types";

// ---------------------------------------------------------------------------
// Score band utilities
// ---------------------------------------------------------------------------

type ScoreBand = "high" | "medium-high" | "medium" | "low" | "none";

function scoreBand(score: number | null | undefined): ScoreBand {
  if (score == null) return "none";
  if (score >= 80) return "high";
  if (score >= 60) return "medium-high";
  if (score >= 40) return "medium";
  return "low";
}

/** OKLCH-based fill colours per band. */
const BAND_FILL: Record<ScoreBand, string> = {
  high: "oklch(0.72 0.17 145)",
  "medium-high": "oklch(0.78 0.14 105)",
  medium: "oklch(0.75 0.16 65)",
  low: "oklch(0.62 0.20 25)",
  none: "oklch(0.90 0 0)",
};

const BAND_LABEL: Record<ScoreBand, string> = {
  high: "80+ Good",
  "medium-high": "60-80 Fair",
  medium: "40-60 Weak",
  low: "<40 Poor",
  none: "N/A",
};

const HOVER_STROKE = "oklch(0.50 0.20 265)";

// ---------------------------------------------------------------------------
// India bounding box for projection fitting
// ---------------------------------------------------------------------------

/** Approximate bounding box: [west, south, east, north] */
const INDIA_BBOX: [[number, number], [number, number]] = [
  [68.0, 6.5],
  [97.5, 37.0],
];

// ---------------------------------------------------------------------------
// DistrictPath -- memoised SVG path for a single district
// ---------------------------------------------------------------------------

interface DistrictPathProps {
  d: string;
  fill: string;
  district: string;
  state: string;
  score: number | null;
  grade: string | null;
  isDisputed: boolean;
  onHover: (
    e: React.MouseEvent,
    info: { district: string; state: string; score: number | null; grade: string | null },
  ) => void;
  onLeave: () => void;
  onClick: (district: string, state: string) => void;
}

const DistrictPath = memo(function DistrictPath({
  d,
  fill,
  district,
  state,
  score,
  grade,
  isDisputed,
  onHover,
  onLeave,
  onClick,
}: DistrictPathProps) {
  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (isDisputed) return;
      onHover(e, { district, state, score, grade });
    },
    [isDisputed, onHover, district, state, score, grade],
  );

  const handleClick = useCallback(() => {
    if (isDisputed) return;
    onClick(district, state);
  }, [isDisputed, onClick, district, state]);

  return (
    <path
      d={d}
      fill={fill}
      stroke="oklch(0.99 0 0)"
      strokeWidth={0.3}
      strokeLinejoin="round"
      className={isDisputed ? "" : "cursor-pointer"}
      style={{ transition: "fill 0.15s, stroke-width 0.15s" }}
      onMouseMove={handleMouseMove}
      onMouseLeave={onLeave}
      onClick={handleClick}
      aria-label={
        isDisputed
          ? "Disputed area"
          : `${district}, ${state}${score != null ? `: score ${score}` : ": N/A"}`
      }
    />
  );
});

// ---------------------------------------------------------------------------
// Tooltip
// ---------------------------------------------------------------------------

interface TooltipData {
  x: number;
  y: number;
  district: string;
  state: string;
  score: number | null;
  grade: string | null;
}

function Tooltip({ tip }: { tip: TooltipData }) {
  const band = scoreBand(tip.score);
  return (
    <div
      className="pointer-events-none absolute z-20 rounded-lg border border-gray-200
                 bg-white/90 backdrop-blur-sm px-3 py-2 shadow-lg text-xs leading-snug"
      style={{ left: tip.x + 14, top: tip.y - 14 }}
    >
      <p className="font-semibold text-sm" style={{ color: "oklch(0.15 0.01 262)" }}>
        {tip.district}
      </p>
      <p className="text-gray-500 mt-0.5">{tip.state}</p>
      {tip.score != null ? (
        <p className="mt-1 font-medium" style={{ color: BAND_FILL[band] }}>
          Score {tip.score.toFixed(1)} -- Grade {tip.grade}
        </p>
      ) : (
        <p className="mt-1 text-gray-400">No score data</p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Legend
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
          <span className="text-xs" style={{ color: "oklch(0.40 0.01 262)" }}>
            {BAND_LABEL[band]}
          </span>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Loading skeleton
// ---------------------------------------------------------------------------

function MapSkeleton() {
  return (
    <div className="w-full aspect-[4/5] rounded-xl overflow-hidden relative"
         style={{ backgroundColor: "oklch(0.96 0.005 260)" }}>
      <div className="absolute inset-0 shimmer-sweep" />
      <style>{`
        .shimmer-sweep::after {
          content: '';
          position: absolute;
          inset: 0;
          background: linear-gradient(
            90deg,
            transparent 0%,
            oklch(0.98 0.003 260 / 0.6) 50%,
            transparent 100%
          );
          animation: shimmer 1.5s infinite;
        }
        @keyframes shimmer {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(100%); }
        }
        @media (prefers-reduced-motion: reduce) {
          .shimmer-sweep::after { animation: none; opacity: 0.5; }
        }
      `}</style>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Error state
// ---------------------------------------------------------------------------

function MapError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="w-full aspect-[4/5] rounded-xl flex flex-col items-center justify-center gap-3"
         style={{ backgroundColor: "oklch(0.96 0.005 260)" }}>
      <p className="text-sm" style={{ color: "oklch(0.40 0.01 262)" }}>
        Could not load map data
      </p>
      <p className="text-xs" style={{ color: "oklch(0.55 0.01 262)" }}>
        {message}
      </p>
      <button
        onClick={onRetry}
        className="mt-2 px-4 py-1.5 rounded-lg text-sm font-medium text-white"
        style={{ background: "oklch(0.50 0.20 265)" }}
      >
        Retry
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main map component
// ---------------------------------------------------------------------------

/** SVG dimensions -- aspect ratio ~4:5 for India. */
const MAP_WIDTH = 600;
const MAP_HEIGHT = 720;

export default function IndiaMap() {
  const router = useRouter();
  const containerRef = useRef<HTMLDivElement>(null);

  const [districts, setDistricts] = useState<DistrictFeature[] | null>(null);
  const [scoreMap, setScoreMap] = useState<Map<string, DistrictScore>>(new Map());
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);
  const [hoveredKey, setHoveredKey] = useState<string | null>(null);

  // ---- Data fetching ----

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [feats, scoresRes] = await Promise.all([
        loadDistrictBoundaries(),
        fetchScores().catch(() => null), // Backend may be down
      ]);

      setDistricts(feats);

      if (scoresRes) {
        const map = new Map<string, DistrictScore>();
        for (const s of scoresRes.scores) {
          // Key: "DISTRICT|STATE" for exact matching
          map.set(`${s.district}|${s.state}`, s);
        }
        setScoreMap(map);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error loading map");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // ---- Projection ----

  const projection = useMemo(() => {
    // Fixed projection centered on India mainland — avoids fitSize issues
    // with outlying islands (Andaman, Lakshadweep) shrinking the mainland
    return geoMercator()
      .center([82.5, 22.5])
      .scale(MAP_WIDTH * 1.5)
      .translate([MAP_WIDTH / 2, MAP_HEIGHT / 2]);
    /* Original fitSize approach (broken by island territories):
    return geoMercator().fitSize([MAP_WIDTH, MAP_HEIGHT], {
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          properties: {},
          geometry: {
            type: "Polygon",
            coordinates: [
              [
                [INDIA_BBOX[0][0], INDIA_BBOX[0][1]],
                [INDIA_BBOX[1][0], INDIA_BBOX[0][1]],
                [INDIA_BBOX[1][0], INDIA_BBOX[1][1]],
                [INDIA_BBOX[0][0], INDIA_BBOX[1][1]],
                [INDIA_BBOX[0][0], INDIA_BBOX[0][1]],
              ],
            ],
          },
        },
      ],
    });
    */
  }, []);

  const pathGenerator = useMemo(() => geoPath(projection), [projection]);

  // ---- Pre-compute paths ----

  const districtPaths = useMemo(() => {
    if (!districts) return [];
    return districts.map((feat) => {
      const d = pathGenerator(feat.geometry as GeoPermissibleObjects) || "";
      const key = `${feat.district}|${feat.state}`;
      const scoreData = scoreMap.get(key);
      const isDisputed = !feat.district;
      const band = scoreBand(scoreData?.score);
      return {
        key,
        d,
        fill: BAND_FILL[band],
        district: feat.district,
        state: feat.state,
        score: scoreData?.score ?? null,
        grade: scoreData?.grade ?? null,
        isDisputed,
      };
    });
  }, [districts, scoreMap, pathGenerator]);

  // ---- Event handlers ----

  const handleHover = useCallback(
    (
      e: React.MouseEvent,
      info: { district: string; state: string; score: number | null; grade: string | null },
    ) => {
      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect) return;
      setHoveredKey(`${info.district}|${info.state}`);
      setTooltip({
        x: e.clientX - rect.left,
        y: e.clientY - rect.top,
        ...info,
      });
    },
    [],
  );

  const handleLeave = useCallback(() => {
    setTooltip(null);
    setHoveredKey(null);
  }, []);

  const handleClick = useCallback(
    (district: string, state: string) => {
      if (!district) return;
      router.push(
        `/district/${encodeURIComponent(district)}?state=${encodeURIComponent(state)}`,
      );
    },
    [router],
  );

  // ---- Render ----

  if (loading) {
    return (
      <div className="w-full max-w-2xl mx-auto">
        <div className="rounded-2xl border shadow-sm overflow-hidden px-4 pt-4 pb-2"
             style={{
               borderColor: "oklch(0.94 0.005 260)",
               backgroundColor: "oklch(0.99 0.003 260)",
             }}>
          <div className="mb-3">
            <h2 className="text-sm font-semibold" style={{ color: "oklch(0.30 0.01 262)" }}>
              District Accountability Map
            </h2>
          </div>
          <MapSkeleton />
        </div>
      </div>
    );
  }

  if (error || !districts) {
    return (
      <div className="w-full max-w-2xl mx-auto">
        <div className="rounded-2xl border shadow-sm overflow-hidden px-4 pt-4 pb-2"
             style={{
               borderColor: "oklch(0.94 0.005 260)",
               backgroundColor: "oklch(0.99 0.003 260)",
             }}>
          <MapError message={error || "N/A"} onRetry={loadData} />
        </div>
      </div>
    );
  }

  const scoredCount = [...scoreMap.values()].filter((s) => s.score != null).length;

  return (
    <div className="w-full max-w-2xl mx-auto">
      <div
        className="rounded-2xl border shadow-sm overflow-hidden px-4 pt-4 pb-2"
        style={{
          borderColor: "oklch(0.94 0.005 260)",
          backgroundColor: "oklch(0.99 0.003 260)",
          boxShadow: "0 8px 32px rgba(0,0,0,0.06)",
        }}
      >
        {/* Header */}
        <div className="mb-3 flex items-baseline justify-between">
          <h2 className="text-sm font-semibold" style={{ color: "oklch(0.30 0.01 262)" }}>
            District Accountability Map
          </h2>
          <span className="text-xs" style={{ color: "oklch(0.55 0.01 262)" }}>
            {scoredCount > 0
              ? `${scoredCount} of ${districts.length - 28} districts scored`
              : `${districts.length - 28} districts`}
          </span>
        </div>

        {/* SVG map */}
        <div ref={containerRef} className="relative">
          <svg
            viewBox={`0 0 ${MAP_WIDTH} ${MAP_HEIGHT}`}
            className="w-full h-auto"
            aria-label="India district accountability map"
            role="img"
            onMouseLeave={handleLeave}
          >
            {districtPaths.map((dp, idx) => (
              <DistrictPath
                key={`${dp.key}_${idx}`}
                d={dp.d}
                fill={hoveredKey === dp.key ? BAND_FILL[scoreBand(dp.score)] : dp.fill}
                district={dp.district}
                state={dp.state}
                score={dp.score}
                grade={dp.grade}
                isDisputed={dp.isDisputed}
                onHover={handleHover}
                onLeave={handleLeave}
                onClick={handleClick}
              />
            ))}

            {/* Hover stroke overlay -- separate so it renders on top */}
            {hoveredKey && districtPaths.find((dp) => dp.key === hoveredKey) && (
              <path
                d={districtPaths.find((dp) => dp.key === hoveredKey)!.d}
                fill="none"
                stroke={HOVER_STROKE}
                strokeWidth={1.5}
                strokeLinejoin="round"
                className="pointer-events-none"
              />
            )}
          </svg>

          {/* Floating tooltip */}
          {tooltip && <Tooltip tip={tooltip} />}
        </div>

        <Legend />
      </div>
    </div>
  );
}
