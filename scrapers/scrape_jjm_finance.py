"""
JJM state-level allocation scraper (data.gov.in API).

Fetches fund allocation data (allocation only — no release/utilization):
  - 792ebf8b: State-wise allocation 2019-2022 (Rs Crore)
    Fields: _2019_20, _2020_21, _2021_22
  - 7cb662d2: 2022-23 allocation (Rs Crore)
    Fields: allocation__in_rs__crore_

Output: data/curated/jjm_allocation_all_latest.json
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
    "alloc_2019_22": "792ebf8b-ffa8-449c-96fd-bb6308c756c3",
    "alloc_2022_23": "7cb662d2-74fb-4e08-ac4f-665c9dd0a56d",
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
    for k in ("state_ut", "states_uts", "state_uts", "state__ut", "state"):
        if r.get(k):
            return _normalize_state(r[k])
    return ""


def transform_alloc_2019_22(
    raw: list[dict[str, Any]], scraped_at: str,
) -> list[dict[str, Any]]:
    """Transform 792ebf8b: fields _2019_20, _2020_21, _2021_22 (Rs Crore)."""
    curated: list[dict[str, Any]] = []
    source = f"api.data.gov.in/resource/{DATASETS['alloc_2019_22']}"

    # Map field suffix -> fin_year
    year_map = {
        "2019_20": "2019-2020",
        "2020_21": "2020-2021",
        "2021_22": "2021-2022",
    }

    for r in raw:
        state = _get_state(r)
        if _is_total_row(state):
            continue

        for suffix, fin_year in year_map.items():
            allocated = 0.0
            for key, val in r.items():
                if suffix in key.lower():
                    allocated = _parse_amount(val)

            if allocated > 0:
                curated.append({
                    "state": state,
                    "fin_year": fin_year,
                    "allocated_crores": allocated,
                    "source_url": source,
                    "scraped_at": scraped_at,
                })

    return curated


def transform_alloc_2022_23(
    raw: list[dict[str, Any]], scraped_at: str,
) -> list[dict[str, Any]]:
    """Transform 7cb662d2: field allocation__in_rs__crore_ (single year)."""
    curated: list[dict[str, Any]] = []
    source = f"api.data.gov.in/resource/{DATASETS['alloc_2022_23']}"

    for r in raw:
        state = _get_state(r)
        if _is_total_row(state):
            continue

        allocated = 0.0
        for key, val in r.items():
            kl = key.lower()
            if "alloc" in kl or "crore" in kl:
                amt = _parse_amount(val)
                if amt > 0:
                    allocated = amt

        if allocated > 0:
            curated.append({
                "state": state,
                "fin_year": "2022-2023",
                "allocated_crores": allocated,
                "source_url": source,
                "scraped_at": scraped_at,
            })

    return curated


def deduplicate(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best: dict[tuple[str, str], dict[str, Any]] = {}
    for r in records:
        key = (r["state"], r["fin_year"])
        existing = best.get(key)
        if existing is None or r.get("allocated_crores", 0) > existing.get("allocated_crores", 0):
            best[key] = r
    return sorted(best.values(), key=lambda x: (x["state"], x["fin_year"]))


def scrape_all() -> list[dict[str, Any]]:
    scraped_at = utc_iso()
    all_curated: list[dict[str, Any]] = []

    print("Fetching JJM allocation 2019-22...")
    raw = fetch_all_records(DATASETS["alloc_2019_22"])
    print(f"  Got {len(raw)} raw records")
    if raw:
        all_curated.extend(transform_alloc_2019_22(raw, scraped_at))

    time.sleep(2)

    print("Fetching JJM allocation 2022-23...")
    raw = fetch_all_records(DATASETS["alloc_2022_23"])
    print(f"  Got {len(raw)} raw records")
    if raw:
        all_curated.extend(transform_alloc_2022_23(raw, scraped_at))

    deduped = deduplicate(all_curated)
    print(f"\nTotal curated records (deduped): {len(deduped)}")
    return deduped


def save_curated(records: list[dict[str, Any]]) -> Path:
    CURATED_DIR.mkdir(parents=True, exist_ok=True)
    path = CURATED_DIR / "jjm_allocation_all_latest.json"
    path.write_text(
        json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8",
    )
    return path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scrape JJM allocation data from data.gov.in",
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
