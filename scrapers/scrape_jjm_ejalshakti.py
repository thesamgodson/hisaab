"""
JJM state-level financial scraper (ejalshakti.gov.in API).

Fetches detailed state-level financial data from the JJM dashboard:
  - Bind_BudjectSanction_Details: state list + central sanction per year
  - Bind_Financial_info: OB, allocation, release, expenditure (central + state)

This replaces/supplements scrape_jjm_finance.py (data.gov.in allocation-only).
Amounts from API are in crores; output is in crores (DB VIEW converts to lakhs).

Output: data/curated/jjm_allocation_all_latest.json

Usage:
    python3 scrape_jjm_ejalshakti.py
    python3 scrape_jjm_ejalshakti.py --years 2023-2024,2024-2025
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

try:
    from scrapers.io_utils import atomic_write_json
except ImportError:
    from io_utils import atomic_write_json

ROOT_DIR = Path(__file__).resolve().parent.parent  # repo root (scrapers/ is a package)
CURATED_DIR = ROOT_DIR / "data" / "curated"

BASE_URL = "https://ejalshakti.gov.in/jjmreport"
HEADERS = {
    "Content-Type": "application/json; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
}

ALL_FIN_YEARS = [
    "2019-2020",
    "2020-2021",
    "2021-2022",
    "2022-2023",
    "2023-2024",
    "2024-2025",
]

ENC_N = 1
DELAY_SECONDS = 1.5
MAX_RETRIES = 3


def utc_iso() -> str:
    return datetime.now(UTC).isoformat()


def encode_txt(s: str) -> str:
    """Python port of the JJM dashboard's encodeTxt(s) with encN=1.

    JS: escape(s) → shift each charCode by +encN → escape again → append encN.
    """
    # JS escape(): encode everything except @*_+-./ and alphanumerics
    escaped = quote(s, safe="@*_+-./")
    shifted = "".join(chr(ord(c) + ENC_N) for c in escaped)
    re_escaped = quote(shifted, safe="@*_+-./")
    return re_escaped + str(ENC_N)


def _prev_year(fin_year: str) -> str:
    """Given '2024-2025', return '2023-2024'."""
    parts = fin_year.split("-")
    return f"{int(parts[0]) - 1}-{int(parts[1]) - 1}"


def _parse_amount(val: Any) -> float:
    if val is None:
        return 0.0
    cleaned = str(val).replace(",", "").strip()
    if not cleaned or cleaned in ("-", "null"):
        return 0.0
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _post(endpoint: str, payload: dict, referer_page: str) -> list[dict]:
    """POST to a JJM AJAX endpoint with retries."""
    url = f"{BASE_URL}/{endpoint}"
    headers = {**HEADERS, "Referer": f"{BASE_URL}/{referer_page}"}

    for attempt in range(MAX_RETRIES):
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            return data.get("d", [])
        except (requests.RequestException, ValueError) as e:
            if attempt < MAX_RETRIES - 1:
                wait = (attempt + 1) * 2
                print(f"  Retry {attempt + 1}/{MAX_RETRIES} after {wait}s: {e}")
                time.sleep(wait)
            else:
                print(f"  ERROR {endpoint}: {e}")
                return []
    return []


def fetch_state_list(fin_year: str) -> list[dict[str, str]]:
    """Get list of states with their codes for a given year."""
    payload = {
        "StCode11": encode_txt("0"),
        "Cat": encode_txt("0"),
        "SubCat": encode_txt("0"),
        "Param": encode_txt("0"),
        "FinYear": encode_txt(fin_year),
    }
    raw = _post(
        "JJMIndia.aspx/Bind_BudjectSanction_Details",
        payload,
        "JJMIndia.aspx",
    )
    states = []
    for r in raw:
        name = r.get("Name", "").strip()
        code = r.get("KeyValue", "").strip()
        if name and code:
            states.append({"name": name, "code": code})
    return states


def fetch_financial_info(state_code: str, fin_year: str) -> dict[str, Any] | None:
    """Get detailed financial breakdown for one state×year."""
    payload = {
        "StCode11": encode_txt(state_code),
        "Cat": encode_txt("0"),
        "SubCat": encode_txt("0"),
        "Param": encode_txt("0"),
        "FinYear": encode_txt(fin_year),
        "FinYear_Prev": encode_txt(_prev_year(fin_year)),
    }
    raw = _post(
        "JJMState.aspx/Bind_Financial_info",
        payload,
        "JJMState.aspx",
    )
    if raw:
        return raw[0]
    return None


_CANONICAL_STATES = {
    "TAMILNADU": "TAMIL NADU",
    "JAMMU & KASHMIR": "JAMMU AND KASHMIR",
    "ANDAMAN & NICOBAR ISLANDS": "ANDAMAN AND NICOBAR ISLANDS",
    "DADRA & NAGAR HAVELI": "DADRA AND NAGAR HAVELI",
    "DADRA & NAGAR HAVELI AND DAMAN & DIU": "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
}


def _normalize_state(name: str) -> str:
    upper = name.strip().upper()
    return _CANONICAL_STATES.get(upper, upper)


def scrape_all(fin_years: list[str]) -> list[dict[str, Any]]:
    scraped_at = utc_iso()
    source_url = "https://ejalshakti.gov.in/jjmreport/JJMState.aspx"
    all_records: list[dict[str, Any]] = []

    for fy in fin_years:
        print(f"\n--- {fy} ---")

        # Get state list for this year
        states = fetch_state_list(fy)
        print(f"  {len(states)} states found")
        time.sleep(DELAY_SECONDS)

        for st in states:
            info = fetch_financial_info(st["code"], fy)
            if not info:
                print(f"  {st['name']}: no data")
                continue

            alloc_c = _parse_amount(info.get("Allocation_C"))
            release_c = _parse_amount(info.get("Release_C"))
            expenditure_c = _parse_amount(info.get("Expenditure_C"))
            alloc_s = _parse_amount(info.get("OB_Alloc_S"))
            expenditure_s = _parse_amount(info.get("Expenditure_S"))
            total_expenditure = _parse_amount(info.get("Total_Expenditure"))

            record = {
                "state": _normalize_state(st["name"]),
                "fin_year": fy,
                "allocated_crores": alloc_c,
                "released_crores": release_c,
                "expended_crores": expenditure_c,
                "state_allocated_crores": alloc_s,
                "state_expended_crores": expenditure_s,
                "total_expended_crores": total_expenditure,
                "funding_pattern": info.get("StateFundingpattern", ""),
                "source_url": source_url,
                "scraped_at": scraped_at,
            }
            all_records.append(record)
            time.sleep(DELAY_SECONDS)

        print(f"  Scraped {sum(1 for r in all_records if r['fin_year'] == fy)} state records")

    print(f"\nTotal: {len(all_records)} records")
    return sorted(all_records, key=lambda x: (x["state"], x["fin_year"]))


def save_curated(records: list[dict[str, Any]]) -> Path:
    path = CURATED_DIR / "jjm_allocation_all_latest.json"
    atomic_write_json(path, records)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scrape JJM financial data from ejalshakti.gov.in",
    )
    parser.add_argument(
        "--years",
        help="Comma-separated fin years (default: all 2019-2025)",
    )
    args = parser.parse_args()

    fin_years = (
        [y.strip() for y in args.years.split(",")]
        if args.years
        else ALL_FIN_YEARS
    )
    print(f"JJM Financial Scraper — {len(fin_years)} years")
    print(f"Years: {', '.join(fin_years)}")

    records = scrape_all(fin_years)
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
