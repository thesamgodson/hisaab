import Link from "next/link";
import ComplaintGuide from "@/components/ComplaintGuide";
import SchemeDataSection from "@/components/SchemeDataSection";
import SourceLink from "@/components/SourceLink";
import type { SchemeData } from "@/components/SchemeRow";
import type {
  ComplaintKit,
  DistrictLineage,
  GrievanceChannel,
} from "@/lib/action-types";
import { titleCasePlace } from "@/lib/format-place";

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
  complaintKits: ComplaintKit[];
  universalChannels: GrievanceChannel[];
  representatives: ResultRepresentative[];
  representativeContext: string;
  schemes: SchemeData[];
  selectedScheme: string | null;
  selectedTrigger: string | null;
  selectedTriggerIndex?: number | null;
}

function changeAreaHref(
  selectedScheme: string | null,
  selectedTriggerIndex: number | null | undefined,
): string {
  const issue = selectedScheme;
  if (!issue) return "/";
  const params = new URLSearchParams({ issue });
  if (selectedTriggerIndex != null) params.set("trigger", String(selectedTriggerIndex));
  return `/?${params.toString()}`;
}

export default function AccountabilityResult({
  pin,
  district,
  state,
  lineage,
  complaintKits,
  universalChannels,
  representatives,
  representativeContext,
  schemes,
  selectedScheme,
  selectedTrigger,
  selectedTriggerIndex,
}: AccountabilityResultProps) {
  const areaHref = changeAreaHref(selectedScheme, selectedTriggerIndex);

  return (
    <div id="result" className="result-shell">
      <nav className="result-nav no-print" aria-label="Change answers">
        <Link href={areaHref}>Change area</Link>
        <Link href="/">Start again</Link>
      </nav>

      <header className="result-context">
        <p className="result-context__label">Public action plan for</p>
        <p className="result-context__area">
          {titleCasePlace(district)}, {titleCasePlace(state)}
        </p>
        <p className="result-context__scope">
          {pin ? `PIN ${pin} resolved to this postal district.` : "District-level context."}
        </p>
        {lineage && (
          <p className="result-context__scope">
            Reorganized in {lineage.split_year}; formerly part of {titleCasePlace(lineage.parent_district)} district.
          </p>
        )}
      </header>

      <ComplaintGuide
        kits={complaintKits}
        universal={universalChannels}
        selectedScheme={selectedScheme}
        selectedTrigger={selectedTrigger}
        district={district}
        state={state}
      />

      <details className="result-secondary">
        <summary>Area evidence and data context</summary>
        <div className="result-secondary__body">
          <SchemeDataSection schemes={schemes} />
          {schemes.length === 0 && (
            <div className="data-caveat">
              We do not have district-level scheme figures for this area. This
              does not mean no money was allocated or no service was delivered.
            </div>
          )}
        </div>
      </details>

      <details className="result-secondary">
        <summary>Representatives for this area</summary>
        <div className="result-secondary__body">
          <p className="representative-context">{representativeContext}</p>
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
        </div>
      </details>

      <p className="print-disclaimer">
        Hisaab is an independent public-interest tool, not a government service.
      </p>
    </div>
  );
}
