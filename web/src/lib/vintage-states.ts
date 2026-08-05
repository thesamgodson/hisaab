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
