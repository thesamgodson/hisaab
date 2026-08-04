"""
PMAY-G state-level financial scraper (data.gov.in API).

Fetches fund allocation, release, and utilization from data.gov.in:
  - 114ded92: 2020-21 allocation + release + utilization (35 states)
  - f0ed0d0a: 2021-22 allocation + release (35 states)

Amounts are in lakhs.

Output: data/curated/pmayg_finance_all_latest.json

Usage:
    python3 scrape_pmayg_dashboard.py
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

try:
    from scrapers.io_utils import atomic_write_json
except ImportError:
    from io_utils import atomic_write_json

ROOT_DIR = Path(__file__).resolve().parent.parent  # repo root (scrapers/ is a package)
CURATED_DIR = ROOT_DIR / "data" / "curated"

API_KEY = "579b464db66ec23bdd000001cdc3b564546246a772a26393094f5645"
API_BASE = "https://api.data.gov.in/resource"
PAGE_SIZE = 500
DELAY_SECONDS = 1.0
MAX_RETRIES = 3

DATASETS = {
    "fin_2020_21": "114ded92-f6b9-4d22-b2e1-82613ea1eda4",
    "fin_2021_22": "f0ed0d0a-1892-4479-a646-0fe72d82eca8",
}


def utc_iso() -> str:
    return datetime.now(UTC).isoformat()


def fetch_all_records(uuid: str) -> list[dict[str, Any]]:
    all_records: list[dict[str, Any]] = []
    offset = 0
    while True:
        params: dict[str, Any] = {
            "api-key": API_KEY,
            "format": "json",
            "offset": offset,
            "limit": PAGE_SIZE,
        }
        for attempt in range(MAX_RETRIES):
            try:
                resp = requests.get(
                    f"{API_BASE}/{uuid}", params=params, timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                break
            except (requests.RequestException, ValueError) as e:
                if attempt < MAX_RETRIES - 1:
                    wait = (attempt + 1) * 2
                    print(f"  Retry {attempt + 1}/{MAX_RETRIES} after {wait}s: {e}")
                    time.sleep(wait)
                else:
                    print(f"  ERROR fetching {uuid} offset={offset}: {e}")
                    return all_records

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


def _parse_amount(val: Any) -> float:
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    cleaned = str(val).replace(",", "").strip()
    if not cleaned or cleaned == "-":
        return 0.0
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


_CANONICAL_STATES = {
    "TAMILNADU": "TAMIL NADU",
    "JAMMU & KASHMIR": "JAMMU AND KASHMIR",
    "ANDAMAN & NICOBAR ISLANDS": "ANDAMAN AND NICOBAR ISLANDS",
    "DADRA & NAGAR HAVELI": "DADRA AND NAGAR HAVELI",
    "DADRA & NAGAR HAVELI AND DAMAN & DIU": "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
    "DAMAN & DIU": "DAMAN AND DIU",
}


def _normalize_state(name: str) -> str:
    cleaned = re.sub(r"[*#@^]+$", "", str(name)).strip()
    cleaned = re.sub(r"\s*\(.*?\)\s*$", "", cleaned).strip()
    upper = cleaned.upper()
    return _CANONICAL_STATES.get(upper, upper)


def _is_total_row(state: str) -> bool:
    if not state:
        return True
    skip_exact = {"TOTAL", "GRAND TOTAL", "ALL INDIA", "INDIA"}
    if state in skip_exact:
        return True
    return any(kw in state for kw in ("TOTAL", "ALL INDIA", "OTHERS"))


def _get_state(r: dict) -> str:
    for k in ("state_ut", "states_uts", "state_uts", "state"):
        if r.get(k):
            return _normalize_state(r[k])
    return ""


def transform_fin_2020_21(
    raw: list[dict[str, Any]], scraped_at: str,
) -> list[dict[str, Any]]:
    """Transform 114ded92: central_allocation_, central_release, utilization_ (2020-21).

    All amounts in lakhs.
    """
    curated: list[dict[str, Any]] = []
    source = f"api.data.gov.in/resource/{DATASETS['fin_2020_21']}"

    for r in raw:
        state = _get_state(r)
        if _is_total_row(state):
            continue

        allocated = _parse_amount(r.get("central_allocation_", 0))
        released = _parse_amount(r.get("central_release", 0))
        utilized = _parse_amount(r.get("utilization_", 0))

        if allocated > 0 or released > 0 or utilized > 0:
            curated.append({
                "state": state,
                "fin_year": "2020-2021",
                "allocated_lakhs": allocated,
                "released_lakhs": released,
                "utilized_lakhs": utilized,
                "source_url": source,
                "scraped_at": scraped_at,
            })

    return curated


def transform_fin_2021_22(
    raw: list[dict[str, Any]], scraped_at: str,
) -> list[dict[str, Any]]:
    """Transform f0ed0d0a: central_allocation_2021_22_, central_release (2021-22)."""
    curated: list[dict[str, Any]] = []
    source = f"api.data.gov.in/resource/{DATASETS['fin_2021_22']}"

    for r in raw:
        state = _get_state(r)
        if _is_total_row(state):
            continue

        allocated = _parse_amount(r.get("central_allocation_2021_22_", 0))
        released = _parse_amount(r.get("central_release", 0))

        if allocated > 0 or released > 0:
            curated.append({
                "state": state,
                "fin_year": "2021-2022",
                "allocated_lakhs": allocated,
                "released_lakhs": released,
                "utilized_lakhs": 0.0,
                "source_url": source,
                "scraped_at": scraped_at,
            })

    return curated


def scrape_all() -> list[dict[str, Any]]:
    scraped_at = utc_iso()
    all_curated: list[dict[str, Any]] = []

    print("Fetching PMAY-G financial 2020-21...")
    raw = fetch_all_records(DATASETS["fin_2020_21"])
    print(f"  Got {len(raw)} raw records")
    if raw:
        all_curated.extend(transform_fin_2020_21(raw, scraped_at))

    time.sleep(2)

    print("Fetching PMAY-G financial 2021-22...")
    raw = fetch_all_records(DATASETS["fin_2021_22"])
    print(f"  Got {len(raw)} raw records")
    if raw:
        all_curated.extend(transform_fin_2021_22(raw, scraped_at))

    print(f"\nTotal curated records: {len(all_curated)}")
    return sorted(all_curated, key=lambda x: (x["state"], x["fin_year"]))


def save_curated(records: list[dict[str, Any]]) -> Path:
    path = CURATED_DIR / "pmayg_finance_all_latest.json"
    atomic_write_json(path, records)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scrape PMAY-G financial data from data.gov.in",
    )
    parser.parse_args()

    records = scrape_all()
    if not records:
        print("\nNo records scraped.")
        return 1

    path = save_curated(records)
    print(f"\nSaved {len(records)} records to {path}")

    years = sorted({r["fin_year"] for r in records})
    states = sorted({r["state"] for r in records})
    print(f"Years: {', '.join(years)}")
    print(f"States: {len(states)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
