"use client";

import { useMemo, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { titleCasePlace } from "@/lib/format-place";
import { useHydrated } from "@/lib/use-hydrated";

interface DistrictOption {
  district: string;
  state: string;
}

function districtOptions(data: unknown): DistrictOption[] {
  if (!data || typeof data !== "object" || !("items" in data)) return [];
  const items = (data as { items: unknown }).items;
  if (!Array.isArray(items)) return [];
  return items.filter((item): item is DistrictOption =>
    Boolean(
      item &&
      typeof item === "object" &&
      "district" in item &&
      typeof item.district === "string" &&
      "state" in item &&
      typeof item.state === "string",
    ),
  );
}

export default function DistrictPicker({
  issue,
}: {
  issue?: string | null;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [options, setOptions] = useState<DistrictOption[]>([]);
  const [selectedState, setSelectedState] = useState("");
  const [selectedDistrict, setSelectedDistrict] = useState("");
  const [selectionError, setSelectionError] = useState<string | null>(null);
  const hydrated = useHydrated();
  const router = useRouter();
  const states = useMemo(
    () => [...new Set(options.map((option) => option.state))].sort(),
    [options],
  );
  const districts = useMemo(
    () => options.filter((option) => option.state === selectedState),
    [options, selectedState],
  );

  const loadOptions = async () => {
    setStatus("loading");
    try {
      const response = await fetch("/api/v1/districts");
      if (!response.ok) throw new Error("District lookup failed");
      const options = districtOptions(await response.json());
      if (options.length === 0) throw new Error("District list is empty");
      options.sort((left, right) =>
        left.state.localeCompare(right.state) || left.district.localeCompare(right.district),
      );
      setOptions(options);
      setStatus("ready");
    } catch {
      setStatus("error");
    }
  };

  const toggle = () => {
    if (isOpen) {
      setIsOpen(false);
      return;
    }
    setIsOpen(true);
    if (status === "idle") void loadOptions();
  };

  const chooseDistrict = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selectedState || !selectedDistrict) {
      setSelectionError("Choose a state and district.");
      return;
    }
    const params = new URLSearchParams({
      district: selectedDistrict,
      state: selectedState,
    });
    if (issue) params.set("issue", issue);
    router.push(`/?${params.toString()}#result`);
  };

  return (
    <div className="district-picker">
      {hydrated ? (
        <button
          type="button"
          className="text-action"
          onClick={toggle}
          aria-expanded={isOpen}
          aria-controls="district-picker-panel"
        >
          {isOpen ? "Close district search" : "Choose state and district"}
        </button>
      ) : (
        <span className="text-action hydration-control-placeholder" aria-hidden="true">
          Choose state and district
        </span>
      )}

      {isOpen && (
        <div id="district-picker-panel" className="district-picker__panel">
          {status === "loading" && <p role="status">Loading districts…</p>}
          {status === "error" && (
            <div className="lookup-message lookup-message--error" role="alert">
              <p>Districts could not be loaded.</p>
              <button type="button" className="button button--secondary" onClick={loadOptions}>
                Try again
              </button>
            </div>
          )}
          {status === "ready" && (
            <form className="district-form" onSubmit={chooseDistrict}>
              <label htmlFor="state-select">
                State
                <select
                  id="state-select"
                  value={selectedState}
                  onChange={(event) => {
                    setSelectedState(event.target.value);
                    setSelectedDistrict("");
                    setSelectionError(null);
                  }}
                  required
                >
                  <option value="">Choose a state</option>
                  {states.map((state) => (
                    <option key={state} value={state}>{titleCasePlace(state)}</option>
                  ))}
                </select>
              </label>
              <label htmlFor="district-select">
                District
                <select
                  id="district-select"
                  value={selectedDistrict}
                  onChange={(event) => {
                    setSelectedDistrict(event.target.value);
                    setSelectionError(null);
                  }}
                  disabled={!selectedState}
                  required
                >
                  <option value="">Choose a district</option>
                  {districts.map((option) => (
                    <option key={option.district} value={option.district}>
                      {titleCasePlace(option.district)}
                    </option>
                  ))}
                </select>
              </label>
              <p className={selectionError ? "field-message lookup-message--error" : "field-message"}
                role={selectionError ? "alert" : undefined}>{selectionError ?? ""}</p>
              <button type="submit" className="button button--secondary">
                Use this district
              </button>
            </form>
          )}
        </div>
      )}
    </div>
  );
}
