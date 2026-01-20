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
    <form onSubmit={handleSubmit} className="flex items-center justify-center gap-2">
      <input
        type="text"
        inputMode="numeric"
        pattern="[0-9]{6}"
        maxLength={6}
        placeholder="Enter PIN code"
        value={pin}
        onChange={(e) => setPin(e.target.value.replace(/\D/g, "").slice(0, 6))}
        className="w-36 px-4 py-2 rounded-lg text-center text-sm font-mono tabular-nums"
        style={{
          background: "var(--surface)",
          color: "var(--text-primary)",
          border: "1px solid var(--border)",
        }}
      />
      <button
        type="submit"
        disabled={pin.length !== 6}
        className="px-4 py-2 rounded-lg text-sm font-semibold transition-opacity hover:opacity-80 disabled:opacity-40"
        style={{
          background: "var(--accent-gradient, var(--accent))",
          color: "white",
        }}
      >
        Go
      </button>
    </form>
  );
}
