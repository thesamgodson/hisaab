"""
UDISE+ state-level education data scraper (api.udiseplus.gov.in).

Fetches school, student, and teacher summary statistics for every state × year
from the Unified District Information System for Education Plus public API.

Available years: 2022-23, 2023-24, 2024-25 (yearId 9, 10, 11).

Output: data/curated/udise_state_all_latest.json

Usage:
    python3 scrape_udise.py
    python3 scrape_udise.py --years 2024-2025
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests
import urllib3

try:
    from scrapers.io_utils import atomic_write_json
except ImportError:
    from io_utils import atomic_write_json

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ROOT_DIR = Path(__file__).resolve().parent.parent  # repo root (scrapers/ is a package)
CURATED_DIR = ROOT_DIR / "data" / "curated"

BASE_URL = "https://api.udiseplus.gov.in/open-services/v1.1"
HEADERS = {
    "Content-Type": "application/json",
    "Origin": "https://dashboard.udiseplus.gov.in",
}

DELAY_SECONDS = 1.0
MAX_RETRIES = 3
SOURCE_URL = "api.udiseplus.gov.in"

# regionType=11 means state-level aggregation; valueType=2 means absolute values
REGION_TYPE_STATE = 11
VALUE_TYPE_ABSOLUTE = 2


def utc_iso() -> str:
    return datetime.now(UTC).isoformat()


def _parse_float(val: Any) -> float:
    """Parse a value that may be a string, number, or None."""
    if val is None:
        return 0.0
    cleaned = str(val).replace(",", "").strip()
    if not cleaned or cleaned in ("-", "null", "N/A", "NA"):
        return 0.0
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _parse_int(val: Any) -> int:
    """Parse an integer value that may be a string or float."""
    return int(_parse_float(val))


def _convert_year(api_year: str) -> str:
    """Convert API year format '2024-25' to our standard '2024-2025'."""
    parts = api_year.split("-")
    if len(parts) != 2:
        return api_year
    start = parts[0].strip()
    # end is 2 digits in the API format; derive the full year from start
    start_int = int(start)
    end_int = start_int + 1
    return f"{start_int}-{end_int}"


def _extract_data(resp_json: Any) -> Any:
    """Extract the 'data' field from UDISE API response wrapper."""
    if isinstance(resp_json, dict) and "data" in resp_json:
        return resp_json["data"]
    return resp_json


def _get(endpoint: str) -> Any:
    """GET from a UDISE+ endpoint with retries."""
    url = f"{BASE_URL}/{endpoint}"
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30, verify=False)
            resp.raise_for_status()
            return _extract_data(resp.json())
        except (requests.RequestException, ValueError) as exc:
            if attempt < MAX_RETRIES - 1:
                wait = (attempt + 1) * 2
                print(f"  Retry {attempt + 1}/{MAX_RETRIES} after {wait}s: {exc}")
                time.sleep(wait)
            else:
                print(f"  ERROR GET {endpoint}: {exc}")
                return None
    return None


def _post(endpoint: str, payload: dict) -> Any:
    """POST to a UDISE+ endpoint with retries."""
    url = f"{BASE_URL}/{endpoint}"
    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(url, json=payload, headers=HEADERS, timeout=30, verify=False)
            resp.raise_for_status()
            return _extract_data(resp.json())
        except (requests.RequestException, ValueError) as exc:
            if attempt < MAX_RETRIES - 1:
                wait = (attempt + 1) * 2
                print(f"  Retry {attempt + 1}/{MAX_RETRIES} after {wait}s: {exc}")
                time.sleep(wait)
            else:
                print(f"  ERROR POST {endpoint}: {exc}")
                return None
    return None


def fetch_years() -> list[dict[str, Any]]:
    """Fetch available academic years from the API."""
    data = _get("acad-year-master/public")
    if not isinstance(data, list):
        return []
    return data


def fetch_states(year_id: int) -> list[dict[str, Any]]:
    """Fetch states for a given yearId."""
    data = _get(f"states/{year_id}")
    if not isinstance(data, list):
        return []
    return data


def fetch_schools_stats(year_id: int, region_code: int) -> dict[str, Any] | None:
    """Fetch schools summarised stats for one state × year."""
    payload = {
        "yearId": year_id,
        "regionType": REGION_TYPE_STATE,
        "regionCode": region_code,
        "valueType": VALUE_TYPE_ABSOLUTE,
    }
    data = _post("schools-summarised-stats/public", payload)
    if isinstance(data, list) and data:
        return data[0]
    if isinstance(data, dict):
        return data
    return None


def fetch_students_stats(year_id: int, region_code: int) -> dict[str, Any] | None:
    """Fetch students summarised stats for one state × year."""
    payload = {
        "yearId": year_id,
        "regionType": REGION_TYPE_STATE,
        "regionCode": region_code,
        "valueType": VALUE_TYPE_ABSOLUTE,
    }
    data = _post("students-summarised-stats/public", payload)
    if isinstance(data, list) and data:
        return data[0]
    if isinstance(data, dict):
        return data
    return None


def fetch_teachers_stats(year_id: int, region_code: int) -> dict[str, Any] | None:
    """Fetch teachers summarised stats for one state × year."""
    payload = {
        "yearId": year_id,
        "regionType": REGION_TYPE_STATE,
        "regionCode": region_code,
        "valueType": VALUE_TYPE_ABSOLUTE,
    }
    data = _post("teachers-summarised-stats/public", payload)
    if isinstance(data, list) and data:
        return data[0]
    if isinstance(data, dict):
        return data
    return None


def _safe_pct(numerator: int, denominator: int) -> float:
    """Compute percentage safely, returning 0.0 on division by zero."""
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator * 100, 2)


def _build_record(
    state_name: str,
    fin_year: str,
    schools: dict[str, Any] | None,
    students: dict[str, Any] | None,
    teachers: dict[str, Any] | None,
    scraped_at: str,
) -> dict[str, Any]:
    """Merge API responses into a single normalised record."""
    sc = schools or {}
    st = students or {}
    tc = teachers or {}

    total_schools = _parse_int(sc.get("totSchools"))
    schools_electricity = _parse_int(sc.get("totSchElectricity"))
    schools_drinkwater = _parse_int(sc.get("totSchDrinkwater"))
    schools_girls_toilet = _parse_int(sc.get("totSchGToilet"))
    schools_library = _parse_int(sc.get("totSchLibrary"))

    return {
        "state": state_name.strip().upper(),
        "fin_year": fin_year,
        "total_schools": total_schools,
        "schools_govt": _parse_int(sc.get("totSchoolGovt")),
        "schools_pvt": _parse_int(sc.get("totSchoolPvt")),
        "schools_rural": _parse_int(sc.get("totSchoolRural")),
        "schools_urban": _parse_int(sc.get("totSchoolUrban")),
        "total_students": _parse_int(st.get("totStudents")),
        "total_teachers": _parse_int(tc.get("totTch")),
        "ptr_primary": _parse_float(st.get("ptrPry") or tc.get("ptrPry")),
        "ptr_secondary": _parse_float(st.get("ptrSec") or tc.get("ptrSec")),
        "ger_primary": _parse_float(st.get("gerPry")),
        "ger_secondary": _parse_float(st.get("gerUPry")),
        "dropout_primary": _parse_float(st.get("dropoutPry")),
        "dropout_secondary": _parse_float(st.get("dropoutSec")),
        "schools_electricity_pct": _safe_pct(schools_electricity, total_schools),
        "schools_drinkwater_pct": _safe_pct(schools_drinkwater, total_schools),
        "schools_girls_toilet_pct": _safe_pct(schools_girls_toilet, total_schools),
        "schools_library_pct": _safe_pct(schools_library, total_schools),
        "source_url": SOURCE_URL,
        "scraped_at": scraped_at,
    }


def scrape_all(target_years: list[str] | None = None) -> list[dict[str, Any]]:
    """Scrape all state × year combinations from UDISE+ API.

    Args:
        target_years: Optional list of fin_years to restrict to (e.g. ['2024-2025']).
                      If None, all available years are fetched.
    """
    scraped_at = utc_iso()
    all_records: list[dict[str, Any]] = []

    print("Fetching academic years...")
    years = fetch_years()
    if not years:
        print("ERROR: Could not fetch year list")
        return []

    for yr in years:
        year_id = yr.get("yearId")
        year_desc = yr.get("yearDesc", "")
        fin_year = _convert_year(year_desc)

        if target_years and fin_year not in target_years:
            continue

        print(f"\n--- {fin_year} (yearId={year_id}) ---")
        time.sleep(DELAY_SECONDS)

        states = fetch_states(year_id)
        if not states:
            print(f"  No states found for yearId={year_id}")
            continue

        print(f"  {len(states)} states found")

        for state in states:
            state_code_raw = state.get("udiseStateCode", "")
            state_name_raw = state.get("udiseStateName", "").strip().upper()
            _STATE_FIXES = {
                "ANDAMAN & NICOBAR ISLANDS": "ANDAMAN AND NICOBAR ISLANDS",
                "JAMMU & KASHMIR": "JAMMU AND KASHMIR",
                "DADRA & NAGAR HAVELI AND DAMAN & DIU": "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
            }
            state_name = _STATE_FIXES.get(state_name_raw, state_name_raw)
            if not state_name or not state_code_raw:
                continue

            try:
                region_code = int(state_code_raw)
            except ValueError:
                print(f"  Skipping {state_name}: non-integer code '{state_code_raw}'")
                continue

            schools = fetch_schools_stats(year_id, region_code)
            time.sleep(DELAY_SECONDS)
            students = fetch_students_stats(year_id, region_code)
            time.sleep(DELAY_SECONDS)
            teachers = fetch_teachers_stats(year_id, region_code)
            time.sleep(DELAY_SECONDS)

            if not schools and not students and not teachers:
                print(f"  {state_name}: no data")
                continue

            record = _build_record(state_name, fin_year, schools, students, teachers, scraped_at)
            all_records.append(record)

        year_count = sum(1 for r in all_records if r["fin_year"] == fin_year)
        print(f"  Scraped {year_count} state records for {fin_year}")

    print(f"\nTotal: {len(all_records)} records")
    return sorted(all_records, key=lambda x: (x["state"], x["fin_year"]))


def save_curated(records: list[dict[str, Any]]) -> Path:
    path = CURATED_DIR / "udise_state_all_latest.json"
    atomic_write_json(path, records)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scrape UDISE+ state-level education data",
    )
    parser.add_argument(
        "--years",
        help="Comma-separated fin years to fetch, e.g. 2024-2025 (default: all available)",
    )
    args = parser.parse_args()

    target_years = (
        [y.strip() for y in args.years.split(",")]
        if args.years
        else None
    )

    print("UDISE+ State Scraper")
    if target_years:
        print(f"Years: {', '.join(target_years)}")
    else:
        print("Years: all available")

    records = scrape_all(target_years)
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
