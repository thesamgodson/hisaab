import Link from "next/link";
import ComplaintGuide from "@/components/ComplaintGuide";
import SchemeDataSection, { actionHref } from "@/components/SchemeDataSection";
import SourceLink from "@/components/SourceLink";
import type { ComplaintKit, DistrictLineage, GrievanceChannel } from "@/lib/action-types";
import type { AreaAccount, DistrictScoreSummary } from "@/lib/area-account";
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
  /** Precomputed verdict from district_scores (see getDistrictScore). */
  score?: DistrictScoreSummary | null;
  complaintSchemes: string[];
  complaintKits: ComplaintKit[];
  universalChannels: GrievanceChannel[];
  representatives: ResultRepresentative[];
  representativeContext: string;
  selectedScheme: string | null;
  selectedTrigger: string | null;
  general: boolean;
}

const GENERAL_ISSUE = "ALL";
/** Colour banding for the grade chip only. The score and grade are computed
 *  once in queries/composite.py; these thresholds tint what it published. */
const TONE_FLOORS = [
  { floor: 80, tone: "ok" },
  { floor: 60, tone: "warn" },
] as const;
const SCORE_METHOD = "DERIVED-2026-0001a: 60% delivery, 30% fund utilization, 10% MGNREGA recovery, computed once at data load. A district needs at least three schemes with data to get any score.";

function scoreTone(score: number): string {
  return TONE_FLOORS.find(({ floor }) => score >= floor)?.tone ?? "bad";
}

function finYearLabel(finYear: string): string {
  const [start, end] = finYear.split("-");
  return end?.length === 4 ? `FY ${start}-${end.slice(2)}` : `FY ${finYear}`;
}

function changeAreaHref(selectedScheme: string | null, general: boolean): string {
  if (general) return "/";
  const issue = selectedScheme;
  return issue ? `/?issue=${encodeURIComponent(issue)}` : "/";
}

function ScoreBadge({ score }: { score: DistrictScoreSummary | null }) {
  if (!score || score.score == null) {
    return (
      <div className="verdict__score verdict__score--none">
        <p className="verdict__unscored">Not enough data for a score</p>
        <p className="verdict__score-note">
          {score
            ? `Hisaab holds scored data for ${score.schemes_count} services here — below the minimum this methodology requires.`
            : "No score row has been published for this district."}
        </p>
      </div>
    );
  }
  return (
    <div className={`verdict__score verdict__score--${scoreTone(score.score)}`}>
      <p className="verdict__number">
        {score.score.toLocaleString("en-IN", { maximumFractionDigits: 1 })}
        <span> / 100</span>
      </p>
      {score.grade && <p className="verdict__grade">Grade {score.grade}</p>}
      <p className="verdict__score-note">
        {finYearLabel(score.fin_year)} data · {score.schemes_count} services scored
      </p>
      <SourceLink
        url="/api/v1/scores"
        label="How this is scored (DERIVED-2026-0001a)"
        accessibleLabel="Published accountability scores and methodology claim"
        title={SCORE_METHOD}
      />
    </div>
  );
}

function RedFlags({ score }: { score: DistrictScoreSummary | null }) {
  if (!score) return null;
  if (score.red_flags.length === 0) {
    return score.score == null ? null : <p className="verdict__clear">No red flags in the scored data.</p>;
  }
  return (
    <div className="verdict__flags">
      <p className="eyebrow">Red flags in the scored data ({score.red_flags.length})</p>
      <ul>
        {score.red_flags.map((flag) => <li className="flag" key={flag}>{flag}</li>)}
      </ul>
    </div>
  );
}

function Verdict({
  pin, district, state, lineage, score, districtSchemeCount, recordCount,
}: Pick<AccountabilityResultProps, "pin" | "district" | "state" | "lineage"> & {
  score: DistrictScoreSummary | null;
  districtSchemeCount: number;
  recordCount: number;
}) {
  return (
    <header className="verdict">
      <div className="verdict__identity">
        <p className="eyebrow">District welfare account</p>
        <h1>{titleCasePlace(district)}</h1>
        <p className="verdict__state">{titleCasePlace(state)}</p>
      </div>
      <ScoreBadge score={score} />
      <RedFlags score={score} />
      <div className="verdict__scope">
        <p>
          {pin ? `PIN ${pin} maps to this district.` : "District selected directly."}
          {" "}These are area records, not your personal benefit record.
        </p>
        <p>
          <strong>{districtSchemeCount}</strong> services · <strong>{recordCount}</strong> district records below
        </p>
        {lineage && (
          <p>
            Reorganized in {lineage.split_year}; formerly part of {titleCasePlace(lineage.parent_district)} district.
          </p>
        )}
      </div>
    </header>
  );
}

function Representatives({
  representatives,
  representativeContext,
}: Pick<AccountabilityResultProps, "representatives" | "representativeContext">) {
  return (
    <section className="reps no-print" aria-labelledby="reps-heading">
      <div className="section-head">
        <p className="eyebrow">Who answers for this</p>
        <h2 id="reps-heading">MPs for constituencies overlapping this district</h2>
        <p className="representative-context">{representativeContext}</p>
      </div>
      {representatives.length > 0 ? (
        <div className="rep-grid">
          {representatives.map((person) => (
            <article className="rep-card card-lift" key={`${person.role}-${person.area}-${person.name}`}>
              <h3>{person.name}</h3>
              <p className="rep-card__area">{person.role} · {person.area}</p>
              <p className="rep-card__party">{person.party}</p>
              <div className="rep-card__provenance">
                <SourceLink
                  url={person.sourceUrl}
                  label="Representative dataset"
                  accessibleLabel={`Representative dataset for ${person.name}`}
                />
                <span>Elected {person.electedYear}</span>
                <span className="claim-id">CLAIM-2026-0035</span>
              </div>
            </article>
          ))}
        </div>
      ) : <p className="coverage-empty">No representative record is available for this area yet.</p>}
    </section>
  );
}

function SchemeChoices({
  pin,
  district,
  state,
  schemes,
  selectedScheme,
  general,
}: Pick<AccountabilityResultProps, "pin" | "district" | "state" | "selectedScheme" | "general"> & {
  schemes: string[];
}) {
  const ordered = [...schemes].sort((left, right) =>
    schemeDisplay(left).need.localeCompare(schemeDisplay(right).need),
  );
  return (
    <nav className="chips" aria-label="Choose the service your problem is about">
      {ordered.map((scheme) => (
        <Link
          className="chip"
          key={scheme}
          href={actionHref(scheme, pin, district, state)}
          aria-current={!general && scheme === selectedScheme ? "true" : undefined}
        >
          {schemeDisplay(scheme).need}
        </Link>
      ))}
      <Link
        className="chip"
        href={actionHref(GENERAL_ISSUE, pin, district, state)}
        aria-current={general ? "true" : undefined}
      >
        Another government-service problem
      </Link>
    </nav>
  );
}

export default function AccountabilityResult(props: AccountabilityResultProps) {
  const {
    pin, district, state, lineage, account, score = null, complaintSchemes, complaintKits,
    universalChannels, representatives, representativeContext, selectedScheme, selectedTrigger, general,
  } = props;
  const districtSchemeCount = new Set(account.districtRecords.map((record) => record.scheme)).size;
  return (
    <div id="result" className="result-shell rise-stagger">
      <nav className="result-nav no-print" aria-label="Account controls">
        <Link href={changeAreaHref(selectedScheme, general)}>Change area</Link>
        <Link href="#action">Get help</Link>
      </nav>

      <Verdict
        pin={pin}
        district={district}
        state={state}
        lineage={lineage}
        score={score}
        districtSchemeCount={districtSchemeCount}
        recordCount={account.districtRecords.length}
      />

      <Representatives representatives={representatives} representativeContext={representativeContext} />

      <section id="action" className="action-section" aria-labelledby="action-heading">
        <div className="section-head">
          <p className="eyebrow">Act on it</p>
          <h2 id="action-heading">File a complaint that sticks</h2>
          <p>
            Pick the service your problem is about. Hisaab shows sourced rights
            and official routes without deciding your case.
          </p>
        </div>
        <SchemeChoices
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

      <SchemeDataSection account={account} pin={pin} district={district} state={state} />

      <p className="print-disclaimer">
        Hisaab is an independent public-interest tool, not a government service.
      </p>
    </div>
  );
}
