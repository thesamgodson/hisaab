"""
NFSA state-level allocation + offtake scraper (data.gov.in API).

Fetches foodgrain allocation and offtake in metric tonnes:
  - 84bb8521: Allocation + offtake by grain type, 2019-2023
  - be339b96: Allocation 2022-2025 (most recent)
    Fields: _2022_23___nfsa (limited metadata)

Output: data/curated/nfsa_allocation_all_latest.json
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
    "alloc_offtake_2019_23": "84bb8521-e41e-434f-a335-f4558f2ae5d9",
    "alloc_2022_25": "be339b96-779f-4e69-88e3-d5dcf1e587fd",
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
    kl = key.lower().replace("-", "_")
    y1, y2 = fy_short.split("-")
    patterns = [
        f"{y1}_{y2}",
        f"{y1}_20{y2}",
        f"20{y1}_20{y2}" if len(y1) == 2 else f"{y1}_20{y2}",
    ]
    return any(p in kl for p in patterns)


def transform_alloc_offtake(
    raw: list[dict[str, Any]], scraped_at: str,
) -> list[dict[str, Any]]:
    """Transform 84bb8521: allocation + offtake by grain, 2019-2023."""
    curated: list[dict[str, Any]] = []
    source = f"api.data.gov.in/resource/{DATASETS['alloc_offtake_2019_23']}"

    year_shorts = ["19-20", "20-21", "21-22", "22-23"]

    for r in raw:
        state = _get_state(r)
        if _is_total_row(state):
            continue

        grain_type = "total"
        for key, val in r.items():
            kl = key.lower()
            if "foodgrain" in kl or "grain" in kl or "type" in kl:
                val_str = str(val).lower()
                if "rice" in val_str:
                    grain_type = "rice"
                elif "wheat" in val_str:
                    grain_type = "wheat"

        for fy_short in year_shorts:
            allocation = 0.0
            offtake = 0.0
            for key, val in r.items():
                if _match_year(key, fy_short):
                    kl = key.lower()
                    if "alloc" in kl:
                        allocation = _parse_amount(val)
                    elif "offtake" in kl or "off_take" in kl or "lifted" in kl:
                        offtake = _parse_amount(val)

            if allocation > 0 or offtake > 0:
                curated.append({
                    "state": state,
                    "fin_year": f"20{fy_short[:2]}-20{fy_short[3:]}",
                    "grain_type": grain_type,
                    "allocation_mt": allocation,
                    "offtake_mt": offtake,
                    "source_url": source,
                    "scraped_at": scraped_at,
                })

    return curated


def transform_alloc_2022_25(
    raw: list[dict[str, Any]], scraped_at: str,
) -> list[dict[str, Any]]:
    """Transform be339b96: allocation 2022-2025.

    Field: _2022_23___nfsa (limited metadata, may have more year columns).
    """
    curated: list[dict[str, Any]] = []
    source = f"api.data.gov.in/resource/{DATASETS['alloc_2022_25']}"

    year_shorts = ["22-23", "23-24", "24-25"]

    for r in raw:
        state = _get_state(r)
        if _is_total_row(state):
            continue

        for fy_short in year_shorts:
            allocation = 0.0
            for key, val in r.items():
                kl = key.lower()
                if _match_year(key, fy_short) and ("nfsa" in kl or "alloc" in kl):
                    amt = _parse_amount(val)
                    if amt > 0:
                        allocation = amt

            if allocation > 0:
                curated.append({
                    "state": state,
                    "fin_year": f"20{fy_short[:2]}-20{fy_short[3:]}",
                    "grain_type": "total",
                    "allocation_mt": allocation,
                    "offtake_mt": 0.0,
                    "source_url": source,
                    "scraped_at": scraped_at,
                })

    return curated


def aggregate_totals(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate rice+wheat into 'total' rows where both exist."""
    by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
    totals: list[dict[str, Any]] = []

    for r in records:
        key = (r["state"], r["fin_year"])
        by_key.setdefault(key, []).append(r)

    for (_state, _fy), recs in by_key.items():
        grain_types = {r["grain_type"] for r in recs}
        totals.extend(recs)
        if "rice" in grain_types and "wheat" in grain_types and "total" not in grain_types:
            total_alloc = sum(
                r["allocation_mt"] for r in recs if r["grain_type"] in ("rice", "wheat")
            )
            total_offtake = sum(
                r["offtake_mt"] for r in recs if r["grain_type"] in ("rice", "wheat")
            )
            totals.append({
                "state": _state,
                "fin_year": _fy,
                "grain_type": "total",
                "allocation_mt": total_alloc,
                "offtake_mt": total_offtake,
                "source_url": recs[0]["source_url"],
                "scraped_at": recs[0]["scraped_at"],
            })

    return totals


def deduplicate(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best: dict[tuple[str, str, str], dict[str, Any]] = {}
    for r in records:
        key = (r["state"], r["fin_year"], r["grain_type"])
        existing = best.get(key)
        if existing is None or r.get("offtake_mt", 0) > 0 and existing.get("offtake_mt", 0) == 0 or r.get("allocation_mt", 0) > existing.get("allocation_mt", 0):
            best[key] = r
    return sorted(
        best.values(),
        key=lambda x: (x["state"], x["fin_year"], x["grain_type"]),
    )


def scrape_all() -> list[dict[str, Any]]:
    scraped_at = utc_iso()
    all_curated: list[dict[str, Any]] = []

    print("Fetching NFSA allocation + offtake 2019-23...")
    raw = fetch_all_records(DATASETS["alloc_offtake_2019_23"])
    print(f"  Got {len(raw)} raw records")
    if raw:
        all_curated.extend(transform_alloc_offtake(raw, scraped_at))

    time.sleep(2)

    print("Fetching NFSA allocation 2022-25...")
    raw = fetch_all_records(DATASETS["alloc_2022_25"])
    print(f"  Got {len(raw)} raw records")
    if raw:
        all_curated.extend(transform_alloc_2022_25(raw, scraped_at))

    aggregated = aggregate_totals(all_curated)
    deduped = deduplicate(aggregated)
    print(f"\nTotal curated records (deduped): {len(deduped)}")
    return deduped


def save_curated(records: list[dict[str, Any]]) -> Path:
    path = CURATED_DIR / "nfsa_allocation_all_latest.json"
    atomic_write_json(path, records)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scrape NFSA allocation data from data.gov.in",
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
    grains = sorted({r["grain_type"] for r in records})
    print(f"Years: {', '.join(years)}")
    print(f"States: {len(states)}")
    print(f"Grain types: {', '.join(grains)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
