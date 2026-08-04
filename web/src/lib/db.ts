/**
 * Turso/libSQL database client for Hisaab.
 *
 * Server-side only — do not import from client components.
 * Client is lazy-initialized to avoid build-time errors when
 * env vars are not yet available.
 */

import { createClient, type Client } from "@libsql/client/web";

let _client: Client | null = null;

function getClient(): Client {
  if (!_client) {
    const rawUrl = process.env.TURSO_DATABASE_URL!;
    // Vercel serverless doesn't support libsql:// — convert to https://
    const url = rawUrl.replace(/^libsql:\/\//, "https://");
    _client = createClient({ url, authToken: process.env.TURSO_AUTH_TOKEN });
  }
  return _client;
}

/** Execute a SQL query and return rows as plain objects. */
export async function query<T = Record<string, unknown>>(
  sql: string,
  args: (string | number | null)[] = [],
): Promise<T[]> {
  const rs = await getClient().execute({ sql, args });
  return rs.rows as unknown as T[];
}

/** Execute a SQL query and return the first row, or null. */
export async function queryOne<T = Record<string, unknown>>(
  sql: string,
  args: (string | number | null)[] = [],
): Promise<T | null> {
  const rows = await query<T>(sql, args);
  return rows[0] ?? null;
}

/** Resolve state for a district name.
 *
 * district_scores is the canonical district registry — it holds every
 * (district, state) pair seen in any scheme table, written at load time.
 * Homonym districts (AURANGABAD in Bihar & Maharashtra) resolve to their
 * first match — callers that know the state should pass it explicitly
 * instead of relying on this.
 */
export async function resolveState(district: string): Promise<string | null> {
  // Normalize: replace hyphens with spaces to match DB convention
  const normalized = district.toUpperCase().trim().replace(/-/g, " ");
  const row = await queryOne<{ state: string }>(
    `SELECT state FROM district_scores WHERE UPPER(district) = UPPER(?)
     ORDER BY state LIMIT 1`,
    [normalized],
  );
  return row?.state ?? null;
}
