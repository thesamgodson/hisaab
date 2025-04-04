# Hisaab — Developer Guide

## What This Is

Public accountability infrastructure for India. 8 government welfare schemes, scraped from official portals, normalized into SQLite, queryable via CLI, surfaced as journalist briefs with red flags.

**Manifesto rule:** No public numeric claim without source and date in `DATA_CLAIMS.md`.

## Stack

- **Python 3.14+**, SQLite, no ORM
- **Scrapers**: requests + Playwright (MGNREGA/PMGSY/PMAY-G need browser)
- **Data flow**: scrape → `data/curated/*.json` → `run_all.py --load-only` → `data/hisaab.db`

## Quick Start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 run_all.py --load-only          # Build DB from curated JSON
python3 run_all.py --summary            # Check DB contents
python3 run_all.py --freshness          # Per-scheme freshness
python3 -m pytest tests/ -v             # Run tests
python3 cli.py "misappropriation villupuram"  # CLI query
python3 journalist_brief.py "CUDDALORE"       # Generate brief
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
| NSAP | nsap_district | nsap.nic.in / data.gov.in | Hollow (zeros) — beneficiaries_paid works |
| PDS/NFSA | nfsa_district | nfsa.gov.in | Hollow (zeros) — ration card counts work |

## 3 Unified VIEWs

- **`scheme_finance`** — allocated/released/expended per scheme×state×district
- **`scheme_delivery`** — units target/completed/delivery_pct per scheme×state×district
- **`money_flow`** — normalized union across ALL schemes for cross-scheme queries

## Key Files

| File | Purpose | Lines |
|------|---------|-------|
| `db.py` | Schema, 13 loaders, 3 VIEWs | ~960 |
| `query.py` | 18 query functions + data_quality_warnings() | ~1230 |
| `journalist_brief.py` | Per-district/state briefs with red flags | ~1195 |
| `run_all.py` | Orchestrator: scrape + load | ~448 |
| `cli.py` | Natural language CLI (keyword routing) | ~303 |
| `normalize_states.py` | State name normalization | ~117 |

## Data Quality Context

- 3/8 schemes have real financial data (MGNREGA, PMGSY, PM Kisan)
- 5/8 have hollow financial columns (zeros) — delivery metrics may still work
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
- DB path: `data/hisaab.db` (defined in `db.py:DB_PATH`, also independently in query.py and journalist_brief.py)
