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
  2: "Couldn't read your location — type your PIN instead.",
  3: "Locating took too long — type your PIN instead.",
};

export default function PinEntry() {
  const [pin, setPin] = useState("");
  const [locate, setLocate] = useState<LocateState>({ status: "idle" });
  const [mounted, setMounted] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const seeOwedRef = useRef<HTMLButtonElement>(null);
  const router = useRouter();

  // navigator only exists on the client: reading it during render made the
  // server tree (no button) disagree with the client tree (button), and React
  // discarded the whole hydrated tree on every load.
  useEffect(() => {
    // The one legitimate set-state-in-effect: a mount flag is the only way to
    // defer a client-only branch past hydration.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setMounted(true);
  }, []);

  // Desktop convenience only — an autofocused input on a touch device throws
  // the software keyboard over the hero before the user has read it.
  useEffect(() => {
    if (window.matchMedia("(pointer: fine)").matches) {
      inputRef.current?.focus();
    }
  }, []);

  // The locate button unmounts the moment a match lands, dropping focus to
  // <body> mid-flow; move it to the action the match card is asking for.
  useEffect(() => {
    if (locate.status === "matched") {
      seeOwedRef.current?.focus();
    }
  }, [locate.status]);

  const handleChange = (value: string) => {
    const cleaned = value.replace(/\D/g, "").slice(0, 6);
    setPin(cleaned);
    if (cleaned.length === 6) {
      router.push(`/action/${cleaned}`);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    // Cmd/Ctrl/Alt chords are shortcuts, not input — blocking "v" here broke paste.
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    if (
      !/^\d$/.test(e.key) &&
      !["Backspace", "Delete", "ArrowLeft", "ArrowRight", "Tab"].includes(e.key)
    ) {
      e.preventDefault();
    }
  };

  // One-shot lookup: coordinates go to /api/v1/locate (POST body, never the
  // URL) and are not stored anywhere — the microcopy below promises this.
  const handleUseLocation = () => {
    setLocate({ status: "locating" });
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          const res = await fetch("/api/v1/locate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              lat: pos.coords.latitude,
              lng: pos.coords.longitude,
            }),
          });
          const data = await res.json();
          if (!res.ok) {
            setLocate({
              status: "error",
              message: data?.error ?? "Couldn't match a PIN — type it instead.",
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
      (err) => {
        setLocate({
          status: "error",
          message: GEO_ERROR_COPY[err.code] ?? "Couldn't read your location.",
        });
      },
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 60000 },
    );
  };

  return (
    <div className="w-full max-w-xs mx-auto">
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
        onChange={(e) => handleChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="110001"
        className="w-full text-center text-3xl font-mono tracking-[0.3em] py-4 px-4 rounded-xl transition-all duration-200 placeholder:text-lg placeholder:tracking-normal placeholder:opacity-30"
        style={{
          background: "var(--background)",
          color: "var(--text-primary)",
          border: "2px solid var(--border)",
          boxShadow: "var(--shadow-xs)",
        }}
        onFocus={(e) => {
          e.currentTarget.style.borderColor = "var(--accent)";
          e.currentTarget.style.boxShadow = "0 0 0 3px var(--ring-color)";
        }}
        onBlur={(e) => {
          e.currentTarget.style.borderColor = "var(--border)";
          e.currentTarget.style.boxShadow = "var(--shadow-xs)";
        }}
      />
      <p
        className="text-xs text-center mt-3"
        style={{ color: "var(--text-muted)" }}
      >
        Auto-navigates when you type 6 digits
      </p>

      {mounted && "geolocation" in navigator && locate.status !== "matched" && (
        <>
          <button
            type="button"
            onClick={handleUseLocation}
            disabled={locate.status === "locating"}
            aria-busy={locate.status === "locating"}
            className="w-full mt-4 py-3 px-4 rounded-xl text-sm font-medium transition-all duration-200 disabled:opacity-60"
            style={{
              background: "var(--background)",
              color: "var(--text-primary)",
              border: "2px solid var(--border)",
              boxShadow: "var(--shadow-xs)",
            }}
          >
            {locate.status === "locating"
              ? "Finding your PIN…"
              : "📍 Use my location"}
          </button>
          <p
            className="text-xs text-center mt-2"
            style={{ color: "var(--text-muted)" }}
          >
            Checked once to find your PIN — never stored.
          </p>
        </>
      )}

      <div aria-live="polite">
        {locate.status === "error" && (
          <p
            className="text-xs text-center mt-2"
            style={{ color: "var(--text-primary)" }}
          >
            {locate.message}
          </p>
        )}

        {locate.status === "matched" && (
          <div
            className="mt-4 p-4 rounded-xl text-center"
            style={{
              background: "var(--background)",
              border: "2px solid var(--accent)",
              boxShadow: "var(--shadow-xs)",
            }}
          >
            <p className="text-sm" style={{ color: "var(--text-primary)" }}>
              📍 PIN <span className="font-mono font-semibold">{locate.match.pin_code}</span>
              {" · "}
              {formatDistrictLabel(locate.match.district, locate.match.state)}
            </p>
            <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
              nearest post office area, ~{locate.match.distance_km} km from you
            </p>
            <button
              type="button"
              ref={seeOwedRef}
              onClick={() => router.push(`/action/${locate.match.pin_code}`)}
              className="w-full mt-3 py-3 px-4 rounded-xl text-sm font-semibold transition-all duration-200"
              style={{
                background: "var(--accent)",
                color: "var(--background)",
              }}
            >
              See what&apos;s owed here →
            </button>
            <button
              type="button"
              onClick={() => {
                setLocate({ status: "idle" });
                inputRef.current?.focus();
              }}
              className="w-full mt-2 py-2 text-xs"
              style={{ color: "var(--text-muted)" }}
            >
              Not my area? Type your PIN instead
            </button>
            <p className="text-[10px] mt-2" style={{ color: "var(--text-muted)" }}>
              Location matching via GeoNames postal data (CC BY 4.0)
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
