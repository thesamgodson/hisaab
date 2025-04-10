/** Shared TypeScript types matching the FastAPI backend responses. */

export interface Scheme {
  name: string;
  warnings: string[];
}

export interface SchemesResponse {
  schemes: Scheme[];
  count: number;
}

export interface DistrictsResponse {
  districts: string[];
  count: number;
}

export interface SchemeData {
  answer: string;
  data: Record<string, unknown> | Record<string, unknown>[] | null;
  source_url?: string;
  source_urls?: string[];
}

export interface BriefResponse {
  district: string;
  state: string;
  brief: string;
  format: string;
}

export interface FreshnessEntry {
  scheme: string;
  source: string;
  latest_scraped: string | null;
  records: number;
  states: number;
}

export interface FreshnessResponse {
  freshness: FreshnessEntry[];
  total_records: number;
}

export interface DataQualityResponse {
  [scheme: string]: string[];
}

export interface QueryResponse {
  query: string;
  intent: string;
  district: string | null;
  answer: string;
  lang: string;
}

export interface RedFlagsResponse {
  misappropriation: SchemeData;
  pmgsy_completion: SchemeData;
  jjm_coverage: SchemeData;
}

/** Maps scheme names to their display colors and icons. */
export const SCHEME_META: Record<
  string,
  {
    color: string;
    bg: string;
    icon: string;
    shortName: string;
    sourceBase: string;
  }
> = {
  MGNREGA: {
    color: "text-amber-700",
    bg: "bg-amber-50",
    icon: "briefcase",
    shortName: "MGNREGA",
    sourceBase: "https://nrega.nic.in",
  },
  PMGSY: {
    color: "text-slate-700",
    bg: "bg-slate-50",
    icon: "road",
    shortName: "PMGSY",
    sourceBase: "https://omms.nic.in",
  },
  "PMAY-G": {
    color: "text-orange-700",
    bg: "bg-orange-50",
    icon: "home",
    shortName: "PMAY-G",
    sourceBase: "https://pmayg.nic.in",
  },
  "PM Kisan": {
    color: "text-green-700",
    bg: "bg-green-50",
    icon: "sprout",
    shortName: "PM Kisan",
    sourceBase: "https://pmkisan.gov.in",
  },
  JJM: {
    color: "text-cyan-700",
    bg: "bg-cyan-50",
    icon: "droplet",
    shortName: "JJM",
    sourceBase: "https://ejalshakti.gov.in",
  },
  "PM POSHAN": {
    color: "text-rose-700",
    bg: "bg-rose-50",
    icon: "utensils",
    shortName: "PM POSHAN",
    sourceBase: "https://pmposhan.education.gov.in",
  },
  NSAP: {
    color: "text-purple-700",
    bg: "bg-purple-50",
    icon: "heart",
    shortName: "NSAP",
    sourceBase: "https://nsap.nic.in",
  },
  "PDS/NFSA": {
    color: "text-teal-700",
    bg: "bg-teal-50",
    icon: "wheat",
    shortName: "PDS/NFSA",
    sourceBase: "https://nfsa.gov.in",
  },
};
