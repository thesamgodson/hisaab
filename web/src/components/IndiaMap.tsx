"use client";

import { geoMercator, geoPath } from "d3-geo";
import type { GeoPermissibleObjects } from "d3-geo";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ChangeEvent } from "react";
import {
  BAND_FILL,
  DistrictPath,
  Legend,
  MapError,
  MapFrame,
  MapSkeleton,
  Tooltip,
  scoreBand,
  type TooltipData,
} from "@/components/IndiaMapParts";
import { loadDistrictBoundaries, type DistrictFeature } from "@/lib/geodata";
import { titleCasePlace } from "@/lib/format-place";
import type { DistrictScore, ScoreBreakdown, ScoresResponse } from "@/lib/types";

const MAP_WIDTH = 600;
const MAP_HEIGHT = 720;

async function fetchScores(): Promise<ScoresResponse> {
  const response = await fetch("/api/v1/scores");
  if (!response.ok) throw new Error(`Scores API: ${response.status}`);
  return response.json() as Promise<ScoresResponse>;
}

export default function IndiaMap() {
  const router = useRouter();
  const rootRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [districts, setDistricts] = useState<DistrictFeature[] | null>(null);
  const [scoreMap, setScoreMap] = useState<Map<string, DistrictScore>>(new Map());
  const [finYear, setFinYear] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);
  const [hoveredKey, setHoveredKey] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [features, scoresResponse] = await Promise.all([
        loadDistrictBoundaries(),
        fetchScores().catch(() => null),
      ]);
      setDistricts(features);

      if (scoresResponse) {
        const scores = new Map<string, DistrictScore>();
        for (const item of scoresResponse.scores) {
          scores.set(`${item.district.toUpperCase()}|${item.state.toUpperCase()}`, item);
        }
        setScoreMap(scores);
        setFinYear(scoresResponse.fin_year ?? null);
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unknown error loading map");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      void loadData();
      return;
    }
    const element = rootRef.current;
    if (!element) return;

    const observer = new IntersectionObserver((entries) => {
      if (!entries.some((entry) => entry.isIntersecting)) return;
      observer.disconnect();
      void loadData();
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, [loadData]);

  const projection = useMemo(
    () => geoMercator()
      .center([82.5, 22.5])
      .scale(MAP_WIDTH * 1.5)
      .translate([MAP_WIDTH / 2, MAP_HEIGHT / 2]),
    [],
  );
  const pathGenerator = useMemo(() => geoPath(projection), [projection]);
  const districtPaths = useMemo(() => {
    if (!districts) return [];
    return districts.map((feature) => {
      const key = `${feature.district.toUpperCase()}|${feature.state.toUpperCase()}`;
      const scoreData = scoreMap.get(key);
      return {
        key,
        d: pathGenerator(feature.geometry as GeoPermissibleObjects) || "",
        fill: BAND_FILL[scoreBand(scoreData?.score)],
        district: feature.district,
        state: feature.state,
        score: scoreData?.score ?? null,
        grade: scoreData?.grade ?? null,
        breakdown: scoreData?.breakdown ?? null,
        isDisputed: !feature.district,
      };
    });
  }, [districts, scoreMap, pathGenerator]);
  const disputedCount = useMemo(
    () => districts?.filter((feature) => !feature.district).length ?? 0,
    [districts],
  );
  const districtOptions = useMemo(
    () => [...(districts ?? [])]
      .filter((feature) => feature.district)
      .sort((left, right) => left.district.localeCompare(right.district)),
    [districts],
  );

  const handleHover = useCallback((
    event: React.MouseEvent,
    info: {
      district: string;
      state: string;
      score: number | null;
      grade: string | null;
      breakdown: ScoreBreakdown | null;
    },
  ) => {
    const bounds = containerRef.current?.getBoundingClientRect();
    if (!bounds) return;
    setHoveredKey(`${info.district}|${info.state}`);
    setTooltip({
      x: event.clientX - bounds.left,
      y: event.clientY - bounds.top,
      ...info,
      finYear,
    });
  }, [finYear]);

  const handleLeave = useCallback(() => {
    setTooltip(null);
    setHoveredKey(null);
  }, []);

  useEffect(() => {
    if (!tooltip) return;
    const dismiss = (event: KeyboardEvent) => {
      if (event.key === "Escape") handleLeave();
    };
    window.addEventListener("keydown", dismiss);
    return () => window.removeEventListener("keydown", dismiss);
  }, [tooltip, handleLeave]);

  const handleClick = useCallback((district: string, state: string) => {
    if (!district) return;
    router.push(
      `/district/${encodeURIComponent(district)}?state=${encodeURIComponent(state)}`,
    );
  }, [router]);
  const handleDistrictSelect = useCallback((event: ChangeEvent<HTMLSelectElement>) => {
    const [district, state] = event.target.value.split("|");
    if (district && state) handleClick(district, state);
  }, [handleClick]);

  if (loading) {
    return (
      <div ref={rootRef} className="map-wrap">
        <MapFrame title="District evidence map"><MapSkeleton /></MapFrame>
      </div>
    );
  }

  if (error || !districts) {
    return (
      <div ref={rootRef} className="map-wrap">
        <MapFrame title="District evidence map">
          <MapError message={error || "Not available"} onRetry={loadData} />
        </MapFrame>
      </div>
    );
  }

  const scoredCount = [...scoreMap.values()].filter((score) => score.score != null).length;
  const districtCount = districts.length - disputedCount;
  const hoveredPath = hoveredKey
    ? districtPaths.find((district) => district.key === hoveredKey)
    : undefined;

  return (
    <div ref={rootRef} className="map-wrap">
      <MapFrame
        title="District evidence map"
        meta={scoredCount > 0
          ? `${scoredCount} of ${districtCount} districts scored`
          : `${districtCount} districts`}
      >
        <label className="map-picker">
          <span>Open a district brief</span>
          <select defaultValue="" onChange={handleDistrictSelect}>
            <option value="" disabled>Choose a district</option>
            {districtOptions.map((district) => (
              <option
                key={`${district.district}|${district.state}`}
                value={`${district.district}|${district.state}`}
              >
                {titleCasePlace(district.district)}, {titleCasePlace(district.state)}
              </option>
            ))}
          </select>
        </label>
        <div ref={containerRef} className="map-canvas">
          <svg
            viewBox={`0 0 ${MAP_WIDTH} ${MAP_HEIGHT}`}
            aria-label={`India district accountability map: ${scoredCount} of ${districtCount} districts scored`}
            role="img"
            onMouseLeave={handleLeave}
          >
            {districtPaths.map((district, index) => (
              <DistrictPath
                {...district}
                key={`${district.key}_${index}`}
                onHover={handleHover}
                onLeave={handleLeave}
                onClick={handleClick}
              />
            ))}
            {hoveredPath && (
              <path
                d={hoveredPath.d}
                fill="none"
                stroke="var(--color-accent)"
                strokeWidth={1.5}
                strokeLinejoin="round"
                className="map-hover-path"
              />
            )}
          </svg>
          {tooltip && <Tooltip tip={tooltip} />}
        </div>
        <Legend />
      </MapFrame>
    </div>
  );
}
