import type { ReactNode } from "react";
import type { DiagnosisItem, DistrictLineage } from "@/lib/action-types";
import { titleCasePlace } from "@/lib/format-place";
import { schemeDisplay } from "@/lib/scheme-display";

export interface BriefRepresentative {
  role: "MP" | "MLA";
  name: string;
  party: string;
  area: string;
}

interface BriefOverviewProps {
  districtLabel: string;
  stateLabel: string;
  pin?: string;
  generatedDate?: string;
  lineage: DistrictLineage | null;
  diagnosis: DiagnosisItem[];
  schemesChecked: string[];
  guideCount: number;
  representatives: BriefRepresentative[];
  representativeNote?: ReactNode;
}

function overviewCopy(
  diagnosis: DiagnosisItem[],
  schemesChecked: string[],
): string {
  if (diagnosis.length > 0) {
    const need = schemeDisplay(diagnosis[0].scheme).need.toLowerCase();
    return `The public data flags ${need} here. Start with that route, then use the official evidence to support your complaint.`;
  }
  if (schemesChecked.length === 0) {
    return "District-level shortfall data is limited here. Your legal rights and official complaint routes still apply.";
  }
  return "The district data checked did not trigger a shortfall flag. That does not rule out a valid personal grievance.";
}

export default function BriefOverview({
  districtLabel,
  stateLabel,
  pin,
  generatedDate,
  lineage,
  diagnosis,
  schemesChecked,
  guideCount,
  representatives,
  representativeNote,
}: BriefOverviewProps) {
  const firstIssue = diagnosis[0] ?? null;
  const actionLabel = firstIssue
    ? `Start with ${schemeDisplay(firstIssue.scheme).shortNeed.toLowerCase()}`
    : "Find a complaint route";

  return (
    <header className="brief-overview">
      <div className="brief-overview__title">
        <p className="eyebrow">Your local accountability brief</p>
        <h1>{districtLabel}</h1>
        <p className="brief-overview__place">
          {pin ? `PIN ${pin} · ` : ""}{stateLabel}
        </p>
        {lineage && (
          <p className="brief-overview__lineage">
            Reorganized in {lineage.split_year}; formerly part of {titleCasePlace(lineage.parent_district)} district.
          </p>
        )}
      </div>

      <p className="brief-overview__lead">
        {overviewCopy(diagnosis, schemesChecked)}
      </p>

      <div className="brief-overview__stats" aria-label="Brief summary">
        <div>
          <strong>{diagnosis.length}</strong>
          <span>data flag{diagnosis.length === 1 ? "" : "s"}</span>
        </div>
        <div>
          <strong>{guideCount}</strong>
          <span>rights guide{guideCount === 1 ? "" : "s"}</span>
        </div>
        <div>
          <strong>{representatives.length}</strong>
          <span>named representative{representatives.length === 1 ? "" : "s"}</span>
        </div>
      </div>

      <nav className="brief-overview__actions" aria-label="Brief sections">
        <a className="button button--primary" href="#complaints">
          {actionLabel}
        </a>
        <a className="button button--secondary" href="#evidence">
          See official evidence
        </a>
      </nav>

      {representatives.length > 0 && (
        <section className="representatives" aria-labelledby="representatives-heading">
          <div className="representatives__heading">
            <p className="eyebrow">Accountable here</p>
            <h2 id="representatives-heading">Who represents this area</h2>
          </div>
          <div className="representatives__list">
            {representatives.map((representative) => (
              <article
                className="representative"
                key={`${representative.role}-${representative.area}-${representative.name}`}
              >
                <p className="representative__role">
                  {representative.role} · {representative.area}
                </p>
                <h3>{representative.name}</h3>
                <p>{representative.party}</p>
              </article>
            ))}
          </div>
          {representativeNote && (
            <p className="representatives__note">{representativeNote}</p>
          )}
        </section>
      )}

      {generatedDate && (
        <p className="brief-overview__generated">Brief generated {generatedDate}</p>
      )}
    </header>
  );
}
