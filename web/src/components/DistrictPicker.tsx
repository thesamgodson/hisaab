"use client";

import { useState, type ChangeEvent } from "react";
import { useRouter } from "next/navigation";
import { titleCasePlace } from "@/lib/format-place";

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

export default function DistrictPicker() {
  const [isOpen, setIsOpen] = useState(false);
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [options, setOptions] = useState<DistrictOption[]>([]);
  const router = useRouter();

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

  const chooseDistrict = (event: ChangeEvent<HTMLSelectElement>) => {
    const [district, state] = event.target.value.split("|");
    if (!district || !state) return;
    router.push(
      `/?district=${encodeURIComponent(district)}&state=${encodeURIComponent(state)}#result`,
    );
  };

  return (
    <div className="district-picker">
      <button
        type="button"
        className="text-action"
        onClick={toggle}
        aria-expanded={isOpen}
        aria-controls="district-picker-panel"
      >
        {isOpen ? "Close district search" : "Browse by district"}
      </button>

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
            <label>
              District
              <select defaultValue="" onChange={chooseDistrict}>
                <option value="" disabled>Choose a district</option>
                {options.map((option) => (
                  <option
                    key={`${option.district}|${option.state}`}
                    value={`${option.district}|${option.state}`}
                  >
                    {titleCasePlace(option.district)}, {titleCasePlace(option.state)}
                  </option>
                ))}
              </select>
            </label>
          )}
        </div>
      )}
    </div>
  );
}
