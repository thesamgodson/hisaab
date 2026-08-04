"""
NSAP state-level real financial data scraper (data.gov.in API).

Fetches actual fund release data to replace imputation at state level:
  - 8cb45bd3: 5 years (2019-24) of release (lakhs) + beneficiaries per state
    Fields: _2019_2020___release__in_lakh_, _2019_2020___number_of_beneficiaries, etc.
  - cdff8477: Central funds released per state, 2018-23 (crores)
    Fields: fund_release___2018_19, fund_release___2019_20, etc.

Output: data/curated/nsap_finance_all_latest.json
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
    "release_lakhs_2019_24": "8cb45bd3-04b4-4b1f-8eac-e1ea7311c755",
    "release_crores_2018_23": "cdff8477-d69a-4791-b995-6fd66731b08b",
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


def _match_year(key: str, fy_short: str) -> bool:
    """Check if a field key contains a year reference."""
    kl = key.lower().replace("-", "_")
    y1, y2 = fy_short.split("-")
    patterns = [
        f"{y1}_{y2}",
        f"{y1}_20{y2}",
        f"20{y1}_20{y2}" if len(y1) == 2 else f"{y1}_20{y2}",
    ]
    return any(p in kl for p in patterns)


def transform_release_lakhs(
    raw: list[dict[str, Any]], scraped_at: str,
) -> list[dict[str, Any]]:
    """Transform 8cb45bd3: release in lakhs + beneficiaries, 2019-24.

    Actual fields: _2019_2020___release__in_lakh_, _2019_2020___number_of_beneficiaries
    """
    curated: list[dict[str, Any]] = []
    source = f"api.data.gov.in/resource/{DATASETS['release_lakhs_2019_24']}"

    year_shorts = ["19-20", "20-21", "21-22", "22-23", "23-24"]

    for r in raw:
        state = _get_state(r)
        if _is_total_row(state):
            continue

        for fy_short in year_shorts:
            released = 0.0
            beneficiaries = 0
            for key, val in r.items():
                if _match_year(key, fy_short):
                    kl = key.lower()
                    if "release" in kl or "lakh" in kl:
                        released = _parse_amount(val)
                    elif "beneficiar" in kl or "number" in kl:
                        beneficiaries = int(_parse_amount(val))

            if released > 0 or beneficiaries > 0:
                curated.append({
                    "state": state,
                    "fin_year": f"20{fy_short[:2]}-20{fy_short[3:]}",
                    "released_lakhs": released,
                    "beneficiaries": beneficiaries,
                    "source_url": source,
                    "scraped_at": scraped_at,
                })

    return curated


def transform_release_crores(
    raw: list[dict[str, Any]], scraped_at: str,
) -> list[dict[str, Any]]:
    """Transform cdff8477: release in crores, 2018-23.

    Actual fields: fund_release___2018_19, fund_release___2019_20, etc.
    """
    curated: list[dict[str, Any]] = []
    source = f"api.data.gov.in/resource/{DATASETS['release_crores_2018_23']}"

    year_shorts = ["18-19", "19-20", "20-21", "21-22", "22-23"]

    for r in raw:
        state = _get_state(r)
        if _is_total_row(state):
            continue

        for fy_short in year_shorts:
            released_crores = 0.0
            for key, val in r.items():
                if _match_year(key, fy_short):
                    released_crores = _parse_amount(val)

            if released_crores > 0:
                curated.append({
                    "state": state,
                    "fin_year": f"20{fy_short[:2]}-20{fy_short[3:]}",
                    "released_lakhs": released_crores * 100,
                    "beneficiaries": 0,
                    "source_url": source,
                    "scraped_at": scraped_at,
                })

    return curated


def deduplicate(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep best record per (state, fin_year). Prefer with beneficiaries."""
    best: dict[tuple[str, str], dict[str, Any]] = {}
    for r in records:
        key = (r["state"], r["fin_year"])
        existing = best.get(key)
        if existing is None or r.get("beneficiaries", 0) > existing.get("beneficiaries", 0) or (
            r.get("released_lakhs", 0) > existing.get("released_lakhs", 0)
            and existing.get("beneficiaries", 0) == 0
        ):
            best[key] = r
    return sorted(best.values(), key=lambda x: (x["state"], x["fin_year"]))


def scrape_all() -> list[dict[str, Any]]:
    scraped_at = utc_iso()
    all_curated: list[dict[str, Any]] = []

    print("Fetching NSAP release (lakhs) 2019-24...")
    raw = fetch_all_records(DATASETS["release_lakhs_2019_24"])
    print(f"  Got {len(raw)} raw records")
    if raw:
        all_curated.extend(transform_release_lakhs(raw, scraped_at))

    time.sleep(2)

    print("Fetching NSAP release (crores) 2018-23...")
    raw = fetch_all_records(DATASETS["release_crores_2018_23"])
    print(f"  Got {len(raw)} raw records")
    if raw:
        all_curated.extend(transform_release_crores(raw, scraped_at))

    deduped = deduplicate(all_curated)
    print(f"\nTotal curated records (deduped): {len(deduped)}")
    return deduped


def save_curated(records: list[dict[str, Any]]) -> Path:
    path = CURATED_DIR / "nsap_finance_all_latest.json"
    atomic_write_json(path, records)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scrape NSAP real financial data from data.gov.in",
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
