"""
Scrape PMGSY state/district ID catalog from pmgsy.dord.gov.in.

The PMGSY portal uses numeric IDs for states and districts.
This script discovers these by calling the PopulateDistricts API
and saves the mapping to data/catalog/pmgsy_geo.json.

Usage:
    python scrape_pmgsy_catalog.py
"""

from __future__ import annotations

import json
import time
from datetime import UTC, datetime
from pathlib import Path

import requests

BASE_URL = "https://pmgsy.dord.gov.in"
POPULATE_DISTRICTS_URL = f"{BASE_URL}/Home/PopulateDistricts"
POPULATE_STATES_URL = f"{BASE_URL}/Home/PopulateStates"

OUT_DIR = Path("data/catalog")
STATES_FILE = Path(__file__).resolve().parent / "states.json"

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (compatible; Hisaab/0.2)",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Referer": f"{BASE_URL}/",
})


def fetch_pmgsy_states() -> list[dict]:
    """Try to get state list from the PMGSY portal directly."""
    # First load the homepage to get cookies
    session.get(BASE_URL, timeout=30)

    # Try the states API endpoint
    try:
        resp = session.post(POPULATE_STATES_URL, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list) and data:
            return [
                {
                    "pmgsy_state_id": str(item.get("Value", item.get("value", ""))),
                    "state_name": str(item.get("Text", item.get("text", ""))).strip(),
                }
                for item in data
                if item.get("Value", item.get("value", "")) not in ("", "0", "-1")
            ]
    except Exception as exc:
        print(f"  Warning: PMGSY states API unavailable ({exc}), will use known IDs")

    return []


def fetch_districts_for_state(state_id: str) -> list[dict]:
    """Fetch district list for a given PMGSY state ID."""
    try:
        resp = session.post(
            POPULATE_DISTRICTS_URL,
            data={"stateId": state_id, "StateCode": state_id},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return [
                {
                    "pmgsy_district_id": str(item.get("Value", item.get("value", ""))),
                    "district_name": str(item.get("Text", item.get("text", ""))).strip(),
                }
                for item in data
                if item.get("Value", item.get("value", "")) not in ("", "0", "-1")
            ]
    except Exception as exc:
        print(f"    Error fetching districts: {exc}")

    return []


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    print("Fetching PMGSY state list...")
    pmgsy_states = fetch_pmgsy_states()

    if not pmgsy_states:
        print("Could not fetch states from PMGSY API. Trying known IDs...")
        # Fallback: use well-known PMGSY state IDs
        # These are stable numeric IDs used by the portal
        pmgsy_states = _known_state_ids()

    print(f"Found {len(pmgsy_states)} states")

    catalog: list[dict] = []
    for i, state in enumerate(pmgsy_states, 1):
        state_id = state["pmgsy_state_id"]
        state_name = state["state_name"]
        print(f"[{i:02d}/{len(pmgsy_states)}] {state_name} (id={state_id})...", end=" ")

        districts = fetch_districts_for_state(state_id)
        print(f"{len(districts)} districts")

        for d in districts:
            catalog.append({
                "pmgsy_state_id": state_id,
                "state_name": state_name,
                "pmgsy_district_id": d["pmgsy_district_id"],
                "district_name": d["district_name"],
            })

        if i < len(pmgsy_states):
            time.sleep(0.5)

    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    versioned_path = OUT_DIR / f"pmgsy_geo_{ts}.json"
    latest_path = OUT_DIR / "pmgsy_geo.json"

    output = {
        "scraped_at": datetime.now(UTC).isoformat(),
        "states": pmgsy_states,
        "districts": catalog,
    }

    for path in (versioned_path, latest_path):
        path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nPMGSY catalog scraped")
    print(f"  States:    {len(pmgsy_states)}")
    print(f"  Districts: {len(catalog)}")
    print(f"  Saved:     {latest_path}")
    return 0


def _known_state_ids() -> list[dict]:
    """Fallback: known PMGSY state IDs derived from the portal."""
    # These IDs are stable and publicly documented in PMGSY OMMAS
    known = [
        (1, "ANDAMAN AND NICOBAR"),
        (2, "ANDHRA PRADESH"),
        (3, "ARUNACHAL PRADESH"),
        (4, "ASSAM"),
        (5, "BIHAR"),
        (6, "CHHATTISGARH"),
        (7, "GOA"),
        (8, "GUJARAT"),
        (9, "HARYANA"),
        (10, "HIMACHAL PRADESH"),
        (11, "JAMMU AND KASHMIR"),
        (12, "JHARKHAND"),
        (13, "KARNATAKA"),
        (14, "KERALA"),
        (15, "MADHYA PRADESH"),
        (16, "MAHARASHTRA"),
        (17, "MANIPUR"),
        (18, "MEGHALAYA"),
        (19, "MIZORAM"),
        (20, "NAGALAND"),
        (21, "ODISHA"),
        (22, "PUNJAB"),
        (23, "RAJASTHAN"),
        (24, "SIKKIM"),
        (25, "TAMIL NADU"),
        (26, "TRIPURA"),
        (27, "UTTAR PRADESH"),
        (28, "UTTARAKHAND"),
        (29, "WEST BENGAL"),
        (30, "TELANGANA"),
        (31, "LADAKH"),
        (32, "PUDUCHERRY"),
    ]
    return [{"pmgsy_state_id": str(sid), "state_name": name} for sid, name in known]


if __name__ == "__main__":
    raise SystemExit(main())
