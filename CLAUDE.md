# Hisaab — Developer Guide

## What This Is

Public accountability infrastructure for India. 11 government welfare schemes, scraped from official portals, normalized into SQLite, queryable via CLI, surfaced as journalist briefs with red flags.

**Manifesto rule:** No public numeric claim without source and date in `DATA_CLAIMS.md`.

## Stack

- **Backend**: Python 3.14+, SQLite, FastAPI
- **Frontend**: Next.js 15, React 19, Tailwind CSS, TypeScript
- **Scrapers**: requests + Playwright (MGNREGA/PMGSY/PMAY-G/NRLM need browser)
- **Data flow**: scrape → `data/curated/*.json` → `run_all.py --load-only` → `data/hisaab.db` → FastAPI → Next.js

## Quick Start

```bash
# Backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 run_all.py --load-only          # Build DB from curated JSON
python3 -m pytest tests/ -v             # Run tests
uvicorn api.main:app --reload           # Start API at localhost:8000

# Frontend
cd web && npm install && npm run dev    # Start at localhost:3000
```

## 11 Schemes

| Scheme | Table(s) | Source | Financial Data? |
|--------|----------|--------|----------------|
| MGNREGA | misappropriation, financial_statement, fto_status, fto_pendency, issues_reported | nrega.nic.in | Yes — district-level (lakhs) |
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
| `db/` | Schema, 21 loaders, 3 VIEWs, NSAP imputation |
| `queries/` | 35 query functions + data_quality_warnings() |
| `briefs/` | Per-district/state briefs with red flags |
| `api/` | FastAPI REST API (13 endpoints) |
| `web/` | Next.js 15 frontend (citizen interface) |
| `run_all.py` | Orchestrator: scrape + load |
| `cli.py` | Natural language CLI (keyword routing) |
| `data_audit.py` | Per-column completeness report |

## API Endpoints

```
GET  /api/v1/schemes                    — list 8 schemes + warnings
GET  /api/v1/scheme/{scheme}            — state-level summary
GET  /api/v1/scheme/{scheme}/worst      — worst districts
GET  /api/v1/districts                  — list all districts with data
GET  /api/v1/district/{name}            — full district overview
GET  /api/v1/district/{name}/schemes    — schemes with data for district
GET  /api/v1/district/{name}/money-flow — cross-scheme money flow
GET  /api/v1/district/{name}/{scheme}   — per-scheme data for district
GET  /api/v1/brief/{district}           — journalist brief
GET  /api/v1/freshness                  — per-scheme scrape dates
GET  /api/v1/data-quality               — quality warnings
GET  /api/v1/red-flags                  — worst districts
POST /api/v1/query                      — natural language query
```

## Data Quality Context

- **8/10 schemes** have financial data:
  - District-level: MGNREGA, PMGSY (real); NSAP (imputed at district, real at state); DAY-NRLM (RF disbursement)
  - State-level: PM Kisan, PM POSHAN (2016-25), NSAP (2019-24), PMAY-G (2019-26, 7 years), JJM (2019-25, alloc+release+expend), NFSA (MT, 2019-25)
  - No financial data: SBM-G (delivery metrics only), PM POSHAN/PMAY-G/JJM/NFSA at district level
- District-level financial columns remain zero for PM POSHAN, PMAY-G, JJM, NFSA — delivery metrics still work
- PM Kisan: 28/36 states have district='ALL' (state-level only)
- NFSA tracks metric tonnes, not rupees — do not compare with other schemes' lakhs columns
- `queries/common.py:data_quality_warnings()` returns per-scheme caveats

## Testing

```bash
python3 -m pytest tests/ -v
```

6 test files:
- `test_queries.py` — query function correctness
- `test_pmgsy.py` — PMGSY-specific queries
- `test_cross_scheme.py` — cross-scheme VIEW queries
- `test_loaders.py` — loader ingestion
- `test_scrapers.py` — pure scraper function unit tests
- `test_data_integrity.py` — DB invariant checks (skips if no DB)

## Conventions

- All amounts in lakhs internally (PMGSY converts crores→lakhs in VIEWs)
- State names UPPER CASE, district names UPPER CASE
- `scraped_at` timestamp on every record
- `fin_year` format: `"2024-2025"`
- DB path: `data/hisaab.db` (single source of truth in `db/connection.py:DB_PATH`)
