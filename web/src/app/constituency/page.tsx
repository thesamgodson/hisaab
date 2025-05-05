/**
 * Constituency entry page — PIN code lookup.
 *
 * Mobile-optimised: large PIN input, clean feedback, links to
 * constituency detail pages.  This is the WhatsApp-shared entry point.
 */

import type { Metadata } from "next";
import Link from "next/link";
import PinSearchForm from "@/components/PinSearchForm";

export const metadata: Metadata = {
  title: "Find Your MP's Report Card — Hisaab",
  description:
    "Enter your PIN code to see how your MP's constituency is performing across 11 government welfare schemes.",
  openGraph: {
    title: "Find Your MP's Report Card — Hisaab",
    description:
      "Enter your PIN code to see how your MP's constituency is performing across 11 government welfare schemes.",
    siteName: "Hisaab",
  },
};

export default function ConstituencyPage() {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Nav */}
      <nav className="border-b border-gray-100 bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-lg mx-auto px-4 py-3 flex items-center justify-between">
          <Link
            href="/"
            className="text-lg font-bold text-gray-900 hover:text-indigo-600 transition-colors"
          >
            Hisaab
          </Link>
          <span className="text-sm text-gray-400">MP Report Cards</span>
        </div>
      </nav>

      {/* Hero */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 py-12">
        <div className="w-full max-w-md">
          <div className="text-center mb-10">
            <div className="text-5xl mb-4">🗳️</div>
            <h1 className="text-3xl font-bold text-gray-900 mb-3">
              Your MP&apos;s Report Card
            </h1>
            <p className="text-gray-500 text-base leading-relaxed">
              Enter your 6-digit PIN code to see how 11 government welfare
              schemes are performing in your constituency.
            </p>
          </div>

          {/* PIN input form — client component */}
          <PinSearchForm />

          <p className="text-center text-xs text-gray-400 mt-6">
            Data from official government portals. Updated periodically.
          </p>
        </div>

        {/* Sample constituencies */}
        <div className="mt-16 w-full max-w-md">
          <p className="text-xs font-medium text-gray-400 uppercase tracking-widest mb-4 text-center">
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
                className="flex items-center justify-between px-4 py-3 rounded-xl bg-white border border-gray-100 shadow-sm hover:border-indigo-200 hover:shadow-md transition-all group"
              >
                <span className="text-sm font-medium text-gray-800 group-hover:text-indigo-700">
                  {c.name}
                </span>
                <span className="text-xs text-gray-400">{c.state}</span>
              </Link>
            ))}
          </div>
        </div>
      </main>

      <footer className="border-t border-gray-100 py-6">
        <p className="text-center text-xs text-gray-400">
          Hisaab is open-source public infrastructure. Not affiliated with any
          government body.
        </p>
      </footer>
    </div>
  );
}
