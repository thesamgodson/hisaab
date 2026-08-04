# web/ conventions

Next.js 15 (App Router) + React 19 + Tailwind v3 + TypeScript. Deployed on
Vercel; data lives in Turso (libSQL over HTTPS).

## Rules that reflect real decisions

1. **Server components query the DB directly** via `src/lib/db.ts`. Never
   fetch your own API routes from a page (self-HTTP breaks on protected
   preview deployments — this bug took the hero flow down once already).
   API routes exist for external consumers and client components.
2. **No formulas in TypeScript.** Derived numbers (scores, grades, red flags)
   are precomputed by `queries/composite.py` into the `district_scores`
   table at load time. TS reads tables; it never reimplements methodology.
3. **District identity is canonical.** Names arrive normalized (see
   `db/normalize_districts.py`). Always filter by `(district, state)` —
   14 district names exist in two states.
4. **No misleading claims.** A percentage is only shown when the underlying
   metric honestly supports one (see `src/lib/data-quality.ts` and
   DATA_CLAIMS.md). "Reported" ≠ "Good"; missing target ≠ "No data".
5. **Env vars**: `TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN` (pull with
   `vercel env pull .env.local`). `src/lib/db.ts` has no local-SQLite
   fallback.
6. Read-heavy routes set `export const revalidate = 3600` — data changes
   only when the pipeline publishes.
