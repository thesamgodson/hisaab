"use client";

import { useState } from "react";
import SourceLink from "@/components/SourceLink";
import type { ComplaintKit, GrievanceChannel } from "@/lib/action-types";
import { titleCasePlace } from "@/lib/format-place";
import { schemeDisplay } from "@/lib/scheme-display";
import { useHydrated } from "@/lib/use-hydrated";

const LEVEL_LABEL: Record<string, string> = {
  local: "Local",
  district: "District",
  state: "State",
  national: "National",
};

function checkedDate(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(date);
}

function OfficialLink({
  channel,
  label,
}: {
  channel: GrievanceChannel;
  label: string;
}) {
  return (
    <a
      className="button button--secondary"
      href={channel.portal_url}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={`${label}: ${channel.portal_name}`}
    >
      {label}<span className="sr-only"> (opens official site in a new tab)</span>
    </a>
  );
}

function Evidence({
  url,
  label,
  scheme,
  checked,
}: {
  url: string;
  label: string;
  scheme: string;
  checked?: string | null;
}) {
  return (
    <div className="route__source">
      <SourceLink url={url} label={label} accessibleLabel={`${label} for ${scheme}`} />
      {checked && <span>Checked {checkedDate(checked)}</span>}
    </div>
  );
}

function Route({ channel }: { channel: GrievanceChannel }) {
  const phone = channel.phone?.replace(/[^\d+]/g, "") ?? null;

  return (
    <article className="route card-lift">
      <p className="route__level">{LEVEL_LABEL[channel.level] ?? channel.level} route</p>
      <h5>{channel.authority ?? channel.portal_name}</h5>
      {channel.authority && <p className="route__portal">{channel.portal_name}</p>}
      <p className="route__description">{channel.description}</p>
      <div className="route__actions">
        <OfficialLink channel={channel} label="Open official page" />
        {phone && (
          <a className="button button--secondary" href={`tel:${phone}`}>
            Call {channel.phone}
          </a>
        )}
      </div>
      <div className="route__source">
        <SourceLink
          url={channel.source_url}
          label="Route evidence"
          accessibleLabel={`Route evidence: ${channel.portal_name}`}
        />
        <span>Checked {checkedDate(channel.scraped_at)}</span>
      </div>
    </article>
  );
}

function Preparation({
  kit,
  trigger,
  district,
  state,
}: {
  kit: ComplaintKit;
  trigger: string | null;
  district: string;
  state: string;
}) {
  const display = schemeDisplay(kit.scheme);
  const situation = trigger
    ? `Situation selected: ${trigger}`
    : "Situation: [describe what happened in your own words]";
  const note = [
    `Problem category: ${display.shortNeed} — ${kit.scheme}`,
    situation,
    `Area: ${titleCasePlace(district)}, ${titleCasePlace(state)}`,
    "",
    "What happened: [write this in your own words]",
    "Relevant dates: [add dates]",
    "Previous complaint or reference number: [add if you have one]",
    "What you want the authority to do: [add the outcome you are asking for]",
    "Documents you can refer to: [list only what you choose to submit]",
  ].join("\n");
  const [status, setStatus] = useState("");
  const hydrated = useHydrated();

  const copyNote = async () => {
    try {
      await navigator.clipboard.writeText(note);
      setStatus("Case outline copied.");
    } catch {
      setStatus("Copy was blocked. Select the note below and copy it manually.");
    }
  };

  const sharePlan = async () => {
    try {
      if (navigator.share) {
        await navigator.share({ title: "Hisaab public action plan", url: window.location.href });
        setStatus("Public plan shared.");
        return;
      }
      await navigator.clipboard.writeText(window.location.href);
      setStatus("Public plan link copied.");
    } catch {
      setStatus("Share was cancelled or unavailable. You can copy the page address.");
    }
  };

  return (
    <details id="prepare" className="guide__prepare text-disclosure">
      <summary><strong>Prepare your case</strong></summary>
      <div className="guide-disclosure__body">
        <p>
          Add personal details only to the version you submit directly to an
          official authority.
        </p>
        <pre className="complaint-note">{note}</pre>
        <div
          className={`plan-actions no-print${hydrated ? "" : " hydration-placeholder"}`}
          aria-hidden={hydrated ? undefined : "true"}
        >
          {hydrated ? (
            <>
              <button type="button" className="button button--secondary" onClick={copyNote}>Copy case outline</button>
              <button type="button" className="button button--secondary" onClick={() => window.print()}>Print this plan</button>
              <button type="button" className="button button--secondary" onClick={sharePlan}>Share public plan</button>
            </>
          ) : (
            <>
              <span className="button button--secondary">Copy case outline</span>
              <span className="button button--secondary">Print this plan</span>
              <span className="button button--secondary">Share public plan</span>
            </>
          )}
        </div>
        <p
          className="action-status"
          role={hydrated ? "status" : undefined}
          aria-live={hydrated ? "polite" : undefined}
        >
          {hydrated ? status : ""}
        </p>
        <p className="keep-note">
          Hisaab’s practical advice: keep a dated copy and any receipt,
          acknowledgement, or reference number you receive.
        </p>
      </div>
    </details>
  );
}

function GeneralRoutes({ universal }: { universal: GrievanceChannel[] }) {
  if (universal.length === 0) return null;
  return (
    <article id="complaint" className="guide action-plan">
      <header className="guide__header">
        <p className="eyebrow">General government grievance</p>
        <h3>Official places to raise it</h3>
        <p>These options serve different purposes. Read each sourced instruction before choosing one.</p>
      </header>
      <p className="official-handoff">
        Hisaab does not file anything. Complete registration and any CAPTCHA on
        the official service yourself.
      </p>
      <section className="kit-block" aria-labelledby="universal-routes-heading">
        <h4 id="universal-routes-heading">Official routes ({universal.length})</h4>
        <div className="route-list">{universal.map((channel) => (
          <Route key={`${channel.level}-${channel.portal_name}`} channel={channel} />
        ))}</div>
      </section>
    </article>
  );
}

export default function ComplaintGuide({
  kits,
  universal,
  selectedScheme,
  selectedTrigger,
  district,
  state,
  general = false,
}: {
  kits: ComplaintKit[];
  universal: GrievanceChannel[];
  selectedScheme: string | null;
  selectedTrigger: string | null;
  district: string;
  state: string;
  general?: boolean;
}) {
  if (general) return <GeneralRoutes universal={universal} />;
  const kit = kits.find((item) => item.scheme === selectedScheme) ?? null;
  if (!kit) return null;
  const display = schemeDisplay(kit.scheme);

  return (
    <article id="complaint" className="guide action-plan">
      <header className="guide__header">
        <p className="eyebrow">{display.need} · {kit.scheme}</p>
        <h3>Your rights and official options</h3>
        {selectedTrigger && <p className="chosen-trigger">You chose: {selectedTrigger}</p>}
      </header>
      <p className="official-handoff">
        Hisaab does not file complaints. Enter personal details and complete any
        CAPTCHA only on the official service.
      </p>

      {kit.entitlement && (
        <section className="kit-block kit-block--right" aria-labelledby="entitlement-heading">
          <h4 id="entitlement-heading">What you are owed</h4>
          <p>People covered by this scheme have the following right.</p>
          <p className="kit-entitlement">{kit.entitlement}</p>
          {kit.legal_basis && <p className="guide__basis">{kit.legal_basis}</p>}
          {kit.entitlement_source_url && (
            <Evidence
              url={kit.entitlement_source_url}
              label="Entitlement source"
              scheme={kit.scheme}
              checked={kit.entitlement_scraped_at}
            />
          )}
        </section>
      )}

      {kit.complain_when.length > 0 && (
        <section className="kit-block" aria-labelledby="situations-heading">
          <h4 id="situations-heading">When this may help ({kit.complain_when.length})</h4>
          <ul className="kit-situations">
            {kit.complain_when.map((situation) => <li key={situation}>{situation}</li>)}
          </ul>
          <p>These are sourced examples, not a decision about your case.</p>
          {kit.entitlement_source_url && (
            <Evidence
              url={kit.entitlement_source_url}
              label="Situation evidence"
              scheme={kit.scheme}
              checked={kit.entitlement_scraped_at}
            />
          )}
        </section>
      )}

      <Preparation kit={kit} trigger={selectedTrigger} district={district} state={state} />

      {kit.channels.length > 0 ? (
        <section className="kit-block" aria-labelledby="routes-heading">
          <h4 id="routes-heading">Complaint routes ({kit.channels.length})</h4>
          <p className="official-handoff">
            Routes are ordered from local to national. Hisaab has not matched
            one to your situation, and does not claim you must use them in sequence.
          </p>
          <div className="route-list">{kit.channels.map((channel) => (
            <Route key={`${channel.level}-${channel.portal_name}`} channel={channel} />
          ))}</div>
        </section>
      ) : (
        <p className="data-caveat">No scheme-specific route is published. Review the general official options below.</p>
      )}

      {universal.length > 0 && (
        <details className="text-disclosure kit-disclosure">
          <summary><strong>Other official routes ({universal.length})</strong></summary>
          <div className="guide-disclosure__body">
            <p className="disclosure-note">
              CPGRAMS, RTI, and representative contact serve different purposes.
              Read each sourced instruction before using it.
            </p>
            <div className="route-list">{universal.map((channel) => (
              <Route key={`${channel.level}-${channel.portal_name}`} channel={channel} />
            ))}</div>
          </div>
        </details>
      )}
    </article>
  );
}
