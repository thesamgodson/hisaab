# Hisaab web

Citizen interface for [Hisaab](../README.md): PIN code → district reality →
who is accountable → what to do about it.

## Run locally

```bash
npm install
vercel env pull .env.local   # TURSO_DATABASE_URL + TURSO_AUTH_TOKEN
npm run dev                  # localhost:3000
```

There is no local-SQLite fallback — the app reads Turso directly. Data is
published to Turso by `python3 scripts/sync_turso.py` from the repo root.

## Layout

- `src/app/` — pages (`/`, `/district/[name]`, `/action/[pin]`) and
  `/api/v1/*` route handlers for external consumers
- `src/lib/` — `db.ts` (Turso client), `scores.ts` (reads precomputed
  `district_scores`), `action-brief.ts` (PIN → brief), `data-quality.ts`
  (per-scheme caveats), `report-card.ts`, `schemes.ts`, `geodata.ts`
- `src/components/` — `IndiaMap`, `PinEntry`, `SchemeRow`, `SourceLink`

Conventions: see [AGENTS.md](AGENTS.md).
