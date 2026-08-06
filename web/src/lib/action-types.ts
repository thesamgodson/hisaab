/** TypeScript interfaces for the /api/v1/action/{pin} response. */

export interface DiagnosisItem {
  severity: "high" | "medium" | "low";
  scheme: string;
  summary: string;
  detail: string;
  amount: number | null;
  source_url: string | null;
}

export interface ActionStep {
  action: string;
  url: string | null;
  source_url?: string | null;
  verified_at?: string | null;
}

export interface ActionItem {
  scheme: string;
  steps: ActionStep[];
}

export interface GrievanceChannel {
  scheme: string;
  level: string;
  /** WHO hears this rung — Programme Officer, Collector, Ombudsperson… */
  authority: string | null;
  portal_name: string;
  portal_url: string;
  phone: string | null;
  /** HOW: what to do at this rung, one sentence. */
  description: string;
  /** Official evidence for the route instruction, not necessarily the filing URL. */
  source_url: string;
  /** When Hisaab last checked the route against its official evidence. */
  scraped_at: string;
}

/** WHY + WHO + HOW to complain for one scheme, assembled per district. */
export interface ComplaintKit {
  scheme: string;
  /** Reserved for a registered load-time flag contract; false today. */
  flagged: boolean;
  /** What the citizen is legally owed, plain language (null if uncurated). */
  entitlement: string | null;
  legal_basis: string | null;
  complain_when: string[];
  entitlement_source_url: string | null;
  entitlement_scraped_at: string | null;
  /** Official routes ordered by administrative level, not a guaranteed ladder. */
  channels: GrievanceChannel[];
}

export interface SchemeDataEntry {
  severity: string;
  summary: string;
  detail: string;
  amount: number | null;
  source_url: string | null;
}

export interface MPInfo {
  mp_name: string;
  party: string;
  constituency: string;
  state: string;
  elected_year: number;
  source_url: string;
}

export interface MLAInfo {
  mla_name: string;
  party: string;
  ac_name: string;
  state: string;
  source_url: string;
}

export interface DistrictLineage {
  parent_district: string;
  split_year: number;
}

export interface ActionBriefResponse {
  pin: string;
  district: string;
  state: string;
  formerly_part_of: DistrictLineage | null;
  mp: MPInfo | null;
  mla: MLAInfo | null;
  diagnosis: DiagnosisItem[];
  /** Empty until a registered load-time diagnosis contract exists. */
  schemes_checked: string[];
  actions: ActionItem[];
  grievance_channels: GrievanceChannel[];
  /** Every curated complaint family, independent of district performance data. */
  complaint_kits: ComplaintKit[];
  /** Scheme-independent channels (CPGRAMS, RTI) — always applicable. */
  universal_channels: GrievanceChannel[];
  scheme_data: Record<string, SchemeDataEntry>;
  generated_at: string;
}
