# Hisaab — Developer Guide

## What This Is

Public accountability infrastructure for India. 8 government welfare schemes, scraped from official portals, normalized into SQLite, queryable via CLI, surfaced as journalist briefs with red flags.

**Manifesto rule:** No public numeric claim without source and date in `DATA_CLAIMS.md`.

## Stack

- **Backend**: Python 3.14+, SQLite, FastAPI
- **Frontend**: Next.js 15, React 19, Tailwind CSS, TypeScript
- **Scrapers**: requests + Playwright (MGNREGA/PMGSY/PMAY-G need browser)
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

## 8 Schemes

| Scheme | Table(s) | Source | Financial Data? |
|--------|----------|--------|----------------|
| MGNREGA | misappropriation, financial_statement, fto_status, fto_pendency, issues_reported | nrega.nic.in | Yes (lakhs) |
| PMGSY | pmgsy_progress, pmgsy_district | pmgsy.dord.gov.in | Yes (crores→lakhs in VIEWs) |
| PM Kisan | pmkisan_district | data.gov.in | Yes (amount_paid_lakhs) |
| PMAY-G | pmayg_district | report.pmayg.dord.gov.in | Hollow (zeros) |
| JJM | jjm_district | ejalshakti.gov.in | Hollow (zeros) |
| PM POSHAN | pmposhan_district | pmposhan-ams.education.gov.in | Hollow (zeros) — children_fed works |
| NSAP | nsap_district | nsap.nic.in / data.gov.in | Imputed (beneficiaries × GoI pension rate × 12) |
| PDS/NFSA | nfsa_district | nfsa.gov.in | Hollow (zeros) — ration card counts work |

## 3 Unified VIEWs

- **`scheme_finance`** — allocated/released/expended per scheme×state×district
- **`scheme_delivery`** — units target/completed/delivery_pct per scheme×state×district
- **`money_flow`** — normalized union across ALL schemes for cross-scheme queries

## Key Modules

| Module | Purpose |
|--------|---------|
| `db/` | Schema, 13 loaders, 3 VIEWs, NSAP imputation |
| `queries/` | 33 query functions + data_quality_warnings() |
| `briefs/` | Per-district/state briefs with red flags |
| `api/` | FastAPI REST API (13 endpoints) |
| `web/` | Next.js 15 frontend (citizen interface) |
| `run_all.py` | Orchestrator: scrape + load |
| `cli.py` | Natural language CLI (keyword routing) |
| `data_audit.py` | Per-column completeness report |

## API Endpoints

```
GET  /api/v1/schemes              — list 8 schemes + warnings
GET  /api/v1/scheme/{name}        — state-level summary
GET  /api/v1/scheme/{name}/worst  — worst districts
GET  /api/v1/district/{name}      — full district overview
GET  /api/v1/brief/{district}     — journalist brief
GET  /api/v1/freshness            — per-scheme scrape dates
GET  /api/v1/data-quality         — quality warnings
GET  /api/v1/red-flags            — worst districts
POST /api/v1/query                — natural language query
```

## Data Quality Context

- 4/8 schemes have financial data (MGNREGA, PMGSY, PM Kisan = real; NSAP = imputed from GoI pension rates)
- 4/8 have hollow financial columns (PMAY-G, JJM, PM POSHAN, NFSA) — delivery metrics still work
- PM Kisan: 28/36 states have district='ALL' (state-level only)
- `query.py:data_quality_warnings()` returns per-scheme caveats

## Testing

```bash
python3 -m pytest tests/ -v
```

4 test files:
- `test_queries.py` — query function correctness
- `test_pmgsy.py` — PMGSY-specific queries
- `test_cross_scheme.py` — cross-scheme VIEW queries
- `test_loaders.py` — loader ingestion

## Conventions

- All amounts in lakhs internally (PMGSY converts crores→lakhs in VIEWs)
- State names UPPER CASE, district names UPPER CASE
- `scraped_at` timestamp on every record
- `fin_year` format: `"2024-2025"`
- DB path: `data/hisaab.db` (single source of truth in `db/connection.py:DB_PATH`)
