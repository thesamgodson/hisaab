/**
 * API client for the Hisaab FastAPI backend.
 *
 * In the browser, requests go through Next.js rewrites (/api/v1/...).
 * On the server (RSC), requests go directly to the backend.
 */

import type {
  BriefResponse,
  DataQualityResponse,
  DistrictsResponse,
  FreshnessResponse,
  QueryResponse,
  RedFlagsResponse,
  SchemeData,
  SchemesResponse,
} from "./types";

const BACKEND_URL =
  typeof window === "undefined"
    ? (process.env.API_BASE_URL ?? "http://localhost:8000")
    : "";

function apiUrl(path: string): string {
  return `${BACKEND_URL}${path}`;
}

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const url = apiUrl(path);
  const res = await fetch(url, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${res.statusText} — ${url}`);
  }
  return res.json() as Promise<T>;
}

/** List all 8 schemes with data quality warnings. */
export function fetchSchemes(): Promise<SchemesResponse> {
  return fetchJson("/api/v1/schemes");
}

/** List all districts, optionally filtered by state. */
export function fetchDistricts(state?: string): Promise<DistrictsResponse> {
  const qs = state ? `?state=${encodeURIComponent(state)}` : "";
  return fetchJson(`/api/v1/districts${qs}`);
}

/** Full district overview across all schemes. */
export function fetchDistrictOverview(
  name: string,
  state?: string,
): Promise<SchemeData> {
  const qs = state ? `?state=${encodeURIComponent(state)}` : "";
  return fetchJson(`/api/v1/district/${encodeURIComponent(name)}${qs}`);
}

/** Which schemes have data for a district. */
export function fetchDistrictSchemes(
  name: string,
): Promise<{ answer: string; data: string[] }> {
  return fetchJson(`/api/v1/district/${encodeURIComponent(name)}/schemes`);
}

/** Per-scheme detail for a district. */
export function fetchDistrictScheme(
  name: string,
  scheme: string,
  state?: string,
): Promise<SchemeData> {
  const qs = state ? `?state=${encodeURIComponent(state)}` : "";
  return fetchJson(
    `/api/v1/district/${encodeURIComponent(name)}/${encodeURIComponent(scheme)}${qs}`,
  );
}

/** Generate journalist brief for a district. */
export function fetchBrief(
  district: string,
  state?: string,
): Promise<BriefResponse> {
  const qs = state ? `?state=${encodeURIComponent(state)}` : "";
  return fetchJson(`/api/v1/brief/${encodeURIComponent(district)}${qs}`);
}

/** Per-scheme data freshness. */
export function fetchFreshness(): Promise<FreshnessResponse> {
  return fetchJson("/api/v1/freshness");
}

/** Per-scheme data quality warnings. */
export function fetchDataQuality(): Promise<DataQualityResponse> {
  return fetchJson("/api/v1/data-quality");
}

/** Worst districts across key indicators. */
export function fetchRedFlags(
  state?: string,
  limit?: number,
): Promise<RedFlagsResponse> {
  const params = new URLSearchParams();
  if (state) params.set("state", state);
  if (limit) params.set("limit", String(limit));
  const qs = params.toString() ? `?${params.toString()}` : "";
  return fetchJson(`/api/v1/red-flags${qs}`);
}

/** State-level summary for a scheme. */
export function fetchSchemeSummary(
  scheme: string,
  state?: string,
): Promise<SchemeData> {
  const qs = state ? `?state=${encodeURIComponent(state)}` : "";
  return fetchJson(`/api/v1/scheme/${encodeURIComponent(scheme)}${qs}`);
}

/** Worst districts for a scheme. */
export function fetchSchemeWorst(
  scheme: string,
  state?: string,
  limit?: number,
): Promise<SchemeData> {
  const params = new URLSearchParams();
  if (state) params.set("state", state);
  if (limit) params.set("limit", String(limit));
  const qs = params.toString() ? `?${params.toString()}` : "";
  return fetchJson(`/api/v1/scheme/${encodeURIComponent(scheme)}/worst${qs}`);
}

/** Natural language query. */
export function postQuery(text: string): Promise<QueryResponse> {
  return fetchJson("/api/v1/query", {
    method: "POST",
    body: JSON.stringify({ text }),
  });
}

/** Cross-scheme money flow for a district. */
export function fetchMoneyFlow(
  name: string,
  state?: string,
): Promise<SchemeData> {
  const qs = state ? `?state=${encodeURIComponent(state)}` : "";
  return fetchJson(
    `/api/v1/district/${encodeURIComponent(name)}/money-flow${qs}`,
  );
}
