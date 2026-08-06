import Link from "next/link";
import ComplaintGuide from "@/components/ComplaintGuide";
import SchemeDataSection from "@/components/SchemeDataSection";
import SourceLink from "@/components/SourceLink";
import type { SchemeData } from "@/components/SchemeRow";
import type {
  ComplaintKit,
  DiagnosisItem,
  DistrictLineage,
  GrievanceChannel,
} from "@/lib/action-types";
import { titleCasePlace } from "@/lib/format-place";
import { schemeDisplay } from "@/lib/scheme-display";

export interface ResultRepresentative {
  role: "MP" | "MLA";
  name: string;
  party: string;
  area: string;
  sourceUrl: string;
}

interface AccountabilityResultProps {
  pin?: string;
  district: string;
  state: string;
  lineage: DistrictLineage | null;
  diagnosis: DiagnosisItem[];
  schemesChecked: string[];
  complaintKits: ComplaintKit[];
  universalChannels: GrievanceChannel[];
  representatives: ResultRepresentative[];
  representativeContext: string;
  schemes: SchemeData[];
}

const LIST_FORMAT = new Intl.ListFormat("en", { type: "conjunction" });

function checkedSchemesLabel(schemes: string[]): string {
  return LIST_FORMAT.format(
    schemes.map((scheme) => schemeDisplay(scheme).shortNeed.toLowerCase()),
  );
}

export default function AccountabilityResult({
  pin,
  district,
  state,
  lineage,
  diagnosis,
  schemesChecked,
  complaintKits,
  universalChannels,
  representatives,
  representativeContext,
  schemes,
}: AccountabilityResultProps) {
  const nothingChecked = diagnosis.length === 0 && schemesChecked.length === 0;

  return (
    <div id="result" className="result-shell">
      <nav className="result-nav" aria-label="Area search">
        <Link href="/">Search another area</Link>
      </nav>

      <header className="result-header">
        <p className="result-header__scope">{pin ? `PIN ${pin}` : "District view"}</p>
        <h1>{titleCasePlace(district)}</h1>
        <p className="result-header__state">{titleCasePlace(state)}</p>
        {lineage && (
          <p className="result-header__lineage">
            Reorganized in {lineage.split_year}; formerly part of {titleCasePlace(lineage.parent_district)} district.
          </p>
        )}
        <p className="result-header__intro">
          Use this brief to choose a welfare problem, check the right, and start with one official route.
        </p>
        <a className="button button--primary" href="#complaint">Choose a complaint route</a>
      </header>

      <section className="result-section data-section" aria-labelledby="data-heading">
        <header className="section-title">
          <h2 id="data-heading">What the district data says</h2>
          <p>These are area-wide indicators. They do not decide whether your personal complaint is valid.</p>
        </header>

        {diagnosis.length > 0 ? (
          <div className="finding-list">
            {diagnosis.map((item) => (
              <article className={`finding finding--${item.severity}`} key={`${item.scheme}-${item.summary}`}>
                <p className="finding__scheme">
                  {schemeDisplay(item.scheme).need} · {item.scheme}
                </p>
                <h3>{item.summary}</h3>
                <p>{item.detail}</p>
                {item.source_url && <SourceLink url={item.source_url} label="Check this data source" />}
              </article>
            ))}
          </div>
        ) : (
          <div className="data-caveat">
            <h3>{nothingChecked ? "Not enough district data to run the checks" : "No district-level flag crossed the threshold"}</h3>
            <p>
              {nothingChecked
                ? "This is not an all-clear. Your entitlement and complaint routes still apply."
                : `The checked data for ${checkedSchemesLabel(schemesChecked)} did not trigger a flag. A personal grievance may still be valid.`}
            </p>
          </div>
        )}
      </section>

      <ComplaintGuide kits={complaintKits} universal={universalChannels} />

      <section className="result-section" aria-labelledby="people-heading">
        <header className="section-title">
          <h2 id="people-heading">Who represents this area</h2>
          <p>{representativeContext}</p>
        </header>

        {representatives.length > 0 ? (
          <div className="people-list">
            {representatives.map((person) => (
              <article className="person-row" key={`${person.role}-${person.area}-${person.name}`}>
                <div>
                  <p>{person.role} · {person.area}</p>
                  <h3>{person.name}</h3>
                  <span>{person.party}</span>
                </div>
                <SourceLink url={person.sourceUrl} label="Official record" />
              </article>
            ))}
          </div>
        ) : (
          <p className="data-caveat">No representative record is available for this area yet.</p>
        )}
      </section>

      <SchemeDataSection schemes={schemes} />

      {schemes.length === 0 && (
        <section id="evidence" className="result-section">
          <header className="section-title"><h2>Evidence</h2></header>
          <div className="data-caveat">
            <p>
              We do not have district-level scheme figures for this area. This does not mean no money was allocated or no service was delivered.
            </p>
          </div>
        </section>
      )}
    </div>
  );
}
