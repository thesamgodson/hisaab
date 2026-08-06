import AccountabilityResult, {
  type ResultRepresentative,
} from "@/components/AccountabilityResult";
import GeneralResult from "@/components/GeneralResult";
import ServiceStart from "@/components/ServiceStart";
import { buildActionBrief, buildDistrictBrief, getComplaintCatalog } from "@/lib/action-brief";
import { queryOne, resolveState } from "@/lib/db";
import { displayPersonName, titleCasePlace } from "@/lib/format-place";
import { getDistrictSchemeRows } from "@/lib/money-flow";

export const revalidate = 3600;

interface PageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

function param(value: string | string[] | undefined): string | null {
  if (Array.isArray(value)) return value[0] ?? null;
  return value ?? null;
}

function triggerIndex(value: string | null, count: number): number | null {
  if (value == null || !/^\d+$/.test(value)) return null;
  const index = Number(value);
  return index >= 0 && index < count ? index : null;
}

export default async function Home({ searchParams }: PageProps) {
  const search = await searchParams;
  const pin = param(search.pin)?.trim() ?? null;
  const rawDistrict = param(search.district)?.trim() ?? null;
  const rawState = param(search.state)?.trim() ?? null;
  const issue = param(search.issue)?.trim() ?? null;
  const trigger = param(search.trigger)?.trim() ?? null;
  const { kits: complaintKits, universal: universalChannels } = await getComplaintCatalog();
  const selectedKit = complaintKits.find((kit) => kit.scheme === issue) ?? null;
  const general = issue === "ALL";
  const selectedTriggerIndex = selectedKit
    ? triggerIndex(trigger, selectedKit.complain_when.length)
    : null;
  const area = {
    pin: pin ?? undefined,
    district: rawDistrict ?? undefined,
    state: rawState ?? undefined,
  };

  if (!selectedKit && !general) {
    return (
      <div className="lookup-shell">
        <ServiceStart
          kits={complaintKits}
          area={area}
          error={issue ? "Choose a problem from the list." : undefined}
        />
      </div>
    );
  }

  if (selectedKit && selectedTriggerIndex == null) {
    return (
      <div className="lookup-shell">
        <ServiceStart
          kits={complaintKits}
          selectedKit={selectedKit}
          area={area}
          error={trigger ? "Choose one of the listed situations." : undefined}
        />
      </div>
    );
  }

  if (general) {
    return <GeneralResult universal={universalChannels} />;
  }

  if (!pin && !rawDistrict) {
    return (
      <div className="lookup-shell">
        <ServiceStart
          kits={complaintKits}
          selectedKit={selectedKit}
          triggerIndex={selectedTriggerIndex}
        />
      </div>
    );
  }

  if (pin) {
    if (!/^\d{6}$/.test(pin)) {
      return (
        <div className="lookup-shell">
          <ServiceStart kits={complaintKits} selectedKit={selectedKit}
            triggerIndex={selectedTriggerIndex}
            error="Enter a valid 6-digit PIN code." />
        </div>
      );
    }
    const brief = await buildActionBrief(pin);
    if (!brief) {
      return (
        <div className="lookup-shell">
          <ServiceStart kits={complaintKits} selectedKit={selectedKit}
            triggerIndex={selectedTriggerIndex}
            error={`PIN ${pin} is not in the postal directory we serve.`} />
        </div>
      );
    }
    const [schemes, districtBrief] = await Promise.all([
      getDistrictSchemeRows(brief.district, brief.state),
      buildDistrictBrief(brief.district, brief.state),
    ]);
    const representatives: ResultRepresentative[] = districtBrief.mps.map((mp) => ({
      role: "MP",
      name: displayPersonName(mp.mp_name),
      party: mp.party,
      area: titleCasePlace(mp.constituency),
      sourceUrl: mp.source_url,
    }));

    return (
      <AccountabilityResult
        pin={pin}
        district={brief.district}
        state={brief.state}
        lineage={brief.formerly_part_of}
        complaintKits={selectedKit ? [selectedKit] : []}
        universalChannels={universalChannels}
        representatives={representatives}
        representativeContext="A PIN resolves to a postal district, not a reliable assembly-constituency match. These MPs represent constituencies overlapping the district; Hisaab does not claim an exact MLA."
        schemes={schemes}
        selectedScheme={selectedKit?.scheme ?? null}
        selectedTrigger={selectedKit && selectedTriggerIndex != null
          ? selectedKit.complain_when[selectedTriggerIndex]
          : null}
        selectedTriggerIndex={selectedTriggerIndex}
      />
    );
  }

  if (rawDistrict) {
    const district = rawDistrict.toUpperCase().replace(/-/g, " ");
    const state = rawState?.toUpperCase().replace(/-/g, " ") ?? await resolveState(district);
    if (!state) {
      return (
        <div className="lookup-shell">
          <ServiceStart kits={complaintKits} selectedKit={selectedKit}
            triggerIndex={selectedTriggerIndex}
            error="Choose a district together with its state." />
        </div>
      );
    }
    const exists = await queryOne<{ present: number }>(
      `SELECT 1 AS present FROM (
         SELECT district, state FROM district_scores
         UNION
         SELECT district, state FROM pin_district_mapping
       )
       WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?) LIMIT 1`,
      [district, state],
    );
    if (!exists) {
      return (
        <div className="lookup-shell">
          <ServiceStart kits={complaintKits} selectedKit={selectedKit}
            triggerIndex={selectedTriggerIndex}
            error="That district and state combination is not in the registry." />
        </div>
      );
    }
    const [brief, schemes] = await Promise.all([
      buildDistrictBrief(district, state),
      getDistrictSchemeRows(district, state),
    ]);
    const representatives: ResultRepresentative[] = brief.mps.map((mp) => ({
      role: "MP",
      name: displayPersonName(mp.mp_name),
      party: mp.party,
      area: titleCasePlace(mp.constituency),
      sourceUrl: mp.source_url,
    }));

    return (
      <AccountabilityResult
        district={district}
        state={state}
        lineage={brief.formerly_part_of}
        complaintKits={selectedKit ? [selectedKit] : []}
        universalChannels={universalChannels}
        representatives={representatives}
        representativeContext="A district can overlap several parliamentary and assembly constituencies. These MPs represent the overlapping parliamentary constituencies."
        schemes={schemes}
        selectedScheme={selectedKit?.scheme ?? null}
        selectedTrigger={selectedKit && selectedTriggerIndex != null
          ? selectedKit.complain_when[selectedTriggerIndex]
          : null}
        selectedTriggerIndex={selectedTriggerIndex}
      />
    );
  }

  return null;
}
