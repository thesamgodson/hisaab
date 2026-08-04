"""
Swachh Bharat Mission - Gramin (SBM-G) ODF Plus district scraper.

Scrapes village-level ODF Plus (star rating) data from the public SBM-G dashboard.
All ~600+ districts are embedded as a JavaScript array in the dashboard HTML —
a single HTTP GET is sufficient, no JS execution required.

Data includes: total villages, ODF+ villages, star ratings (1/3/5 star),
model village %, and historical snapshots (Sep 2022, Mar 2023, Mar 2024).

Usage:
    python scrape_sbm.py                        # All districts (national)
    python scrape_sbm.py --states "BIHAR"       # Single state filter
    python scrape_sbm.py --states "BIHAR,TAMIL NADU"
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent  # repo root (scrapers/ is a package)
DATA_DIR = ROOT_DIR / "data"
CURATED_DIR = DATA_DIR / "curated"

DASHBOARD_URL = "https://sbm.gov.in/sbmgdashboard/StatesDashboard.aspx"
SOURCE_URL = DASHBOARD_URL

# Canonical state name map: dashboard name → UPPER CASE standard form
# Handles known SBM-G spelling / casing differences
_CANONICAL_STATES: dict[str, str] = {
    "Andaman & Nicobar Islands": "ANDAMAN AND NICOBAR ISLANDS",
    "Andaman & Nicobar": "ANDAMAN AND NICOBAR ISLANDS",
    "Arunachal Pradesh": "ARUNACHAL PRADESH",
    "Assam": "ASSAM",
    "Bihar": "BIHAR",
    "Chandigarh": "CHANDIGARH",
    "Chhattisgarh": "CHHATTISGARH",
    "Dadra & Nagar Haveli and Daman & Diu": "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
    "Dadra & Nagar Haveli": "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
    "Daman & Diu": "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
    "Goa": "GOA",
    "Gujarat": "GUJARAT",
    "Haryana": "HARYANA",
    "Himachal Pradesh": "HIMACHAL PRADESH",
    "Jammu & Kashmir": "JAMMU AND KASHMIR",
    "Jammu and Kashmir": "JAMMU AND KASHMIR",
    "Jharkhand": "JHARKHAND",
    "Karnataka": "KARNATAKA",
    "Kerala": "KERALA",
    "Ladakh": "LADAKH",
    "Lakshadweep": "LAKSHADWEEP",
    "Madhya Pradesh": "MADHYA PRADESH",
    "Maharashtra": "MAHARASHTRA",
    "Manipur": "MANIPUR",
    "Meghalaya": "MEGHALAYA",
    "Mizoram": "MIZORAM",
    "Nagaland": "NAGALAND",
    "Odisha": "ODISHA",
    "Orissa": "ODISHA",
    "Puducherry": "PUDUCHERRY",
    "Pondicherry": "PUDUCHERRY",
    "Punjab": "PUNJAB",
    "Rajasthan": "RAJASTHAN",
    "Sikkim": "SIKKIM",
    "Tamil Nadu": "TAMIL NADU",
    "Telangana": "TELANGANA",
    "Tripura": "TRIPURA",
    "Uttar Pradesh": "UTTAR PRADESH",
    "Uttarakhand": "UTTARAKHAND",
    "Uttaranchal": "UTTARAKHAND",
    "West Bengal": "WEST BENGAL",
    "Delhi": "DELHI",
    "NCT of Delhi": "DELHI",
}


def utc_iso() -> str:
    return datetime.now(UTC).isoformat()


def ensure_dirs() -> None:
    CURATED_DIR.mkdir(parents=True, exist_ok=True)


def normalize_state(raw_name: str) -> str:
    """Map dashboard state name to canonical UPPER CASE form."""
    import html as _html

    # Unescape HTML entities (&amp; → &, etc.)
    stripped = _html.unescape(raw_name).strip()
    if stripped in _CANONICAL_STATES:
        return _CANONICAL_STATES[stripped]
    upper = stripped.upper()
    # Normalize common variants
    _UPPER_FIXES = {
        "A & N ISLANDS": "ANDAMAN AND NICOBAR ISLANDS",
        "JAMMU & KASHMIR": "JAMMU AND KASHMIR",
        "D & N HAVELI AND DAMAN & DIU": "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
    }
    return _UPPER_FIXES.get(upper, upper)


def fetch_dashboard_html() -> str:
    """Fetch the SBM-G States Dashboard HTML page.

    Uses curl because sbm.gov.in TLS resets Python's ssl module.
    Server is flaky — retries with backoff.
    """
    import subprocess
    import time as _time

    max_retries = 5
    for attempt in range(max_retries):
        result = subprocess.run(
            ["curl", "-s", "-L", "--max-time", "60", "--retry", "2", DASHBOARD_URL],
            capture_output=True,
            text=True,
            timeout=90,
        )
        if result.returncode == 0 and len(result.stdout) > 1000:
            return result.stdout
        wait = (attempt + 1) * 5
        print(f"  Attempt {attempt + 1}/{max_retries} failed (exit {result.returncode}), retrying in {wait}s...")
        _time.sleep(wait)

    msg = f"curl failed after {max_retries} attempts (exit {result.returncode})"
    raise RuntimeError(msg)


def extract_markers_district(html: str) -> list[dict[str, Any]]:
    """Extract the markersDistrict[] JS array embedded in the dashboard HTML.

    The dashboard inlines data as:
        var markersDistrict = [...];
    or
        markersDistrict.push({...});
    We prefer the full array form; fall back to individual push() extraction.
    """
    # Strategy 1: full array assignment  var markersDistrict=[{...},...];
    match = re.search(
        r"markersDistrict\s*=\s*(\[[\s\S]*?\])\s*;",
        html,
        re.IGNORECASE,
    )
    if match:
        raw_js = match.group(1)
        # Dashboard uses single-quoted JS strings — convert to valid JSON
        raw_json = raw_js.replace("'", '"')
        # Remove trailing commas before } or ]
        raw_json = re.sub(r",\s*([}\]])", r"\1", raw_json)
        try:
            return json.loads(raw_json)
        except json.JSONDecodeError:
            pass

    # Strategy 2: collect all push({...}) calls
    items: list[dict[str, Any]] = []
    for push_match in re.finditer(
        r"markersDistrict\.push\s*\(\s*(\{[\s\S]*?\})\s*\)\s*;",
        html,
        re.IGNORECASE,
    ):
        try:
            items.append(json.loads(push_match.group(1)))
        except json.JSONDecodeError:
            continue
    return items


def _parse_int(val: Any) -> int:
    if isinstance(val, int):
        return val
    s = str(val).strip().replace(",", "")
    if not s or s in ("-", "null", "None"):
        return 0
    try:
        return int(float(s))
    except ValueError:
        return 0


def _parse_float(val: Any) -> float:
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace(",", "")
    if not s or s in ("-", "null", "None"):
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def transform_record(raw: dict[str, Any], scraped_at: str) -> dict[str, Any] | None:
    """Convert one markersDistrict entry to a curated record.

    Returns None if the record is missing required identifiers.
    """
    state_raw = raw.get("STNAME", raw.get("StName", "")).strip()
    district_raw = raw.get("dtname", raw.get("DtName", "")).strip()

    if not state_raw or not district_raw:
        return None

    state = normalize_state(state_raw)
    district = district_raw.upper()
    state_code = str(raw.get("STCODE11", raw.get("StCode11", ""))).strip()

    total_villages = _parse_int(raw.get("TotalVillages", 0))
    odf_plus_villages = _parse_int(raw.get("TotalStarVillage", 0))
    odf_plus_pct = _parse_float(raw.get("TotalStarVillagePer", 0))

    one_star = _parse_int(raw.get("NoOfOneStarVillage", 0))
    three_star = _parse_int(raw.get("NoOfThreeStarVillage", 0))
    five_star = _parse_int(raw.get("NoOfFiveStarVillage", 0))
    model_village_pct = _parse_float(raw.get("TotalModeVillagePer", 0))

    return {
        "district": district,
        "state": state,
        "state_code": state_code,
        "fin_year": "cumulative",
        "total_villages": total_villages,
        "odf_plus_villages": odf_plus_villages,
        "odf_plus_pct": odf_plus_pct,
        "one_star_villages": one_star,
        "three_star_villages": three_star,
        "five_star_villages": five_star,
        "model_village_pct": model_village_pct,
        "source_url": SOURCE_URL,
        "scraped_at": scraped_at,
    }


def parse_records(
    raw_data: list[dict[str, Any]],
    states_filter: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Convert extracted markersDistrict entries to curated records."""
    scraped_at = utc_iso()
    upper_filter = {s.upper() for s in states_filter} if states_filter else None

    records: list[dict[str, Any]] = []
    for raw in raw_data:
        record = transform_record(raw, scraped_at)
        if record is None:
            continue
        if upper_filter and record["state"] not in upper_filter:
            continue
        records.append(record)

    return records


def save_curated(records: list[dict[str, Any]]) -> Path:
    """Save all records to a single national file (SBM-G is one dataset)."""
    path = CURATED_DIR / "sbm_district_all_latest.json"
    path.write_text(
        json.dumps(records, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def scrape(states: list[str] | None = None) -> dict[str, int]:
    """Scrape SBM-G ODF Plus data. Returns {state: record_count}."""
    ensure_dirs()

    print("  Fetching SBM-G dashboard HTML...")
    html = fetch_dashboard_html()
    print(f"  Downloaded {len(html):,} bytes")

    print("  Extracting markersDistrict array...")
    raw_data = extract_markers_district(html)
    print(f"  Found {len(raw_data)} raw district entries")

    if not raw_data:
        print("  WARNING: No markersDistrict data found — page structure may have changed")
        return {}

    records = parse_records(raw_data, states_filter=states)
    filter_msg = f" (filtered to {len(states)} states)" if states else ""
    print(f"  Parsed {len(records)} records{filter_msg}")

    # Tally by state
    by_state: dict[str, int] = {}
    for r in records:
        by_state[r["state"]] = by_state.get(r["state"], 0) + 1

    path = save_curated(records)
    print(f"  Saved → {path.name}")

    for state_name in sorted(by_state):
        print(f"    {state_name}: {by_state[state_name]} districts")

    return by_state


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scrape SBM-G ODF Plus district data from sbm.gov.in"
    )
    parser.add_argument(
        "--states",
        help="Comma-separated state names to include (default: all states)",
    )
    args = parser.parse_args()

    states = [s.strip() for s in args.states.split(",")] if args.states else None
    label = "all states" if not states else f"{len(states)} state(s)"
    print(f"SBM-G Scraper — {label}")

    results = scrape(states)

    if not results:
        print("No records scraped.")
        return 1

    total = sum(results.values())
    print(f"\nTotal: {total} districts across {len(results)} states")
    return 0


if __name__ == "__main__":
    sys.exit(main())
