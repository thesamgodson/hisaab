/**
 * Constituency entry page -- PIN code lookup.
 *
 * Mobile-optimised: large PIN input, clean feedback, links to
 * constituency detail pages. This is the WhatsApp-shared entry point.
 */

import type { Metadata } from "next";
import Link from "next/link";
import PinSearchForm from "@/components/PinSearchForm";

export const metadata: Metadata = {
  title: "Find Your MP's Report Card -- Hisaab",
  description:
    "Enter your PIN code to see how your MP's constituency is performing across 11 government welfare schemes.",
  openGraph: {
    title: "Find Your MP's Report Card -- Hisaab",
    description:
      "Enter your PIN code to see how your MP's constituency is performing across 11 government welfare schemes.",
    siteName: "Hisaab",
  },
};

export default function ConstituencyPage() {
  return (
    <main className="flex-1 flex flex-col items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        <div className="text-center mb-10 animate-fade-in-up">
          {/* Icon */}
          <div
            className="w-16 h-16 mx-auto mb-5 rounded-2xl flex items-center justify-center"
            style={{ background: "var(--accent-light)" }}
          >
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" style={{ color: "var(--accent)" }} aria-hidden="true">
              <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
              <path d="M22 21v-2a4 4 0 0 0-3-3.87" />
              <path d="M16 3.13a4 4 0 0 1 0 7.75" />
            </svg>
          </div>
          <h1
            className="text-3xl sm:text-4xl font-bold mb-3"
            style={{ color: "var(--text-primary)" }}
          >
            Your MP&apos;s Report Card
          </h1>
          <p className="text-base leading-relaxed" style={{ color: "var(--text-secondary)" }}>
            Enter your 6-digit PIN code to see how 11 government welfare
            schemes are performing in your constituency.
          </p>
        </div>

        {/* PIN input form -- client component */}
        <div className="animate-fade-in-up stagger-2">
          <PinSearchForm />
        </div>

        <p
          className="text-center text-xs mt-6 animate-fade-in-up stagger-3"
          style={{ color: "var(--text-muted)" }}
        >
          Data from official government portals. Updated periodically.
        </p>
      </div>

      {/* Sample constituencies */}
      <div className="mt-16 w-full max-w-md animate-fade-in-up stagger-4">
        <p
          className="text-xs font-semibold uppercase tracking-widest mb-4 text-center"
          style={{ color: "var(--text-muted)" }}
        >
          Sample constituencies
        </p>
        <div className="grid grid-cols-2 gap-2">
          {[
            { name: "VARANASI", state: "UP" },
            { name: "LUCKNOW", state: "UP" },
            { name: "PATNA SAHIB", state: "Bihar" },
            { name: "MUZAFFARPUR", state: "Bihar" },
          ].map((c) => (
            <Link
              key={c.name}
              href={`/constituency/${encodeURIComponent(c.name)}`}
              className="flex items-center justify-between px-4 py-3 rounded-xl card-hover group transition-colors duration-150"
              style={{
                background: "var(--surface)",
                boxShadow: "var(--shadow-sm)",
                border: "1px solid var(--border-subtle)",
              }}
            >
              <span
                className="text-sm font-medium transition-colors duration-150 group-hover:text-[var(--accent)]"
                style={{ color: "var(--text-primary)" }}
              >
                {c.name}
              </span>
              <span className="text-xs" style={{ color: "var(--text-muted)" }}>
                {c.state}
              </span>
            </Link>
          ))}
        </div>
      </div>
    </main>
  );
}
