"""
PM POSHAN AMS (Automated Monitoring System) scraper.

Scrapes district-level meal reporting data from the PM POSHAN AMS portal
at pmposhan-ams.education.gov.in. Uses ASP.NET WebForms postback mechanism
to drill down from state-level to district-level data.

Data includes: total schools, schools reported, student enrolment,
meals served count and percentage per district.

Usage:
    python3 scrape_pmposhan_ams.py                        # All states
    python3 scrape_pmposhan_ams.py --states "BIHAR"       # Single state
    python3 scrape_pmposhan_ams.py --states "BIHAR,TAMIL NADU"
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
from bs4 import BeautifulSoup

ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw" / "pmposhan"
CURATED_DIR = DATA_DIR / "curated"

BASE_URL = "https://pmposhan-ams.education.gov.in/Reported_ams_School.aspx"
SOURCE_URL = "pmposhan-ams.education.gov.in/Reported_ams_School.aspx"

TABLE_ID = "ctl00_ContentPlaceHolder1_Grd_total_detail"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": BASE_URL,
    "Origin": "https://pmposhan-ams.education.gov.in",
    "Content-Type": "application/x-www-form-urlencoded",
}

DELAY_SECONDS = 2


def utc_iso() -> str:
    return datetime.now(UTC).isoformat()


def state_slug(name: str) -> str:
    return name.lower().replace("&", "and").replace(" ", "-")


def ensure_dirs() -> None:
    for d in (RAW_DIR, CURATED_DIR):
        d.mkdir(parents=True, exist_ok=True)


def extract_form_fields(soup: BeautifulSoup) -> dict[str, str]:
    """Extract all form fields (hidden + visible) from ASP.NET page."""
    fields: dict[str, str] = {}
    form = soup.find("form", {"id": "aspnetForm"})
    if not form:
        form = soup

    for tag in form.find_all("input"):
        name = tag.get("name")
        if name:
            fields[name] = tag.get("value", "")

    return fields


def extract_postback_target(href: str) -> str:
    """Extract the __doPostBack target from a javascript href.

    Example input:  javascript:__doPostBack('ctl00$...name','')
    Example output: ctl00$...name
    """
    match = re.search(r"__doPostBack\('([^']+)'", href)
    return match.group(1) if match else ""


def parse_number(text: str) -> int:
    """Parse a number from table cell text, ignoring percentage annotations.

    Examples: '1[1.69%]' -> 1, '58[98.31%]' -> 58, '100%' -> 100
    """
    # Strip bracket annotations like [1.69%]
    clean = re.split(r"\[", text)[0].strip()
    clean = clean.replace(",", "").replace("%", "").strip()
    if not clean or clean == "-":
        return 0
    try:
        return int(float(clean))
    except ValueError:
        return 0


def parse_pct(text: str) -> float:
    """Parse a percentage from table cell text like '87.86%' or '100 %'."""
    clean = text.strip().replace("%", "").replace(",", "").strip()
    if not clean or clean == "-":
        return 0.0
    try:
        return float(clean)
    except ValueError:
        return 0.0


def parse_state_table(soup: BeautifulSoup) -> list[dict[str, str]]:
    """Parse the state-level table to get state names and postback targets."""
    table = soup.find("table", {"id": TABLE_ID})
    if not table:
        return []

    states: list[dict[str, str]] = []
    for link in table.find_all("a", href=re.compile(r"lnkbtn_name")):
        state_name = link.get_text(strip=True)
        postback_target = extract_postback_target(link["href"])
        if state_name and postback_target:
            states.append(
                {
                    "name": state_name,
                    "postback_target": postback_target,
                }
            )

    return states


def parse_district_table(
    soup: BeautifulSoup,
    state_name: str,
    state_code: str,
    scraped_at: str,
) -> list[dict[str, Any]]:
    """Parse the district-level table into records.

    District table columns (0-indexed):
      0: S.No
      1: District name
      2: Total Schools
      3: Reported [with %]
      4: Not Reported [with %]
      5: Holiday
      6: Meal served (%)
      7: Meal not served %
      8: Student Enrolment
      9: Enrolment (in reporting schools)
     10: Enrolment %
     11: Availed meals
     12: Availed meals %
    """
    table = soup.find("table", {"id": TABLE_ID})
    if not table:
        return []

    rows = table.find_all("tr")
    records: list[dict[str, Any]] = []

    # Skip header rows (first 3 rows: merged header, sub-header, column numbers)
    for row in rows[3:]:
        cells = row.find_all("td")
        if len(cells) < 13:
            continue

        cell_texts = [c.get_text(strip=True) for c in cells]

        district = cell_texts[1]
        if not district or district.upper() == "TOTAL":
            continue

        total_schools = parse_number(cell_texts[2])
        schools_reported = parse_number(cell_texts[3])
        student_enrolment = parse_number(cell_texts[8])
        meals_served = parse_number(cell_texts[11])
        meals_served_pct = parse_pct(cell_texts[12])

        record = {
            "district": district.upper(),
            "state": state_name.upper(),
            "state_code": state_code,
            "fin_year": "2025-2026",
            "schools_covered": total_schools,
            "schools_reported": schools_reported,
            "children_enrolled": student_enrolment,
            "children_fed": meals_served,
            "funds_released_lakhs": 0,
            "funds_utilized_lakhs": 0,
            "utilization_pct": round(meals_served_pct, 2),
            "source_url": SOURCE_URL,
            "scraped_at": scraped_at,
        }
        records.append(record)

    return records


def load_state_codes() -> dict[str, str]:
    """Load state code mapping from states.json."""
    states_path = ROOT_DIR / "states.json"
    if not states_path.exists():
        return {}
    with states_path.open(encoding="utf-8") as f:
        states_data = json.load(f)
    mapping: dict[str, str] = {}
    for s in states_data:
        name = s.get("state_name", "").upper()
        code = s.get("state_code", "")
        if name and code:
            mapping[name] = code
    return mapping


def resolve_state_code(
    state_name: str,
    code_map: dict[str, str],
) -> str:
    """Resolve state code from name, handling naming differences."""
    upper = state_name.upper()
    if upper in code_map:
        return code_map[upper]

    # Handle common naming mismatches between portal and states.json
    aliases: dict[str, str] = {
        "A & N ISLANDS": "ANDAMAN AND NICOBAR",
        "JAMMU & KASHMIR": "JAMMU AND KASHMIR",
        "DNH & DD": "DADRA & NAGAR HAVELI",
        "DELHI": "DELHI",
        "LADAKH": "LADAKH",
    }
    canonical = aliases.get(upper, upper)
    return code_map.get(canonical, "")


def fetch_page(session: requests.Session, url: str) -> BeautifulSoup:
    """GET a page and return parsed soup."""
    resp = session.get(url, headers=REQUEST_HEADERS, timeout=60)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def fetch_district_page(
    session: requests.Session,
    form_fields: dict[str, str],
    postback_target: str,
) -> BeautifulSoup:
    """POST with __doPostBack to drill down to district view."""
    form_data = dict(form_fields)
    form_data["__EVENTTARGET"] = postback_target
    form_data["__EVENTARGUMENT"] = ""
    # Remove submit buttons from form data (they shouldn't be sent
    # unless the user clicked them)
    form_data.pop("ctl00$ContentPlaceHolder1$btnPdf", None)

    resp = session.post(
        BASE_URL,
        data=form_data,
        headers=REQUEST_HEADERS,
        timeout=60,
    )
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def scrape_all(
    states_filter: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Scrape district-level data for all (or filtered) states."""
    scraped_at = utc_iso()
    code_map = load_state_codes()
    all_records: list[dict[str, Any]] = []

    session = requests.Session()

    # Step 1: GET the initial page to get state list and hidden fields
    print("Fetching initial state-level page...")
    soup = fetch_page(session, BASE_URL)
    states = parse_state_table(soup)
    print(f"Found {len(states)} states/UTs")

    if not states:
        print("ERROR: No states found on page. The portal may be down or changed.")
        return []

    # Apply filter
    if states_filter:
        filter_upper = [s.upper() for s in states_filter]
        states = [s for s in states if s["name"].upper() in filter_upper]
        print(f"Filtered to {len(states)} states: {[s['name'] for s in states]}")

    # Step 2: For each state, POST to get district data
    for i, state_info in enumerate(states):
        state_name = state_info["name"]
        postback_target = state_info["postback_target"]
        state_code = resolve_state_code(state_name, code_map)

        print(f"\n[{i + 1}/{len(states)}] Drilling into {state_name}...")

        # Re-extract hidden fields from current page state
        hidden_fields = extract_form_fields(soup)
        if not hidden_fields.get("__VIEWSTATE"):
            print("  WARNING: Missing __VIEWSTATE, re-fetching main page...")
            soup = fetch_page(session, BASE_URL)
            hidden_fields = extract_form_fields(soup)

        district_soup = None
        max_retries = 2
        for attempt in range(max_retries):
            try:
                district_soup = fetch_district_page(
                    session,
                    hidden_fields,
                    postback_target,
                )
                break
            except requests.RequestException as e:
                if attempt < max_retries - 1:
                    print(f"  Attempt {attempt + 1} failed: {e}. Retrying...")
                    time.sleep(DELAY_SECONDS)
                    soup = fetch_page(session, BASE_URL)
                    hidden_fields = extract_form_fields(soup)
                else:
                    print(f"  SKIPPING {state_name}: {e} (no district data available)")

        if district_soup is None:
            time.sleep(DELAY_SECONDS)
            soup = fetch_page(session, BASE_URL)
            continue

        records = parse_district_table(
            district_soup,
            state_name,
            state_code,
            scraped_at,
        )
        print(f"  Found {len(records)} districts")
        all_records.extend(records)

        # Update soup for next iteration (use current page to navigate back)
        # We need to re-fetch main page for next state since we drilled down
        time.sleep(DELAY_SECONDS)

        if i < len(states) - 1:
            try:
                soup = fetch_page(session, BASE_URL)
            except requests.RequestException as e:
                print(f"  ERROR re-fetching main page: {e}")
                time.sleep(DELAY_SECONDS)
                soup = fetch_page(session, BASE_URL)

    return all_records


def save_raw(records: list[dict[str, Any]]) -> Path:
    """Save all records to raw JSON."""
    path = RAW_DIR / "pmposhan_ams_raw.json"
    path.write_text(
        json.dumps(records, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def save_curated_by_state(records: list[dict[str, Any]]) -> dict[str, Path]:
    """Save per-state curated JSON files."""
    by_state: dict[str, list[dict[str, Any]]] = {}
    for r in records:
        by_state.setdefault(r["state"], []).append(r)

    paths: dict[str, Path] = {}
    for state_name, state_records in sorted(by_state.items()):
        slug = state_slug(state_name)
        path = CURATED_DIR / f"pmposhan_district_{slug}_latest.json"
        path.write_text(
            json.dumps(state_records, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        paths[state_name] = path

    return paths


def print_summary(records: list[dict[str, Any]], paths: dict[str, Path]) -> None:
    """Print summary of scraped data."""
    states_covered = len(paths)
    total_districts = len(records)

    print("\n" + "=" * 60)
    print("PM POSHAN AMS Scraping Summary")
    print("=" * 60)
    print(f"States/UTs covered: {states_covered}")
    print(f"Total districts:    {total_districts}")
    print()

    for state_name, path in sorted(paths.items()):
        count = sum(1 for r in records if r["state"] == state_name)
        print(f"  {state_name}: {count} districts -> {path.name}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scrape PM POSHAN AMS district-level data",
    )
    parser.add_argument(
        "--states",
        help="Comma-separated list of states to scrape (default: all)",
    )
    args = parser.parse_args()

    ensure_dirs()

    states_filter = None
    if args.states:
        states_filter = [s.strip() for s in args.states.split(",")]

    records = scrape_all(states_filter)

    if not records:
        print("\nNo records scraped.")
        return 1

    raw_path = save_raw(records)
    print(f"\nRaw data saved: {raw_path}")

    paths = save_curated_by_state(records)

    print_summary(records, paths)
    return 0


if __name__ == "__main__":
    sys.exit(main())
