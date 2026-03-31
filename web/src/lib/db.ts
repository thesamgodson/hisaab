/**
 * Turso/libSQL database client for Hisaab.
 *
 * Server-side only — do not import from client components.
 * Client is lazy-initialized to avoid build-time errors when
 * env vars are not yet available.
 */

import { createClient, type Client } from "@libsql/client";

let _client: Client | null = null;

function getClient(): Client {
  if (!_client) {
    _client = createClient({
      url: process.env.TURSO_DATABASE_URL!,
      authToken: process.env.TURSO_AUTH_TOKEN,
    });
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

/** Resolve state for a district by checking multiple tables. */
export async function resolveState(district: string): Promise<string | null> {
  for (const table of ["pmgsy_district", "misappropriation", "financial_statement"]) {
    const row = await queryOne<{ state: string }>(
      `SELECT state FROM ${table} WHERE UPPER(district) = UPPER(?) LIMIT 1`,
      [district],
    );
    if (row) return row.state;
  }
  return null;
}
