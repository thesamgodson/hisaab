/** Shows data freshness — how recently data was scraped and total records. */

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
  if (days === null) return "bg-gray-300";
  if (days <= 7) return "bg-green-500";
  if (days <= 30) return "bg-yellow-500";
  return "bg-red-500";
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
    <div className="flex items-center gap-2 text-xs text-gray-500">
      <span className={`w-2 h-2 rounded-full ${color}`} />
      <span>{label}</span>
      <span className="text-gray-300">|</span>
      <span>{entry.records.toLocaleString()} records</span>
      <span className="text-gray-300">|</span>
      <span>{entry.source}</span>
    </div>
  );
}
