import AccountabilityResult, { type ResultRepresentative } from "@/components/AccountabilityResult";
import ServiceStart from "@/components/ServiceStart";
import { buildActionBrief, buildDistrictBrief, getComplaintCatalog } from "@/lib/action-brief";
import { getAreaAccount } from "@/lib/area-account";
import { queryOne } from "@/lib/db";
import { displayPersonName, titleCasePlace } from "@/lib/format-place";

export const revalidate = 3600;

interface PageProps {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}

function param(value: string | string[] | undefined): string | null {
  if (Array.isArray(value)) return value[0] ?? null;
  return value ?? null;
}

function selectedTrigger(value: string | null, triggers: string[]): string | null {
  if (value == null || !/^\d+$/.test(value)) return null;
  return triggers[Number(value)] ?? null;
}

function resultRepresentatives(
  mps: Array<{ mp_name: string; party: string; constituency: string; source_url: string; elected_year: number }>,
): ResultRepresentative[] {
  return mps.map((mp) => ({
    role: "MP",
    name: displayPersonName(mp.mp_name),
    party: mp.party,
    area: titleCasePlace(mp.constituency),
    sourceUrl: mp.source_url,
    electedYear: mp.elected_year,
  }));
}

async function districtExists(district: string, state: string): Promise<boolean> {
  return Boolean(await queryOne<{ present: number }>(
    `SELECT 1 AS present FROM (
       SELECT district, state FROM district_scores
       UNION
       SELECT district, state FROM pin_district_mapping
     ) WHERE district = ? AND state = ? LIMIT 1`,
    [district, state],
  ));
}

export default async function Home({ searchParams }: PageProps) {
  const search = await searchParams;
  const pin = param(search.pin)?.trim() ?? null;
  const rawDistrict = param(search.district)?.trim() ?? null;
  const rawState = param(search.state)?.trim() ?? null;
  const issue = param(search.issue)?.trim() ?? null;
  const trigger = param(search.trigger)?.trim() ?? null;

  if (!pin && !rawDistrict && !issue) {
    return <div className="lookup-shell"><ServiceStart /></div>;
  }

  const { kits, universal } = await getComplaintCatalog();
  const kit = kits.find((item) => item.scheme === issue) ?? null;
  const general = issue === "ALL";
  const triggerText = kit ? selectedTrigger(trigger, kit.complain_when) : null;
  const preservedIssue = general ? "ALL" : kit?.scheme ?? null;

  if (!pin && !rawDistrict) {
    return (
      <div className="lookup-shell">
        <ServiceStart
          issue={preservedIssue}
          error={issue && !kit && !general ? "That service is not in the current guide." : undefined}
        />
      </div>
    );
  }

  if (pin) {
    if (!/^\d{6}$/.test(pin)) {
      return <div className="lookup-shell"><ServiceStart issue={preservedIssue} error="Enter a valid 6-digit PIN code." /></div>;
    }
    const brief = await buildActionBrief(pin);
    if (!brief) {
      return <div className="lookup-shell"><ServiceStart issue={preservedIssue} error={`PIN ${pin} is not in the postal directory we serve.`} /></div>;
    }
    const [account, districtBrief] = await Promise.all([
      getAreaAccount(brief.district, brief.state),
      buildDistrictBrief(brief.district, brief.state),
    ]);
    return (
      <AccountabilityResult
        pin={pin}
        district={brief.district}
        state={brief.state}
        lineage={brief.formerly_part_of}
        account={account}
        complaintSchemes={kits.map((item) => item.scheme)}
        complaintKits={kit ? [kit] : []}
        universalChannels={kit || general ? universal : []}
        representatives={resultRepresentatives(districtBrief.mps)}
        representativeContext="A PIN resolves to a postal district, not an exact constituency. These MPs represent mapped parliamentary constituencies that overlap the district; Hisaab does not claim an exact MLA."
        selectedScheme={kit?.scheme ?? null}
        selectedTrigger={triggerText}
        general={general}
      />
    );
  }

  const district = rawDistrict!.toUpperCase().replace(/-/g, " ");
  const state = rawState?.toUpperCase().replace(/-/g, " ") ?? null;
  if (!state) {
    return <div className="lookup-shell"><ServiceStart issue={preservedIssue} error="Choose a district together with its state." /></div>;
  }
  if (!await districtExists(district, state)) {
    return <div className="lookup-shell"><ServiceStart issue={preservedIssue} error="That district and state combination is not in the registry." /></div>;
  }
  const [brief, account] = await Promise.all([
    buildDistrictBrief(district, state),
    getAreaAccount(district, state),
  ]);
  return (
    <AccountabilityResult
      district={district}
      state={state}
      lineage={brief.formerly_part_of}
      account={account}
      complaintSchemes={kits.map((item) => item.scheme)}
      complaintKits={kit ? [kit] : []}
      universalChannels={kit || general ? universal : []}
      representatives={resultRepresentatives(brief.mps)}
      representativeContext="A district can overlap several parliamentary constituencies. These MPs represent mapped parliamentary constituencies that overlap the district."
      selectedScheme={kit?.scheme ?? null}
      selectedTrigger={triggerText}
      general={general}
    />
  );
}
