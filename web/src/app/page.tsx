import AccountabilityResult, {
  type ResultRepresentative,
} from "@/components/AccountabilityResult";
import DistrictPicker from "@/components/DistrictPicker";
import PinEntry from "@/components/PinEntry";
import { buildActionBrief, buildDistrictBrief } from "@/lib/action-brief";
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

function Lookup({ error }: { error?: string }) {
  return (
    <div className="lookup-shell">
      <section className="lookup" aria-labelledby="lookup-heading">
        <h1 id="lookup-heading">Get help with a welfare problem.</h1>
        <p className="lookup__intro">
          Enter your PIN to see what you are owed, where to complain first, and who represents your area.
        </p>
        {error && <p className="lookup-error" role="alert">{error}</p>}
        <PinEntry />
        <DistrictPicker />
        <p className="lookup__privacy">
          No account required. Your PIN is used only to match the relevant district and constituency.
        </p>
      </section>
    </div>
  );
}

export default async function Home({ searchParams }: PageProps) {
  const search = await searchParams;
  const pin = param(search.pin)?.trim() ?? null;
  const rawDistrict = param(search.district)?.trim() ?? null;
  const rawState = param(search.state)?.trim() ?? null;

  if (pin) {
    if (!/^\d{6}$/.test(pin)) {
      return <Lookup error="Enter a valid 6-digit PIN code." />;
    }
    const brief = await buildActionBrief(pin);
    if (!brief) {
      return <Lookup error={`PIN ${pin} is not in the postal directory we serve.`} />;
    }
    const schemes = await getDistrictSchemeRows(brief.district, brief.state);
    const representatives: ResultRepresentative[] = [];
    if (brief.mp) {
      representatives.push({
        role: "MP",
        name: displayPersonName(brief.mp.mp_name),
        party: brief.mp.party,
        area: titleCasePlace(brief.mp.constituency),
        sourceUrl: brief.mp.source_url,
      });
    }
    if (brief.mla) {
      representatives.push({
        role: "MLA",
        name: displayPersonName(brief.mla.mla_name),
        party: brief.mla.party,
        area: titleCasePlace(brief.mla.ac_name),
        sourceUrl: brief.mla.source_url,
      });
    }

    return (
      <AccountabilityResult
        pin={pin}
        district={brief.district}
        state={brief.state}
        lineage={brief.formerly_part_of}
        diagnosis={brief.diagnosis}
        schemesChecked={brief.schemes_checked}
        complaintKits={brief.complaint_kits}
        universalChannels={brief.universal_channels}
        representatives={representatives}
        schemes={schemes}
      />
    );
  }

  if (rawDistrict) {
    const district = rawDistrict.toUpperCase().replace(/-/g, " ");
    const state = rawState?.toUpperCase().replace(/-/g, " ") ?? await resolveState(district);
    if (!state) {
      return <Lookup error="Choose a district together with its state." />;
    }
    const exists = await queryOne<{ present: number }>(
      `SELECT 1 AS present FROM district_scores
       WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?) LIMIT 1`,
      [district, state],
    );
    if (!exists) {
      return <Lookup error="That district and state combination is not in the registry." />;
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
        diagnosis={brief.diagnosis}
        schemesChecked={brief.schemes_checked}
        complaintKits={brief.complaint_kits}
        universalChannels={brief.universal_channels}
        representatives={representatives}
        schemes={schemes}
      />
    );
  }

  return <Lookup />;
}
