import { notFound } from "next/navigation";
import { Suspense } from "react";
import Link from "next/link";
import ActionCard from "@/components/ActionCard";
import ContactCardDisplay from "@/components/ContactCardDisplay";
import DiagnosisCard from "@/components/DiagnosisCard";
import type { ActionBriefResponse } from "@/lib/action-types";
import ActionBriefLoading from "./loading";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchActionBrief(pin: string): Promise<ActionBriefResponse | null> {
  const res = await fetch(
    `${API}/api/v1/action/${encodeURIComponent(pin)}`,
    { cache: "no-store" },
  );
  if (res.status === 404) return null;
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return (await res.json()) as ActionBriefResponse;
}

async function ActionBriefContent({ pin }: { pin: string }) {
  const brief = await fetchActionBrief(pin);

  if (!brief) {
    notFound();
  }

  const hasDiagnosis = brief.diagnosis.length > 0;

  return (
    <>
      {/* Page header */}
      <div className="mb-10 animate-fade-in-up">
        {/* Breadcrumb */}
        <div
          className="flex items-center gap-2 mb-4 text-sm"
          style={{ color: "var(--text-muted)" }}
        >
          <Link
            href="/"
            className="transition-colors duration-150 hover:text-[var(--accent)]"
          >
            Home
          </Link>
          <svg
            width="12"
            height="12"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden="true"
          >
            <path d="M9 18l6-6-6-6" />
          </svg>
          <span style={{ color: "var(--text-secondary)" }}>
            Action Brief — {pin}
          </span>
        </div>

        <h1
          className="text-3xl sm:text-4xl font-bold"
          style={{ color: "var(--text-primary)" }}
        >
          Your Action Brief
        </h1>
        <p className="text-lg mt-2" style={{ color: "var(--text-secondary)" }}>
          {brief.district}, {brief.state}
          {brief.mp && (
            <span style={{ color: "var(--text-muted)" }}>
              {" "}· MP: {brief.mp.mp_name} ({brief.mp.party})
            </span>
          )}
        </p>
        {brief.mla && (
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
            MLA ({brief.mla.ac_name}): {brief.mla.mla_name} ({brief.mla.party})
          </p>
        )}
        <p className="text-xs mt-3" style={{ color: "var(--text-muted)" }}>
          Generated {new Date(brief.generated_at).toLocaleDateString("en-IN", {
            day: "numeric",
            month: "long",
            year: "numeric",
          })}
        </p>
      </div>

      {/* ---- Layer 1: What's Wrong ---- */}
      <section className="mb-12 animate-fade-in-up stagger-1">
        <SectionHeader
          label="What's Wrong"
          description="Issues identified in government scheme delivery for your area"
        />

        {hasDiagnosis ? (
          <div className="space-y-3 mt-5">
            {brief.diagnosis.map((item, i) => (
              <DiagnosisCard key={i} item={item} />
            ))}
          </div>
        ) : (
          <div
            className="mt-5 rounded-xl p-6 flex items-center gap-4"
            style={{
              background: "oklch(0.96 0.06 145)",
              border: "1px solid oklch(0.88 0.08 145)",
            }}
          >
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              style={{ color: "oklch(0.40 0.15 145)", flexShrink: 0 }}
              aria-hidden="true"
            >
              <polyline points="20 6 9 17 4 12" />
            </svg>
            <div>
              <p
                className="text-sm font-semibold"
                style={{ color: "oklch(0.35 0.14 145)" }}
              >
                No issues detected
              </p>
              <p
                className="text-sm"
                style={{ color: "oklch(0.45 0.10 145)" }}
              >
                Scheme delivery for your area appears to be on track.
              </p>
            </div>
          </div>
        )}
      </section>

      {/* ---- Layer 2: Who's Responsible ---- */}
      {brief.contacts.length > 0 && (
        <section className="mb-12 animate-fade-in-up stagger-2">
          <SectionHeader
            label="Who's Responsible"
            description="Officials you can contact to report issues or demand accountability"
          />
          <div className="grid gap-4 sm:grid-cols-2 mt-5">
            {brief.contacts.map((contact, i) => (
              <ContactCardDisplay key={i} contact={contact} />
            ))}
          </div>
        </section>
      )}

      {/* ---- Layer 3: What You Can Do ---- */}
      {brief.actions.length > 0 && (
        <section className="mb-12 animate-fade-in-up stagger-3">
          <SectionHeader
            label="What You Can Do"
            description="Specific actions to escalate issues and demand accountability"
          />
          <div className="space-y-3 mt-5">
            {brief.actions.map((action, i) => (
              <ActionCard key={i} item={action} />
            ))}
          </div>
        </section>
      )}

      {/* Footer note */}
      <div
        className="rounded-xl p-4 mt-4 animate-fade-in-up stagger-4"
        style={{
          background: "var(--surface-tinted)",
          border: "1px solid var(--border)",
        }}
      >
        <p className="text-xs" style={{ color: "var(--text-muted)" }}>
          Data sourced from official government portals. Financial figures are in
          Indian Rupees (lakhs). Scheme coverage and accuracy varies by
          district.{" "}
          <Link
            href={`/district/${encodeURIComponent(brief.district)}`}
            className="underline transition-colors duration-150 hover:text-[var(--accent)]"
            style={{ color: "var(--text-secondary)" }}
          >
            View full district data
          </Link>
        </p>
      </div>
    </>
  );
}

function SectionHeader({
  label,
  description,
}: {
  label: string;
  description: string;
}) {
  return (
    <div
      className="pb-4 border-b"
      style={{ borderColor: "var(--border-subtle)" }}
    >
      <h2
        className="text-xl font-bold"
        style={{ color: "var(--text-primary)" }}
      >
        {label}
      </h2>
      <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
        {description}
      </p>
    </div>
  );
}

export default async function ActionBriefPage({
  params,
}: {
  params: Promise<{ pin: string }>;
}) {
  const { pin } = await params;

  return (
    <div className="flex-1">
      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
        <Suspense fallback={<ActionBriefLoading />}>
          <ActionBriefContent pin={pin} />
        </Suspense>
      </main>
    </div>
  );
}
