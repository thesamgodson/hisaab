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

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
# Build database from curated data (no scraping needed)
python3 run_all.py --load-only

# Check what's loaded
python3 run_all.py --summary
python3 run_all.py --freshness

# Query via CLI
python3 cli.py “misappropriation villupuram”
python3 cli.py “worst roads bihar”
python3 cli.py “funds cuddalore”

# Generate journalist brief
python3 journalist_brief.py “CUDDALORE”
python3 journalist_brief.py --state “TAMIL NADU”

# Run tests
python3 -m pytest tests/ -v
```

## Architecture

```
scrape_*.py          → data/curated/*_latest.json    (scrapers → normalized JSON)
run_all.py --load-only → data/hisaab.db              (JSON → SQLite)
query.py             → 18 query functions             (SQL → structured answers)
cli.py               → natural language interface     (keyword routing)
journalist_brief.py  → per-district/state briefs      (red flags + citations)
```

### Unified VIEWs

- **`scheme_finance`** — allocated/released/expended across all schemes
- **`scheme_delivery`** — targets/completed/delivery_pct across all schemes
- **`money_flow`** — normalized cross-scheme union for comparative queries

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

3/8 schemes have full financial data (MGNREGA, PMGSY, PM Kisan). 5/8 have hollow financial columns but working delivery metrics. See `CLAUDE.md` for details.

## License

GNU Affero General Public License v3.0 — see `LICENSE`.
