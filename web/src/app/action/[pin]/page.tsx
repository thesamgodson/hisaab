import { cache } from "react";
import type { Metadata } from "next";
import Link from "next/link";
import BriefOverview, {
  type BriefRepresentative,
} from "@/components/BriefOverview";
import ComplaintKitSection from "@/components/ComplaintKit";
import DiagnosisCard from "@/components/DiagnosisCard";
import PinNotice from "@/components/PinNotice";
import SchemeDataSection from "@/components/SchemeDataSection";
import SectionHeader from "@/components/SectionHeader";
import { buildActionBrief } from "@/lib/action-brief";
import { displayPersonName, titleCasePlace } from "@/lib/format-place";
import { getDistrictSchemeRows } from "@/lib/money-flow";
import { schemeDisplay } from "@/lib/scheme-display";

const getBrief = cache(buildActionBrief);
export const revalidate = 3600;

interface PageProps {
  params: Promise<{ pin: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { pin } = await params;
  if (!/^\d{6}$/.test(pin)) return { title: "Invalid PIN code" };

  const data = await getBrief(pin);
  if (!data) return { title: `PIN ${pin}` };

  return {
    title: `PIN ${pin} · ${titleCasePlace(data.district)}`,
    description: `Local welfare evidence, legal entitlements, complaint routes, and elected representatives for PIN ${pin}.`,
  };
}

export default async function ActionPage({ params }: PageProps) {
  const { pin } = await params;

  if (!/^\d{6}$/.test(pin)) {
    return (
      <PinNotice heading="Invalid PIN code">
        &ldquo;{pin}&rdquo; is not a valid 6-digit PIN code.
      </PinNotice>
    );
  }

  const data = await getBrief(pin);
  if (!data) {
    return (
      <PinNotice heading={`PIN ${pin} not found`}>
        This PIN isn&apos;t in the postal directory we serve. Double-check the
        code, or try a nearby PIN.
      </PinNotice>
    );
  }

  const schemes = await getDistrictSchemeRows(data.district, data.state);
  const districtSlug = data.district.toLowerCase().replace(/\s+/g, "-");
  const districtHref = `/district/${districtSlug}?state=${encodeURIComponent(data.state)}`;
  const generatedDate = new Date(data.generated_at).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
  const representatives: BriefRepresentative[] = [];

  if (data.mp) {
    representatives.push({
      role: "MP",
      name: displayPersonName(data.mp.mp_name),
      party: data.mp.party,
      area: titleCasePlace(data.mp.constituency),
    });
  }
  if (data.mla) {
    representatives.push({
      role: "MLA",
      name: displayPersonName(data.mla.mla_name),
      party: data.mla.party,
      area: titleCasePlace(data.mla.ac_name),
    });
  }

  const nothingChecked =
    data.diagnosis.length === 0 && data.schemes_checked.length === 0;
  const representativeLabels = representatives.map(
    (representative) => `${representative.role} ${representative.name} (${representative.party})`,
  );

  return (
    <div className="brief-shell">
      <nav className="breadcrumb" aria-label="Breadcrumb">
        <ol>
          <li><Link href="/">Home</Link></li>
          <li aria-hidden="true">/</li>
          <li>PIN {pin}</li>
        </ol>
      </nav>

      <BriefOverview
        districtLabel={titleCasePlace(data.district)}
        stateLabel={titleCasePlace(data.state)}
        pin={pin}
        generatedDate={generatedDate}
        lineage={data.formerly_part_of}
        diagnosis={data.diagnosis}
        schemesChecked={data.schemes_checked}
        guideCount={data.complaint_kits.length}
        representatives={representatives}
      />

      <section id="issues" className="content-section">
        <SectionHeader
          title="What the public data flags"
          count={data.diagnosis.length}
          description="District-level indicators, not a verdict on your individual case."
        />
        {data.diagnosis.length > 0 ? (
          <div className="diagnosis-stack">
            {data.diagnosis.map((item) => (
              <DiagnosisCard key={`${item.scheme}-${item.summary}`} item={item} />
            ))}
          </div>
        ) : (
          <p className={`notice${nothingChecked ? "" : " notice--success"}`}>
            {nothingChecked
              ? "The district-level sources we can test for shortfalls do not report enough data here. This is not an all-clear."
              : `No shortfall crossed our flag threshold in ${formatSchemeList(data.schemes_checked)}. Personal grievances may still be valid.`}
          </p>
        )}
      </section>

      <ComplaintKitSection
        kits={data.complaint_kits}
        universal={data.universal_channels}
        representatives={representativeLabels}
      />

      <SchemeDataSection schemes={schemes} />

      {schemes.length === 0 && (
        <section id="evidence" className="content-section">
          <SectionHeader title="Official figures behind this brief" count={0} />
          <p className="notice">
            We do not have district-level scheme figures for this area yet.
            This does not mean no money was allocated or no service was delivered.
          </p>
        </section>
      )}

      <footer className="brief-footer">
        <Link href={districtHref}>View the district-level brief</Link>
        <p>Data comes from official government portals. Every finding links to its source.</p>
      </footer>
    </div>
  );
}

const SCHEME_LIST_FORMAT = new Intl.ListFormat("en", { type: "conjunction" });

function formatSchemeList(schemes: string[]): string {
  return SCHEME_LIST_FORMAT.format(
    schemes.map((scheme) => schemeDisplay(scheme).shortNeed.toLowerCase()),
  );
}
