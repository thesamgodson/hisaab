/**
 * "How to complain" — WHY (legal entitlement), WHO (escalation ladder +
 * elected representatives), HOW (per-rung instruction) for every scheme
 * present in the district. Content is curated from official sources
 * (grievance_channels / scheme_entitlements tables, DATA_CLAIMS-backed);
 * this component renders it verbatim and never invents a route.
 */

import type { ComplaintKit, GrievanceChannel } from "@/lib/action-types";
import SectionHeader from "@/components/SectionHeader";
import SourceLink from "@/components/SourceLink";

const LEVEL_LABEL: Record<string, string> = {
  local: "Start local",
  district: "District",
  state: "State",
  national: "National",
};

function ChannelRung({ ch }: { ch: GrievanceChannel }) {
  return (
    <li className="flex items-start gap-3 text-sm">
      <span
        className="flex-shrink-0 mt-0.5 px-2 py-0.5 rounded-md text-[11px] font-semibold uppercase tracking-wide"
        style={{ background: "var(--accent-light)", color: "var(--accent)" }}
      >
        {LEVEL_LABEL[ch.level] ?? ch.level}
      </span>
      <span className="flex-1" style={{ color: "var(--text-secondary)" }}>
        {ch.authority && (
          <span className="font-medium" style={{ color: "var(--text-primary)" }}>
            {ch.authority}
            {" — "}
          </span>
        )}
        {ch.description}{" "}
        <a
          href={ch.portal_url}
          target="_blank"
          rel="noopener noreferrer"
          className="font-medium underline underline-offset-2 hover:opacity-80"
          style={{ color: "var(--accent)" }}
        >
          {ch.portal_name}
        </a>
        {ch.phone && (
          <span style={{ color: "var(--text-muted)" }}>
            {" · "}
            <a href={`tel:${ch.phone.replace(/[^\d+]/g, "")}`} className="underline underline-offset-2">
              {ch.phone}
            </a>
          </span>
        )}
      </span>
    </li>
  );
}

function KitCard({ kit }: { kit: ComplaintKit }) {
  return (
    <details
      open={kit.flagged}
      className="rounded-xl overflow-hidden"
      style={{
        background: "var(--elevated)",
        border: "1px solid var(--border-subtle)",
        boxShadow: "var(--shadow-sm)",
      }}
    >
      <summary className="cursor-pointer px-5 py-4 flex items-center justify-between gap-3 list-none [&::-webkit-details-marker]:hidden">
        <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
          {kit.scheme}
        </span>
        {kit.flagged && (
          <span
            className="px-2.5 py-0.5 rounded-md text-[11px] font-semibold uppercase tracking-wide text-white"
            style={{ background: "oklch(0.55 0.20 25)" }}
          >
            Shortfall flagged
          </span>
        )}
      </summary>

      <div className="px-5 pb-5 flex flex-col gap-4">
        {kit.entitlement && (
          <div>
            <p
              className="text-[11px] uppercase tracking-wide font-medium mb-1"
              style={{ color: "var(--text-muted)" }}
            >
              What you are owed
            </p>
            <p className="text-sm leading-relaxed" style={{ color: "var(--text-primary)" }}>
              {kit.entitlement}
            </p>
            {kit.legal_basis && (
              <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
                {kit.legal_basis}
              </p>
            )}
          </div>
        )}

        {kit.complain_when.length > 0 && (
          <div>
            <p
              className="text-[11px] uppercase tracking-wide font-medium mb-1"
              style={{ color: "var(--text-muted)" }}
            >
              Complain when
            </p>
            <ul className="flex flex-col gap-1">
              {kit.complain_when.map((w, i) => (
                <li
                  key={i}
                  className="text-sm flex items-start gap-2"
                  style={{ color: "var(--text-secondary)" }}
                >
                  <span aria-hidden="true" style={{ color: "var(--accent)" }}>
                    •
                  </span>
                  {w}
                </li>
              ))}
            </ul>
          </div>
        )}

        {kit.channels.length > 0 && (
          <div>
            <p
              className="text-[11px] uppercase tracking-wide font-medium mb-2"
              style={{ color: "var(--text-muted)" }}
            >
              Where to take it
            </p>
            <ol className="flex flex-col gap-2.5">
              {kit.channels.map((ch, i) => (
                <ChannelRung key={i} ch={ch} />
              ))}
            </ol>
          </div>
        )}

        {kit.entitlement_source_url && <SourceLink url={kit.entitlement_source_url} />}
      </div>
    </details>
  );
}

export default function ComplaintKitSection({
  kits,
  universal,
  representatives,
}: {
  kits: ComplaintKit[];
  universal: GrievanceChannel[];
  /** Pre-formatted "MP Name (Party)" / "MLA Name (Party)" lines, if known. */
  representatives: string[];
}) {
  if (kits.length === 0 && universal.length === 0) return null;

  return (
    <section className="mb-12">
      <SectionHeader title="How to Complain" count={kits.length} />

      <div className="flex flex-col gap-4">
        {kits.map((kit) => (
          <KitCard key={kit.scheme} kit={kit} />
        ))}
      </div>

      {(universal.length > 0 || representatives.length > 0) && (
        <div
          className="mt-5 rounded-xl px-5 py-4"
          style={{
            background: "var(--surface)",
            border: "1px solid var(--border-subtle)",
          }}
        >
          <p
            className="text-[11px] uppercase tracking-wide font-medium mb-2"
            style={{ color: "var(--text-muted)" }}
          >
            For any scheme, anywhere
          </p>
          <ol className="flex flex-col gap-2.5">
            {universal.map((ch, i) => (
              <ChannelRung key={i} ch={ch} />
            ))}
          </ol>
          {representatives.length > 0 && (
            <p className="text-sm mt-3" style={{ color: "var(--text-secondary)" }}>
              Your elected representatives answer to you —{" "}
              {representatives.join(" and ")}. Their offices take scheme
              complaints and can escalate them directly.
            </p>
          )}
        </div>
      )}
    </section>
  );
}
