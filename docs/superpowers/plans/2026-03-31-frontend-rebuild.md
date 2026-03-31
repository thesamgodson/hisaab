# Frontend Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the Hisaab frontend from scratch — 3 pages, each doing one thing correctly, every number sourced.

**Architecture:** Next.js 15 App Router with server components. Home page = PIN input + map. District page = unified scheme cards. Action page = PIN → your area → what's wrong → what to do. All API routes stay, only frontend pages and components are rebuilt.

**Tech Stack:** Next.js 15, React 19, TypeScript, Tailwind CSS. Reuse existing `globals.css` design tokens, `IndiaMap` component, `SourceLink` component, `db.ts`, `geodata.ts`, `scores.ts`.

---

### Task 0: Clean slate — delete old pages and components

**Files:**
- Delete: `web/src/app/page.tsx`
- Delete: `web/src/app/district/[name]/page.tsx`
- Delete: `web/src/app/action/[pin]/page.tsx`
- Delete: `web/src/app/action/[pin]/loading.tsx`
- Delete: `web/src/app/constituency/page.tsx`
- Delete: `web/src/app/constituency/[name]/page.tsx`
- Delete: `web/src/components/ActionCard.tsx`
- Delete: `web/src/components/BriefButton.tsx`
- Delete: `web/src/components/ContactCardDisplay.tsx`
- Delete: `web/src/components/DataQuality.tsx`
- Delete: `web/src/components/DiagnosisCard.tsx`
- Delete: `web/src/components/FreshnessBar.tsx`
- Delete: `web/src/components/MoneyFlowGrid.tsx`
- Delete: `web/src/components/PinInput.tsx`
- Delete: `web/src/components/PinSearchForm.tsx`
- Delete: `web/src/components/RedFlagBadge.tsx`
- Delete: `web/src/components/SchemeCard.tsx`
- Delete: `web/src/components/SearchBar.tsx`
- Delete: `web/src/components/ShareButton.tsx`
- Delete: `web/src/lib/api.ts`
- Delete: `web/src/lib/constituency-types.ts`
- Keep: `web/src/components/IndiaMap.tsx`
- Keep: `web/src/components/SourceLink.tsx`
- Keep: `web/src/lib/db.ts`
- Keep: `web/src/lib/geodata.ts`
- Keep: `web/src/lib/scores.ts`
- Keep: `web/src/lib/types.ts` (for DistrictScore, ScoresResponse)
- Keep: `web/src/app/globals.css`
- Keep: All `web/src/app/api/` routes
- Modify: `web/src/app/layout.tsx`

- [ ] **Step 1: Delete old pages**

```bash
rm web/src/app/page.tsx
rm web/src/app/district/[name]/page.tsx
rm -rf web/src/app/action/[pin]
rm -rf web/src/app/constituency
```

- [ ] **Step 2: Delete old components**

```bash
rm web/src/components/ActionCard.tsx
rm web/src/components/BriefButton.tsx
rm web/src/components/ContactCardDisplay.tsx
rm web/src/components/DataQuality.tsx
rm web/src/components/DiagnosisCard.tsx
rm web/src/components/FreshnessBar.tsx
rm web/src/components/MoneyFlowGrid.tsx
rm web/src/components/PinInput.tsx
rm web/src/components/PinSearchForm.tsx
rm web/src/components/RedFlagBadge.tsx
rm web/src/components/SchemeCard.tsx
rm web/src/components/SearchBar.tsx
rm web/src/components/ShareButton.tsx
```

- [ ] **Step 3: Delete unused lib files**

```bash
rm web/src/lib/api.ts
rm web/src/lib/constituency-types.ts
```

- [ ] **Step 4: Simplify layout.tsx**

Replace `web/src/app/layout.tsx` with:

```tsx
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: { default: "Hisaab — Where did the money go?", template: "%s | Hisaab" },
  description: "Public accountability data for Indian government welfare schemes. Enter your PIN code to see how schemes perform in your area.",
  icons: { icon: "/favicon.svg" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">
        <header className="sticky top-0 z-50 glass border-b" style={{ borderColor: "var(--border-subtle)" }}>
          <nav className="max-w-5xl mx-auto px-4 sm:px-6 h-14 flex items-center">
            <Link href="/" className="flex items-center gap-2 group">
              <span className="text-lg font-bold tracking-tight transition-colors duration-150 group-hover:text-[var(--accent)]" style={{ color: "var(--text-primary)" }}>
                Hisaab
              </span>
              <span className="text-[11px] font-medium px-1.5 py-0.5 rounded-md" style={{ background: "var(--accent-light)", color: "var(--accent)" }}>
                BETA
              </span>
            </Link>
          </nav>
        </header>
        <main className="flex-1">{children}</main>
        <footer className="mt-auto border-t" style={{ borderColor: "var(--border-subtle)" }}>
          <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs" style={{ color: "var(--text-muted)" }}>
            <span>Hisaab — Open-source public accountability infrastructure</span>
            <span>Data from official government portals · Not affiliated with any government body</span>
          </div>
        </footer>
      </body>
    </html>
  );
}
```

- [ ] **Step 5: Create placeholder pages so the app compiles**

Create `web/src/app/page.tsx`:
```tsx
export default function Home() {
  return <div className="max-w-5xl mx-auto px-4 py-12">Building...</div>;
}
```

Create `web/src/app/district/[name]/page.tsx`:
```tsx
export default function DistrictPage() {
  return <div className="max-w-5xl mx-auto px-4 py-12">Building...</div>;
}
```

Create `web/src/app/action/[pin]/page.tsx`:
```tsx
export default function ActionPage() {
  return <div className="max-w-5xl mx-auto px-4 py-12">Building...</div>;
}
```

- [ ] **Step 6: Verify it compiles**

Run: `cd web && npx tsc --noEmit`
Expected: clean (no errors). If IndiaMap imports deleted types, fix imports.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "refactor: clean slate — delete old frontend pages and components"
```

---

### Task 1: Fix action API types — `steps[]` not flat `action` string

**Files:**
- Modify: `web/src/lib/action-types.ts`

The action API returns `{ scheme, steps: [{action, url}] }` but the old `ActionItem` type had `{ scheme, action, portal_url, ... }`. Fix the types to match reality.

- [ ] **Step 1: Rewrite action-types.ts**

Replace `web/src/lib/action-types.ts` with:

```ts
/** TypeScript interfaces for the /api/v1/action/{pin} response. */

export interface DiagnosisItem {
  severity: "high" | "medium" | "low";
  scheme: string;
  summary: string;
  detail: string;
  amount: number | null;
  source_url: string | null;
}

export interface ActionStep {
  action: string;
  url: string | null;
}

export interface ActionItem {
  scheme: string;
  steps: ActionStep[];
}

export interface GrievanceChannel {
  scheme: string;
  level: string;
  portal_name: string;
  portal_url: string;
  phone: string | null;
  description: string;
}

export interface SchemeDataEntry {
  severity: string;
  summary: string;
  detail: string;
  amount: number | null;
  source_url: string | null;
}

export interface MPInfo {
  mp_name: string;
  party: string;
  constituency: string;
  state: string;
  elected_year: number;
  source_url: string;
}

export interface MLAInfo {
  mla_name: string;
  party: string;
  ac_name: string;
  state: string;
  source_url: string;
}

export interface ActionBriefResponse {
  pin: string;
  district: string;
  state: string;
  mp: MPInfo | null;
  mla: MLAInfo | null;
  diagnosis: DiagnosisItem[];
  actions: ActionItem[];
  grievance_channels: GrievanceChannel[];
  scheme_data: Record<string, SchemeDataEntry>;
  generated_at: string;
}
```

- [ ] **Step 2: Verify**

Run: `npx tsc --noEmit`
Expected: clean

- [ ] **Step 3: Commit**

```bash
git add web/src/lib/action-types.ts
git commit -m "fix: action-types match actual API response shape"
```

---

### Task 2: Home page — PIN input + India map

**Files:**
- Create: `web/src/app/page.tsx`
- Create: `web/src/components/PinEntry.tsx`

- [ ] **Step 1: Create PinEntry client component**

Create `web/src/components/PinEntry.tsx`:

```tsx
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
```

- [ ] **Step 2: Create home page**

Replace `web/src/app/page.tsx` with:

```tsx
import { Suspense } from "react";
import PinEntry from "@/components/PinEntry";
import IndiaMap from "@/components/IndiaMap";

export default function Home() {
  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6">
      {/* PIN entry */}
      <section className="py-10 text-center">
        <h1
          className="text-2xl sm:text-3xl font-bold mb-1"
          style={{ color: "var(--text-primary)" }}
        >
          Where did the money go?
        </h1>
        <p className="text-sm mb-8" style={{ color: "var(--text-muted)" }}>
          Enter your PIN code to see how government schemes perform in your area
        </p>
        <PinEntry />
      </section>

      {/* Map */}
      <section className="pb-12">
        <Suspense
          fallback={
            <div
              className="w-full aspect-[4/3] rounded-xl animate-pulse"
              style={{ background: "var(--surface)" }}
            />
          }
        >
          <IndiaMap />
        </Suspense>
      </section>
    </div>
  );
}
```

- [ ] **Step 3: Verify**

Run: `npx tsc --noEmit`
Expected: clean

- [ ] **Step 4: Test in browser**

Run: `npm run dev`
Visit: `http://localhost:3000`
Expected: PIN input centered above India map. Typing 6 digits navigates to `/action/{pin}`.

- [ ] **Step 5: Commit**

```bash
git add web/src/app/page.tsx web/src/components/PinEntry.tsx
git commit -m "feat: home page — PIN input + India map"
```

---

### Task 3: District page — unified scheme cards

**Files:**
- Create: `web/src/app/district/[name]/page.tsx`
- Create: `web/src/components/SchemeRow.tsx`

The district page shows one card per scheme with finance + delivery + source inline. No separate money flow grid. Data comes from the existing `/api/v1/district/{name}/money-flow` API which returns structured rows with `source_url`.

- [ ] **Step 1: Create SchemeRow component**

Create `web/src/components/SchemeRow.tsx`:

```tsx
import SourceLink from "./SourceLink";

interface SchemeRowProps {
  scheme: string;
  finYear: string;
  allocated: number | null;
  released: number | null;
  expended: number | null;
  utilization: number | null;
  target: number | null;
  completed: number | null;
  label: string | null;
  sourceUrl: string | null;
}

function fmtRs(lakhs: number): string {
  if (Math.abs(lakhs) >= 100) return `₹${(lakhs / 100).toFixed(1)} Cr`;
  return `₹${lakhs.toFixed(1)} L`;
}

function fmtNum(n: number): string {
  return n.toLocaleString("en-IN");
}

function pctColor(pct: number | null): string {
  if (pct === null) return "var(--text-muted)";
  if (pct >= 75) return "oklch(0.50 0.17 145)";
  if (pct >= 50) return "oklch(0.55 0.16 65)";
  return "oklch(0.50 0.18 25)";
}

function dotColor(pct: number | null): string {
  if (pct === null) return "var(--border)";
  if (pct >= 75) return "oklch(0.55 0.20 145)";
  if (pct >= 50) return "oklch(0.60 0.20 65)";
  return "oklch(0.55 0.22 25)";
}

export default function SchemeRow({
  scheme,
  finYear,
  allocated,
  released,
  expended,
  utilization,
  target,
  completed,
  label,
  sourceUrl,
}: SchemeRowProps) {
  const hasFinance =
    (allocated != null && allocated > 0) ||
    (released != null && released > 0) ||
    (expended != null && expended > 0);
  const hasDelivery = completed != null && completed > 0;
  const hasTarget = target != null && target > 0;
  const deliveryPct = hasTarget && completed != null ? Math.min(100, (completed / target!) * 100) : null;
  const showUtil = utilization != null && (utilization > 0 || hasFinance);
  const bestPct = deliveryPct ?? (showUtil ? utilization : null);

  return (
    <div
      className="rounded-xl p-4"
      style={{ background: "var(--surface)", border: "1px solid var(--border-subtle)" }}
    >
      {/* Header row */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span
            className="w-2.5 h-2.5 rounded-full flex-shrink-0"
            style={{ background: dotColor(bestPct) }}
          />
          <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
            {scheme}
          </span>
        </div>
        <span className="text-xs tabular-nums" style={{ color: "var(--text-muted)" }}>
          {finYear}
        </span>
      </div>

      {/* Finance line */}
      {hasFinance && (
        <div className="flex flex-wrap gap-x-4 gap-y-0.5 text-xs mb-1" style={{ color: "var(--text-secondary)" }}>
          {allocated != null && allocated > 0 && <span>Allocated {fmtRs(allocated)}</span>}
          {released != null && released > 0 && <span>Released {fmtRs(released)}</span>}
          {expended != null && expended > 0 && <span>Expended {fmtRs(expended)}</span>}
        </div>
      )}

      {/* Delivery line */}
      {hasDelivery && (
        <div className="flex items-center gap-2 text-xs mb-1" style={{ color: "var(--text-secondary)" }}>
          <span>{label ?? "units"}: {fmtNum(completed!)}{hasTarget ? ` / ${fmtNum(target!)}` : ""}</span>
          {deliveryPct != null && (
            <span className="font-semibold tabular-nums" style={{ color: pctColor(deliveryPct) }}>
              {deliveryPct.toFixed(0)}%
            </span>
          )}
        </div>
      )}

      {/* Utilization */}
      {showUtil && (
        <div className="text-xs" style={{ color: "var(--text-secondary)" }}>
          Utilization{" "}
          <span className="font-semibold tabular-nums" style={{ color: pctColor(utilization) }}>
            {utilization!.toFixed(0)}%
          </span>
        </div>
      )}

      {/* No data */}
      {!hasFinance && !hasDelivery && !showUtil && (
        <p className="text-xs italic" style={{ color: "var(--text-muted)" }}>
          No detailed data available
        </p>
      )}

      {/* Source */}
      {sourceUrl && (
        <div className="mt-2 pt-2" style={{ borderTop: "1px solid var(--border-subtle)" }}>
          <SourceLink url={sourceUrl} />
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Create district page**

Replace `web/src/app/district/[name]/page.tsx` with:

```tsx
import Link from "next/link";
import SchemeRow from "@/components/SchemeRow";
import { query, resolveState } from "@/lib/db";

function getBaseUrl(): string {
  if (process.env.VERCEL_URL) return `https://${process.env.VERCEL_URL}`;
  return `http://localhost:${process.env.PORT ?? 3000}`;
}

interface MoneyFlowRow {
  scheme: string;
  fin_year: string;
  allocated_lakhs: number | null;
  released_lakhs: number | null;
  expended_lakhs: number | null;
  utilization_pct: number | null;
  units_target: number | null;
  units_completed: number | null;
  units_label: string | null;
  source_url: string | null;
}

interface ScoreRow {
  score: number | null;
  grade: string | null;
}

export default async function DistrictPage({
  params,
  searchParams,
}: {
  params: Promise<{ name: string }>;
  searchParams: Promise<Record<string, string | undefined>>;
}) {
  const { name } = await params;
  const sp = await searchParams;
  const district = decodeURIComponent(name).toUpperCase().trim().replace(/-/g, " ");

  let state = sp.state ?? null;
  if (!state) state = await resolveState(district);
  if (!state) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-16 text-center">
        <h1 className="text-2xl font-bold mb-2" style={{ color: "var(--text-primary)" }}>
          District not found
        </h1>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>
          No data for &ldquo;{district}&rdquo;. <Link href="/" className="underline" style={{ color: "var(--accent)" }}>Go home</Link>
        </p>
      </div>
    );
  }

  // Fetch money flow data (has source_url)
  const rows = await query<MoneyFlowRow>(
    `SELECT scheme, fin_year, allocated_lakhs, released_lakhs, expended_lakhs,
            utilization_pct, units_target, units_completed, units_label, source_url
     FROM money_flow
     WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?)
     ORDER BY scheme, fin_year`,
    [district, state],
  );

  // Group by scheme — take latest year per scheme
  const byScheme = new Map<string, MoneyFlowRow>();
  for (const row of rows) {
    byScheme.set(row.scheme, row); // last row per scheme = latest fin_year
  }

  // Fetch score
  const scoreRes = await fetch(
    `${getBaseUrl()}/api/v1/scores/${encodeURIComponent(district)}?state=${encodeURIComponent(state)}`,
    { cache: "no-store" },
  ).then((r) => r.ok ? r.json() as Promise<ScoreRow> : null).catch(() => null);

  const schemes = [...byScheme.values()];

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 mb-4 text-xs" style={{ color: "var(--text-muted)" }}>
        <Link href="/" className="hover:underline" style={{ color: "var(--accent)" }}>Home</Link>
        <span>/</span>
        <span>{district}</span>
      </div>

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl sm:text-3xl font-bold" style={{ color: "var(--text-primary)" }}>
          {district}
        </h1>
        <p className="text-sm mt-0.5" style={{ color: "var(--text-secondary)" }}>
          {state}
          {scoreRes?.grade && (
            <span className="ml-2 inline-flex items-center px-2 py-0.5 rounded-md text-xs font-bold" style={{ background: "var(--accent-light)", color: "var(--accent)" }}>
              Score: {scoreRes.score?.toFixed(0)} ({scoreRes.grade})
            </span>
          )}
        </p>
      </div>

      {/* Scheme cards */}
      {schemes.length === 0 ? (
        <p className="text-sm py-8 text-center" style={{ color: "var(--text-muted)" }}>
          No scheme data found for this district.
        </p>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2">
          {schemes.map((s) => (
            <SchemeRow
              key={s.scheme}
              scheme={s.scheme}
              finYear={s.fin_year}
              allocated={s.allocated_lakhs}
              released={s.released_lakhs}
              expended={s.expended_lakhs}
              utilization={s.utilization_pct}
              target={s.units_target}
              completed={s.units_completed}
              label={s.units_label}
              sourceUrl={s.source_url}
            />
          ))}
        </div>
      )}

      {/* Methodology note */}
      <p className="text-xs mt-6" style={{ color: "var(--text-muted)" }}>
        Data from official government portals. Financial figures in Indian Rupees (lakhs).
      </p>
    </div>
  );
}
```

- [ ] **Step 3: Verify**

Run: `npx tsc --noEmit`
Expected: clean

- [ ] **Step 4: Test in browser**

Visit: `http://localhost:3000/district/UJJAIN?state=MADHYA+PRADESH`
Expected: scheme cards with finance, delivery, colored dots, source links.

- [ ] **Step 5: Commit**

```bash
git add web/src/app/district/[name]/page.tsx web/src/components/SchemeRow.tsx
git commit -m "feat: district page — unified scheme cards with sources"
```

---

### Task 4: Action page — PIN → your area → what's wrong → what to do

**Files:**
- Create: `web/src/app/action/[pin]/page.tsx`

This is a server component that calls the existing `/api/v1/action/{pin}` endpoint internally.

- [ ] **Step 1: Create action page**

Create `web/src/app/action/[pin]/page.tsx`:

```tsx
import Link from "next/link";
import SourceLink from "@/components/SourceLink";
import type {
  ActionBriefResponse,
  DiagnosisItem,
  ActionItem,
  GrievanceChannel,
} from "@/lib/action-types";

function getBaseUrl(): string {
  if (process.env.VERCEL_URL) return `https://${process.env.VERCEL_URL}`;
  return `http://localhost:${process.env.PORT ?? 3000}`;
}

function severityColor(s: string): string {
  if (s === "high") return "oklch(0.50 0.22 25)";
  if (s === "medium") return "oklch(0.55 0.18 65)";
  return "oklch(0.50 0.14 145)";
}

function severityBg(s: string): string {
  if (s === "high") return "oklch(0.96 0.03 25)";
  if (s === "medium") return "oklch(0.96 0.03 65)";
  return "oklch(0.96 0.03 145)";
}

export default async function ActionPage({
  params,
}: {
  params: Promise<{ pin: string }>;
}) {
  const { pin } = await params;

  if (!/^\d{6}$/.test(pin)) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-16 text-center">
        <h1 className="text-xl font-bold" style={{ color: "var(--text-primary)" }}>
          Invalid PIN code
        </h1>
        <p className="text-sm mt-2" style={{ color: "var(--text-muted)" }}>
          Enter a 6-digit Indian postal code. <Link href="/" className="underline" style={{ color: "var(--accent)" }}>Go home</Link>
        </p>
      </div>
    );
  }

  const res = await fetch(`${getBaseUrl()}/api/v1/action/${pin}`, {
    cache: "no-store",
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: "Unknown error" }));
    return (
      <div className="max-w-3xl mx-auto px-4 py-16 text-center">
        <h1 className="text-xl font-bold" style={{ color: "var(--text-primary)" }}>
          PIN not found
        </h1>
        <p className="text-sm mt-2" style={{ color: "var(--text-muted)" }}>
          {(err as Record<string, string>).error ?? `No data for PIN ${pin}.`}{" "}
          <Link href="/" className="underline" style={{ color: "var(--accent)" }}>Try another</Link>
        </p>
      </div>
    );
  }

  const brief = (await res.json()) as ActionBriefResponse;

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 mb-4 text-xs" style={{ color: "var(--text-muted)" }}>
        <Link href="/" className="hover:underline" style={{ color: "var(--accent)" }}>Home</Link>
        <span>/</span>
        <span>PIN {pin}</span>
      </div>

      {/* ---- Section 1: Your Area ---- */}
      <div className="mb-8">
        <h1 className="text-2xl sm:text-3xl font-bold" style={{ color: "var(--text-primary)" }}>
          {brief.district}, {brief.state}
        </h1>
        <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-sm" style={{ color: "var(--text-secondary)" }}>
          {brief.mp && (
            <span>
              MP: <strong>{brief.mp.mp_name}</strong>
              <span style={{ color: "var(--text-muted)" }}> · {brief.mp.party}</span>
            </span>
          )}
          {brief.mla && (
            <span>
              MLA ({brief.mla.ac_name}): <strong>{brief.mla.mla_name}</strong>
              <span style={{ color: "var(--text-muted)" }}> · {brief.mla.party}</span>
            </span>
          )}
        </div>
        <p className="text-xs mt-2" style={{ color: "var(--text-muted)" }}>
          Generated {new Date(brief.generated_at).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" })}
        </p>
      </div>

      {/* ---- Section 2: What's Wrong (Diagnosis) ---- */}
      {brief.diagnosis.length > 0 && (
        <div className="mb-8">
          <h2 className="text-xs font-semibold uppercase tracking-widest mb-3" style={{ color: "var(--accent)" }}>
            Issues Found
          </h2>
          <div className="space-y-2">
            {brief.diagnosis.map((d: DiagnosisItem, i: number) => (
              <div
                key={i}
                className="rounded-xl p-4"
                style={{ background: severityBg(d.severity), border: `1px solid ${severityColor(d.severity)}20` }}
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <span className="text-xs font-bold uppercase" style={{ color: severityColor(d.severity) }}>
                      {d.scheme}
                    </span>
                    <p className="text-sm font-medium mt-0.5" style={{ color: "var(--text-primary)" }}>
                      {d.summary}
                    </p>
                    <p className="text-xs mt-0.5" style={{ color: "var(--text-secondary)" }}>
                      {d.detail}
                    </p>
                  </div>
                  <span
                    className="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full flex-shrink-0"
                    style={{ color: severityColor(d.severity), background: `${severityColor(d.severity)}15` }}
                  >
                    {d.severity}
                  </span>
                </div>
                {d.source_url && (
                  <div className="mt-2">
                    <SourceLink url={d.source_url} />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {brief.diagnosis.length === 0 && (
        <div className="mb-8 rounded-xl p-5 text-center" style={{ background: "oklch(0.96 0.03 145)", border: "1px solid oklch(0.90 0.06 145)" }}>
          <p className="text-sm font-medium" style={{ color: "oklch(0.40 0.14 145)" }}>
            No major issues flagged for {brief.district}
          </p>
          <p className="text-xs mt-1" style={{ color: "oklch(0.50 0.08 145)" }}>
            All tracked schemes are performing within normal thresholds.
          </p>
        </div>
      )}

      {/* ---- Section 3: What You Can Do ---- */}
      {brief.actions.length > 0 && (
        <div className="mb-8">
          <h2 className="text-xs font-semibold uppercase tracking-widest mb-3" style={{ color: "var(--accent)" }}>
            What You Can Do
          </h2>
          <div className="space-y-2">
            {brief.actions.map((a: ActionItem, i: number) => (
              <div
                key={i}
                className="rounded-xl p-4"
                style={{ background: "var(--surface)", border: "1px solid var(--border-subtle)" }}
              >
                <span className="text-xs font-bold uppercase tracking-wider" style={{ color: "var(--accent)" }}>
                  {a.scheme}
                </span>
                <ul className="mt-2 space-y-1.5">
                  {a.steps.map((step, j) => (
                    <li key={j} className="flex items-start gap-2 text-sm" style={{ color: "var(--text-primary)" }}>
                      <span className="text-xs font-bold mt-0.5 flex-shrink-0" style={{ color: "var(--accent)" }}>{j + 1}.</span>
                      <span>
                        {step.action}
                        {step.url && (
                          <>
                            {" "}
                            <a
                              href={step.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-flex items-center gap-0.5 text-xs font-medium"
                              style={{ color: "var(--accent)" }}
                            >
                              Visit portal ↗
                            </a>
                          </>
                        )}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ---- Grievance channels ---- */}
      {brief.grievance_channels && brief.grievance_channels.length > 0 && (
        <div className="mb-8">
          <h2 className="text-xs font-semibold uppercase tracking-widest mb-3" style={{ color: "var(--accent)" }}>
            Grievance Portals
          </h2>
          <div className="flex flex-wrap gap-2">
            {brief.grievance_channels.map((g: GrievanceChannel, i: number) => (
              <a
                key={i}
                href={g.portal_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-xs font-medium px-3 py-2 rounded-lg transition-opacity hover:opacity-80"
                style={{ background: "var(--accent-light)", color: "var(--accent)" }}
              >
                {g.portal_name} ↗
              </a>
            ))}
          </div>
        </div>
      )}

      {/* ---- View district data link ---- */}
      <div className="pt-4" style={{ borderTop: "1px solid var(--border-subtle)" }}>
        <Link
          href={`/district/${encodeURIComponent(brief.district)}?state=${encodeURIComponent(brief.state)}`}
          className="text-sm font-medium hover:underline"
          style={{ color: "var(--accent)" }}
        >
          View full district data for {brief.district} →
        </Link>
      </div>

      {/* Footer note */}
      <p className="text-xs mt-6" style={{ color: "var(--text-muted)" }}>
        Data from official government portals. Source links provided per finding.
      </p>
    </div>
  );
}
```

- [ ] **Step 2: Verify**

Run: `npx tsc --noEmit`
Expected: clean

- [ ] **Step 3: Test in browser**

Visit: `http://localhost:3000/action/600088`
Expected: Chennai, Tamil Nadu header with MP/MLA. PM POSHAN diagnosis card with summary/detail/source. Action steps with numbered list and portal links. Grievance portal link. Link to district page.

- [ ] **Step 4: Test PIN with no issues**

Visit: `http://localhost:3000/action/110001`
Expected: Area info. "No major issues flagged" green banner. Still shows grievance portals if available.

- [ ] **Step 5: Commit**

```bash
git add web/src/app/action/[pin]/page.tsx
git commit -m "feat: action page — PIN → diagnosis → actions → grievance portals"
```

---

### Task 5: Verify full flow end-to-end

- [ ] **Step 1: TypeScript check**

Run: `cd web && npx tsc --noEmit`
Expected: zero errors

- [ ] **Step 2: Test all three pages**

```bash
# Home page loads
curl -s http://localhost:3000 | grep "Where did the money go"

# District page loads with data
curl -s "http://localhost:3000/district/UJJAIN?state=MADHYA+PRADESH" | grep "MGNREGA"

# Action page loads with diagnosis
curl -s http://localhost:3000/action/600088 | grep "PM POSHAN"
```

- [ ] **Step 3: Test map click navigation**

In browser: click any district on the map. Should navigate to `/district/{name}?state={state}`.

- [ ] **Step 4: Test PIN auto-navigate**

In browser: type `600088` in PIN input. Should navigate to `/action/600088`.

- [ ] **Step 5: Python tests still pass**

Run: `cd .. && python3 -m pytest tests/ -v`
Expected: 500 passed

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "feat: frontend rebuild complete — 3 pages, every number sourced"
```
