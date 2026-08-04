"""
PM POSHAN state-level financial data scraper (data.gov.in API).

Fetches allocation, release, and utilization data from 3 datasets covering 2016-2025:
  - 5c82fb41: MDM era 2016-17 to 2020-21 (release + expenditure)
  - fd834f3b: Transition 2021-22 to 2023-24 (released + utilized + allocated)
  - 37e69f20: Latest 2023-24 & 2024-25 (PAB allocation + release + utilization)

Output: data/curated/pmposhan_finance_all_latest.json

Usage:
    python3 scrape_pmposhan_finance.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

ROOT_DIR = Path(__file__).resolve().parent.parent  # repo root (scrapers/ is a package)
CURATED_DIR = ROOT_DIR / "data" / "curated"

API_KEY = "579b464db66ec23bdd000001cdc3b564546246a772a26393094f5645"
API_BASE = "https://api.data.gov.in/resource"
PAGE_SIZE = 500
DELAY_SECONDS = 1.0
MAX_RETRIES = 3

DATASETS = {
    "mdm_2016_21": "5c82fb41-e702-4e7a-a966-735fe6f319bd",
    "transition_2021_24": "fd834f3b-2a23-4fcd-ae4d-03884ba48e6f",
    "latest_2023_25": "37e69f20-19af-4024-a34c-915e5b098aaa",
}


def utc_iso() -> str:
    return datetime.now(UTC).isoformat()


def fetch_all_records(uuid: str) -> list[dict[str, Any]]:
    """Fetch all records from a data.gov.in dataset with retries."""
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
    """Check if a field key contains a year reference like '2021_22' or '2021na2022'."""
    kl = key.lower().replace("-", "_")
    # Match patterns: _2021_22, 2021_22, 2021na2022, _2021_2022_
    y1, y2 = fy_short.split("-")
    patterns = [
        f"{y1}_{y2}",        # 2021_22
        f"{y1}_20{y2}",      # 2021_2022
        f"20{y1}_20{y2}" if len(y1) == 2 else f"{y1}_20{y2}",
        f"{y1}na20{y2}",     # 2021na2022
    ]
    return any(p in kl for p in patterns)


def transform_transition_2021_24(
    raw: list[dict[str, Any]], scraped_at: str,
) -> list[dict[str, Any]]:
    """Transform fd834f3b dataset.

    Actual fields: fund_released_2021na2022, fund_utilized_2021na2022,
    fund_released_2022na2023, fund_utilized_2022na2023,
    fund_allocated_2023na2024, _fund_utilized_as_per_pfms_
    """
    curated: list[dict[str, Any]] = []
    source = f"api.data.gov.in/resource/{DATASETS['transition_2021_24']}"

    year_shorts = ["21-22", "22-23", "23-24"]

    for r in raw:
        state = _get_state(r)
        if _is_total_row(state):
            continue

        for fy_short in year_shorts:
            released = 0.0
            utilized = 0.0
            allocated = 0.0
            for key, val in r.items():
                if _match_year(key, fy_short):
                    kl = key.lower()
                    if "allocat" in kl:
                        allocated = _parse_amount(val)
                    elif "released" in kl or "release" in kl:
                        released = _parse_amount(val)
                    elif "utiliz" in kl or "utilised" in kl:
                        utilized = _parse_amount(val)

            if released > 0 or utilized > 0 or allocated > 0:
                curated.append({
                    "state": state,
                    "fin_year": f"20{fy_short[:2]}-20{fy_short[3:]}",
                    "allocated_lakhs": allocated,
                    "released_lakhs": released,
                    "utilized_lakhs": utilized,
                    "source_url": source,
                    "scraped_at": scraped_at,
                })

    return curated


def transform_mdm_2016_21(
    raw: list[dict[str, Any]], scraped_at: str,
) -> list[dict[str, Any]]:
    """Transform 5c82fb41: MDM 2016-21 with release + expenditure per year."""
    curated: list[dict[str, Any]] = []
    source = f"api.data.gov.in/resource/{DATASETS['mdm_2016_21']}"

    year_shorts = ["16-17", "17-18", "18-19", "19-20", "20-21"]

    for r in raw:
        state = _get_state(r)
        if _is_total_row(state):
            continue

        for fy_short in year_shorts:
            released = 0.0
            utilized = 0.0
            for key, val in r.items():
                if _match_year(key, fy_short):
                    kl = key.lower()
                    if "released" in kl or "release" in kl or "assistance" in kl:
                        released = _parse_amount(val)
                    elif "expenditure" in kl or "expend" in kl or "utiliz" in kl:
                        utilized = _parse_amount(val)

            if released > 0 or utilized > 0:
                curated.append({
                    "state": state,
                    "fin_year": f"20{fy_short[:2]}-20{fy_short[3:]}",
                    "allocated_lakhs": 0.0,
                    "released_lakhs": released,
                    "utilized_lakhs": utilized,
                    "source_url": source,
                    "scraped_at": scraped_at,
                })

    return curated


def transform_latest_2023_25(
    raw: list[dict[str, Any]], scraped_at: str,
) -> list[dict[str, Any]]:
    """Transform 37e69f20: 2023-25 PAB allocation + release + utilization."""
    curated: list[dict[str, Any]] = []
    source = f"api.data.gov.in/resource/{DATASETS['latest_2023_25']}"

    year_shorts = ["23-24", "24-25"]

    for r in raw:
        state = _get_state(r)
        if _is_total_row(state):
            continue

        for fy_short in year_shorts:
            released = 0.0
            utilized = 0.0
            allocated = 0.0
            for key, val in r.items():
                if _match_year(key, fy_short):
                    kl = key.lower()
                    if "pab" in kl or "allocat" in kl:
                        allocated = _parse_amount(val)
                    elif "released" in kl or "release" in kl or "assistance" in kl:
                        released = _parse_amount(val)
                    elif "utiliz" in kl:
                        utilized = _parse_amount(val)

            if released > 0 or utilized > 0 or allocated > 0:
                curated.append({
                    "state": state,
                    "fin_year": f"20{fy_short[:2]}-20{fy_short[3:]}",
                    "allocated_lakhs": allocated,
                    "released_lakhs": released,
                    "utilized_lakhs": utilized,
                    "source_url": source,
                    "scraped_at": scraped_at,
                })

    return curated


def deduplicate(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep best record per (state, fin_year). Later datasets override earlier."""
    best: dict[tuple[str, str], dict[str, Any]] = {}
    for r in records:
        key = (r["state"], r["fin_year"])
        existing = best.get(key)
        if existing is None:
            best[key] = r
        else:
            fin_keys = ("allocated_lakhs", "released_lakhs", "utilized_lakhs")
            new_nz = sum(1 for k in fin_keys if r.get(k, 0) > 0)
            old_nz = sum(1 for k in fin_keys if existing.get(k, 0) > 0)
            if new_nz >= old_nz:
                best[key] = r
    return sorted(best.values(), key=lambda x: (x["state"], x["fin_year"]))


def scrape_all() -> list[dict[str, Any]]:
    """Scrape all PM POSHAN financial datasets from data.gov.in."""
    scraped_at = utc_iso()
    all_curated: list[dict[str, Any]] = []

    print("Fetching PM POSHAN MDM 2016-21...")
    raw = fetch_all_records(DATASETS["mdm_2016_21"])
    print(f"  Got {len(raw)} raw records")
    if raw:
        all_curated.extend(transform_mdm_2016_21(raw, scraped_at))

    time.sleep(2)

    print("Fetching PM POSHAN transition 2021-24...")
    raw = fetch_all_records(DATASETS["transition_2021_24"])
    print(f"  Got {len(raw)} raw records")
    if raw:
        all_curated.extend(transform_transition_2021_24(raw, scraped_at))

    time.sleep(2)

    print("Fetching PM POSHAN latest 2023-25...")
    raw = fetch_all_records(DATASETS["latest_2023_25"])
    print(f"  Got {len(raw)} raw records")
    if raw:
        all_curated.extend(transform_latest_2023_25(raw, scraped_at))

    deduped = deduplicate(all_curated)
    print(f"\nTotal curated records (deduped): {len(deduped)}")
    return deduped


def save_curated(records: list[dict[str, Any]]) -> Path:
    CURATED_DIR.mkdir(parents=True, exist_ok=True)
    path = CURATED_DIR / "pmposhan_finance_all_latest.json"
    path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scrape PM POSHAN financial data from data.gov.in",
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
