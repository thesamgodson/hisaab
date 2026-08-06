/**
 * Display-only place formatting. Canonical names in the DB, joins, and URLs
 * are UPPER CASE and stay untouched — nothing here may feed a query or a link.
 */

/** UPPER CASE canonical name -> human title case ("WEST DELHI" -> "West Delhi"). */
export function titleCasePlace(s: string): string {
  return s.toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase());
}

// Delhi's 9 revenue districts are bare compass names in the postal/census data
// ("WEST", "NORTH EAST"). Rendered as "West, Delhi" they read like a direction,
// not a place. Explicit set — no prefix guessing, or SHAHDARA and NEW DELHI
// (real proper names) would get mangled too.
const DELHI_DIRECTIONAL_DISTRICTS = new Set([
  "CENTRAL",
  "EAST",
  "NORTH",
  "NORTH EAST",
  "NORTH WEST",
  "SOUTH",
  "SOUTH EAST",
  "SOUTH WEST",
  "WEST",
]);

/** "WEST"/"DELHI" -> "West Delhi"; "GAYAJI"/"BIHAR" -> "Gayaji, Bihar". */
export function formatDistrictLabel(district: string, state: string): string {
  const d = district.trim().toUpperCase();
  const s = state.trim().toUpperCase();

  if (s === "DELHI" && DELHI_DIRECTIONAL_DISTRICTS.has(d)) {
    return `${titleCasePlace(district)} Delhi`;
  }
  if (d.includes("DELHI")) {
    return titleCasePlace(district);
  }
  return `${titleCasePlace(district)}, ${titleCasePlace(state)}`;
}
