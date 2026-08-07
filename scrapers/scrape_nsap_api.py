"""Fetch NSAP district pension snapshots from the data.gov.in API.

Only beneficiary counts are published. The latest month in each Indian fiscal
year is selected by stable LGD district identity for IGNOAPS, IGNWPS and IGNDPS.
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
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

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
    """Choose the requested FY or the newest populated FY in the lookback."""
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


def aggregate_latest_month(records: list[dict[str, Any]]) -> dict[tuple[str, str, str], dict[str, Any]]:
    """Keep the latest fiscal-month snapshot for each LGD district identity."""
    best: dict[tuple[str, str, str], dict[str, Any]] = {}
    ranks: dict[tuple[str, str, str], int] = {}

    for r in records:
        state = str(r.get("state_name", "")).strip().upper()
        district = str(r.get("district_name", "")).strip().upper()
        scheme = str(r.get("scheme_code", "")).strip().upper()
        code = str(r.get("lgd_district_code", "")).strip()
        month = str(r.get("mnth", "")).strip()
        if not state or not district or not scheme or not code.isdigit() or int(code) <= 0:
            raise ValueError(
                f"Unusable NSAP district identity: {state}/{district}/{scheme}/{code}"
            )
        if not month.isdigit() or not 1 <= int(month) <= 12:
            raise ValueError(f"Unusable NSAP month for {state}/{district}/{scheme}: {month!r}")
        key = (state, code, scheme)
        rank = (int(month) - 4) % 12
        if key in ranks and rank == ranks[key] and r != best[key]:
            raise ValueError(f"Conflicting NSAP snapshots for {key} in month {month}")
        if key not in ranks or rank > ranks[key]:
            best[key] = r
            ranks[key] = rank

    return best


def transform_records(
    raw_records: list[dict[str, Any]],
    fin_year: str,
    scraped_at: str,
) -> list[dict[str, Any]]:
    """Transform API records into our standard schema, taking latest month per district."""
    latest = aggregate_latest_month(raw_records)
    from db.normalize_districts import normalize_district

    canonical: dict[tuple[str, str, str], dict[str, Any]] = {}
    for (state, _code, scheme), row in latest.items():
        district = normalize_district(str(row["district_name"]), state)
        key = (state, district, scheme)
        current = canonical.get(key)
        rank = (int(row["mnth"]) - 4) % 12
        if current and rank == (int(current["mnth"]) - 4) % 12 and row != current:
            raise ValueError(f"Conflicting NSAP identities for {key} in month {row['mnth']}")
        if current is None or rank > (int(current["mnth"]) - 4) % 12:
            canonical[key] = row

    curated: list[dict[str, Any]] = []
    for (_state, district, _scheme), r in sorted(canonical.items()):
        curated.append(
            {
                "district": district,
                "state": _state,
                "state_code": r.get("lgd_state_code", ""),
                "district_lgd_code": str(r["lgd_district_code"]).strip(),
                "source_month": f"{int(r['mnth']):02d}",
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
    """Scrape all three NSAP schemes for the requested or resolved FY."""
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


def _coverage_identities(records: list[dict[str, Any]]) -> set[tuple[str, str]]:
    identities: set[tuple[str, str]] = set()
    for r in records:
        state = str(r.get("state", "")).strip().upper()
        code = str(r.get("district_lgd_code", "")).strip()
        if not state or not code.isdigit() or int(code) <= 0:
            raise ValueError(f"Unusable curated NSAP LGD identity: {state}/{code}")
        identities.add((state, code))
    return identities


def _existing_curated_identities(
    new_records: list[dict[str, Any]],
) -> set[tuple[str, str]]:
    from db.normalize_districts import normalize_district

    by_name: dict[tuple[str, str], str] = {}
    for r in new_records:
        state = str(r["state"]).strip().upper()
        district = normalize_district(str(r["district"]), state)
        code = str(r["district_lgd_code"]).strip()
        prior = by_name.setdefault((state, district), code)
        if prior != code:
            raise ValueError(f"Conflicting NSAP LGD codes for {state}/{district}")

    identities: set[tuple[str, str]] = set()
    for p in CURATED_DIR.glob("nsap_district_*_latest.json"):
        try:
            for r in json.loads(p.read_text(encoding="utf-8")):
                state = str(r.get("state", "")).strip().upper()
                code = str(r.get("district_lgd_code", "")).strip()
                if not code:
                    district = normalize_district(str(r.get("district", "")), state)
                    code = by_name.get((state, district), "")
                if not code.isdigit() or int(code) <= 0:
                    raise ValueError(f"Cannot map existing NSAP identity in {p.name}")
                identities.add((state, code))
        except (json.JSONDecodeError, OSError):
            continue
    return identities


def save_curated_by_state(
    records: list[dict[str, Any]], national: bool = True
) -> dict[str, Path]:
    """Save by state; national runs may not lose an LGD district identity."""
    if national:
        new_ids = _coverage_identities(records)
        existing = _existing_curated_identities(records)
        missing = existing - new_ids
        if missing:
            raise ValueError(
                f"Refusing NSAP save: new pull lost {len(missing)} LGD district "
                f"identities (new {len(new_ids)}, existing {len(existing)}); prior data kept"
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
    """Scrape the resolved FY and save per-state curated files."""
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
