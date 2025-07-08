/** Shows data freshness -- how recently data was scraped and total records. */

import type { FreshnessEntry } from "@/lib/types";

interface FreshnessBarProps {
  entry: FreshnessEntry;
}

function daysSince(dateStr: string | null): number | null {
  if (!dateStr) return null;
  const scraped = new Date(dateStr);
  const now = new Date();
  return Math.floor(
    (now.getTime() - scraped.getTime()) / (1000 * 60 * 60 * 24),
  );
}

function freshnessColor(days: number | null): string {
  if (days === null) return "oklch(0.80 0 0)";
  if (days <= 7) return "oklch(0.55 0.17 145)";
  if (days <= 30) return "oklch(0.60 0.16 80)";
  return "oklch(0.55 0.18 25)";
}

export default function FreshnessBar({ entry }: FreshnessBarProps) {
  const days = daysSince(entry.latest_scraped);
  const color = freshnessColor(days);
  const label =
    days === null
      ? "Never scraped"
      : days === 0
        ? "Today"
        : days === 1
          ? "1 day ago"
          : `${days} days ago`;

  return (
    <div className="flex items-center gap-2 text-xs" style={{ color: "var(--text-muted)" }}>
      <span
        className="w-2 h-2 rounded-full"
        style={{ backgroundColor: color }}
      />
      <span>{label}</span>
      <span style={{ color: "var(--border)" }}>|</span>
      <span>{entry.records.toLocaleString()} records</span>
      <span style={{ color: "var(--border)" }}>|</span>
      <span>{entry.source}</span>
    </div>
  );
}
