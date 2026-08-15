import { memo, useCallback } from "react";
import type { MouseEvent, ReactNode } from "react";
import type { ScoreBreakdown } from "@/lib/types";

type ScoreBand = "high" | "medium-high" | "medium" | "low" | "none";

/* --color-map-* are reserved theme slots for this choropleth; theme.css does
 * not define them yet, so each falls back to an existing semantic token
 * (same success/warning/danger family the grade badges use) rather than a
 * literal — swap the fallback for a dedicated theme.css value with no
 * change needed here. */
export const BAND_FILL: Record<ScoreBand, string> = {
  high: "var(--color-map-high, var(--color-success-soft))",
  "medium-high": "var(--color-map-medium-high, var(--color-warning-soft))",
  medium: "var(--color-map-medium, var(--color-warning-rule))",
  low: "var(--color-map-low, var(--color-danger-soft))",
  none: "var(--color-map-none, var(--color-surface-strong))",
};

const BAND_TEXT: Record<ScoreBand, string> = {
  high: "var(--color-map-high-ink, var(--color-success))",
  "medium-high": "var(--color-map-medium-high-ink, var(--color-warning))",
  medium: "var(--color-map-medium-ink, var(--color-warning))",
  low: "var(--color-map-low-ink, var(--color-danger))",
  none: "var(--color-map-none-ink, var(--color-muted))",
};

const BAND_LABEL: Record<ScoreBand, string> = {
  high: "80–100",
  "medium-high": "60–79.9",
  medium: "40–59.9",
  low: "Below 40",
  none: "Not scored",
};

export function scoreBand(score: number | null | undefined): ScoreBand {
  if (score == null) return "none";
  if (score >= 80) return "high";
  if (score >= 60) return "medium-high";
  if (score >= 40) return "medium";
  return "low";
}

interface DistrictPathProps {
  d: string;
  fill: string;
  district: string;
  state: string;
  score: number | null;
  grade: string | null;
  breakdown: ScoreBreakdown | null;
  isDisputed: boolean;
  onHover: (event: MouseEvent, info: DistrictInfo) => void;
  onLeave: () => void;
  onClick: (district: string, state: string) => void;
}

interface DistrictInfo {
  district: string;
  state: string;
  score: number | null;
  grade: string | null;
  breakdown: ScoreBreakdown | null;
}

export const DistrictPath = memo(function DistrictPath({
  d,
  fill,
  district,
  state,
  score,
  grade,
  breakdown,
  isDisputed,
  onHover,
  onLeave,
  onClick,
}: DistrictPathProps) {
  const hover = useCallback((event: MouseEvent) => {
    if (!isDisputed) onHover(event, { district, state, score, grade, breakdown });
  }, [isDisputed, onHover, district, state, score, grade, breakdown]);
  const click = useCallback(() => {
    if (!isDisputed) onClick(district, state);
  }, [isDisputed, onClick, district, state]);

  return (
    <path
      d={d}
      fill={fill}
      stroke="var(--color-surface)"
      strokeWidth={0.3}
      strokeLinejoin="round"
      className={isDisputed ? undefined : "map-district"}
      onMouseMove={hover}
      onMouseLeave={onLeave}
      onClick={click}
    />
  );
});

export interface TooltipData extends DistrictInfo {
  x: number;
  y: number;
  finYear: string | null;
}

function formatFinYear(finYear: string): string {
  const parts = finYear.split("-");
  if (parts.length === 2 && parts[1].length === 4) {
    return `FY ${parts[0]}-${parts[1].slice(2)}`;
  }
  return `FY ${finYear}`;
}

export function Tooltip({ tip }: { tip: TooltipData }) {
  const band = scoreBand(tip.score);
  const breakdown = tip.breakdown;

  return (
    <div className="map-tooltip" style={{ left: tip.x + 14, top: tip.y - 14 }}>
      <p className="map-tooltip__district">{tip.district}</p>
      <p className="map-tooltip__state">{tip.state}</p>
      {tip.score != null ? (
        <>
          <p className="map-tooltip__score" style={{ color: BAND_TEXT[band] }}>
            Score {tip.score.toFixed(1)} · Grade {tip.grade}
          </p>
          {breakdown && (
            <div className="map-tooltip__breakdown">
              {breakdown.delivery_avg != null && (
                <p>Delivery: {breakdown.delivery_avg.toFixed(1)}% · 60% weight</p>
              )}
              {breakdown.finance_avg != null && (
                <p>Utilization: {breakdown.finance_avg.toFixed(1)}% · 30% weight</p>
              )}
              {breakdown.governance_score != null && (
                <p>Governance: {breakdown.governance_score.toFixed(1)}% · 10% weight</p>
              )}
            </div>
          )}
          {tip.finYear && <p className="map-tooltip__period">As of {formatFinYear(tip.finYear)}</p>}
        </>
      ) : (
        <p className="map-tooltip__period">No score data</p>
      )}
    </div>
  );
}

export function Legend() {
  const bands: ScoreBand[] = ["high", "medium-high", "medium", "low", "none"];

  return (
    <div className="map-legend">
      <div className="map-legend__bands">
        {bands.map((band) => (
          <div key={band}>
            <span className="map-legend__swatch" style={{ backgroundColor: BAND_FILL[band] }} />
            <span>{BAND_LABEL[band]}</span>
          </div>
        ))}
      </div>
      <p>Score = 60% delivery + 30% utilization + 10% governance.</p>
    </div>
  );
}

export function MapSkeleton() {
  return <div className="map-placeholder shimmer" aria-label="Loading district map" />;
}

export function MapError({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="map-error">
      <p>Could not load map data</p>
      <span>{message}</span>
      <button type="button" className="button button--secondary" onClick={onRetry}>Retry</button>
    </div>
  );
}

export function MapFrame({
  title,
  meta,
  children,
}: {
  title: string;
  meta?: string;
  children: ReactNode;
}) {
  return (
    <section className="map-frame" aria-labelledby="district-map-title">
      <header className="map-frame__header">
        <h3 id="district-map-title">{title}</h3>
        {meta && <span>{meta}</span>}
      </header>
      {children}
    </section>
  );
}
