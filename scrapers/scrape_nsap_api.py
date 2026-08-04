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
  - Uses the shared data.gov.in demo key by default; set DATA_GOV_IN_API_KEY to a
    registered project key to lift the rate-limit ceiling.

Usage:
    python3 scrape_nsap_api.py                           # All states, auto FY
    python3 scrape_nsap_api.py --states "BIHAR"          # Single state
    python3 scrape_nsap_api.py --fin-year "2023-2024"    # Pin a specific FY
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

try:
    from scrapers.io_utils import (
        atomic_write_json,
        current_indian_fy,
        datagov_api_key,
        datagov_session,
    )
except ImportError:
    from io_utils import (
        atomic_write_json,
        current_indian_fy,
        datagov_api_key,
        datagov_session,
    )

ROOT_DIR = Path(__file__).resolve().parent.parent  # repo root (scrapers/ is a package)
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw" / "nsap"
CURATED_DIR = DATA_DIR / "curated"

# data.gov.in public demo API key
SESSION = datagov_session()
API_KEY = datagov_api_key()
API_BASE = "https://api.data.gov.in/resource"

SCHEMES = {
    "IGNOAPS": "81ebd89d-a528-4d33-bdd1-430527b6f8aa",
    "IGNWPS": "6ffcdce4-bcbc-45a7-8bd4-286b7e2860e3",
    "IGNDPS": "e1a7ca20-36b6-46ba-b6ed-6495f11c4242",
}

DELAY_SECONDS = 2.5  # demo API key rate-limits hard; 0.5s drew 429s mid-pagination
PAGE_SIZE = 500


def utc_iso() -> str:
    return datetime.now(UTC).isoformat()


def state_slug(name: str) -> str:
    return name.lower().replace("&", "and").replace(" ", "-")


def ensure_dirs() -> None:
    for d in (RAW_DIR, CURATED_DIR):
        d.mkdir(parents=True, exist_ok=True)


def _fy_has_data(fin_year: str) -> bool:
    """One cheap request: does the resource carry any IGNOAPS rows for this FY?"""
    params = {
        "api-key": API_KEY,
        "format": "json",
        "offset": 0,
        "limit": 1,
        "filters[fin_year]": fin_year,
    }
    resp = SESSION.get(f"{API_BASE}/{SCHEMES['IGNOAPS']}", params=params, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return bool(data.get("records")) or int(data.get("total") or 0) > 0


def resolve_fin_year(preferred: str | None = None, lookback: int = 2) -> str:
    """Choose the FY to scrape.

    An explicit `preferred` FY wins outright. Otherwise start at the current
    Indian FY and step back a year at a time (up to `lookback` steps) until the
    resource actually carries data — data.gov.in publishes NSAP monthly and the
    running FY can be empty for weeks after it begins while the prior year stays
    populated. Returns the current FY if every probe is empty (the empty-result
    no-op then leaves existing curated data untouched)."""
    if preferred:
        return preferred
    fy = current_indian_fy()
    newest = fy
    for _ in range(lookback + 1):
        try:
            if _fy_has_data(fy):
                return fy
        except (requests.RequestException, ValueError):
            pass  # transient probe failure: try the next-older FY
        start = int(fy.split("-")[0]) - 1
        fy = f"{start}-{start + 1}"
    return newest


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
            resp = SESSION.get(url, params=params, timeout=120)
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, ValueError) as e:
            # A partial page set must never be persisted: a swallowed 429 at
            # offset=500 once truncated IGNDPS 5720→500 raw records and the
            # caller wrote the 15%-short result over all 36 state files.
            raise RuntimeError(
                f"{scheme_code} pull failed at offset={offset} after session retries: {e}"
            ) from e

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

        curated.append(
            {
                "district": _district,
                "state": _state,
                "state_code": r.get("lgd_state_code", ""),
                "fin_year": fin_year,
                "scheme_type": _scheme,
                "beneficiaries_eligible": 0,  # Not available in API
                "beneficiaries_paid": int(r.get("total_beneficiaries", 0)),
                "amount_paid_lakhs": 0,  # Not available in API
                "pension_per_month": 0,  # Not available in API
                "source_url": "api.data.gov.in/resource/nsap",
                "scraped_at": scraped_at,
            }
        )

    return curated


def scrape_all(
    fin_year: str | None = None,
    states_filter: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Scrape all NSAP scheme data from data.gov.in API.

    With no fin_year, auto-resolves to the current Indian FY (falling back to the
    latest year the resource publishes) — never a stale hardcoded year.
    """
    if fin_year is None:
        fin_year = resolve_fin_year()
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
    atomic_write_json(path, records)
    return path


def _distinct_pairs(records: list[dict[str, Any]]) -> set[tuple[str, str]]:
    return {(str(r.get("state", "")), str(r.get("district", ""))) for r in records}


def _existing_curated_pairs() -> set[tuple[str, str]]:
    """Distinct (state, district) pairs across all existing nsap curated files."""
    pairs: set[tuple[str, str]] = set()
    for p in CURATED_DIR.glob("nsap_district_*_latest.json"):
        try:
            for r in json.loads(p.read_text(encoding="utf-8")):
                pairs.add((str(r.get("state", "")), str(r.get("district", ""))))
        except (json.JSONDecodeError, OSError):
            continue
    return pairs


def save_curated_by_state(
    records: list[dict[str, Any]], national: bool = True
) -> dict[str, Path]:
    """Save per-state curated files.

    Granularity guard (national runs only): a full pull covering fewer distinct
    (state, district) pairs than the existing curated set is refused, not
    written — this is the partial-early-FY trap, where the running year has a
    handful of reporting districts and would otherwise replace the complete
    prior year. Mirrors the NRLM/PM Kisan/NFSA guards (learnings.md 2026-08-04).
    Targeted --states runs skip the aggregate guard: they legitimately touch
    only the named states' files.
    """
    if national:
        new_pairs = _distinct_pairs(records)
        existing = _existing_curated_pairs()
        if existing and len(new_pairs) < len(existing):
            raise ValueError(
                f"Refusing NSAP save: new pull covers {len(new_pairs)} distinct "
                f"(state, district) pairs, existing curated has {len(existing)} — a "
                "refresh must never reduce coverage. Likely a partial early-FY pull; "
                "the prior complete year is kept."
            )

    by_state: dict[str, list[dict[str, Any]]] = {}
    for r in records:
        by_state.setdefault(r["state"], []).append(r)

    paths: dict[str, Path] = {}
    for state_name, state_records in sorted(by_state.items()):
        slug = state_slug(state_name)
        path = CURATED_DIR / f"nsap_district_{slug}_latest.json"
        atomic_write_json(path, state_records)
        paths[state_name] = path

    return paths


def process_live(fin_year: str | None = None) -> int:
    """Scrape NSAP district data for the resolved FY and save per-state.

    Entry point for run_all.py (mirrors scrape_nfsa.process_live). With no
    fin_year it auto-tracks the current Indian FY, falling back to the latest
    year the resource actually publishes. Returns the number of curated rows.
    """
    ensure_dirs()
    resolved = resolve_fin_year(fin_year)
    print(f"  NSAP: resolved FY -> {resolved}")
    records = scrape_all(fin_year=resolved)
    if not records:
        print(f"  NSAP: no records for FY {resolved} — curated files untouched")
        return 0
    save_raw(records, resolved)
    save_curated_by_state(records, national=True)
    return len(records)


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
    parser.add_argument(
        "--fin-year",
        default=None,
        help="Financial year, e.g. 2025-2026. Default: auto — current Indian FY, "
        "falling back to the latest year the resource publishes.",
    )
    args = parser.parse_args()

    ensure_dirs()

    states_filter = None
    if args.states:
        states_filter = [s.strip() for s in args.states.split(",")]

    fin_year = resolve_fin_year(args.fin_year)
    print(f"NSAP scrape — FY {fin_year}{' (auto-resolved)' if not args.fin_year else ''}")
    records = scrape_all(fin_year=fin_year, states_filter=states_filter)

    if not records:
        print("\nNo records scraped.")
        return 1

    raw_path = save_raw(records, fin_year)
    print(f"\nRaw data saved: {raw_path}")

    paths = save_curated_by_state(records, national=states_filter is None)
    print_summary(records, paths)
    return 0


if __name__ == "__main__":
    sys.exit(main())
