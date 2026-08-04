"""
Jal Jeevan Mission (JJM) scraper.

Scrapes rural tap water connection data from ejalshakti.gov.in JSON API.
Returns all 754 districts across 34 states/UTs in a single API call.

Data includes: total households, households with tap water, coverage %,
year-wise progress (2019-20, 2020-21), district and national rankings.

Usage:
    python scrape_jjm.py                        # All states
    python scrape_jjm.py --states "BIHAR"       # Single state
    python scrape_jjm.py --states "BIHAR,TAMIL NADU"
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

ROOT_DIR = Path(__file__).resolve().parent.parent  # repo root (scrapers/ is a package)
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
CURATED_DIR = DATA_DIR / "curated"

API_URL = "https://ejalshakti.gov.in/jjmreport/JJMDistrictView.aspx/Bind_table_graph"
API_HEADERS = {
    "Content-Type": "application/json; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
}
API_PAYLOAD = {"StCode11": "11", "Cat": "11", "SubCat": "11", "Param": "21"}


def utc_iso() -> str:
    return datetime.now(UTC).isoformat()


def state_slug(name: str) -> str:
    return name.lower().replace(" ", "-").replace("&", "and")


def ensure_dirs() -> None:
    for d in (RAW_DIR, CURATED_DIR):
        d.mkdir(parents=True, exist_ok=True)


def fetch_all_districts() -> list[dict[str, Any]]:
    """Fetch all district data from JJM API in one call."""
    resp = requests.post(API_URL, json=API_PAYLOAD, headers=API_HEADERS, timeout=60)
    resp.raise_for_status()
    return resp.json().get("d", [])


def parse_records(
    raw_data: list[dict[str, Any]],
    states_filter: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Convert JJM API response to our standard record format."""
    scraped_at = utc_iso()
    source_url = "https://ejalshakti.gov.in/jjmreport/JJMDistrictView.aspx"
    records: list[dict[str, Any]] = []

    for d in raw_data:
        state_name = d.get("StateName", "").strip()
        district_name = d.get("Name", "").strip()

        if not state_name or not district_name:
            continue

        if states_filter and state_name.upper() not in [s.upper() for s in states_filter]:
            continue

        total_hh = _parse_int(d.get("Total", "0"))
        hh_with_tap = _parse_int(d.get("Value", "0"))
        hh_as_of_2019 = _parse_int(d.get("HH_01042019", "0"))
        hcpws_2019 = _parse_int(d.get("HCPWS_01042019", "0"))
        hcpws_19_20 = _parse_int(d.get("HCPWS_19_20", "0"))
        hcpws_20_21 = _parse_int(d.get("HCPWS_20_21", "0"))

        record = {
            "district": district_name.upper(),
            "state": state_name,
            "state_code": d.get("KeyValue", "").strip(),
            "fin_year": "cumulative",
            "total_households": total_hh,
            "households_with_tap": hh_with_tap,
            "tap_connections_provided": hh_with_tap,
            "coverage_pct": _parse_float(d.get("Per", "0")),
            "funds_released_lakhs": 0,  # Not in this API
            "funds_utilized_lakhs": 0,
            "hh_as_of_2019": hh_as_of_2019,
            "connections_pre_2019": hcpws_2019,
            "connections_2019_20": hcpws_19_20,
            "connections_2020_onwards": hcpws_20_21,
            "remaining_households": _parse_int(d.get("HC_Remain", "0")),
            "district_rank": _parse_int(d.get("Rank", "0")),
            "national_rank": _parse_int(d.get("AllIndiaRank", "0")),
            "district_name_hindi": d.get("Name_hi", ""),
            "source_url": source_url,
            "scraped_at": scraped_at,
        }
        records.append(record)

    return records


def _parse_int(val: str | int) -> int:
    if isinstance(val, int):
        return val
    val = str(val).strip().replace(",", "")
    if not val or val == "-":
        return 0
    try:
        return int(float(val))
    except ValueError:
        return 0


def _parse_float(val: str | float) -> float:
    if isinstance(val, (int, float)):
        return float(val)
    val = str(val).strip().replace(",", "")
    if not val or val == "-":
        return 0.0
    try:
        return float(val)
    except ValueError:
        return 0.0


def save_curated(records: list[dict[str, Any]], state_name: str) -> Path:
    slug = state_slug(state_name)
    path = CURATED_DIR / f"jjm_district_{slug}_latest.json"
    path.write_text(
        json.dumps(records, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def save_raw(raw_data: list[dict[str, Any]]) -> Path:
    path = RAW_DIR / "jjm_national_latest.json"
    path.write_text(
        json.dumps(raw_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def scrape(states: list[str] | None = None) -> dict[str, int]:
    """Scrape JJM data. Returns {state: record_count}."""
    ensure_dirs()

    print("  Fetching JJM national district data...")
    raw_data = fetch_all_districts()
    print(f"  Got {len(raw_data)} districts from API")

    save_raw(raw_data)

    records = parse_records(raw_data, states_filter=states)
    print(f"  Parsed {len(records)} records" + (f" (filtered to {len(states)} states)" if states else ""))

    # Group by state and save
    by_state: dict[str, list[dict[str, Any]]] = {}
    for r in records:
        by_state.setdefault(r["state"], []).append(r)

    results: dict[str, int] = {}
    for state_name, state_records in sorted(by_state.items()):
        path = save_curated(state_records, state_name)
        print(f"    {state_name}: {len(state_records)} districts → {path.name}")
        results[state_name] = len(state_records)

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape Jal Jeevan Mission data")
    parser.add_argument(
        "--states",
        help="Comma-separated state names (default: all states)",
    )
    args = parser.parse_args()

    states = [s.strip() for s in args.states.split(",")] if args.states else None
    print(f"JJM Scraper — {'all states' if not states else f'{len(states)} states'}")

    results = scrape(states)

    total = sum(results.values())
    print(f"\nTotal: {total} districts across {len(results)} states")
    return 0


if __name__ == "__main__":
    sys.exit(main())
