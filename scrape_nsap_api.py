"""
NSAP (National Social Assistance Programme) API scraper.

Fetches district-level pension beneficiary data directly from data.gov.in API.
Covers 3 sub-schemes with district+monthly beneficiary counts:
  - IGNOAPS: Old Age Pension (UUID: 81ebd89d-a528-4d33-bdd1-430527b6f8aa)
  - IGNWPS: Widow Pension (UUID: 6ffcdce4-bcbc-45a7-8bd4-286b7e2860e3)
  - IGNDPS: Disability Pension (UUID: e1a7ca20-36b6-46ba-b6ed-6495f11c4242)

Data limitations:
  - Only beneficiary counts available (no amounts, no eligibility, no pension rates)
  - Monthly snapshots — we take the latest available month per district per FY
  - Free API key from data.gov.in (public key included for convenience)

Usage:
    python3 scrape_nsap_api.py                           # All states, latest FY
    python3 scrape_nsap_api.py --states "BIHAR"          # Single state
    python3 scrape_nsap_api.py --fin-year "2023-2024"    # Specific FY
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw" / "nsap"
CURATED_DIR = DATA_DIR / "curated"

# data.gov.in public demo API key
API_KEY = "579b464db66ec23bdd000001cdc3b564546246a772a26393094f5645"
API_BASE = "https://api.data.gov.in/resource"

SCHEMES = {
    "IGNOAPS": "81ebd89d-a528-4d33-bdd1-430527b6f8aa",
    "IGNWPS": "6ffcdce4-bcbc-45a7-8bd4-286b7e2860e3",
    "IGNDPS": "e1a7ca20-36b6-46ba-b6ed-6495f11c4242",
}

DELAY_SECONDS = 0.5
PAGE_SIZE = 500


def utc_iso() -> str:
    return datetime.now(UTC).isoformat()


def state_slug(name: str) -> str:
    return name.lower().replace("&", "and").replace(" ", "-")


def ensure_dirs() -> None:
    for d in (RAW_DIR, CURATED_DIR):
        d.mkdir(parents=True, exist_ok=True)


def fetch_scheme_data(
    scheme_code: str,
    uuid: str,
    fin_year: str,
    state_filter: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch all records for a scheme from data.gov.in API."""
    all_records: list[dict[str, Any]] = []
    offset = 0

    while True:
        params: dict[str, Any] = {
            "api-key": API_KEY,
            "format": "json",
            "offset": offset,
            "limit": PAGE_SIZE,
            "filters[fin_year]": fin_year,
        }
        if state_filter:
            params["filters[state_name]"] = state_filter

        url = f"{API_BASE}/{uuid}"

        try:
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, ValueError) as e:
            print(f"  ERROR fetching {scheme_code} offset={offset}: {e}")
            break

        records = data.get("records", [])
        if not records:
            break

        all_records.extend(records)
        total = int(data.get("total", 0))

        if offset + PAGE_SIZE >= total:
            break
        offset += PAGE_SIZE
        time.sleep(DELAY_SECONDS)

    return all_records


def aggregate_latest_month(
    records: list[dict[str, Any]],
) -> dict[tuple[str, str, str], dict[str, Any]]:
    """For each (state, district, scheme), keep only the latest month's data."""
    best: dict[tuple[str, str, str], dict[str, Any]] = {}

    for r in records:
        key = (
            r.get("state_name", "").upper(),
            r.get("district_name", "").upper(),
            r.get("scheme_code", "").upper(),
        )
        month = r.get("mnth", "00")
        existing = best.get(key)
        if existing is None or month > existing.get("mnth", "00"):
            best[key] = r

    return best


def transform_records(
    raw_records: list[dict[str, Any]],
    fin_year: str,
    scraped_at: str,
) -> list[dict[str, Any]]:
    """Transform API records into our standard schema, taking latest month per district."""
    # Aggregate to latest month
    latest = aggregate_latest_month(raw_records)

    curated: list[dict[str, Any]] = []
    for (_state, _district, _scheme), r in sorted(latest.items()):
        if not _district or _district in ("TOTAL", "GRAND TOTAL"):
            continue

        curated.append({
            "district": _district,
            "state": _state,
            "state_code": r.get("lgd_state_code", ""),
            "fin_year": fin_year,
            "scheme_type": _scheme,
            "beneficiaries_eligible": 0,  # Not available in API
            "beneficiaries_paid": int(r.get("total_beneficiaries", 0)),
            "amount_paid_lakhs": 0,  # Not available in API
            "pension_per_month": 0,  # Not available in API
            "source_url": f"api.data.gov.in/resource/nsap",
            "scraped_at": scraped_at,
        })

    return curated


def scrape_all(
    fin_year: str = "2024-2025",
    states_filter: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Scrape all NSAP scheme data from data.gov.in API."""
    scraped_at = utc_iso()
    all_raw: list[dict[str, Any]] = []

    for scheme_code, uuid in SCHEMES.items():
        state_arg = states_filter[0] if states_filter and len(states_filter) == 1 else None
        print(f"\nFetching {scheme_code}...")
        raw = fetch_scheme_data(scheme_code, uuid, fin_year, state_filter=state_arg)
        print(f"  Got {len(raw)} raw records")
        all_raw.extend(raw)

    # If multiple states in filter, apply filter post-fetch
    if states_filter and len(states_filter) > 1:
        filter_upper = {s.upper() for s in states_filter}
        all_raw = [r for r in all_raw if r.get("state_name", "").upper() in filter_upper]

    curated = transform_records(all_raw, fin_year, scraped_at)
    print(f"\nTotal curated records: {len(curated)}")
    return curated


def save_raw(records: list[dict[str, Any]], fin_year: str) -> Path:
    path = RAW_DIR / f"nsap_api_{fin_year}_raw.json"
    path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def save_curated_by_state(records: list[dict[str, Any]]) -> dict[str, Path]:
    by_state: dict[str, list[dict[str, Any]]] = {}
    for r in records:
        by_state.setdefault(r["state"], []).append(r)

    paths: dict[str, Path] = {}
    for state_name, state_records in sorted(by_state.items()):
        slug = state_slug(state_name)
        path = CURATED_DIR / f"nsap_district_{slug}_latest.json"
        path.write_text(
            json.dumps(state_records, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        paths[state_name] = path

    return paths


def print_summary(records: list[dict[str, Any]], paths: dict[str, Path]) -> None:
    print("\n" + "=" * 60)
    print("NSAP API Scraping Summary")
    print("=" * 60)
    print(f"States/UTs covered: {len(paths)}")
    print(f"Total records: {len(records)}")

    schemes = {}
    for r in records:
        schemes[r["scheme_type"]] = schemes.get(r["scheme_type"], 0) + 1
    for s, c in sorted(schemes.items()):
        print(f"  {s}: {c} district records")

    print()
    for state_name, path in sorted(paths.items()):
        count = sum(1 for r in records if r["state"] == state_name)
        print(f"  {state_name}: {count} records -> {path.name}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scrape NSAP pension data from data.gov.in API",
    )
    parser.add_argument("--states", help="Comma-separated list of states")
    parser.add_argument("--fin-year", default="2024-2025")
    args = parser.parse_args()

    ensure_dirs()

    states_filter = None
    if args.states:
        states_filter = [s.strip() for s in args.states.split(",")]

    records = scrape_all(fin_year=args.fin_year, states_filter=states_filter)

    if not records:
        print("\nNo records scraped.")
        return 1

    raw_path = save_raw(records, args.fin_year)
    print(f"\nRaw data saved: {raw_path}")

    paths = save_curated_by_state(records)
    print_summary(records, paths)
    return 0


if __name__ == "__main__":
    sys.exit(main())
