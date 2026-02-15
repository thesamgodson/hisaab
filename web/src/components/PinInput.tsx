"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function PinInput() {
  const [pin, setPin] = useState("");
  const router = useRouter();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const clean = pin.trim();
    if (/^\d{6}$/.test(clean)) {
      router.push(`/action/${clean}`);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex items-center justify-center gap-3">
      <input
        type="text"
        inputMode="numeric"
        pattern="[0-9]{6}"
        maxLength={6}
        autoFocus
        placeholder="6-digit PIN code"
        value={pin}
        onChange={(e) => setPin(e.target.value.replace(/\D/g, "").slice(0, 6))}
        className="w-44 px-5 py-3 rounded-xl text-center text-lg font-mono tabular-nums tracking-widest"
        style={{
          background: "var(--surface)",
          color: "var(--text-primary)",
          border: "2px solid var(--border)",
          boxShadow: "var(--shadow-sm)",
        }}
      />
      <button
        type="submit"
        disabled={pin.length !== 6}
        className="px-6 py-3 rounded-xl text-sm font-semibold transition-opacity hover:opacity-80 disabled:opacity-40"
        style={{
          background: "var(--accent-gradient, var(--accent))",
          color: "white",
          boxShadow: "var(--shadow-sm)",
        }}
      >
        Check Your Area
      </button>
    </form>
  );
}
