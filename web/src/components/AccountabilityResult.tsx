import Link from "next/link";
import ComplaintGuide from "@/components/ComplaintGuide";
import SchemeDataSection from "@/components/SchemeDataSection";
import SourceLink from "@/components/SourceLink";
import type { ComplaintKit, DistrictLineage, GrievanceChannel } from "@/lib/action-types";
import type { AreaAccount } from "@/lib/area-account";
import { schemeDisplay } from "@/lib/scheme-display";
import { titleCasePlace } from "@/lib/format-place";

export interface ResultRepresentative {
  role: "MP" | "MLA";
  name: string;
  party: string;
  area: string;
  sourceUrl: string;
  electedYear: number;
}

interface AccountabilityResultProps {
  pin?: string;
  district: string;
  state: string;
  lineage: DistrictLineage | null;
  account: AreaAccount;
  complaintSchemes: string[];
  complaintKits: ComplaintKit[];
  universalChannels: GrievanceChannel[];
  representatives: ResultRepresentative[];
  representativeContext: string;
  selectedScheme: string | null;
  selectedTrigger: string | null;
  general: boolean;
}

function changeAreaHref(selectedScheme: string | null, general: boolean): string {
  if (general) return "/";
  const issue = selectedScheme;
  return issue ? `/?issue=${encodeURIComponent(issue)}` : "/";
}

function ActionPicker({
  pin,
  district,
  state,
  schemes,
  selectedScheme,
  general,
}: Pick<AccountabilityResultProps, "pin" | "district" | "state" | "selectedScheme" | "general"> & {
  schemes: string[];
}) {
  return (
    <form action="/#action" method="get" className="guide-picker">
      {pin ? <input type="hidden" name="pin" value={pin} /> : (
        <>
          <input type="hidden" name="district" value={district} />
          <input type="hidden" name="state" value={state} />
        </>
      )}
      <label htmlFor="guide-select">
        Scheme or service
        <select id="guide-select" name="issue" defaultValue={general ? "ALL" : selectedScheme ?? ""} required>
          <option value="" disabled>Choose a service</option>
          {[...schemes].sort((left, right) =>
            schemeDisplay(left).need.localeCompare(schemeDisplay(right).need),
          ).map((scheme) => (
            <option key={scheme} value={scheme}>{schemeDisplay(scheme).need}</option>
          ))}
          <option value="ALL">Another government-service problem</option>
        </select>
      </label>
      <button className="button button--primary" type="submit">See rights and routes</button>
    </form>
  );
}

function Representatives({
  representatives,
  representativeContext,
}: Pick<AccountabilityResultProps, "representatives" | "representativeContext">) {
  return (
    <details className="representative-section no-print">
      <summary>MPs for constituencies overlapping this district</summary>
      <div className="representative-section__body">
        <p className="representative-context">{representativeContext}</p>
        {representatives.length > 0 ? representatives.map((person) => (
          <article className="person-row" key={`${person.role}-${person.area}-${person.name}`}>
            <div>
              <p>{person.role} · {person.area}</p>
              <h3>{person.name}</h3>
              <span>{person.party}</span>
            </div>
            <div className="person-row__provenance">
              <SourceLink
                url={person.sourceUrl}
                label="Representative dataset"
                accessibleLabel={`Representative dataset for ${person.name}`}
              />
              <span>Elected {person.electedYear}</span>
              <span className="claim-id">CLAIM-2026-0035</span>
            </div>
          </article>
        )) : <p className="coverage-empty">No representative record is available for this area yet.</p>}
      </div>
    </details>
  );
}

export default function AccountabilityResult(props: AccountabilityResultProps) {
  const {
    pin, district, state, lineage, account, complaintSchemes, complaintKits, universalChannels,
    representatives, representativeContext, selectedScheme, selectedTrigger, general,
  } = props;
  const districtSchemeCount = new Set(account.districtRecords.map((record) => record.scheme)).size;
  return (
    <div id="result" className="result-shell">
      <nav className="result-nav no-print" aria-label="Account controls">
        <Link href={changeAreaHref(selectedScheme, general)}>Change area</Link>
        <Link href="#action">Get help</Link>
      </nav>

      <header className="account-header">
        <div className="account-header__identity">
          <p className="service-label">District welfare account</p>
          <h1>{titleCasePlace(district)}</h1>
          <p className="account-header__state">{titleCasePlace(state)}</p>
          <p className="account-header__summary">
            <strong>{districtSchemeCount}</strong> services · <strong>{account.districtRecords.length}</strong> district records
          </p>
        </div>
        <div className="account-header__scope">
          <strong>What this covers</strong>
          <p>
            {pin ? `PIN ${pin} maps to this district.` : "District selected directly."}
            {" "}These are area records, not your personal benefit record.
          </p>
        </div>
        {lineage && (
          <p className="account-header__lineage">
            Reorganized in {lineage.split_year}; formerly part of {titleCasePlace(lineage.parent_district)} district.
          </p>
        )}
      </header>

      <SchemeDataSection account={account} pin={pin} district={district} state={state} />

      <section id="action" className="action-section" aria-labelledby="action-heading">
        <header className="account-section__header">
          <p className="section-kicker">Question a service</p>
          <h2 id="action-heading">Need to take this further?</h2>
          <p>
            Choose the service. Hisaab will show sourced rights and official
            routes without deciding your case.
          </p>
        </header>
        <ActionPicker
          pin={pin}
          district={district}
          state={state}
          schemes={complaintSchemes}
          selectedScheme={selectedScheme}
          general={general}
        />
        {(selectedScheme || general) && (
          <ComplaintGuide
            kits={complaintKits}
            universal={universalChannels}
            selectedScheme={selectedScheme}
            selectedTrigger={selectedTrigger}
            district={district}
            state={state}
            general={general}
          />
        )}
      </section>

      <Representatives representatives={representatives} representativeContext={representativeContext} />

      <p className="print-disclaimer">
        Hisaab is an independent public-interest tool, not a government service.
      </p>
    </div>
  );
}
