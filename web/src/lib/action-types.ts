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
}

export interface ActionItem {
  scheme: string;
  steps: ActionStep[];
}

export interface GrievanceChannel {
  scheme: string;
  level: string;
  portal_name: string;
  portal_url: string;
  phone: string | null;
  description: string;
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
  /** Schemes that reported district data at all — an empty diagnosis with an
   *  empty list means "nothing was checked", not "nothing is wrong". */
  schemes_checked: string[];
  actions: ActionItem[];
  grievance_channels: GrievanceChannel[];
  scheme_data: Record<string, SchemeDataEntry>;
  generated_at: string;
}
