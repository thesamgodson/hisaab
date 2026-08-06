"use client";

import { useState } from "react";
import SourceLink from "@/components/SourceLink";
import type { ComplaintKit, GrievanceChannel } from "@/lib/action-types";
import { schemeDisplay } from "@/lib/scheme-display";

const LEVEL_LABEL: Record<string, string> = {
  local: "Local",
  district: "District",
  state: "State",
  national: "National",
};

function Route({ channel, primary = false }: { channel: GrievanceChannel; primary?: boolean }) {
  const phone = channel.phone?.replace(/[^\d+]/g, "") ?? null;

  return (
    <div className={primary ? "route route--primary" : "route"}>
      <p className="route__level">{LEVEL_LABEL[channel.level] ?? channel.level}</p>
      <h3>{channel.authority ?? channel.portal_name}</h3>
      {channel.authority && <p className="route__portal">{channel.portal_name}</p>}
      {channel.description && <p className="route__description">{channel.description}</p>}
      <div className="route__actions">
        <a className="button button--primary" href={channel.portal_url} target="_blank" rel="noopener noreferrer">
          Open official route
        </a>
        {channel.phone && phone && <a className="button button--secondary" href={`tel:${phone}`}>Call {channel.phone}</a>}
      </div>
    </div>
  );
}

function SelectedGuide({ kit }: { kit: ComplaintKit }) {
  const firstRoute = kit.channels[0] ?? null;
  const escalation = kit.channels.slice(1);
  const display = schemeDisplay(kit.scheme);

  return (
    <article id="selected-complaint-guide" className="guide">
      <header className="guide__header">
        <h3>{display.need}</h3>
        <p>{kit.scheme}{kit.flagged ? " · district data flag" : ""}</p>
      </header>

      {kit.entitlement && (
        <div className="guide__entitlement">
          <h3>What you are owed</h3>
          <p>{kit.entitlement}</p>
          {kit.legal_basis && <p className="guide__basis">{kit.legal_basis}</p>}
          {kit.entitlement_source_url && (
            <SourceLink url={kit.entitlement_source_url} label="Check the entitlement source" />
          )}
        </div>
      )}

      {kit.complain_when.length > 0 && (
        <div className="guide__triggers">
          <h3>When to complain</h3>
          <ul>
            {kit.complain_when.map((reason) => <li key={reason}>{reason}</li>)}
          </ul>
        </div>
      )}

      {firstRoute && (
        <div>
          <h3 className="guide__step-title">Start here</h3>
          <Route channel={firstRoute} primary />
        </div>
      )}

      {escalation.length > 0 && (
        <details className="text-disclosure">
          <summary>Show escalation routes</summary>
          <ol className="escalation-list">
            {escalation.map((channel) => (
              <li key={`${channel.level}-${channel.portal_name}`}><Route channel={channel} /></li>
            ))}
          </ol>
        </details>
      )}
    </article>
  );
}

export default function ComplaintGuide({
  kits,
  universal,
}: {
  kits: ComplaintKit[];
  universal: GrievanceChannel[];
}) {
  const flaggedKit = kits.find((kit) => kit.flagged) ?? null;
  const [selectedScheme, setSelectedScheme] = useState(flaggedKit?.scheme ?? "");
  const selectedKit = kits.find((kit) => kit.scheme === selectedScheme) ?? null;
  const generalRoute =
    universal.find((channel) => channel.portal_name.includes("Centralised")) ??
    universal[0] ??
    null;

  if (kits.length === 0 && !generalRoute) return null;

  return (
    <section id="complaint" className="result-section">
      <header className="section-title">
        <h2>Find the complaint route</h2>
        <p>Choose the problem you recognize. You do not need to know the scheme name.</p>
      </header>

      {kits.length > 0 && (
        <div className="guide-picker">
          <label htmlFor="issue-select">What do you need help with?</label>
          <select
            id="issue-select"
            aria-controls="selected-complaint-guide"
            value={selectedScheme}
            onChange={(event) => setSelectedScheme(event.target.value)}
          >
            <option value="">Choose a problem</option>
            {kits.map((kit) => (
              <option key={kit.scheme} value={kit.scheme}>
                {schemeDisplay(kit.scheme).need}{kit.flagged ? " — data flag" : ""}
              </option>
            ))}
          </select>
        </div>
      )}

      {selectedKit ? (
        <SelectedGuide kit={selectedKit} />
      ) : (
        <p id="selected-complaint-guide" className="guide-empty">
          Choose one problem to see your entitlement and the first official route.
        </p>
      )}

      {generalRoute && (
        <details className="text-disclosure general-route">
          <summary>Not sure what to choose?</summary>
          <Route channel={generalRoute} />
        </details>
      )}
    </section>
  );
}
