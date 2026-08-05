import { PC_NAME_REGISTRY } from "@/lib/pc-name-registry";

// datameet's 2008-delimitation polygons predate Telangana (2014) and Ladakh
// (2019): constituency_district/ac_district rows carry the parent state's
// label while pin_district_mapping/mp_info/mla_info carry today's. Queries
// that join across that divide must accept either label. Keep in lockstep
// with VINTAGE_STATE_EQUIV in scripts/clean_pin_constituency.py.
const VINTAGE_STATE_EQUIV: Record<string, string[]> = {
  "ANDHRA PRADESH": ["TELANGANA"],
  TELANGANA: ["ANDHRA PRADESH"],
  "JAMMU AND KASHMIR": ["LADAKH"],
  LADAKH: ["JAMMU AND KASHMIR"],
};

/** The state's own canonical name plus any vintage-equivalent labels. */
export function candidateStates(state: string): string[] {
  const upper = state.toUpperCase();
  return [upper, ...(VINTAGE_STATE_EQUIV[upper] ?? [])];
}

// datameet writes reservation suffixes with and without a leading space
// ("GAYA (SC)", "WARANGAL(SC)"); OpenCity/MyNeta mostly drop them. Both
// sides of any cross-source PC/AC name join must pass through this
// normalizer. Keep in lockstep with PC_NAME_NORM_SQL in constituency/mapper.py.
export function pcNameNorm(expr: string): string {
  return (
    `TRIM(REPLACE(REPLACE(REPLACE(REPLACE(UPPER(${expr}),` +
    ` ' (SC)', ''), ' (ST)', ''), '(SC)', ''), '(ST)', ''))`
  );
}

/** JS twin of pcNameNorm, for query parameters. */
export function stripReservation(name: string): string {
  return name
    .trim()
    .toUpperCase()
    .replace(/\s*\((?:SC|ST)\)\s*$/, "")
    .trim();
}

// Stored PC labels are canonical (the state-scoped registry is applied at
// ingest/load — constituency/pc_name_registry.py, CLAIM-2026-0036), so joins
// between tables need only pcNameNorm. User-supplied names go through this
// expansion so legacy forms (PONDICHERRY, KALIABOR, PATLIPUTRA) still
// resolve. Twin of pc_name_lookup_candidates in the Python registry.
export function pcNameLookupCandidates(name: string, state?: string): string[] {
  const collapsed = name.trim().toUpperCase().replace(/\s+/g, " ");
  const stripped = stripReservation(collapsed);
  const scopes = state ? candidateStates(state) : Object.keys(PC_NAME_REGISTRY);
  const out = [stripped];
  for (const st of scopes) {
    const variants = PC_NAME_REGISTRY[st];
    const hit = variants?.[collapsed] ?? variants?.[stripped];
    if (hit) {
      const clean = stripReservation(hit);
      if (!out.includes(clean)) out.push(clean);
    }
  }
  return out;
}
