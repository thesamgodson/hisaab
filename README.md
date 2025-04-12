# हिसाब / Hisaab

> Public accountability infrastructure for 8 Indian government welfare schemes.

## Manifesto

Any citizen should be able to ask, in their own language, “Where did the money go?” and get a plain-language answer with a verifiable government source.

Read: [`MANIFESTO.md`](MANIFESTO.md) | Claims policy: [`DATA_CLAIMS.md`](DATA_CLAIMS.md)

## 8 Schemes

| Scheme | What it covers | Source portal |
|--------|---------------|---------------|
| MGNREGA | Rural employment: fund flow, misappropriation, FTO status, social audit | nrega.nic.in |
| PMGSY | Rural roads: sanctioned vs completed, expenditure | pmgsy.dord.gov.in |
| PMAY-G | Rural housing: targets, completion, fund release | report.pmayg.dord.gov.in |
| PM Kisan | Farmer direct payments | data.gov.in |
| JJM | Rural water: tap connections target vs completed | ejalshakti.gov.in |
| PM POSHAN | School nutrition: children fed, meals served | pmposhan-ams.education.gov.in |
| NSAP | Pensions: beneficiaries paid (IGNOAPS, IGNWPS, IGNDPS) | nsap.nic.in / data.gov.in |
| PDS/NFSA | Ration distribution: card counts, allocation | nfsa.gov.in |

## Quick Start

```bash
# 1. Backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 run_all.py --load-only          # Build DB from curated data
uvicorn api.main:app --reload           # API at localhost:8000

# 2. Frontend
cd web && npm install && npm run dev    # UI at localhost:3000

# 3. Verify
python3 -m pytest tests/ -v            # 91 tests
curl localhost:8000/api/v1/schemes      # API health check
```

## Usage

```bash
# CLI queries
python3 cli.py “misappropriation villupuram”
python3 cli.py “worst roads bihar”

# Journalist briefs
python3 journalist_brief.py “CUDDALORE”
python3 journalist_brief.py --state “TAMIL NADU”

# Data audit
python3 data_audit.py                   # Per-column completeness
python3 data_audit.py --json            # Machine-readable
```

## Architecture

```
scrape_*.py     → data/curated/*.json   (scrapers → normalized JSON)
run_all.py      → data/hisaab.db        (JSON → SQLite + NSAP imputation)
db/             → schema, loaders, VIEWs (scheme_finance, scheme_delivery, money_flow)
queries/        → 33 query functions     (SQL → structured answers)
briefs/         → journalist briefs      (red flags + citations)
api/            → FastAPI REST API       (13 endpoints at /api/v1/*)
web/            → Next.js 15 frontend    (citizen interface at localhost:3000)
cli.py          → keyword-based CLI      (natural language routing)
```

## Scraping (optional)

Most data is already in `data/curated/`. To refresh:

```bash
# Scrape specific schemes
python3 run_all.py --schemes jjm              # JJM (all India, no login)
python3 run_all.py --schemes mgnrega,pmgsy    # Needs Playwright
python3 run_all.py --schemes all              # Everything

# Scrape specific states
python3 run_all.py --schemes mgnrega --states “TAMIL NADU,BIHAR”
```

## Data Quality

4/8 schemes have financial data (MGNREGA, PMGSY, PM Kisan = real; NSAP = imputed from GoI pension rates). 4/8 have hollow financial columns but working delivery metrics. See `CLAUDE.md` for details.

## License

GNU Affero General Public License v3.0 — see `LICENSE`.
