"use client";

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
      <div
        className="flex rounded-xl mb-5 overflow-hidden"
        style={{ border: "1px solid var(--border)" }}
      >
        <button
          type="button"
          onClick={() => { setSearchMode(false); reset(); }}
          className="flex-1 py-2.5 text-sm font-semibold transition-all duration-150"
          style={{
            background: !searchMode ? "var(--accent-gradient)" : "var(--surface)",
            color: !searchMode ? "white" : "var(--text-muted)",
          }}
        >
          PIN Code
        </button>
        <button
          type="button"
          onClick={() => { setSearchMode(true); reset(); }}
          className="flex-1 py-2.5 text-sm font-semibold transition-all duration-150"
          style={{
            background: searchMode ? "var(--accent-gradient)" : "var(--surface)",
            color: searchMode ? "white" : "var(--text-muted)",
          }}
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
              className="w-full text-center text-3xl font-mono tracking-[0.3em] py-5 px-4 rounded-xl transition-all duration-200 placeholder:tracking-normal placeholder:text-lg"
              style={{
                background: "var(--surface)",
                color: "var(--text-primary)",
                border: "2px solid var(--border)",
              }}
              onFocus={(e) => { e.currentTarget.style.borderColor = "var(--accent)"; }}
              onBlur={(e) => { e.currentTarget.style.borderColor = "var(--border)"; }}
            />
          </div>
          <button
            type="submit"
            disabled={pin.length !== 6 || status === "loading"}
            className="w-full py-4 rounded-xl text-white text-base font-semibold transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ background: "var(--accent-gradient)" }}
          >
            {status === "loading" ? "Looking up..." : "Find My Constituency"}
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
            className="w-full py-4 px-5 rounded-xl text-base transition-all duration-200"
            style={{
              background: "var(--surface)",
              color: "var(--text-primary)",
              border: "2px solid var(--border)",
            }}
            onFocus={(e) => { e.currentTarget.style.borderColor = "var(--accent)"; }}
            onBlur={(e) => { e.currentTarget.style.borderColor = "var(--border)"; }}
          />
          <button
            type="submit"
            disabled={!searchQuery.trim() || status === "loading"}
            className="w-full py-4 rounded-xl text-white text-base font-semibold transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ background: "var(--accent-gradient)" }}
          >
            {status === "loading" ? "Searching..." : "Search"}
          </button>
        </form>
      )}

      {/* Results */}
      {status === "not_found" && (
        <div
          className="mt-6 rounded-xl p-4 text-center"
          style={{
            background: "oklch(0.96 0.03 80)",
            border: "1px solid oklch(0.90 0.06 80)",
          }}
        >
          <p className="text-sm font-medium mb-1" style={{ color: "oklch(0.40 0.12 80)" }}>
            {searchMode ? "No constituencies found." : "PIN code not found."}
          </p>
          <p className="text-xs" style={{ color: "oklch(0.50 0.08 80)" }}>
            {searchMode
              ? "Try a different spelling or switch to PIN code lookup."
              : "The PIN database is growing. Try searching by constituency name instead."}
          </p>
          {!searchMode && (
            <button
              type="button"
              onClick={() => { setSearchMode(true); reset(); }}
              className="mt-3 text-xs underline"
              style={{ color: "var(--accent)" }}
            >
              Search by constituency name
            </button>
          )}
        </div>
      )}

      {status === "error" && (
        <div
          className="mt-6 rounded-xl p-4 text-center"
          style={{
            background: "oklch(0.96 0.03 25)",
            border: "1px solid oklch(0.90 0.06 25)",
          }}
        >
          <p className="text-sm" style={{ color: "oklch(0.45 0.16 25)" }}>
            Could not reach the server. Please try again.
          </p>
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

function PinResultCard({
  result,
  onReset,
}: {
  result: PinLookupResponse;
  onReset: () => void;
}) {
  return (
    <div className="mt-6 space-y-4">
      <div
        className="rounded-xl p-5"
        style={{
          background: "var(--surface)",
          boxShadow: "var(--shadow-md)",
          border: "1px solid var(--border-subtle)",
        }}
      >
        <div className="flex items-start justify-between mb-1">
          <p className="text-xs uppercase tracking-widest font-medium" style={{ color: "var(--text-muted)" }}>
            PIN {result.pin_code}
          </p>
          <button
            type="button"
            onClick={onReset}
            className="text-xs transition-colors duration-150"
            style={{ color: "var(--text-muted)" }}
          >
            Clear
          </button>
        </div>
        <p className="text-lg font-bold" style={{ color: "var(--text-primary)" }}>
          {result.district}
        </p>
        <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
          {result.state}
        </p>
        {result.office_name && (
          <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
            {result.office_name}
          </p>
        )}
      </div>

      {result.constituencies.length === 0 ? (
        <p className="text-sm text-center py-4" style={{ color: "var(--text-muted)" }}>
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
        <p className="text-xs uppercase tracking-widest font-medium" style={{ color: "var(--text-muted)" }}>
          {results.count} result{results.count !== 1 ? "s" : ""} for &ldquo;{results.query}&rdquo;
        </p>
        <button
          type="button"
          onClick={onReset}
          className="text-xs transition-colors duration-150"
          style={{ color: "var(--text-muted)" }}
        >
          Clear
        </button>
      </div>
      {results.results.map((r) => (
        <Link
          key={r.constituency}
          href={`/constituency/${encodeURIComponent(r.constituency)}`}
          className="block rounded-xl p-4 card-hover group transition-colors duration-150"
          style={{
            background: "var(--surface)",
            boxShadow: "var(--shadow-sm)",
            border: "1px solid var(--border-subtle)",
          }}
        >
          <p
            className="font-semibold transition-colors duration-150 group-hover:text-[var(--accent)]"
            style={{ color: "var(--text-primary)" }}
          >
            {r.constituency}
          </p>
          <p className="text-sm mt-0.5" style={{ color: "var(--text-secondary)" }}>
            {r.mp_name}
            {r.party && (
              <span style={{ color: "var(--text-muted)" }}> \u00B7 {r.party}</span>
            )}
          </p>
          <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
            {r.state}
          </p>
        </Link>
      ))}
    </div>
  );
}

function ConstituencyCard({ name, mp }: { name: string; mp: PinLookupResponse["constituencies"][number]["mp"] }) {
  return (
    <Link href={`/constituency/${encodeURIComponent(name)}`} className="block rounded-xl p-5 card-hover group transition-colors duration-150" style={{ background: "var(--surface)", boxShadow: "var(--shadow-sm)", border: "1px solid var(--border-subtle)" }}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs uppercase tracking-widest font-medium mb-1" style={{ color: "var(--text-muted)" }}>Lok Sabha Constituency</p>
          <p className="text-lg font-bold transition-colors duration-150 group-hover:text-[var(--accent)]" style={{ color: "var(--text-primary)" }}>{name}</p>
          {mp ? (
            <>
              <p className="text-sm font-medium mt-1" style={{ color: "var(--text-secondary)" }}>{mp.mp_name}</p>
              <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>{mp.party} {"\u00B7"} Elected {mp.elected_year}</p>
            </>
          ) : (
            <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>MP data not yet loaded</p>
          )}
        </div>
        <span className="text-xl transition-transform duration-200 group-hover:translate-x-1" style={{ color: "var(--accent)" }}>&rarr;</span>
      </div>
      <p className="text-xs mt-3 font-semibold" style={{ color: "var(--accent)" }}>View Report Card &rarr;</p>
    </Link>
  );
}
