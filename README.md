# Hisaab

[![CI](https://github.com/thesamgodson/hisaab/actions/workflows/ci.yml/badge.svg)](https://github.com/thesamgodson/hisaab/actions/workflows/ci.yml)
[![Python 3.14+](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/downloads/)
[![Next.js 15](https://img.shields.io/badge/Next.js-15-black.svg)](https://nextjs.org/)
[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL--3.0-green.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Deploy](https://img.shields.io/badge/Vercel-Live-brightgreen.svg)](https://hisaab-one.vercel.app)

**Where did the money go?** Public accountability infrastructure for Indian government welfare schemes.

Enter your PIN code. See what your MP promised. Check what actually reached your district.

**Live:** [hisaab-one.vercel.app](https://hisaab-one.vercel.app)

Read the [Manifesto](MANIFESTO.md) | [Data Claims Policy](DATA_CLAIMS.md)

---

## Schemes Tracked

| Scheme | Coverage | Source |
|--------|----------|--------|
| MGNREGA | Rural employment, fund flow, FTO status (misappropriation frozen at FY2024-25) | mnregaweb2.dord.gov.in |
| PMGSY | Rural roads — sanctioned vs completed, expenditure | pmgsy.dord.gov.in |
| PMAY-G | Rural housing — targets, completion, fund release | report.pmayg.dord.gov.in |
| PM Kisan | Farmer direct benefit transfers | data.gov.in |
| JJM | Rural water — tap connections, coverage | ejalshakti.gov.in |
| PM POSHAN | School nutrition — children fed, meals served | pmposhan-ams.education.gov.in |
| NSAP | Pensions — IGNOAPS, IGNWPS, IGNDPS beneficiaries | nsap.nic.in / data.gov.in |
| PDS/NFSA | Ration distribution — card counts, allocation | nfsa.gov.in |
| SBM-G | Sanitation — ODF+ villages, star ratings | sbm.gov.in |
| DAY-NRLM | Rural livelihoods — SHGs, revolving fund | nrlm.gov.in |
| UDISE+ | Education — schools, enrollment, PTR, infra | udiseplus.gov.in |

## Stack

**Frontend:** Next.js 15 + React 19 + Tailwind CSS + TypeScript, deployed on Vercel
**Backend:** Python 3.14, SQLite/Turso, FastAPI
**Data:** Scrapers (requests + Playwright) → curated JSON → SQLite → API

## Local Development

```bash
# Data pipeline (Python)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 run_all.py --load-only              # build data/hisaab.db from curated JSON
python3 scripts/sync_turso.py --env-file web/.env.local   # publish to production DB

# Frontend (serves production traffic from Turso)
cd web && npm install
vercel env pull .env.local                  # Turso credentials
npm run dev
```

Data refreshes weekly via `.github/workflows/refresh-data.yml`
(scrape → load → publish → prod smoke test).

## API

All endpoints under `/api/v1/`:

| Endpoint | Description |
|----------|-------------|
| `GET /schemes` | List all schemes with data quality warnings |
| `GET /scheme/:scheme` | State-level summary |
| `GET /scheme/:scheme/worst` | Worst-performing districts |
| `GET /districts` | All districts with data |
| `GET /district/:name` | Full district overview |
| `GET /district/:name/schemes` | Schemes with data for a district |
| `GET /district/:name/money-flow` | Cross-scheme money flow |
| `GET /district/:name/:scheme` | Per-scheme district data |
| `GET /brief/:district` | Journalist brief with red flags |
| `GET /freshness` | Per-scheme scrape dates |
| `GET /data-quality` | Quality warnings |
| `GET /red-flags` | Worst districts by scheme |
| `POST /query` | Natural language query |

## Project Structure

```
web/            Next.js frontend + production /api/v1 (Vercel deployment root)
db/             Schema, loaders, VIEWs, district canonicalization
queries/        SQL query functions + composite scoring (precomputed)
scrapers/       Scheme-specific scrapers
constituency/   PIN / constituency / MP / MLA / district-lineage ingest
action_brief/   PIN → diagnosis → actions engine
briefs/         Journalist brief generator
scripts/        sync_turso.py (publish), gen_district_aliases.py, data_audit.py
api/            FastAPI (local analysis only — not deployed)
data/curated/   Normalized JSON from scrapers (source of truth for the DB)
tests/          pytest suite
```

## License

[AGPL-3.0](LICENSE)
