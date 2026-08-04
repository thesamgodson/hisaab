/** Scheme name registry + URL-slug resolution shared by /api/v1/scheme/*. */

export type SchemeKey =
  | "MGNREGA"
  | "PMGSY"
  | "PMAY-G"
  | "PM Kisan"
  | "JJM"
  | "PM POSHAN"
  | "NSAP"
  | "PDS/NFSA";

export const VALID_SCHEMES: SchemeKey[] = [
  "MGNREGA",
  "PMGSY",
  "PMAY-G",
  "PM Kisan",
  "JJM",
  "PM POSHAN",
  "NSAP",
  "PDS/NFSA",
];

/** URL-safe slug for a scheme name ("PDS/NFSA" -> "pds-nfsa"). Names with a
 *  slash can never arrive as a raw path segment, so slugs are the canonical
 *  address; exact display names still work where they survive routing. */
function slugify(name: string): string {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, "-");
}

const SLUG_TO_SCHEME = new Map<string, SchemeKey>(
  VALID_SCHEMES.map((s) => [slugify(s), s]),
);
SLUG_TO_SCHEME.set("nfsa", "PDS/NFSA");

export const VALID_SCHEME_SLUGS = [...SLUG_TO_SCHEME.keys()];

export function resolveSchemeParam(raw: string): SchemeKey | null {
  const decoded = decodeURIComponent(raw);
  if (VALID_SCHEMES.includes(decoded as SchemeKey)) {
    return decoded as SchemeKey;
  }
  return SLUG_TO_SCHEME.get(slugify(decoded)) ?? null;
}
