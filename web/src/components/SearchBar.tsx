"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { DistrictsResponse } from "@/lib/types";

const EXAMPLES = [
  "VILLUPURAM",
  "CUDDALORE",
  "PATNA",
  "SALEM",
  "GAYA",
  "DARBHANGA",
];

export default function SearchBar({
  autoFocus = false,
}: {
  autoFocus?: boolean;
}) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [allDistricts, setAllDistricts] = useState<string[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedIdx, setSelectedIdx] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    fetch("/api/v1/districts")
      .then((r) => r.json() as Promise<DistrictsResponse>)
      .then((data) => setAllDistricts(data.districts))
      .catch(() => {
        /* backend not running -- degrade gracefully */
      });
  }, []);

  const suggestions = useMemo(
    () =>
      query.length < 2
        ? []
        : allDistricts
            .filter((d) => d.toUpperCase().includes(query.toUpperCase()))
            .slice(0, 8),
    [query, allDistricts],
  );

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (
        wrapperRef.current &&
        !wrapperRef.current.contains(e.target as Node)
      ) {
        setShowSuggestions(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const navigate = useCallback(
    (district: string) => {
      const slug = district.trim().toUpperCase();
      if (!slug) return;
      router.push(`/district/${encodeURIComponent(slug)}`);
    },
    [router],
  );

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIdx((prev) => Math.min(prev + 1, suggestions.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIdx((prev) => Math.max(prev - 1, -1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (selectedIdx >= 0 && suggestions[selectedIdx]) {
        navigate(suggestions[selectedIdx]);
      } else {
        navigate(query);
      }
    } else if (e.key === "Escape") {
      setShowSuggestions(false);
    }
  }

  return (
    <div ref={wrapperRef} className="relative w-full max-w-xl mx-auto">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          navigate(query);
        }}
      >
        <div className="relative group">
          {/* Search icon */}
          <div className="absolute left-4 top-1/2 -translate-y-1/2 pointer-events-none" style={{ color: "var(--text-muted)" }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <circle cx="11" cy="11" r="8" />
              <path d="M21 21l-4.35-4.35" />
            </svg>
          </div>

          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setShowSuggestions(true);
              setSelectedIdx(-1);
            }}
            onFocus={() => setShowSuggestions(true)}
            onKeyDown={handleKeyDown}
            autoFocus={autoFocus}
            placeholder="Search any district..."
            className="w-full pl-12 pr-24 py-4 text-base sm:text-lg rounded-2xl transition-all duration-200"
            style={{
              background: "var(--surface)",
              color: "var(--text-primary)",
              boxShadow: "var(--shadow-md)",
              border: "1px solid var(--border)",
            }}
            onFocusCapture={(e) => {
              const el = e.currentTarget;
              el.style.boxShadow = "var(--shadow-lg)";
              el.style.borderColor = "var(--accent)";
            }}
            onBlurCapture={(e) => {
              const el = e.currentTarget;
              el.style.boxShadow = "var(--shadow-md)";
              el.style.borderColor = "var(--border)";
            }}
            aria-label="Search districts"
            autoComplete="off"
          />

          <button
            type="submit"
            className="absolute right-2.5 top-1/2 -translate-y-1/2 px-5 py-2 text-white text-sm font-semibold rounded-xl transition-all duration-150"
            style={{ background: "var(--accent-gradient)" }}
            onMouseEnter={(e) => {
              e.currentTarget.style.opacity = "0.9";
              e.currentTarget.style.transform = "translateY(-50%) scale(1.02)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.opacity = "1";
              e.currentTarget.style.transform = "translateY(-50%) scale(1)";
            }}
          >
            Search
          </button>
        </div>
      </form>

      {/* Suggestions dropdown */}
      {showSuggestions && suggestions.length > 0 && (
        <ul
          className="absolute z-20 mt-2 w-full rounded-xl overflow-hidden max-h-72 overflow-y-auto"
          style={{
            background: "var(--elevated)",
            boxShadow: "var(--shadow-xl)",
            border: "1px solid var(--border)",
          }}
          role="listbox"
        >
          {suggestions.map((d, i) => (
            <li
              key={d}
              role="option"
              aria-selected={i === selectedIdx}
              className="px-5 py-3 cursor-pointer text-sm transition-colors duration-100"
              style={{
                color: i === selectedIdx ? "var(--accent)" : "var(--text-primary)",
                background: i === selectedIdx ? "var(--accent-light)" : "transparent",
              }}
              onMouseDown={() => navigate(d)}
              onMouseEnter={() => setSelectedIdx(i)}
            >
              {d}
            </li>
          ))}
        </ul>
      )}

      {/* Example chips */}
      {!query && (
        <div className="mt-4 flex flex-wrap gap-2 justify-center">
          <span className="text-sm" style={{ color: "var(--text-muted)" }}>Try:</span>
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              type="button"
              onClick={() => navigate(ex)}
              className="text-sm px-3 py-1 rounded-lg transition-all duration-150"
              style={{
                background: "var(--surface)",
                color: "var(--text-secondary)",
                border: "1px solid var(--border-subtle)",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "var(--accent-light)";
                e.currentTarget.style.color = "var(--accent)";
                e.currentTarget.style.borderColor = "var(--accent-light)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = "var(--surface)";
                e.currentTarget.style.color = "var(--text-secondary)";
                e.currentTarget.style.borderColor = "var(--border-subtle)";
              }}
            >
              {ex}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
