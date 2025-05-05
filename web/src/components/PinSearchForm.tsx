"use client";

/**
 * PIN code search form — client component.
 *
 * Handles:
 *  1. 6-digit PIN input with validation
 *  2. API call to /api/v1/pin/{pin_code}
 *  3. Display of constituency results + links to detail pages
 *  4. Fallback: constituency name search if PIN not found
 */

import { useState, useRef, type FormEvent, type KeyboardEvent } from "react";
import Link from "next/link";
import type { PinLookupResponse, ConstituencySearchResponse } from "@/lib/constituency-types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type Status = "idle" | "loading" | "success" | "not_found" | "error";

export default function PinSearchForm() {
  const [pin, setPin] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [pinResult, setPinResult] = useState<PinLookupResponse | null>(null);
  const [searchResults, setSearchResults] = useState<ConstituencySearchResponse | null>(null);
  const [searchMode, setSearchMode] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const handlePinSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const cleaned = pin.replace(/\D/g, "").slice(0, 6);
    if (cleaned.length !== 6) return;

    setStatus("loading");
    setPinResult(null);
    setSearchResults(null);

    try {
      const res = await fetch(`${API_BASE}/api/v1/pin/${cleaned}`);
      if (res.status === 404) {
        setStatus("not_found");
        return;
      }
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = (await res.json()) as PinLookupResponse;
      setPinResult(data);
      setStatus("success");
    } catch {
      setStatus("error");
    }
  };

  const handleNameSearch = async (e: FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setStatus("loading");
    setSearchResults(null);
    setPinResult(null);

    try {
      const res = await fetch(
        `${API_BASE}/api/v1/constituency/search?q=${encodeURIComponent(searchQuery)}`
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = (await res.json()) as ConstituencySearchResponse;
      setSearchResults(data);
      setStatus(data.count > 0 ? "success" : "not_found");
    } catch {
      setStatus("error");
    }
  };

  const handlePinKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    // Allow only digits, backspace, delete, arrows, tab
    if (
      !/^\d$/.test(e.key) &&
      !["Backspace", "Delete", "ArrowLeft", "ArrowRight", "Tab", "Enter"].includes(e.key)
    ) {
      e.preventDefault();
    }
  };

  const reset = () => {
    setStatus("idle");
    setPinResult(null);
    setSearchResults(null);
    setPin("");
    setSearchQuery("");
    setTimeout(() => inputRef.current?.focus(), 50);
  };

  return (
    <div className="w-full">
      {/* Mode toggle */}
      <div className="flex rounded-xl border border-gray-200 mb-5 overflow-hidden">
        <button
          type="button"
          onClick={() => { setSearchMode(false); reset(); }}
          className={`flex-1 py-2.5 text-sm font-medium transition-colors ${
            !searchMode
              ? "bg-indigo-600 text-white"
              : "bg-white text-gray-500 hover:text-gray-700"
          }`}
        >
          PIN Code
        </button>
        <button
          type="button"
          onClick={() => { setSearchMode(true); reset(); }}
          className={`flex-1 py-2.5 text-sm font-medium transition-colors ${
            searchMode
              ? "bg-indigo-600 text-white"
              : "bg-white text-gray-500 hover:text-gray-700"
          }`}
        >
          Search by Name
        </button>
      </div>

      {/* PIN form */}
      {!searchMode && (
        <form onSubmit={handlePinSubmit} className="space-y-4">
          <div>
            <input
              ref={inputRef}
              type="text"
              inputMode="numeric"
              pattern="[0-9]{6}"
              maxLength={6}
              value={pin}
              onChange={(e) => setPin(e.target.value.replace(/\D/g, "").slice(0, 6))}
              onKeyDown={handlePinKeyDown}
              placeholder="Enter 6-digit PIN code"
              autoFocus
              className="w-full text-center text-3xl font-mono tracking-[0.3em] py-5 px-4 rounded-2xl border-2 border-gray-200 focus:border-indigo-500 focus:ring-0 focus:outline-none transition-colors placeholder:text-gray-300 placeholder:tracking-normal placeholder:text-lg"
            />
          </div>
          <button
            type="submit"
            disabled={pin.length !== 6 || status === "loading"}
            className="w-full py-4 rounded-2xl bg-indigo-600 text-white text-base font-semibold hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {status === "loading" ? "Looking up…" : "Find My Constituency"}
          </button>
        </form>
      )}

      {/* Name search form */}
      {searchMode && (
        <form onSubmit={handleNameSearch} className="space-y-4">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="e.g. Varanasi, Rajnath Singh, Lucknow"
            autoFocus
            className="w-full py-4 px-5 rounded-2xl border-2 border-gray-200 focus:border-indigo-500 focus:ring-0 focus:outline-none transition-colors text-base placeholder:text-gray-300"
          />
          <button
            type="submit"
            disabled={!searchQuery.trim() || status === "loading"}
            className="w-full py-4 rounded-2xl bg-indigo-600 text-white text-base font-semibold hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {status === "loading" ? "Searching…" : "Search"}
          </button>
        </form>
      )}

      {/* Results */}
      {status === "not_found" && (
        <div className="mt-6 rounded-xl border border-amber-100 bg-amber-50 p-4 text-center">
          <p className="text-sm text-amber-800 font-medium mb-1">
            {searchMode ? "No constituencies found." : "PIN code not found."}
          </p>
          <p className="text-xs text-amber-600">
            {searchMode
              ? "Try a different spelling or switch to PIN code lookup."
              : "The PIN database is growing. Try searching by constituency name instead."}
          </p>
          {!searchMode && (
            <button
              type="button"
              onClick={() => { setSearchMode(true); reset(); }}
              className="mt-3 text-xs text-indigo-600 underline"
            >
              Search by constituency name →
            </button>
          )}
        </div>
      )}

      {status === "error" && (
        <div className="mt-6 rounded-xl border border-red-100 bg-red-50 p-4 text-center">
          <p className="text-sm text-red-700">Could not reach the server. Please try again.</p>
        </div>
      )}

      {status === "success" && pinResult && (
        <PinResultCard result={pinResult} onReset={reset} />
      )}

      {status === "success" && searchResults && (
        <SearchResultList results={searchResults} onReset={reset} />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function PinResultCard({
  result,
  onReset,
}: {
  result: PinLookupResponse;
  onReset: () => void;
}) {
  return (
    <div className="mt-6 space-y-4">
      <div className="rounded-2xl border border-gray-100 bg-white shadow-sm p-5">
        <div className="flex items-start justify-between mb-1">
          <p className="text-xs text-gray-400 uppercase tracking-wide">PIN {result.pin_code}</p>
          <button
            type="button"
            onClick={onReset}
            className="text-xs text-gray-400 hover:text-gray-600"
          >
            ✕ Clear
          </button>
        </div>
        <p className="text-lg font-bold text-gray-900">{result.district}</p>
        <p className="text-sm text-gray-500">{result.state}</p>
        {result.office_name && (
          <p className="text-xs text-gray-400 mt-1">{result.office_name}</p>
        )}
      </div>

      {result.constituencies.length === 0 ? (
        <p className="text-sm text-gray-400 text-center py-4">
          No constituency mapping for this district yet.
        </p>
      ) : (
        result.constituencies.map((c) => (
          <ConstituencyCard
            key={c.constituency}
            name={c.constituency}
            mp={c.mp}
          />
        ))
      )}
    </div>
  );
}

function SearchResultList({
  results,
  onReset,
}: {
  results: ConstituencySearchResponse;
  onReset: () => void;
}) {
  return (
    <div className="mt-6 space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs text-gray-400 uppercase tracking-wide">
          {results.count} result{results.count !== 1 ? "s" : ""} for &ldquo;{results.query}&rdquo;
        </p>
        <button
          type="button"
          onClick={onReset}
          className="text-xs text-gray-400 hover:text-gray-600"
        >
          ✕ Clear
        </button>
      </div>
      {results.results.map((r) => (
        <Link
          key={r.constituency}
          href={`/constituency/${encodeURIComponent(r.constituency)}`}
          className="block rounded-2xl border border-gray-100 bg-white shadow-sm p-4 hover:border-indigo-200 hover:shadow-md transition-all group"
        >
          <p className="font-semibold text-gray-900 group-hover:text-indigo-700">
            {r.constituency}
          </p>
          <p className="text-sm text-gray-500 mt-0.5">
            {r.mp_name}
            {r.party && (
              <span className="text-gray-400"> · {r.party}</span>
            )}
          </p>
          <p className="text-xs text-gray-400 mt-0.5">{r.state}</p>
        </Link>
      ))}
    </div>
  );
}

function ConstituencyCard({
  name,
  mp,
}: {
  name: string;
  mp: PinLookupResponse["constituencies"][number]["mp"];
}) {
  return (
    <Link
      href={`/constituency/${encodeURIComponent(name)}`}
      className="block rounded-2xl border border-gray-100 bg-white shadow-sm p-5 hover:border-indigo-200 hover:shadow-md transition-all group"
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Lok Sabha Constituency</p>
          <p className="text-lg font-bold text-gray-900 group-hover:text-indigo-700">
            {name}
          </p>
          {mp && (
            <>
              <p className="text-sm font-medium text-gray-700 mt-1">{mp.mp_name}</p>
              <p className="text-xs text-gray-400 mt-0.5">
                {mp.party} · Elected {mp.elected_year}
              </p>
            </>
          )}
          {!mp && (
            <p className="text-xs text-gray-400 mt-1">MP data not yet loaded</p>
          )}
        </div>
        <span className="text-indigo-500 text-xl group-hover:translate-x-1 transition-transform">→</span>
      </div>
      <p className="text-xs text-indigo-600 mt-3 font-medium">View Report Card →</p>
    </Link>
  );
}
