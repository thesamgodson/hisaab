"use client";

import { useCallback, useState } from "react";
import { fetchBrief } from "@/lib/api";

interface BriefButtonProps {
  district: string;
}

export default function BriefButton({ district }: BriefButtonProps) {
  const [brief, setBrief] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchBrief(district);
      setBrief(data.brief);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate brief");
    } finally {
      setLoading(false);
    }
  }, [district]);

  const handleCopy = useCallback(async () => {
    if (!brief) return;
    try {
      await navigator.clipboard.writeText(brief);
    } catch {
      /* clipboard API may not be available */
    }
  }, [brief]);

  if (brief) {
    return (
      <div
        className="rounded-xl p-5"
        style={{
          background: "var(--surface-tinted)",
          border: "1px solid var(--border)",
        }}
      >
        <div className="flex items-center justify-between mb-3">
          <h3
            className="text-xs font-semibold uppercase tracking-widest"
            style={{ color: "var(--accent)" }}
          >
            Journalist Brief
          </h3>
          <div className="flex gap-2">
            <button
              onClick={handleCopy}
              className="text-xs px-3 py-1 rounded-lg font-medium transition-all duration-150"
              style={{
                background: "var(--surface)",
                color: "var(--accent)",
                border: "1px solid var(--border)",
              }}
            >
              Copy
            </button>
            <button
              onClick={() => setBrief(null)}
              className="text-xs px-3 py-1 rounded-lg font-medium transition-all duration-150"
              style={{
                background: "var(--surface)",
                color: "var(--text-muted)",
                border: "1px solid var(--border)",
              }}
            >
              Close
            </button>
          </div>
        </div>
        <pre
          className="text-sm whitespace-pre-wrap font-sans leading-relaxed"
          style={{ color: "var(--text-secondary)" }}
        >
          {brief}
        </pre>
      </div>
    );
  }

  return (
    <>
      <button
        onClick={handleGenerate}
        disabled={loading}
        className="inline-flex items-center gap-2 px-4 py-2 text-white text-sm font-semibold rounded-xl transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
        style={{ background: "var(--accent-gradient)" }}
        onMouseEnter={(e) => { e.currentTarget.style.opacity = "0.9"; }}
        onMouseLeave={(e) => { e.currentTarget.style.opacity = "1"; }}
      >
        {loading ? (
          <>
            <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
              />
            </svg>
            Generating...
          </>
        ) : (
          <>
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            Generate Brief
          </>
        )}
      </button>
      {error && (
        <span className="text-xs mt-1 block" style={{ color: "oklch(0.55 0.20 25)" }} role="alert">
          {error}
        </span>
      )}
    </>
  );
}
