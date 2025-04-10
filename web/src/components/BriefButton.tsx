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
      <div className="rounded-2xl border border-indigo-100 bg-indigo-50/50 p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-indigo-800">
            Journalist Brief
          </h3>
          <div className="flex gap-2">
            <button
              onClick={handleCopy}
              className="text-xs px-3 py-1 rounded-lg bg-white text-indigo-600 border border-indigo-200
                         hover:bg-indigo-50 transition-colors"
            >
              Copy
            </button>
            <button
              onClick={() => setBrief(null)}
              className="text-xs px-3 py-1 rounded-lg bg-white text-gray-500 border border-gray-200
                         hover:bg-gray-50 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
        <pre className="text-sm text-gray-700 whitespace-pre-wrap font-sans leading-relaxed">
          {brief}
        </pre>
      </div>
    );
  }

  return (
    <button
      onClick={handleGenerate}
      disabled={loading}
      className="inline-flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white text-sm font-medium
                 rounded-xl hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed
                 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
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
      {error && <span className="text-red-200 text-xs ml-2">{error}</span>}
    </button>
  );
}
