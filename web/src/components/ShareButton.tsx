"use client";

import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ShareButton({ pin, district }: { pin: string; district: string }) {
  const [sharing, setSharing] = useState(false);

  async function handleShare() {
    setSharing(true);
    try {
      const res = await fetch(`${API}/api/v1/action/${pin}/card?format=portrait`);
      if (!res.ok) throw new Error("Failed to fetch card");
      const svgText = await res.text();

      const img = new Image();
      const blob = new Blob([svgText], { type: "image/svg+xml" });
      const url = URL.createObjectURL(blob);

      img.onload = async () => {
        const canvas = document.createElement("canvas");
        canvas.width = 1080;
        canvas.height = 1920;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;
        ctx.drawImage(img, 0, 0, 1080, 1920);
        URL.revokeObjectURL(url);

        canvas.toBlob(async (pngBlob) => {
          if (!pngBlob) return;

          const file = new File([pngBlob], `hisaab-${district.toLowerCase()}.png`, {
            type: "image/png",
          });

          if (navigator.share && navigator.canShare?.({ files: [file] })) {
            await navigator.share({
              title: `Hisaab — ${district}`,
              text: `Check the government scheme performance in ${district}`,
              files: [file],
            });
          } else {
            const a = document.createElement("a");
            a.href = URL.createObjectURL(pngBlob);
            a.download = `hisaab-${district.toLowerCase()}.png`;
            a.click();
            URL.revokeObjectURL(a.href);
          }
          setSharing(false);
        }, "image/png");
      };
      img.src = url;
    } catch {
      setSharing(false);
    }
  }

  return (
    <button
      onClick={handleShare}
      disabled={sharing}
      className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-opacity hover:opacity-80 disabled:opacity-50"
      style={{
        background: "var(--surface)",
        color: "var(--text-primary)",
        boxShadow: "var(--shadow-sm)",
        border: "1px solid var(--border)",
      }}
    >
      <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M4 12v1a2 2 0 002 2h4a2 2 0 002-2v-1M12 5l-4-4-4 4M8 1v10" />
      </svg>
      {sharing ? "Sharing..." : "Share"}
    </button>
  );
}
