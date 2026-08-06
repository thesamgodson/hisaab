# Hisaab — Teammate Onboarding

Welcome. Hisaab is public accountability infrastructure for India: 11 welfare
schemes scraped from official government portals, normalized into SQLite,
published to Turso, and served as a citizen-facing site — PIN in, "what's owed
here" out. Live: https://hisaab-one.vercel.app

Your mission as a new teammate is most likely **scheme expansion** (new
schemes, deeper data on existing ones). The hero surface — map, PIN flow,
mobile, "use my location" — is polished and considered done; change it only
with a reason.

## The four tenets (acceptance criteria for everything)

1. **No public numeric claim without source and date** — every number the
   site serves traces to an entry in `DATA_CLAIMS.md`. New data = new claim
   with source URL, retrieval date, method, confidence, caveats.
2. **No misleading claims.** A percentage is shown only when the metric
   honestly supports one. Views never fabricate: a missing denominator is
   `NULL` ("not reported"), never 0. "Reported" is a neutral badge, not a
   judgment (see DERIVED-2026-0005).
3. **No captcha automation — ever.** Citability is the product: a journalist
   must be able to say "scraped from the government's public interface".
   Captcha-gated sources get recorded as limitations in DATA_CLAIMS.md.
   (Also: never proxy around the *.dord.gov.in datacenter-IP block.)
4. **A refresh never reduces granularity, coverage, or money.**
   `scripts/verify_refresh.py` enforces this in CI; don't fight it, fix the
   scrape.

## Architecture in one paragraph

**TypeScript serves, Python produces.** Next.js 15 route handlers
(`web/src/app/api/v1/`) read **Turso** directly and never compute
methodology; Python owns scrape → `data/curated/*.json` (tracked in git —
git is the canon) → `run_all.py --load-only` (canonical district
normalization + precomputed `district_scores`) → `data/hisaab.db` →
`scripts/sync_turso.py` → Turso. Derived numbers live in DB tables
(`queries/composite.py` is THE scoring implementation); TS reads tables.
FastAPI (`api/`) is local-analysis only, not deployed.

## Setup (10 minutes)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 run_all.py --load-only            # build DB from curated JSON
python3 -m constituency.ingest            # seed civic tables (PIN/MP/MLA)
python3 -m pytest tests/ -q               # ~570 tests, all green
cd web && npm install
vercel env pull .env.local                # Turso creds (ask Sam for access)
npm run dev                               # localhost:3000
```

Read next, in order: `CLAUDE.md` (conventions), `findings.md` (system facts),
`learnings.md` (failure postmortems — these are laws, not suggestions),
`DATA_CLAIMS.md` (every number's provenance), `web/AGENTS.md`.

## Adding or refreshing a scheme (your main loop)

1. **Scrape**: new module in `scrapers/`, writing
   `data/curated/<table>_<scope>_latest.json`. Every record carries its OWN
   `fin_year`, `scraped_at`, `source_url` (loader params are fallback-only —
   a load-time default once silently relabeled frozen data). Write to a temp
   file, atomically rename on non-empty success. All data.gov.in calls go
   through `scrapers/io_utils.py:datagov_session()` (UA + key handling;
   pagination silently caps at offset 500k — partition big pulls by a
   server-side filter).
2. **Load**: schema in `db/schema.py`, loader in `db/loaders.py` (registry
   picks up `<loader>_*_latest.json` by glob). District names route through
   `db/normalize_districts.py` — **always state-scoped**; India reuses names
   across states at every level, and any name key without `state` is a
   landmine.
3. **Views**: wire into `scheme_finance` / `scheme_delivery` / `money_flow`
   in `db/schema.py`. Honesty rules: `ELSE NULL` (never 0), exclude metrics
   with no honest shortfall interpretation, aggregate sub-scheme rows if a
   consumer would otherwise pick one arbitrarily (NSAP precedent).
4. **Caveats**: `queries/common.py:data_quality_warnings()` ↔
   `web/src/lib/data-quality.ts` — update together, always.
5. **Claims**: `DATA_CLAIMS.md` entry. Supersede, never edit in place.
6. **Tests**: `tests/` mirror; CI builds the DB from curated JSON first, so
   integration tests really run.
7. **Score safety**: if your change could move `district_scores`, prove it
   (dump before/after) and say so in the claim. `composite.py` requires ≥3
   schemes for a grade and reads only `utilization_pct > 0`.

## Publishing (order is law)

```
verify → load → COMMIT → scripts/sync_turso.py --env-file web/.env.local → push → prod smoke
```

Git lands before prod (a failed publish must leave git ahead of prod, never
the reverse). `sync_turso` has a wipe-guard (never replaces a populated
remote table with an empty local one) — if it says KEPT, you forgot
`python -m constituency.ingest` after rebuilding the DB. Never `rm
data/hisaab.db` casually; the civic tables are seeded outside `--load-only`.

Prod smoke minimum:

```bash
curl -s https://hisaab-one.vercel.app/api/v1/pin/823001          # GAYAJI + MP
curl -s -X POST https://hisaab-one.vercel.app/api/v1/locate \
  -H 'Content-Type: application/json' -d '{"lat":24.7955,"lng":84.9994}'
curl -s https://hisaab-one.vercel.app/api/v1/action/110018       # Delhi MP via pin_constituency
```

## Ops you inherit

- **Weekly refresh**: `.github/workflows/refresh-data.yml`, Sundays 21:30
  UTC, `schemes=all` (incl. PM Kisan — `DATA_GOV_IN_API_KEY` repo secret is
  registered and account-wide). Partial portal failures are tolerated;
  last-good data + honest `/api/v1/freshness` dates persist.
- ***.dord.gov.in blocks GitHub-runner IPs** (MGNREGA, PMGSY, PMAY-G): those
  three refresh only from a residential IP — run locally, then commit +
  publish. Do not proxy around it.
- **Frozen tables**: `misappropriation` + `issues_reported` (FY2024-25,
  captcha-gated upstream — CLAIM-2026-0001). PM Kisan money frozen at 8
  states' FY2024-25 rows.
- **Civic identity**: PC names canon lives ONLY in
  `constituency/pc_name_registry.py`; `web/src/lib/pc-name-registry.ts` is
  GENERATED (`scripts/gen_pc_name_registry.py`) — never hand-edit. District
  aliases regenerate additively via `scripts/gen_district_aliases.py`.
- **Privacy contract** (CLAIM-2026-0038): `/api/v1/locate` takes coordinates
  in the POST body, processes them transiently, and never logs or stores
  them. Do not add logging to that route. Ever.

## Known open threads (good first units)

- District-fragment folds: PANCH MAHALS/PANCHMAHAL, GANGANAGAR/SRI
  GANGANAGAR, BARABANKI/BARA BANKI, LAKSHADWEEP DISTRICT/LAKSHADWEEP, Sikkim
  2021 renames — use the recorded rename-migration procedure (one audited
  sweep; scores will move; DATA_CLAIMS entry required). Never fold piecemeal.
- Delhi's 7 PC↔district mappings are a structural gap (datameet has blank
  DIST_NAME) — Delhi MPs serve via `pin_constituency`; do NOT invent the
  mapping.
- LokOS publishes more district money feeds (VO/CLF CIF, startup funds) —
  candidates for deepening DAY-NRLM.
- PMAY-G district-level utilization + SNA all-schemes report exist on the
  un-gated B.3 route — unmined.

When in doubt: read `learnings.md`, then ask. Every painful rule in there was
paid for.
