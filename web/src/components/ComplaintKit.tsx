import type { ComplaintKit, GrievanceChannel } from "@/lib/action-types";
import SectionHeader from "@/components/SectionHeader";
import SourceLink from "@/components/SourceLink";
import { schemeDisplay } from "@/lib/scheme-display";

const LEVEL_LABEL: Record<string, string> = {
  local: "Start local",
  district: "District",
  state: "State",
  national: "National",
};

function schemeAnchor(scheme: string): string {
  return `complaint-${scheme.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;
}

function ChannelRoute({ channel }: { channel: GrievanceChannel }) {
  const phoneHref = channel.phone?.replace(/[^\d+]/g, "") ?? null;

  return (
    <div className="channel-route">
      <span className="channel-rung__level">
        {LEVEL_LABEL[channel.level] ?? channel.level}
      </span>
      {channel.authority && <p className="channel-route__authority">{channel.authority}</p>}
      <p className="channel-route__name">{channel.portal_name}</p>
      <div className="channel-route__links">
        <a href={channel.portal_url} target="_blank" rel="noopener noreferrer">
          Open official route
        </a>
        {channel.phone && phoneHref && <a href={`tel:${phoneHref}`}>Call {channel.phone}</a>}
      </div>
      {channel.description && (
        <details className="channel-how">
          <summary>How to use this route</summary>
          <p>{channel.description}</p>
        </details>
      )}
    </div>
  );
}

function ChannelRung({ channel }: { channel: GrievanceChannel }) {
  return (
    <li className="channel-rung">
      <ChannelRoute channel={channel} />
    </li>
  );
}

function KitCard({ kit }: { kit: ComplaintKit }) {
  const display = schemeDisplay(kit.scheme);
  const firstChannel = kit.channels[0] ?? null;
  const escalation = kit.channels.slice(1);

  return (
    <details
      id={schemeAnchor(kit.scheme)}
      open={kit.flagged}
      className="complaint-card"
    >
      <summary>
        <span className="complaint-card__title">
          <span className="complaint-card__need">{display.need}</span>
          <span className="complaint-card__scheme">{kit.scheme}</span>
        </span>
        {kit.flagged && <span className="complaint-card__badge">Data flag</span>}
      </summary>

      <div className="complaint-card__body">
        {kit.entitlement && (
          <section className="complaint-block">
            <h3>What you are owed</h3>
            <p>{kit.entitlement}</p>
            {kit.legal_basis && <p className="complaint-block__basis">{kit.legal_basis}</p>}
            {kit.entitlement_source_url && (
              <SourceLink url={kit.entitlement_source_url} label="Entitlement source" />
            )}
          </section>
        )}

        {kit.complain_when.length > 0 && (
          <section className="complaint-block">
            <h3>Complain when</h3>
            <ul>
              {kit.complain_when.map((reason) => <li key={reason}>{reason}</li>)}
            </ul>
          </section>
        )}

        {firstChannel && (
          <section className="complaint-block complaint-start">
            <h3>Start here</h3>
            <ChannelRoute channel={firstChannel} />
          </section>
        )}

        {escalation.length > 0 && (
          <details className="escalation">
            <summary>
              Show {escalation.length} escalation step{escalation.length === 1 ? "" : "s"}
            </summary>
            <ol className="channel-list">
              {escalation.map((channel) => (
                <ChannelRung
                  key={`${channel.level}-${channel.portal_name}`}
                  channel={channel}
                />
              ))}
            </ol>
          </details>
        )}
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
  representatives: string[];
}) {
  if (kits.length === 0 && universal.length === 0) return null;

  const generalStart =
    universal.find((channel) => channel.portal_name.includes("Centralised")) ??
    universal[0] ??
    null;
  const generalEscalation = universal.filter((channel) => channel !== generalStart);

  return (
    <section id="complaints" className="content-section">
      <SectionHeader
        title="Your rights and complaint routes"
        count={kits.length}
        description="Choose the problem you recognize. You do not need to know the scheme acronym."
      />

      {kits.length > 1 && (
        <nav className="complaint-index" aria-label="Choose a complaint guide">
          {kits.map((kit) => (
            <a
              key={kit.scheme}
              href={`#${schemeAnchor(kit.scheme)}`}
              className={kit.flagged ? "is-flagged" : undefined}
            >
              {schemeDisplay(kit.scheme).shortNeed}
            </a>
          ))}
        </nav>
      )}

      <div className="complaint-stack">
        {kits.map((kit) => <KitCard key={kit.scheme} kit={kit} />)}
      </div>

      {generalStart && (
        <details className="universal-card">
          <summary>
            <span>
              <span className="eyebrow">Not sure which scheme applies?</span>
              <h3>Use a general grievance route</h3>
            </span>
            <span className="evidence-panel__count">{universal.length} routes</span>
          </summary>
          <div className="universal-card__body">
            <section className="complaint-block complaint-start">
              <h3>Start here</h3>
              <ChannelRoute channel={generalStart} />
            </section>
            {generalEscalation.length > 0 && (
              <details className="escalation">
                <summary>Show every general route</summary>
                <ol className="channel-list">
                  {generalEscalation.map((channel) => (
                    <ChannelRung
                      key={`${channel.level}-${channel.portal_name}`}
                      channel={channel}
                    />
                  ))}
                </ol>
              </details>
            )}
            {representatives.length > 0 && (
              <p className="universal-card__note">
                Your named elected representatives are listed at the top of this brief.
              </p>
            )}
          </div>
        </details>
      )}
    </section>
  );
}
