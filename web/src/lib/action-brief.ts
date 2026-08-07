/**
 * Citizen action brief: PIN -> district reality -> who is accountable ->
 * what to do about it.
 *
 * Called directly by the root service page (same process — no self-HTTP) and
 * wrapped by /api/v1/action/[pin_code] for external consumers.
 *
 * Runtime severity formulas are deliberately absent. Raw reported evidence is
 * rendered separately; a future judgment contract must be precomputed and
 * registered in DATA_CLAIMS.md before both public twins consume it.
 */

import { query, queryOne } from "@/lib/db";
import {
  candidateStates,
  pcNameNorm,
  stripReservation,
} from "@/lib/vintage-states";
import type {
  ActionBriefResponse,
  ActionItem,
  ComplaintKit,
  DiagnosisItem,
  GrievanceChannel,
  MPInfo,
} from "@/lib/action-types";

/**
 * Estimated MP lookup from the derived PIN→PC relation. Reservation suffixes
 * are normalized on both sides and state is matched against vintage-equivalent
 * labels. No district-level singular fallback is allowed.
 */
async function findMpByPin(pinCode: string): Promise<{
  mp: MPInfo;
  method: string;
} | null> {
  const pinPc = await queryOne<{ constituency: string; state: string; method: string }>(
    `SELECT constituency, state, method FROM pin_constituency WHERE pin_code = ?`,
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
    if (mp) return { mp, method: pinPc.method };
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
  scraped_at: string;
}

/**
 * WHY / WHO / HOW to complain for every curated scheme. Complaint rights are
 * independent of district performance-data coverage.
 */
export async function getComplaintCatalog(): Promise<{
  kits: ComplaintKit[];
  universal: GrievanceChannel[];
}> {
  const [channelRows, entitlements] = await Promise.all([
    query<GrievanceChannel>(
      `SELECT scheme, level, authority, portal_name, portal_url, phone,
              COALESCE(description, '') AS description, source_url, scraped_at
         FROM grievance_channels
        ORDER BY scheme, ${LEVEL_ORDER_SQL}, portal_name`,
      [],
    ),
    query<EntitlementRow>(
      `SELECT scheme, entitlement, legal_basis, complain_when, source_url, scraped_at
         FROM scheme_entitlements`,
      [],
    ),
  ]);
  const channels = channelRows.map((channel) => ({ ...channel }));

  const universal = channels.filter((c) => c.scheme === "ALL");
  const bySchemeChannels = new Map<string, GrievanceChannel[]>();
  for (const c of channels) {
    if (c.scheme === "ALL") continue;
    const list = bySchemeChannels.get(c.scheme) ?? [];
    list.push(c);
    bySchemeChannels.set(c.scheme, list);
  }
  const bySchemeEntitlement = new Map(entitlements.map((e) => [e.scheme, e]));

  const schemes = [
    ...new Set([
      ...entitlements.map((entitlement) => entitlement.scheme),
      ...bySchemeChannels.keys(),
    ]),
  ].sort((a, b) => a.localeCompare(b));

  const kits: ComplaintKit[] = [];
  for (const scheme of schemes) {
    const ent = bySchemeEntitlement.get(scheme);
    const schemeChannels = bySchemeChannels.get(scheme) ?? [];
    if (!ent && schemeChannels.length === 0) continue; // nothing curated — no kit
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
      flagged: false,
      entitlement: ent?.entitlement ?? null,
      legal_basis: ent?.legal_basis ?? null,
      complain_when: complainWhen,
      entitlement_source_url: ent?.source_url ?? null,
      entitlement_scraped_at: ent?.scraped_at ?? null,
      channels: schemeChannels,
    });
  }
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
  /** Assembly seats overlapping this district. Hisaab has no PIN-to-AC mapping. */
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
  const [lineage, mps, acCount] = await Promise.all([
    getLineage(district, state),
    findDistrictMps(district, state),
    queryOne<{ n: number }>(
      `SELECT COUNT(DISTINCT ac_name) AS n FROM ac_district
       WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?)`,
      [district, state],
    ),
  ]);
  const { kits, universal } = await getComplaintCatalog();
  return {
    district,
    state,
    formerly_part_of: lineage
      ? { parent_district: lineage.parent_district, split_year: lineage.split_year }
      : null,
    mps,
    ac_count: acCount?.n ?? 0,
    diagnosis: [],
    schemes_checked: [],
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
  const [lineage, pinMp] = await Promise.all([
    getLineage(district, state),
    findMpByPin(pinCode),
  ]);

  const { kits, universal } = await getComplaintCatalog();
  const grievanceChannels = kits.flatMap((kit) => kit.channels);
  const actions: ActionItem[] = kits.map((kit) => ({
    scheme: kit.scheme,
    steps: kit.channels.map((channel) => ({
      action: channel.portal_name,
      url: channel.portal_url,
      source_url: channel.source_url,
      verified_at: channel.scraped_at,
    })),
  }));

  return {
    pin: pinCode,
    district: mapping.district,
    state: mapping.state,
    formerly_part_of: lineage
      ? { parent_district: lineage.parent_district, split_year: lineage.split_year }
      : null,
    mp: pinMp?.mp ?? null,
    mla: null,
    representative_mapping: {
      mp_scope: pinMp ? "estimated_parliamentary_constituency" : "unavailable",
      mp_method: pinMp?.method ?? null,
      mla_scope: "unavailable",
      claim_id: "DERIVED-2026-0002",
    },
    diagnosis: [],
    schemes_checked: [],
    actions,
    grievance_channels: grievanceChannels,
    complaint_kits: kits,
    universal_channels: universal,
    scheme_data: {},
    generated_at: new Date().toISOString(),
  };
}
