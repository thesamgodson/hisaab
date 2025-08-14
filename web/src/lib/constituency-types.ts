/** TypeScript types for the constituency / MP Report Card API responses. */

export interface SchemePerf {
  scheme: string;
  delivery_pct: number | null;
  utilization_pct: number | null;
  score: number | null;
  grade: string | null;
  status: "green" | "yellow" | "orange" | "red" | "no_data";
}

export interface ConstituencyReport {
  constituency: string;
  state: string;
  mp_name: string;
  party: string;
  elected_year: number;
  districts: string[];
  fin_year: string;
  composite_score: number | null;
  composite_grade: string | null;
  national_avg_score: number | null;
  red_flags: string[];
  schemes: SchemePerf[];
  source_note: string;
}

export interface PinLookupConstituency {
  constituency: string;
  state: string;
  district: string;
  constituency_type: string;
  mp: {
    constituency: string;
    mp_name: string;
    party: string;
    state: string;
    elected_year: number;
    source_url: string | null;
  } | null;
}

export interface MlaInfo {
  ac_name: string;
  ac_no: number | null;
  state: string;
  mla_name: string;
  party: string;
  elected_year: number;
  source_url: string | null;
}

export interface PinLookupAssemblyConstituency {
  type: "VIDHAN_SABHA";
  ac_name: string;
  ac_no: number | null;
  pc_name: string | null;
  mla: MlaInfo | null;
}

export interface PinLookupResponse {
  pin_code: string;
  district: string;
  state: string;
  office_name: string | null;
  constituencies: PinLookupConstituency[];
  constituency_count: number;
  assembly_constituencies: PinLookupAssemblyConstituency[];
  assembly_constituency_count: number;
}

export interface ConstituencySearchResult {
  constituency: string;
  mp_name: string;
  party: string;
  state: string;
}

export interface ConstituencySearchResponse {
  query: string;
  results: ConstituencySearchResult[];
  count: number;
}
