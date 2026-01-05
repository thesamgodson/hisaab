/** TypeScript interfaces for the /api/v1/action/{pin} response. */

export interface DiagnosisItem {
  severity: "high" | "medium" | "low";
  scheme: string;
  summary: string;
  detail: string;
  amount: string | null;
  source_url: string;
}

export interface ContactCard {
  role: string;
  name: string | null;
  phone: string | null;
  email: string | null;
  office_address: string | null;
  relevance: string;
  source_url: string;
  last_verified: string;
  freshness: "fresh" | "stale" | "expired";
}

export interface ActionItem {
  scheme: string;
  action: string;
  portal_name: string;
  portal_url: string;
  escalation: string;
  escalation_url: string;
}

export interface MPInfo {
  mp_name: string;
  party: string;
  constituency: string;
  state: string;
}

export interface MLAInfo {
  mla_name: string;
  party: string;
  ac_name: string;
  state: string;
}

export interface ActionBriefResponse {
  pin: string;
  district: string;
  state: string;
  mp: MPInfo | null;
  mla: MLAInfo | null;
  diagnosis: DiagnosisItem[];
  contacts: ContactCard[];
  actions: ActionItem[];
  scheme_data: Record<string, unknown>;
  generated_at: string;
}
