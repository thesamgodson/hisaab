"use client";

import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { useRouter } from "next/navigation";
import { formatDistrictLabel } from "@/lib/format-place";

interface LocatedPin {
  pin_code: string;
  district: string;
  state: string;
  distance_km: number;
}

type LocateState =
  | { status: "idle" }
  | { status: "locating" }
  | { status: "matched"; match: LocatedPin }
  | { status: "error"; message: string };

const GEO_ERROR_COPY: Record<number, string> = {
  1: "Location permission denied — type your 6-digit PIN instead.",
  2: "Couldn’t read your location — type your PIN instead.",
  3: "Locating took too long — type your PIN instead.",
};

export default function PinEntry() {
  const [pin, setPin] = useState("");
  const [locate, setLocate] = useState<LocateState>({ status: "idle" });
  const inputRef = useRef<HTMLInputElement>(null);
  const openBriefRef = useRef<HTMLButtonElement>(null);
  const router = useRouter();

  useEffect(() => {
    if (window.matchMedia("(pointer: fine)").matches) {
      inputRef.current?.focus();
    }
  }, []);

  useEffect(() => {
    if (locate.status === "matched") {
      openBriefRef.current?.focus();
    }
  }, [locate.status]);

  const handleChange = (value: string) => {
    const cleaned = value.replace(/\D/g, "").slice(0, 6);
    setPin(cleaned);
    if (cleaned.length === 6) {
      router.push(`/action/${cleaned}`);
    }
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.metaKey || event.ctrlKey || event.altKey) return;
    if (
      !/^\d$/.test(event.key) &&
      !["Backspace", "Delete", "ArrowLeft", "ArrowRight", "Tab"].includes(event.key)
    ) {
      event.preventDefault();
    }
  };

  const handleUseLocation = () => {
    if (!("geolocation" in navigator)) {
      setLocate({
        status: "error",
        message: "Location isn’t available in this browser — type your PIN instead.",
      });
      return;
    }

    setLocate({ status: "locating" });
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
              message: data?.error ?? "Couldn’t match a PIN — type it instead.",
            });
            return;
          }
          setLocate({ status: "matched", match: data as LocatedPin });
        } catch {
          setLocate({
            status: "error",
            message: "Network error — type your PIN instead.",
          });
        }
      },
      (error) => {
        setLocate({
          status: "error",
          message: GEO_ERROR_COPY[error.code] ?? "Couldn’t read your location.",
        });
      },
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 60000 },
    );
  };

  return (
    <div className="pin-entry">
      <label htmlFor="pin-input" className="sr-only">
        Enter your 6-digit PIN code
      </label>
      <input
        id="pin-input"
        ref={inputRef}
        type="text"
        inputMode="numeric"
        pattern="[0-9]{6}"
        maxLength={6}
        value={pin}
        onChange={(event) => handleChange(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="110001"
        aria-describedby="pin-hint"
        className="pin-entry__input"
      />
      <p id="pin-hint" className="pin-entry__hint">
        Your brief opens after the sixth digit.
      </p>

      {locate.status !== "matched" && (
        <button
          type="button"
          onClick={handleUseLocation}
          disabled={locate.status === "locating"}
          aria-busy={locate.status === "locating"}
          className="button button--secondary pin-entry__locate"
        >
          <LocationIcon />
          {locate.status === "locating" ? "Finding your PIN…" : "Use my location"}
        </button>
      )}

      <div className="pin-entry__feedback">
        {locate.status === "error" && (
          <p role="status" className="pin-entry__error">
            {locate.message}
          </p>
        )}

        {locate.status === "matched" && (
          <div className="pin-match">
            <p className="pin-match__place">
              PIN <strong>{locate.match.pin_code}</strong> ·{" "}
              {formatDistrictLabel(locate.match.district, locate.match.state)}
            </p>
            <p className="pin-match__distance">
              Nearest post-office area, about {locate.match.distance_km} km away
            </p>
            <button
              type="button"
              ref={openBriefRef}
              onClick={() => router.push(`/action/${locate.match.pin_code}`)}
              className="button button--primary pin-match__open"
            >
              Open this brief
            </button>
            <button
              type="button"
              onClick={() => {
                setLocate({ status: "idle" });
                inputRef.current?.focus();
              }}
              className="pin-match__retry"
            >
              Not your area? Type your PIN
            </button>
            <p className="pin-match__source">
              Location match: GeoNames postal data, CC BY 4.0
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

function LocationIcon() {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="none">
      <path
        d="M12 21s6-5.1 6-11a6 6 0 1 0-12 0c0 5.9 6 11 6 11Z"
        stroke="currentColor"
        strokeWidth="1.8"
      />
      <circle cx="12" cy="10" r="2.25" stroke="currentColor" strokeWidth="1.8" />
    </svg>
  );
}
