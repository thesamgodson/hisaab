"""
Hisaab — Run all scrapers and load data into SQLite.

This is the single entry point for collecting data across all 8 government schemes.
Run this script to populate your local database with the latest data.

Schemes supported:
  1. MGNREGA — Rural employment (scrapes nrega.nic.in)
  2. PMGSY — Rural roads (scrapes pmgsy.dord.gov.in)
  3. PMAY-G — Rural housing (scrapes report.pmayg.dord.gov.in, needs Playwright)
  4. PM Kisan — Farmer payments (CSV import from data.gov.in)
  5. JJM — Rural water (scrapes ejalshakti.gov.in JSON API)
  6. PM POSHAN — School nutrition (CSV import)
  7. NSAP — Pensions (CSV import)
  8. PDS/NFSA — Ration system (CSV import)

Quick start:
    pip install -r requirements.txt
    python run_all.py --load-only             # Load existing CSV/JSON data into DB
    python run_all.py --schemes jjm           # Scrape JJM (all India, no login)
    python run_all.py --schemes jjm,pmkisan   # JJM + PM Kisan CSVs
    python run_all.py --schemes all           # Everything (MGNREGA/PMGSY need Playwright)

What each mode does:
    --load-only    Just loads existing data/curated/*.json and data/raw/*/*.csv into DB
    --schemes X    Runs specified scrapers, then loads into DB
    --states X     Filter to specific states (for MGNREGA, PMGSY, PMAY-G)
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent
CURATED_DIR = ROOT_DIR / "data" / "curated"
RAW_DIR = ROOT_DIR / "data" / "raw"
STATES_FILE = ROOT_DIR / "states.json"

# All scheme identifiers
ALL_SCHEMES = ["mgnrega", "pmgsy", "pmayg", "pmkisan", "jjm", "pmposhan", "nsap", "nfsa"]

# Schemes that can be scraped live (have web scrapers)
LIVE_SCRAPERS = {"mgnrega", "pmgsy", "pmayg", "jjm"}

# Schemes that use CSV import only
CSV_IMPORTERS = {"pmkisan", "pmposhan", "nsap", "nfsa"}


def load_states() -> list[dict[str, str]]:
    return json.loads(STATES_FILE.read_text(encoding="utf-8"))


def filter_states(
    all_states: list[dict[str, str]],
    state_names: str | None,
    batch: int = 0,
) -> list[dict[str, str]]:
    if state_names:
        names = {s.strip().upper() for s in state_names.split(",")}
        return [s for s in all_states if s["state_name"].upper() in names]
    if batch > 0:
        return all_states[:batch]
    return all_states


def scrape_jjm(states: list[str] | None = None) -> dict[str, int]:
    """Run JJM scraper — pure requests, all India in one call."""
    try:
        from scrape_jjm import scrape
        return scrape(states)
    except Exception as exc:
        print(f"  JJM scrape failed: {exc}")
        return {}


def scrape_pmayg(states: list[dict[str, str]], fin_year: str) -> dict[str, int]:
    """Run PMAY-G scraper — needs Playwright."""
    results: dict[str, int] = {}
    try:
        import asyncio
        from scrape_pmayg import scrape_state, STATE_CODES
        for state in states:
            name = state["state_name"].upper()
            if name not in STATE_CODES:
                print(f"  PMAY-G: {name} not in state codes, skipping")
                continue
            try:
                count = asyncio.run(scrape_state(name, fin_year))
                results[name] = count
                print(f"  PMAY-G {name}: {count} districts")
            except Exception as exc:
                print(f"  PMAY-G {name} failed: {exc}")
    except ImportError as exc:
        print(f"  PMAY-G import failed (need playwright?): {exc}")
    return results


def scrape_mgnrega(states: list[dict[str, str]], fin_year: str, reports: list[str]) -> dict[str, int]:
    """Run MGNREGA scraper."""
    results: dict[str, int] = {}
    try:
        from scrape_reports import run_for_state, slugify
        for state in states:
            name = state["state_name"]
            code = state["state_code"]
            try:
                rc = run_for_state(
                    state_name=name,
                    state_code=code,
                    fin_year=fin_year,
                    reports=reports,
                    delay_sec=2.0,
                )
                results[name] = 0 if rc != 0 else 1
            except Exception as exc:
                print(f"  MGNREGA {name} failed: {exc}")
            time.sleep(3)
    except ImportError as exc:
        print(f"  MGNREGA import failed: {exc}")
    return results


def scrape_pmgsy(states: list[dict[str, str]]) -> dict[str, int]:
    """Run PMGSY scraper."""
    results: dict[str, int] = {}
    try:
        from scrape_pmgsy import load_catalog, run_for_state
        catalog = load_catalog()
        for state in states:
            name = state["state_name"].upper()
            config = catalog.get(name)
            if not config:
                print(f"  PMGSY: {name} not in catalog, skipping")
                continue
            try:
                rc = run_for_state(
                    state_name=config.state_name,
                    pmgsy_state_id=config.pmgsy_state_id,
                    delay_sec=2.0,
                )
                results[name] = 0 if rc != 0 else 1
            except Exception as exc:
                print(f"  PMGSY {name} failed: {exc}")
            time.sleep(3)
    except ImportError as exc:
        print(f"  PMGSY import failed: {exc}")
    return results


def import_csvs(scheme: str) -> int:
    """Import all CSV files for a scheme from data/raw/{scheme}/."""
    csv_dir = RAW_DIR / scheme
    if not csv_dir.exists():
        return 0

    csv_files = list(csv_dir.glob("*.csv"))
    if not csv_files:
        return 0

    importers = {
        "pmkisan": "scrape_pmkisan",
        "pmposhan": "scrape_pmposhan",
        "nsap": "scrape_nsap",
        "nfsa": "scrape_nfsa",
    }

    module_name = importers.get(scheme)
    if not module_name:
        return 0

    try:
        module = __import__(module_name)
        total = module.process_directory(csv_dir)
        return total
    except Exception as exc:
        print(f"  {scheme} CSV import failed: {exc}")
        return 0


def load_curated_into_db(fin_year: str) -> dict[str, int]:
    """Load all curated JSON files into SQLite."""
    from db import get_connection, init_db, LOADERS, CURATED_DIR
    from normalize_states import normalize_records

    conn = get_connection()
    init_db(conn)
    results: dict[str, int] = {}

    for loader_name, loader_fn in LOADERS.items():
        pattern = f"{loader_name}_*_latest.json"
        files = list(CURATED_DIR.glob(pattern))
        total = 0
        for path in files:
            try:
                records = json.loads(path.read_text(encoding="utf-8"))
                records = normalize_records(records, "state")
                count = loader_fn(conn, records, fin_year)
                conn.commit()
                total += count
            except Exception as exc:
                print(f"  Error loading {path.name}: {exc}")
        if total > 0:
            results[loader_name] = total

    conn.close()
    return results


def print_db_summary() -> None:
    """Print summary of all data in the database."""
    from db import get_connection, init_db

    conn = get_connection()
    init_db(conn)

    print("\n" + "=" * 60)
    print("DATABASE SUMMARY")
    print("=" * 60)

    # Count per scheme table
    tables = [
        ("MGNREGA — Misappropriation", "misappropriation"),
        ("MGNREGA — Financial Statement", "financial_statement"),
        ("MGNREGA — FTO Status", "fto_status"),
        ("MGNREGA — FTO Pendency", "fto_pendency"),
        ("MGNREGA — Issues Reported", "issues_reported"),
        ("PMGSY — State Progress", "pmgsy_progress"),
        ("PMGSY — District Detail", "pmgsy_district"),
        ("PMAY-G — District", "pmayg_district"),
        ("PM Kisan — District", "pmkisan_district"),
        ("JJM — District", "jjm_district"),
        ("PM POSHAN — District", "pmposhan_district"),
        ("NSAP — District", "nsap_district"),
        ("PDS/NFSA — District", "nfsa_district"),
    ]

    total_records = 0
    for label, table in tables:
        try:
            row = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
            count = row[0] if row else 0
            if count > 0:
                states_row = conn.execute(f"SELECT COUNT(DISTINCT state) FROM {table}").fetchone()
                states_count = states_row[0] if states_row else 0
                print(f"  {label}: {count:,} records ({states_count} states)")
                total_records += count
        except Exception:
            pass

    # Money flow view
    try:
        row = conn.execute("SELECT COUNT(*) FROM money_flow").fetchone()
        mf_count = row[0] if row else 0
        schemes_row = conn.execute("SELECT COUNT(DISTINCT scheme) FROM money_flow").fetchone()
        schemes_count = schemes_row[0] if schemes_row else 0
        print(f"\n  money_flow VIEW: {mf_count:,} rows across {schemes_count} schemes")
    except Exception:
        pass

    print(f"\n  TOTAL: {total_records:,} records")
    conn.close()


SCHEME_TABLES = {
    "MGNREGA": ["misappropriation", "financial_statement", "fto_status", "fto_pendency", "issues_reported"],
    "PMGSY": ["pmgsy_progress", "pmgsy_district"],
    "PMAY-G": ["pmayg_district"],
    "PM Kisan": ["pmkisan_district"],
    "JJM": ["jjm_district"],
    "PM POSHAN": ["pmposhan_district"],
    "NSAP": ["nsap_district"],
    "PDS/NFSA": ["nfsa_district"],
}

SCHEME_SOURCES = {
    "MGNREGA": "nrega.nic.in",
    "PMGSY": "pmgsy.dord.gov.in",
    "PMAY-G": "report.pmayg.dord.gov.in",
    "PM Kisan": "data.gov.in",
    "JJM": "ejalshakti.gov.in",
    "PM POSHAN": "pmposhan-ams.education.gov.in",
    "NSAP": "nsap.nic.in / data.gov.in",
    "PDS/NFSA": "nfsa.gov.in",
}


def print_freshness() -> None:
    """Show per-scheme data freshness: newest scraped_at, record counts, state counts."""
    from db import get_connection, init_db

    conn = get_connection()
    init_db(conn)

    print(f"\n{'Scheme':<14} {'Latest scraped':<22} {'Records':>8} {'States':>7}  Source")
    print("-" * 85)

    for scheme, tables in SCHEME_TABLES.items():
        total_records = 0
        all_states: set[str] = set()
        latest_scraped = ""

        for table in tables:
            try:
                row = conn.execute(f"SELECT COUNT(*) as cnt FROM {table}").fetchone()
                total_records += row[0] if row else 0

                states_rows = conn.execute(f"SELECT DISTINCT state FROM {table}").fetchall()
                all_states.update(r[0] for r in states_rows if r[0])

                ts_row = conn.execute(f"SELECT MAX(scraped_at) as ts FROM {table}").fetchone()
                ts = ts_row[0] if ts_row and ts_row[0] else ""
                if ts > latest_scraped:
                    latest_scraped = ts
            except Exception:
                pass

        scraped_display = latest_scraped[:10] if latest_scraped else "no data"
        source = SCHEME_SOURCES.get(scheme, "")
        print(f"  {scheme:<12} {scraped_display:<22} {total_records:>8,} {len(all_states):>5}  {source}")

    conn.close()
    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Hisaab — Run all scrapers and build database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_all.py --load-only                   # Load existing data into DB
  python run_all.py --schemes jjm                 # Scrape JJM (all India)
  python run_all.py --schemes pmkisan,nsap,nfsa   # Import CSVs for 3 schemes
  python run_all.py --schemes pmayg --states BIHAR # Scrape PMAY-G for Bihar
  python run_all.py --schemes all --states BIHAR   # All schemes for Bihar
        """,
    )
    parser.add_argument("--fin-year", default="2024-2025", help="Financial year (default: 2024-2025)")
    parser.add_argument("--states", help="Comma-separated state names (default: all)")
    parser.add_argument("--batch", type=int, default=0, help="Only run first N states")
    parser.add_argument(
        "--schemes",
        default="",
        help=f"Comma-separated schemes to scrape: {','.join(ALL_SCHEMES)} or 'all'",
    )
    parser.add_argument("--load-only", action="store_true", help="Skip scraping, just load existing data into DB")
    parser.add_argument("--summary", action="store_true", help="Just print DB summary and exit")
    parser.add_argument("--freshness", action="store_true", help="Show data freshness per scheme and exit")
    args = parser.parse_args()

    if args.freshness:
        print_freshness()
        return 0

    if args.summary:
        print_db_summary()
        return 0

    all_states = load_states()
    states = filter_states(all_states, args.states, args.batch)

    if args.load_only:
        print("Loading existing curated data into database...")
        # First import any CSVs to curated JSON
        for scheme in CSV_IMPORTERS:
            csv_dir = RAW_DIR / scheme
            if csv_dir.exists() and list(csv_dir.glob("*.csv")):
                print(f"\n  Importing {scheme} CSVs...")
                count = import_csvs(scheme)
                if count:
                    print(f"  {scheme}: {count} records imported")

        results = load_curated_into_db(args.fin_year)
        print("\nLoaded into database:")
        for name, count in sorted(results.items()):
            print(f"  {name}: {count:,} records")
        print(f"  TOTAL: {sum(results.values()):,}")
        print_db_summary()
        return 0

    # Parse schemes
    if not args.schemes:
        print("Specify --schemes or --load-only. See --help.")
        return 1

    schemes = ALL_SCHEMES if args.schemes == "all" else [s.strip().lower() for s in args.schemes.split(",")]
    invalid = [s for s in schemes if s not in ALL_SCHEMES]
    if invalid:
        print(f"Unknown schemes: {', '.join(invalid)}")
        print(f"Valid: {', '.join(ALL_SCHEMES)}")
        return 1

    state_names_for_filter = [s["state_name"] for s in states] if args.states else None

    print(f"Hisaab — Scraping {len(schemes)} scheme(s)")
    if args.states:
        print(f"States: {', '.join(s['state_name'] for s in states)}")
    print(f"FY: {args.fin_year}")
    print()

    # Run scrapers
    for scheme in schemes:
        print(f"\n{'─'*60}")
        print(f"  {scheme.upper()}")
        print(f"{'─'*60}")

        if scheme == "jjm":
            scrape_jjm(state_names_for_filter)

        elif scheme == "mgnrega":
            mgnrega_reports = ["misappropriation", "fto_status", "fto_pendency", "issues_reported", "financial_statement"]
            scrape_mgnrega(states, args.fin_year, mgnrega_reports)

        elif scheme == "pmgsy":
            scrape_pmgsy(states)

        elif scheme == "pmayg":
            scrape_pmayg(states, args.fin_year)

        elif scheme in CSV_IMPORTERS:
            count = import_csvs(scheme)
            if count:
                print(f"  Imported {count} records from CSVs")
            else:
                print(f"  No CSV files found in data/raw/{scheme}/")
                print(f"  Place CSV files there and re-run, or use:")
                print(f"  python scrape_{scheme}.py --csv <file> --state <STATE>")

    # Load all into DB
    print(f"\n{'─'*60}")
    print("  Loading into database...")
    print(f"{'─'*60}")
    results = load_curated_into_db(args.fin_year)
    for name, count in sorted(results.items()):
        if count > 0:
            print(f"  {name}: {count:,} records")

    print_db_summary()
    return 0


if __name__ == "__main__":
    sys.exit(main())
