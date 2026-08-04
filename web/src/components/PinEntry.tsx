"use client";

import { useState, type KeyboardEvent } from "react";
import { useRouter } from "next/navigation";

export default function PinEntry() {
  const [pin, setPin] = useState("");
  const router = useRouter();

  const handleChange = (value: string) => {
    const cleaned = value.replace(/\D/g, "").slice(0, 6);
    setPin(cleaned);
    if (cleaned.length === 6) {
      router.push(`/action/${cleaned}`);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (
      !/^\d$/.test(e.key) &&
      !["Backspace", "Delete", "ArrowLeft", "ArrowRight", "Tab"].includes(e.key)
    ) {
      e.preventDefault();
    }
  };

  return (
    <div className="w-full max-w-xs mx-auto">
      <label htmlFor="pin-input" className="sr-only">
        Enter your 6-digit PIN code
      </label>
      <input
        id="pin-input"
        type="text"
        inputMode="numeric"
        pattern="[0-9]{6}"
        maxLength={6}
        value={pin}
        onChange={(e) => handleChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="110001"
        autoFocus
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
    </div>
  );
}
