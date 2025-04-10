"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
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
  const [suggestions, setSuggestions] = useState<string[]>([]);
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
        /* backend not running — degrade gracefully */
      });
  }, []);

  useEffect(() => {
    if (query.length < 2) {
      setSuggestions([]);
      return;
    }
    const upper = query.toUpperCase();
    const filtered = allDistricts
      .filter((d) => d.toUpperCase().includes(upper))
      .slice(0, 8);
    setSuggestions(filtered);
    setSelectedIdx(-1);
  }, [query, allDistricts]);

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
        <div className="relative">
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setShowSuggestions(true);
            }}
            onFocus={() => setShowSuggestions(true)}
            onKeyDown={handleKeyDown}
            autoFocus={autoFocus}
            placeholder="Search any district..."
            className="w-full px-5 py-4 text-lg rounded-2xl border border-gray-200 bg-white shadow-sm
                       placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500
                       focus:border-transparent transition-shadow"
            aria-label="Search districts"
            autoComplete="off"
          />
          <button
            type="submit"
            className="absolute right-3 top-1/2 -translate-y-1/2 px-4 py-2 bg-indigo-600 text-white
                       rounded-xl text-sm font-medium hover:bg-indigo-700 transition-colors
                       focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
          >
            Search
          </button>
        </div>
      </form>

      {showSuggestions && suggestions.length > 0 && (
        <ul
          className="absolute z-10 mt-1 w-full bg-white border border-gray-200 rounded-xl shadow-lg
                     max-h-64 overflow-y-auto"
          role="listbox"
        >
          {suggestions.map((d, i) => (
            <li
              key={d}
              role="option"
              aria-selected={i === selectedIdx}
              className={`px-5 py-3 cursor-pointer text-sm ${
                i === selectedIdx
                  ? "bg-indigo-50 text-indigo-900"
                  : "text-gray-700 hover:bg-gray-50"
              }`}
              onMouseDown={() => navigate(d)}
              onMouseEnter={() => setSelectedIdx(i)}
            >
              {d}
            </li>
          ))}
        </ul>
      )}

      {!query && (
        <div className="mt-4 flex flex-wrap gap-2 justify-center">
          <span className="text-sm text-gray-400">Try:</span>
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              type="button"
              onClick={() => navigate(ex)}
              className="text-sm px-3 py-1 rounded-lg bg-gray-100 text-gray-600
                         hover:bg-indigo-50 hover:text-indigo-700 transition-colors"
            >
              {ex}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
