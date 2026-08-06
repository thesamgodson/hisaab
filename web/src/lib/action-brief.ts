/**
 * Citizen action brief: PIN -> district reality -> who is accountable ->
 * what to do about it.
 *
 * Called directly by the /action/[pin] page (same process — no self-HTTP)
 * and wrapped by /api/v1/action/[pin_code] for external consumers.
 *
 * Diagnosis rules only use metrics with an honest shortfall interpretation.
 * PM POSHAN, NFSA, and NSAP have none at district level (daily-snapshot
 * feeding, active=total by construction, no eligibility target — see
 * DATA_CLAIMS.md), so they are never diagnosed, only reported.
 */

import { getLatestFinYear } from "@/lib/fin-year";
import { query, queryOne } from "@/lib/db";
import {
  candidateStates,
  pcNameNorm,
  stripReservation,
} from "@/lib/vintage-states";
import type {
  ActionBriefResponse,
  ActionItem,
  ActionStep,
  ComplaintKit,
  DiagnosisItem,
  GrievanceChannel,
  MPInfo,
  SchemeDataEntry,
} from "@/lib/action-types";

const SEVERITY_ORDER: Record<string, number> = { high: 0, medium: 1, low: 2 };

const SCHEME_ACTIONS: Record<string, ActionStep[]> = {
  MGNREGA: [
    { action: "File RTI on MGNREGA portal", url: "https://nrega.nic.in" },
    { action: "Escalate grievance via PG Portal", url: "https://pgportal.gov.in" },
  ],
  "PMAY-G": [
    { action: "Check beneficiary status on PMAY-G portal", url: "https://pmayg.nic.in" },
    { action: "File complaint on PMAY-G grievance portal", url: "https://pmayg.nic.in/grievance" },
  ],
  JJM: [
    { action: "Check tap connection status", url: "https://ejalshakti.gov.in" },
    { action: "File complaint on JJM portal", url: "https://jaljeevanmission.gov.in" },
  ],
  PMGSY: [
    { action: "Check road status on OMMS", url: "https://omms.nic.in" },
    { action: "File complaint on PMGSY portal", url: "https://pmgsy.nic.in" },
  ],
};

/** Shortfall findings plus the schemes we actually had district data to check. */
interface Diagnosis {
  items: DiagnosisItem[];
  schemesChecked: string[];
}

async function buildDiagnosis(
  district: string,
  state: string,
  finYear: string,
): Promise<Diagnosis> {
  const items: DiagnosisItem[] = [];
  // An empty diagnosis means "nothing wrong" only if something was looked at;
  // urban districts report none of these at district level.
  const checked = new Set<string>();

  // MGNREGA misappropriation
  const misapprop = await queryOne<Record<string, unknown>>(
    `SELECT * FROM misappropriation WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?) AND fin_year = ?`,
    [district, state, finYear],
  );
  if (misapprop) {
    checked.add("MGNREGA");
    const recoveryRate = Number(misapprop.recovery_rate_pct ?? 100);
    if (recoveryRate < 50) {
      items.push({
        severity: "high",
        scheme: "MGNREGA",
        summary: `Recovery rate only ${recoveryRate.toFixed(0)}%`,
        detail: `Rs ${Number(misapprop.amount_reported ?? 0).toFixed(2)}L reported misappropriated, only ${recoveryRate.toFixed(0)}% recovered`,
        amount: Number(misapprop.amount_reported ?? 0),
        source_url: (misapprop.source_url as string) ?? null,
      });
    }
  }

  // MGNREGA financial utilization
  const financial = await queryOne<Record<string, unknown>>(
    `SELECT * FROM financial_statement WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?) AND fin_year = ?`,
    [district, state, finYear],
  );
  if (financial) {
    checked.add("MGNREGA");
    const totalAvail = Number(financial.total_availability ?? 0);
    const totalExpend = Number(financial.cumulative_expenditure ?? 0);
    const utilizationPct = Number(
      financial.utilization_pct ??
        (totalAvail > 0 ? (totalExpend / totalAvail) * 100 : 100),
    );
    if (utilizationPct < 60) {
      items.push({
        severity: "high",
        scheme: "MGNREGA",
        summary: `Fund utilization only ${utilizationPct.toFixed(0)}%`,
        detail: `Rs ${totalExpend.toFixed(2)}L spent of Rs ${totalAvail.toFixed(2)}L available`,
        amount: totalAvail - totalExpend,
        source_url: (financial.source_url as string) ?? null,
      });
    }
  }

  // PMAY-G
  const pmayg = await queryOne<Record<string, unknown>>(
    `SELECT * FROM pmayg_district WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?) AND fin_year = ?`,
    [district, state, finYear],
  );
  if (pmayg) {
    checked.add("PMAY-G");
    const sanctioned = Number(pmayg.houses_sanctioned ?? 0);
    const completed = Number(pmayg.houses_completed ?? 0);
    const pct = sanctioned > 0 ? (completed / sanctioned) * 100 : 100;
    if (pct < 50) {
      items.push({
        severity: "high",
        scheme: "PMAY-G",
        summary: `House completion only ${pct.toFixed(0)}%`,
        detail: `${completed} of ${sanctioned} sanctioned houses completed`,
        amount: null,
        source_url: (pmayg.source_url as string) ?? null,
      });
    }
  }

  // JJM
  const jjm = await queryOne<Record<string, unknown>>(
    `SELECT * FROM jjm_district WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?) AND fin_year = ?`,
    [district, state, finYear],
  );
  if (jjm) {
    checked.add("JJM");
    const coveragePct = Number(jjm.coverage_pct ?? 100);
    if (coveragePct < 50) {
      items.push({
        severity: "high",
        scheme: "JJM",
        summary: `Tap water coverage only ${coveragePct.toFixed(0)}%`,
        detail: `${Number(jjm.households_with_tap ?? 0).toLocaleString("en-IN")} households with tap connections`,
        amount: null,
        source_url: (jjm.source_url as string) ?? null,
      });
    }
  }

  // PMGSY
  const pmgsy = await queryOne<Record<string, unknown>>(
    `SELECT * FROM pmgsy_district WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?)`,
    [district, state],
  );
  if (pmgsy) {
    checked.add("PMGSY");
    const sanctioned = Number(pmgsy.length_sanctioned_km ?? 0);
    const completed = Number(pmgsy.length_completed_km ?? 0);
    const pct = sanctioned > 0 ? (completed / sanctioned) * 100 : 100;
    if (pct < 50) {
      items.push({
        severity: "high",
        scheme: "PMGSY",
        summary: `Road completion only ${pct.toFixed(0)}%`,
        detail: `${completed.toFixed(1)} km of ${sanctioned.toFixed(1)} km sanctioned roads completed`,
        amount: null,
        source_url: (pmgsy.source_url as string) ?? null,
      });
    }
  }

  items.sort(
    (a, b) => (SEVERITY_ORDER[a.severity] ?? 9) - (SEVERITY_ORDER[b.severity] ?? 9),
  );
  return { items: items.slice(0, 5), schemesChecked: [...checked] };
}

/**
 * Fallback MP lookup for PINs whose district has no constituency_district row
 * (all of Delhi, among others) but does have a spatial PIN→PC match. Same join
 * discipline as /api/v1/pin/[pin_code]: reservation suffixes normalized on both
 * sides, state matched against its vintage-equivalent labels.
 */
async function findMpByPin(pinCode: string): Promise<MPInfo | null> {
  const pinPc = await queryOne<{ constituency: string; state: string }>(
    `SELECT constituency, state FROM pin_constituency WHERE pin_code = ?`,
    [pinCode],
  );
  if (!pinPc) return null;

  for (const st of candidateStates(pinPc.state)) {
    const mp = await queryOne<MPInfo>(
      `SELECT mp_name, party, constituency, state, elected_year, source_url
       FROM mp_info
       WHERE ${pcNameNorm("constituency")} = ?
         AND UPPER(state) = ?`,
      [stripReservation(pinPc.constituency), st],
    );
    if (mp) return mp;
  }
  return null;
}

const LEVEL_ORDER_SQL =
  "CASE level WHEN 'local' THEN 0 WHEN 'district' THEN 1 WHEN 'state' THEN 2 WHEN 'national' THEN 3 ELSE 4 END";

interface EntitlementRow {
  scheme: string;
  entitlement: string;
  legal_basis: string;
  complain_when: string | null;
  source_url: string;
}

/**
 * WHY / WHO / HOW to complain, per scheme with a presence in this district.
 * Deliberately NOT gated on a flagged shortfall: a citizen's personal
 * grievance (delayed wages, refused rations) exists regardless of whether the
 * district aggregate crosses a diagnosis threshold. Flagged schemes sort
 * first. Empty until the curated grievance data is published.
 */
async function buildComplaintKits(
  district: string,
  state: string,
  flaggedSchemes: string[],
): Promise<{ kits: ComplaintKit[]; universal: GrievanceChannel[] }> {
  const [present, channels, entitlements] = await Promise.all([
    query<{ scheme: string }>(
      `SELECT DISTINCT scheme FROM scheme_delivery
        WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?)
       UNION
       SELECT DISTINCT scheme FROM money_flow
        WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?)`,
      [district, state, district, state],
    ),
    query<GrievanceChannel>(
      `SELECT scheme, level, authority, portal_name, portal_url, phone,
              COALESCE(description, '') AS description
         FROM grievance_channels
        ORDER BY scheme, ${LEVEL_ORDER_SQL}`,
      [],
    ),
    query<EntitlementRow>(
      `SELECT scheme, entitlement, legal_basis, complain_when, source_url
         FROM scheme_entitlements`,
      [],
    ),
  ]);

  const universal = channels.filter((c) => c.scheme === "ALL");
  const bySchemeChannels = new Map<string, GrievanceChannel[]>();
  for (const c of channels) {
    if (c.scheme === "ALL") continue;
    const list = bySchemeChannels.get(c.scheme) ?? [];
    list.push(c);
    bySchemeChannels.set(c.scheme, list);
  }
  const bySchemeEntitlement = new Map(entitlements.map((e) => [e.scheme, e]));

  const flagged = new Set(flaggedSchemes);
  const schemes = [
    ...new Set([...flaggedSchemes, ...present.map((p) => p.scheme)]),
  ];

  const kits: ComplaintKit[] = [];
  for (const scheme of schemes) {
    const ent = bySchemeEntitlement.get(scheme);
    const laddered = bySchemeChannels.get(scheme) ?? [];
    if (!ent && laddered.length === 0) continue; // nothing curated — no kit
    let complainWhen: string[] = [];
    if (ent?.complain_when) {
      try {
        const parsed: unknown = JSON.parse(ent.complain_when);
        if (Array.isArray(parsed)) complainWhen = parsed.map(String);
      } catch {
        complainWhen = [ent.complain_when];
      }
    }
    kits.push({
      scheme,
      flagged: flagged.has(scheme),
      entitlement: ent?.entitlement ?? null,
      legal_basis: ent?.legal_basis ?? null,
      complain_when: complainWhen,
      entitlement_source_url: ent?.source_url ?? null,
      channels: laddered,
    });
  }
  kits.sort(
    (a, b) =>
      Number(b.flagged) - Number(a.flagged) || a.scheme.localeCompare(b.scheme),
  );
  return { kits, universal };
}

async function getLineage(district: string, state: string) {
  return queryOne<{ parent_district: string; split_year: number }>(
    `SELECT parent_district, split_year FROM district_lineage
     WHERE UPPER(new_district) = UPPER(?) AND UPPER(state) = UPPER(?)`,
    [district, state],
  );
}

/** All MPs whose constituencies overlap this district — the honest plural
 *  answer at district grain (a district commonly spans 2-3 PCs). */
async function findDistrictMps(
  district: string,
  state: string,
): Promise<MPInfo[]> {
  const states = candidateStates(state);
  const slots = states.map(() => "?").join(", ");
  return query<MPInfo>(
    `SELECT DISTINCT m.mp_name, m.party, m.constituency, m.state,
            m.elected_year, m.source_url
     FROM constituency_district cd
     JOIN mp_info m
       ON ${pcNameNorm("m.constituency")} = ${pcNameNorm("cd.constituency")}
      AND UPPER(m.state) IN (${slots})
     WHERE UPPER(cd.district) = UPPER(?) AND UPPER(cd.state) IN (${slots})
     ORDER BY m.constituency`,
    [...states, district, ...states],
  );
}

/** District-grain brief: what the /district page renders, and what the
 *  PIN-grain brief specializes. Same sections, honest plural representatives. */
export interface DistrictBriefResponse {
  district: string;
  state: string;
  formerly_part_of: { parent_district: string; split_year: number } | null;
  mps: MPInfo[];
  /** Assembly seats overlapping this district — a PIN pins down which one. */
  ac_count: number;
  diagnosis: DiagnosisItem[];
  schemes_checked: string[];
  complaint_kits: ComplaintKit[];
  universal_channels: GrievanceChannel[];
  generated_at: string;
}

export async function buildDistrictBrief(
  district: string,
  state: string,
): Promise<DistrictBriefResponse> {
  const finYear = await getLatestFinYear();
  const [lineage, mps, acCount, diagnosis] = await Promise.all([
    getLineage(district, state),
    findDistrictMps(district, state),
    queryOne<{ n: number }>(
      `SELECT COUNT(DISTINCT ac_name) AS n FROM ac_district
       WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?)`,
      [district, state],
    ),
    buildDiagnosis(district, state, finYear),
  ]);
  const { kits, universal } = await buildComplaintKits(
    district,
    state,
    [...new Set(diagnosis.items.map((d) => d.scheme))],
  );
  return {
    district,
    state,
    formerly_part_of: lineage
      ? { parent_district: lineage.parent_district, split_year: lineage.split_year }
      : null,
    mps,
    ac_count: acCount?.n ?? 0,
    diagnosis: diagnosis.items,
    schemes_checked: diagnosis.schemesChecked,
    complaint_kits: kits,
    universal_channels: universal,
    generated_at: new Date().toISOString(),
  };
}

/** Build the full action brief for a PIN, or null when the PIN is unknown. */
export async function buildActionBrief(
  pinCode: string,
): Promise<ActionBriefResponse | null> {
  const mapping = await queryOne<{
    pin_code: string;
    district: string;
    state: string;
    office_name: string;
  }>(`SELECT * FROM pin_district_mapping WHERE pin_code = ?`, [pinCode]);

  if (!mapping) return null;

  const { district, state } = mapping;
  const states = candidateStates(state);
  const stateSlots = states.map(() => "?").join(", ");
  const finYear = await getLatestFinYear();

  const [lineage, mpRow, mlaRow, diagnosis] = await Promise.all([
    getLineage(district, state),
    queryOne<{
      mp_name: string;
      party: string;
      constituency: string;
      state: string;
      elected_year: number;
      source_url: string;
    }>(
      // States join through candidateStates (constituency_district carries
      // vintage pre-bifurcation labels; PC names repeat across states).
      // Names join through the shared normalizer: datameet keeps reservation
      // suffixes (with and without a leading space), OpenCity/MyNeta drop them.
      `SELECT m.mp_name, m.party, m.constituency, m.state, m.elected_year, m.source_url
       FROM constituency_district cd
       JOIN mp_info m
         ON ${pcNameNorm("m.constituency")} = ${pcNameNorm("cd.constituency")}
        AND UPPER(m.state) IN (${stateSlots})
       WHERE UPPER(cd.district) = UPPER(?) AND UPPER(cd.state) IN (${stateSlots})
       LIMIT 1`,
      [...states, district, ...states],
    ),
    queryOne<{
      mla_name: string;
      party: string;
      ac_name: string;
      state: string;
      source_url: string;
    }>(
      `SELECT ml.mla_name, ml.party, ml.ac_name, ml.state, ml.source_url
       FROM ac_district ac
       JOIN mla_info ml
         ON ${pcNameNorm("ml.ac_name")} = ${pcNameNorm("ac.ac_name")}
        AND UPPER(ml.state) IN (${stateSlots})
       WHERE UPPER(ac.district) = UPPER(?) AND UPPER(ac.state) IN (${stateSlots})
       LIMIT 1`,
      [...states, district, ...states],
    ),
    buildDiagnosis(district, state, finYear),
  ]);

  const mp = mpRow ?? (await findMpByPin(pinCode));

  const flaggedSchemes = [...new Set(diagnosis.items.map((d) => d.scheme))];
  const { kits, universal } = await buildComplaintKits(
    district,
    state,
    flaggedSchemes,
  );
  let grievanceChannels: GrievanceChannel[] = [];
  if (flaggedSchemes.length > 0) {
    const placeholders = flaggedSchemes.map(() => "?").join(",");
    grievanceChannels = await query<GrievanceChannel>(
      `SELECT * FROM grievance_channels
       WHERE scheme IN (${placeholders})
       ORDER BY scheme, CASE level WHEN 'district' THEN 1 WHEN 'state' THEN 2 WHEN 'national' THEN 3 ELSE 4 END`,
      flaggedSchemes,
    );
  }

  const actions: ActionItem[] = flaggedSchemes
    .filter((scheme) => SCHEME_ACTIONS[scheme])
    .map((scheme) => ({ scheme, steps: SCHEME_ACTIONS[scheme] }));

  const schemeData: Record<string, SchemeDataEntry> = {};
  for (const item of diagnosis.items) {
    if (!schemeData[item.scheme]) {
      schemeData[item.scheme] = {
        severity: item.severity,
        summary: item.summary,
        detail: item.detail,
        amount: item.amount,
        source_url: item.source_url,
      };
    }
  }

  return {
    pin: pinCode,
    district: mapping.district,
    state: mapping.state,
    formerly_part_of: lineage
      ? { parent_district: lineage.parent_district, split_year: lineage.split_year }
      : null,
    mp: mp ?? null,
    mla: mlaRow ?? null,
    diagnosis: diagnosis.items,
    schemes_checked: diagnosis.schemesChecked,
    actions,
    grievance_channels: grievanceChannels,
    complaint_kits: kits,
    universal_channels: universal,
    scheme_data: schemeData,
    generated_at: new Date().toISOString(),
  };
}
