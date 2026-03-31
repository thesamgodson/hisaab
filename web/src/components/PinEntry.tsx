"use client";

import { useState, useRef, type KeyboardEvent } from "react";
import { useRouter } from "next/navigation";

export default function PinEntry() {
  const [pin, setPin] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);
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
    <div className="w-full max-w-sm mx-auto">
      <label
        htmlFor="pin-input"
        className="block text-sm font-medium mb-2 text-center"
        style={{ color: "var(--text-secondary)" }}
      >
        Enter your 6-digit PIN code
      </label>
      <input
        ref={inputRef}
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
        className="w-full text-center text-3xl font-mono tracking-[0.3em] py-4 px-4 rounded-xl transition-all duration-200 placeholder:text-lg placeholder:tracking-normal"
        style={{
          background: "var(--surface)",
          color: "var(--text-primary)",
          border: "2px solid var(--border)",
        }}
        onFocus={(e) => { e.currentTarget.style.borderColor = "var(--accent)"; }}
        onBlur={(e) => { e.currentTarget.style.borderColor = "var(--border)"; }}
      />
      <p className="text-xs text-center mt-2" style={{ color: "var(--text-muted)" }}>
        Auto-navigates when you type 6 digits
      </p>
    </div>
  );
}
