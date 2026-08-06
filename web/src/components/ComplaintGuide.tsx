"use client";

import { useState } from "react";
import SourceLink from "@/components/SourceLink";
import type { ComplaintKit, GrievanceChannel } from "@/lib/action-types";
import { titleCasePlace } from "@/lib/format-place";
import { schemeDisplay } from "@/lib/scheme-display";

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
  primary,
}: {
  channel: GrievanceChannel;
  label: string;
  primary: boolean;
}) {
  return (
    <a
      className={`button ${primary ? "button--primary" : "button--secondary"}`}
      href={channel.portal_url}
      target="_blank"
      rel="noopener noreferrer"
    >
      {label}<span className="sr-only"> (opens official site in a new tab)</span>
    </a>
  );
}

function Route({ channel, primary = false }: { channel: GrievanceChannel; primary?: boolean }) {
  const phone = channel.phone?.replace(/[^\d+]/g, "") ?? null;

  return (
    <article className={primary ? "route route--primary" : "route"}>
      <p className="route__level">{LEVEL_LABEL[channel.level] ?? channel.level} route</p>
      <h2>{channel.authority ?? channel.portal_name}</h2>
      {channel.authority && <p className="route__portal">{channel.portal_name}</p>}
      <p className="route__description">{channel.description}</p>
      <div className="route__actions">
        <OfficialLink channel={channel} label="Open official page" primary={primary} />
        {phone && (
          <a className="button button--secondary" href={`tel:${phone}`}>
            Call {channel.phone}
          </a>
        )}
      </div>
      <div className="route__source">
        <SourceLink url={channel.source_url} label="Route evidence" />
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
  const problem = trigger ?? `A problem with ${display.need.toLowerCase()}`;
  const note = [
    `Problem category: ${display.shortNeed} — ${kit.scheme}`,
    `Situation selected: ${problem}`,
    `Area: ${titleCasePlace(district)}, ${titleCasePlace(state)}`,
    "",
    "What happened: [write this in your own words]",
    "Relevant dates: [add dates]",
    "Previous complaint or reference number: [add if you have one]",
    "What you want the authority to do: [add the outcome you are asking for]",
    "Documents you can refer to: [list only what you choose to submit]",
  ].join("\n");
  const [status, setStatus] = useState("");

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
    <section id="prepare" className="guide__prepare" aria-labelledby="prepare-heading">
      <h2 id="prepare-heading">Prepare your case outline</h2>
      <p>
        This outline contains public guidance and placeholders only. Add names,
        IDs, phone numbers, or documents only in the version you submit directly
        to an official authority.
      </p>
      <pre className="complaint-note">{note}</pre>
      <div className="plan-actions no-print">
        <button type="button" className="button button--secondary" onClick={copyNote}>Copy case outline</button>
        <button type="button" className="button button--secondary" onClick={() => window.print()}>Print this plan</button>
        <button type="button" className="button button--secondary" onClick={sharePlan}>Share public plan</button>
      </div>
      <p className="action-status" role="status" aria-live="polite">{status}</p>
      <p className="keep-note">
        Hisaab’s practical advice: keep a dated copy and any receipt,
        acknowledgement, or reference number you receive.
      </p>
    </section>
  );
}

function GeneralRoutes({ universal }: { universal: GrievanceChannel[] }) {
  const cpgrams = universal.find((channel) => channel.portal_name.includes("Centralised")) ?? universal[0];
  if (!cpgrams) return null;
  const others = universal.filter((channel) => channel !== cpgrams);
  return (
    <article id="complaint" className="guide action-plan">
      <header className="guide__header">
        <p className="service-step__count">General government grievance</p>
        <h1>General official options</h1>
        <p>CPGRAMS is one general-purpose route. Check the sourced alternatives for State services, records, or representative contact.</p>
      </header>
      <Route channel={cpgrams} primary />
      <p className="official-handoff">
        Hisaab does not file anything. Complete registration and any CAPTCHA on
        the official service yourself.
      </p>
      {others.length > 0 && (
        <details className="text-disclosure route-disclosure">
          <summary>Other official options ({others.length})</summary>
          <div className="route-list">{others.map((channel) => (
            <Route key={`${channel.level}-${channel.portal_name}`} channel={channel} />
          ))}</div>
        </details>
      )}
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
        <p className="service-step__count">{display.need} · {kit.scheme}</p>
        <h1>Official route options</h1>
        {selectedTrigger && <p className="chosen-trigger">You chose: {selectedTrigger}</p>}
      </header>

      {kit.channels.length > 0 ? (
        <section className="guide__routes" aria-label="Scheme-specific official routes">
          <p className="official-handoff">
            These routes are ordered from local to national. Hisaab has not
            matched one route to the situation you chose, and does not claim
            that you must use them in sequence.
          </p>
          <div className="route-list">{kit.channels.map((channel) => (
            <Route key={`${channel.level}-${channel.portal_name}`} channel={channel} />
          ))}</div>
        </section>
      ) : (
        <p className="data-caveat">No scheme-specific route is published. Review the general official options below.</p>
      )}
      <p className="official-handoff">
        Hisaab does not file the complaint. Complete personal details and any
        CAPTCHA only on the official service.
      </p>

      {kit.entitlement && (
        <section className="guide__entitlement" aria-labelledby="right-heading">
          <h2 id="right-heading">Your right</h2>
          <p>{kit.entitlement}</p>
          {kit.legal_basis && <p className="guide__basis">{kit.legal_basis}</p>}
          {kit.entitlement_source_url && (
            <div className="route__source">
              <SourceLink url={kit.entitlement_source_url} label="Entitlement source" />
              {kit.entitlement_scraped_at && <span>Checked {checkedDate(kit.entitlement_scraped_at)}</span>}
            </div>
          )}
        </section>
      )}

      <Preparation kit={kit} trigger={selectedTrigger} district={district} state={state} />

      {universal.length > 0 && (
        <details className="text-disclosure route-disclosure">
          <summary>General official options ({universal.length})</summary>
          <p className="disclosure-note">
            CPGRAMS, RTI, and representative contact serve different purposes.
            Read each sourced instruction before using it.
          </p>
          <div className="route-list">{universal.map((channel) => (
            <Route key={`${channel.level}-${channel.portal_name}`} channel={channel} />
          ))}</div>
        </details>
      )}
    </article>
  );
}
