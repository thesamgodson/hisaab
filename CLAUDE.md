# Hisaab — Developer Guide

## What This Is

Public accountability infrastructure for India. 11 government welfare schemes, scraped from official portals, normalized into SQLite, queryable via CLI, surfaced as journalist briefs with red flags.

**Manifesto rule:** No public numeric claim without source and date in `DATA_CLAIMS.md`.

## Architecture — TypeScript serves, Python produces

- **Production serving**: Next.js 15 route handlers (`web/src/app/api/v1/`)
  query **Turso** (libSQL) directly. FastAPI (`api/`) is local/analysis only —
  it is NOT deployed.
- **Data production (Python 3.14+)**: scrape → `data/curated/*.json` →
  `run_all.py --load-only` (canonical district normalization + precomputed
  `district_scores`) → `data/hisaab.db` → `scripts/sync_turso.py` → Turso.
- **Derived numbers live in the DB.** The scoring formula exists ONLY in
  `queries/composite.py`, persisted to `district_scores` at load time. Never
  port a formula into TypeScript; move its output into a table.
- **District identity is canonical.** `db/normalize_districts.py` + the
  generated alias registry (`db/district_aliases.py`, regenerate with
  `scripts/gen_district_aliases.py` — additive only) unify portal, India
  Post, and census spellings and official renames. Always join on
  `(district, state)`.
- **Scrapers**: requests + Playwright (MGNREGA/PMGSY/PMAY-G/NRLM need browser)
- **Refresh**: `.github/workflows/refresh-data.yml` — weekly scrape → load →
  publish → prod smoke probes.

## Quick Start

```bash
# Backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 run_all.py --load-only          # Build DB from curated JSON
python3 -m pytest tests/ -v             # Run tests
python3 scripts/sync_turso.py --env-file web/.env.local   # Publish to prod DB
uvicorn api.main:app --reload           # Optional: local analysis API :8000

# Frontend
cd web && npm install
vercel env pull .env.local              # Turso credentials
npm run dev                             # Start at localhost:3000
```

## 11 Schemes

| Scheme | Table(s) | Source | Financial Data? |
|--------|----------|--------|----------------|
| MGNREGA | financial_statement, fto_status, fto_pendency (live) · misappropriation, issues_reported (**frozen FY2024-25**) | mnregaweb2.dord.gov.in citizen portal | Yes — district-level (lakhs) |
| PMGSY | pmgsy_progress, pmgsy_district | pmgsy.dord.gov.in | Yes — district-level (crores→lakhs in VIEWs) |
| PM Kisan | pmkisan_district | data.gov.in | Yes — state-level (amount_paid_lakhs) |
| PMAY-G | pmayg_district, **pmayg_finance** | report.pmayg.dord.gov.in | Yes — **state-level** alloc/release/utilized (2019-26, 7 years) |
| JJM | jjm_district, **jjm_allocation** | ejalshakti.gov.in | Yes — **state-level** alloc/release/expend (2019-25, 6 years) |
| PM POSHAN | pmposhan_district, **pmposhan_finance** | pmposhan-ams.education.gov.in + data.gov.in | Yes — **state-level** alloc/release/utilized (2016-25) |
| NSAP | nsap_district, **nsap_finance** | data.gov.in | Yes — **state-level real release** (2019-24); district imputed |
| PDS/NFSA | nfsa_district, **nfsa_allocation** | nfsa.gov.in + data.gov.in | Yes — **state-level** alloc/offtake in MT (2019-25) |
| SBM-G | sbm_district | sbm.gov.in | No — delivery only (ODF+ villages, star ratings) |
| DAY-NRLM | nrlm_district | nrlm.gov.in | Partial — RF disbursement (lakhs) at district level |
| UDISE+ | udise_state | api.udiseplus.gov.in | No — education delivery (schools, enrollment, PTR, infra) |

## 3 Unified VIEWs

- **`scheme_finance`** — allocated/released/expended per scheme×state×district
- **`scheme_delivery`** — units target/completed/delivery_pct per scheme×state×district
- **`money_flow`** — normalized union across ALL schemes for cross-scheme queries

## Key Modules

| Module | Purpose |
|--------|---------|
| `db/` | Schema, 21 loaders, 3 VIEWs, district canonicalization, NSAP imputation |
| `queries/` | 38 query functions, `composite.py` (THE scoring implementation → `district_scores`), `common.py:data_quality_warnings()` |
| `briefs/` | Per-district/state journalist briefs (CLI) |
| `action_brief/` | PIN → diagnosis → contacts → actions engine (Python; TS twin in `web/src/lib/action-brief.ts`) |
| `constituency/` | PIN/constituency/MP/MLA ingest + district lineage seed |
| `api/` | FastAPI (31 endpoints) — LOCAL ONLY, not deployed; unique features: /investigate (LLM), /embed, /trends |
| `web/` | Next.js 15 citizen interface + production `/api/v1/*` (see `web/AGENTS.md`) |
| `scripts/` | `sync_turso.py` (publish→prod), `gen_district_aliases.py`, `data_audit.py`, `build_geodata.py` |
| `run_all.py` | Orchestrator: scrape + load + normalize + precompute scores |
| `cli.py` | Natural language CLI (keyword routing) |
| `alerts/`, `llm/` | Complete but unscheduled/unreached (Telegram digest, text-to-SQL investigator) |

## Production API (Next.js route handlers)

```
GET /api/v1/pin/{pin}                    — PIN → district, MP, MLA, lineage
GET /api/v1/action/{pin}                 — full citizen action brief
GET /api/v1/scores[/worst|/states|/{d}]  — precomputed accountability scores
GET /api/v1/districts                    — canonical district registry
GET /api/v1/district/{name}[/*]          — district overview / money-flow
GET /api/v1/scheme/{slug}[/worst]        — per-scheme (slugs: mgnrega, pds-nfsa, …; ?state= required)
GET /api/v1/schemes | /data-quality      — caveats (single source: web/src/lib/data-quality.ts)
GET /api/v1/freshness                    — per-scheme scrape dates (all 11 schemes)
GET /api/v1/brief/{district} | /stats | /red-flags?state= | /constituency/* | /mp/{name}
```

## Data Quality Context

- Financial data: district-level MGNREGA + PMGSY (real), NSAP (imputed); state-level PM Kisan, PM POSHAN (2016-25), NSAP (2019-24), PMAY-G (2019-26), JJM (2019-25), NFSA (MT)
- **No invented percentages**: PM POSHAN children_fed is a daily snapshot; NFSA active=total by construction — both excluded from delivery_pct at the VIEW layer and from diagnoses/rankings
- Scores need ≥3 schemes with data (`MIN_SCHEMES_FOR_SCORE`) — below that: no grade, red flags only
- PM Kisan: 28/36 states have district='ALL' (state-level only)
- NFSA tracks metric tonnes, never rupees — money_flow publishes NULL money columns for it
- Caveats: `queries/common.py:data_quality_warnings()` ↔ `web/src/lib/data-quality.ts` (update together); every caveat backed by a DATA_CLAIMS.md entry

## Testing

```bash
python3 -m pytest tests/ -v    # 16 test files, ~500 tests
```

CI (`.github/workflows/ci.yml`) builds the DB from curated JSON before pytest
so the integration suites actually run, plus ruff + frontend typecheck/build.

## Conventions

- All amounts in lakhs internally (PMGSY converts crores→lakhs in VIEWs)
- State + district names UPPER CASE **canonical** (normalized at load — see
  `db/normalize_districts.py`; regenerate aliases additively via
  `scripts/gen_district_aliases.py`)
- `scraped_at` timestamp on every record; `fin_year` format `"2024-2025"`
- DB path: `data/hisaab.db` (single source of truth in `db/connection.py:DB_PATH`)
- Derived numbers are precomputed in Python and read everywhere — never
  reimplement a formula in TypeScript
