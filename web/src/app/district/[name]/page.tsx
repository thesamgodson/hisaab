import { cache } from "react";
import Link from "next/link";
import { notFound } from "next/navigation";
import BriefOverview, {
  PinPrecisionNote,
  type BriefRepresentative,
} from "@/components/BriefOverview";
import ComplaintKitSection from "@/components/ComplaintKit";
import DiagnosisCard from "@/components/DiagnosisCard";
import SchemeDataSection from "@/components/SchemeDataSection";
import SectionHeader from "@/components/SectionHeader";
import { buildDistrictBrief } from "@/lib/action-brief";
import { resolveState } from "@/lib/db";
import {
  displayPersonName,
  formatDistrictLabel,
  titleCasePlace,
} from "@/lib/format-place";
import { getDistrictSchemeRows } from "@/lib/money-flow";

interface DistrictPageProps {
  params: Promise<{ name: string }>;
  searchParams: Promise<{ state?: string }>;
}

const getState = cache(resolveState);
export const revalidate = 3600;

async function resolveDistrict(props: DistrictPageProps) {
  const [{ name: rawName }, searchParams] = await Promise.all([
    props.params,
    props.searchParams,
  ]);
  const districtName = decodeURIComponent(rawName)
    .toUpperCase()
    .replace(/-/g, " ");
  const stateFromParam = searchParams.state?.toUpperCase().replace(/-/g, " ") ?? null;
  const state = stateFromParam ?? (await getState(districtName));

  return { districtName, state };
}

export async function generateMetadata(props: DistrictPageProps) {
  const { districtName, state } = await resolveDistrict(props);
  const label = state
    ? formatDistrictLabel(districtName, state)
    : titleCasePlace(districtName);

  return {
    title: label,
    description: `Local welfare evidence, legal entitlements, complaint routes, and elected representatives for ${label}.`,
  };
}

export default async function DistrictPage(props: DistrictPageProps) {
  const { districtName, state } = await resolveDistrict(props);
  if (!state) notFound();

  const [brief, schemes] = await Promise.all([
    buildDistrictBrief(districtName, state),
    getDistrictSchemeRows(districtName, state),
  ]);
  const representatives: BriefRepresentative[] = brief.mps.map((mp) => ({
    role: "MP",
    name: displayPersonName(mp.mp_name),
    party: mp.party,
    area: titleCasePlace(mp.constituency),
  }));
  const representativeLabels = representatives.map(
    (representative) => `MP ${representative.name} (${representative.party})`,
  );
  const nothingChecked =
    brief.diagnosis.length === 0 && brief.schemes_checked.length === 0;
  const generatedDate = new Date(brief.generated_at).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  return (
    <div className="brief-shell">
      <nav className="breadcrumb" aria-label="Breadcrumb">
        <ol>
          <li><Link href="/">Home</Link></li>
          <li aria-hidden="true">/</li>
          <li>{titleCasePlace(districtName)}</li>
        </ol>
      </nav>

      <BriefOverview
        districtLabel={titleCasePlace(districtName)}
        stateLabel={titleCasePlace(state)}
        generatedDate={generatedDate}
        lineage={brief.formerly_part_of}
        diagnosis={brief.diagnosis}
        schemesChecked={brief.schemes_checked}
        guideCount={brief.complaint_kits.length}
        representatives={representatives}
        representativeNote={<PinPrecisionNote acCount={brief.ac_count} />}
      />

      <section id="issues" className="content-section">
        <SectionHeader
          title="What the public data flags"
          count={brief.diagnosis.length}
          description="District-level indicators, not a verdict on any individual case."
        />
        {brief.diagnosis.length > 0 ? (
          <div className="diagnosis-stack">
            {brief.diagnosis.map((item) => (
              <DiagnosisCard key={`${item.scheme}-${item.summary}`} item={item} />
            ))}
          </div>
        ) : (
          <p className={`notice${nothingChecked ? "" : " notice--success"}`}>
            {nothingChecked
              ? "The district-level sources we can test for shortfalls do not report enough data here. This is not an all-clear."
              : "No shortfall crossed our flag threshold in the district data checked. Personal grievances may still be valid."}
          </p>
        )}
      </section>

      <ComplaintKitSection
        kits={brief.complaint_kits}
        universal={brief.universal_channels}
        representatives={representativeLabels}
      />

      <SchemeDataSection schemes={schemes} />

      {schemes.length === 0 && (
        <section id="evidence" className="content-section">
          <SectionHeader title="Official figures behind this brief" count={0} />
          <p className="notice">
            We do not have district-level scheme figures for this district yet.
            This does not mean no money was allocated or no service was delivered.
          </p>
        </section>
      )}

      <footer className="brief-footer">
        <p>
          Data comes from official government portals. Financial figures are shown in
          Indian rupees (lakhs) and keep each source&apos;s latest reported period.
        </p>
      </footer>
    </div>
  );
}
