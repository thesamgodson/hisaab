"use client";

import { useState } from "react";
import { formatDistrictLabel } from "@/lib/format-place";
import { useHydrated } from "@/lib/use-hydrated";

interface LocatedPin {
  pin_code: string;
  district: string;
  state: string;
  distance_km: number;
}

type LocateState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "matched"; match: LocatedPin }
  | { status: "error"; message: string };

const GEO_ERROR_COPY: Record<number, string> = {
  1: "Location permission was denied. Enter your PIN instead.",
  2: "We couldn’t read your location. Enter your PIN instead.",
  3: "Location took too long. Enter your PIN instead.",
};

function locatedPin(data: unknown): LocatedPin | null {
  if (!data || typeof data !== "object") return null;
  const value = data as Partial<LocatedPin>;
  if (
    typeof value.pin_code !== "string" ||
    typeof value.district !== "string" ||
    typeof value.state !== "string" ||
    typeof value.distance_km !== "number"
  ) return null;
  return value as LocatedPin;
}

export default function PinEntry({
  issue,
}: {
  issue?: string | null;
}) {
  const [pin, setPin] = useState("");
  const [locate, setLocate] = useState<LocateState>({ status: "idle" });
  const hydrated = useHydrated();

  const pinHref = (nextPin: string) => {
    const params = new URLSearchParams({ pin: nextPin });
    if (issue) params.set("issue", issue);
    return `/?${params.toString()}#result`;
  };

  const useLocation = () => {
    if (!("geolocation" in navigator)) {
      setLocate({ status: "error", message: "Location is not available in this browser." });
      return;
    }

    setLocate({ status: "loading" });
    navigator.geolocation.getCurrentPosition(
      async (position) => {
        try {
          const response = await fetch("/api/v1/locate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              lat: position.coords.latitude,
              lng: position.coords.longitude,
            }),
          });
          const data = await response.json();
          if (!response.ok) {
            setLocate({
              status: "error",
              message: data?.error ?? "We couldn’t match this location to a PIN.",
            });
            return;
          }
          const match = locatedPin(data);
          if (!match) {
            setLocate({ status: "error", message: "The location response was incomplete." });
            return;
          }
          setLocate({ status: "matched", match });
        } catch {
          setLocate({ status: "error", message: "The lookup failed. Enter your PIN instead." });
        }
      },
      (error) => setLocate({
        status: "error",
        message: GEO_ERROR_COPY[error.code] ?? "We couldn’t read your location.",
      }),
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 60000 },
    );
  };

  return (
    <div className="pin-lookup">
      <form action="/" method="get" className="pin-form">
        {issue && <input type="hidden" name="issue" value={issue} />}
        <label htmlFor="pin-input">6-digit PIN</label>
        <div className="pin-form__row">
          <input
            id="pin-input"
            name="pin"
            type="text"
            inputMode="numeric"
            autoComplete="postal-code"
            pattern="[0-9]{6}"
            minLength={6}
            maxLength={6}
            required
            value={pin}
            onChange={(event) => {
              setPin(event.target.value.replace(/\D/g, "").slice(0, 6));
            }}
            placeholder="e.g. 110001"
            aria-describedby="pin-help"
          />
          <button type="submit" className="button button--primary">
            See area account
          </button>
        </div>
        <p id="pin-help">Used only to identify a postal district. Not stored.</p>
      </form>

      <p className="pin-alternative-label">Other ways to find your area</p>
      {hydrated ? (
        <button
          type="button"
          className="text-action"
          onClick={useLocation}
          disabled={locate.status === "loading"}
          aria-busy={locate.status === "loading"}
        >
          {locate.status === "loading" ? "Finding your PIN…" : "Use location"}
        </button>
      ) : (
        <span className="text-action hydration-control-placeholder" aria-hidden="true">
          Use location
        </span>
      )}

      <div aria-live="polite">
        {locate.status === "error" && (
          <p className="lookup-message lookup-message--error">{locate.message}</p>
        )}

        {locate.status === "matched" && (
          <div className="location-match">
            <p>
              Nearest match: <strong>PIN {locate.match.pin_code}</strong><br />
              {formatDistrictLabel(locate.match.district, locate.match.state)} · about {locate.match.distance_km} km
            </p>
            <a className="button button--secondary" href={pinHref(locate.match.pin_code)}>
              Use this PIN
            </a>
            <small>GeoNames postal data, CC BY 4.0. Coordinates are not stored.</small>
          </div>
        )}
      </div>
      <details className="lookup-privacy">
        <summary>How location is used</summary>
        <p>
          Device coordinates are sent only to match a nearby PIN. Hisaab does
          not store them.
        </p>
      </details>
    </div>
  );
}
