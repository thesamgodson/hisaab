"""
PMAY-G (Pradhan Mantri Awas Yojana - Gramin) scraper.

Scrapes rural housing data from report.pmayg.dord.gov.in using Playwright.
The portal uses ASP.NET with cascading postback dropdowns (FY → Scheme → State).

Report scraped:
- Physical Progress (district-level housing targets vs completion)

Output: JSON files in data/curated/ with raw HTML snapshots in data/raw/.

Usage:
    python scrape_pmayg.py --states "BIHAR"
    python scrape_pmayg.py --states "BIHAR,TAMIL NADU" --fin-year 2024-2025
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from scrapers.io_utils import atomic_write_json
except ImportError:
    from io_utils import atomic_write_json

ROOT_DIR = Path(__file__).resolve().parent.parent  # repo root (scrapers/ is a package)
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
CURATED_DIR = DATA_DIR / "curated"
LOG_DIR = DATA_DIR / "logs"

REPORT_URL = "https://report.pmayg.dord.gov.in/netiay/DataAnalytics/PhysicalProgressRpt.aspx"

# State name → PMAY-G state_code mapping (from the dropdown on the portal)
# State codes scraped from the PMAY-G portal dropdown (2026-03-31)
STATE_CODES: dict[str, str] = {
    "ANDAMAN AND NICOBAR": "01",
    "ANDHRA PRADESH": "02",
    "ARUNACHAL PRADESH": "03",
    "ASSAM": "04",
    "BIHAR": "05",
    "CHHATTISGARH": "33",
    "DADRA AND NAGAR HAVELI": "07",
    "DAMAN AND DIU": "08",
    "GOA": "10",
    "GUJARAT": "11",
    "HARYANA": "12",
    "HIMACHAL PRADESH": "13",
    "JAMMU AND KASHMIR": "14",
    "JHARKHAND": "34",
    "KARNATAKA": "15",
    "KERALA": "16",
    "LAKSHADWEEP": "19",
    "MADHYA PRADESH": "17",
    "MAHARASHTRA": "18",
    "MANIPUR": "20",
    "MEGHALAYA": "21",
    "MIZORAM": "22",
    "NAGALAND": "23",
    "ODISHA": "24",
    "PUDUCHERRY": "25",
    "PUNJAB": "26",
    "RAJASTHAN": "27",
    "SIKKIM": "28",
    "TAMIL NADU": "29",
    "TELANGANA": "36",
    "TRIPURA": "30",
    "UTTAR PRADESH": "31",
    "UTTARAKHAND": "35",
    "WEST BENGAL": "32",
    "LADAKH": "37",
}


@dataclass(frozen=True)
class PmaygConfig:
    state_name: str
    state_code: str
    fin_year: str
    scheme: str = "PMAYG"


def utc_iso() -> str:
    return datetime.now(UTC).isoformat()


def state_slug(name: str) -> str:
    return name.lower().replace(" ", "-")


def ensure_dirs() -> None:
    for d in (RAW_DIR, CURATED_DIR, LOG_DIR):
        d.mkdir(parents=True, exist_ok=True)


async def scrape_state(config: PmaygConfig) -> list[dict[str, Any]]:
    """Scrape district-level housing data for one state."""
    from playwright.async_api import async_playwright

    print(f"  Scraping {config.state_name} ({config.fin_year})...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        records: list[dict[str, Any]] = []

        try:
            await page.goto(REPORT_URL, timeout=30000)

            # Step 1: Select Financial Year (triggers postback)
            await page.evaluate(
                """(fy) => {
                    document.getElementById('ctl00_ContentPlaceHolder1_ddlFinYear').value = fy;
                    __doPostBack('ctl00$ContentPlaceHolder1$ddlFinYear', '');
                }""",
                config.fin_year,
            )
            await page.wait_for_load_state("load", timeout=15000)
            await page.wait_for_timeout(2000)

            # Step 2: Select Scheme (force-enable, triggers postback)
            await page.evaluate(
                """(scheme) => {
                    var d = document.getElementById('ctl00_ContentPlaceHolder1_ddlScheme');
                    d.disabled = false;
                    d.value = scheme;
                    __doPostBack('ctl00$ContentPlaceHolder1$ddlScheme', '');
                }""",
                config.scheme,
            )
            await page.wait_for_load_state("load", timeout=15000)
            await page.wait_for_timeout(2000)

            # Step 3: Select State (force-enable, triggers postback)
            await page.evaluate(
                """(code) => {
                    var d = document.getElementById('ctl00_ContentPlaceHolder1_ddlState');
                    d.disabled = false;
                    d.value = code;
                    __doPostBack('ctl00$ContentPlaceHolder1$ddlState', '');
                }""",
                config.state_code,
            )
            await page.wait_for_load_state("load", timeout=15000)
            await page.wait_for_timeout(2000)

            # Step 4: Submit
            await page.evaluate("""() => {
                var b = document.getElementById('ctl00_ContentPlaceHolder1_btnSubmit');
                b.disabled = false;
                b.click();
            }""")
            await page.wait_for_load_state("load", timeout=30000)
            await page.wait_for_timeout(5000)

            # Step 5: Parse the data table
            tables = await page.query_selector_all("table")
            data_table = None
            for t in tables:
                rows = await t.query_selector_all("tr")
                if len(rows) > 5:
                    data_table = t
                    break

            if not data_table:
                print(f"    No data table found for {config.state_name}")
                await browser.close()
                return []

            rows = await data_table.query_selector_all("tr")
            print(f"    Found {len(rows)} rows")

            # Save raw HTML
            raw_html = await data_table.inner_html()
            raw_path = RAW_DIR / f"pmayg_{state_slug(config.state_name)}_{config.fin_year}.html"
            raw_path.write_text(raw_html, encoding="utf-8")

            # Parse data rows (skip header rows and total row)
            scraped_at = utc_iso()
            source_url = f"{REPORT_URL}?state={config.state_code}&fy={config.fin_year}"

            for row in rows[2:]:  # Skip header rows
                cells = await row.query_selector_all("td")
                if len(cells) < 10:
                    continue

                texts = [(await c.inner_text()).strip() for c in cells]

                # Skip total/summary rows
                sno = texts[0]
                if not sno.isdigit():
                    continue

                district = texts[1].strip()
                if not district or district.lower() in ("total", "grand total"):
                    continue

                record = {
                    "district": district,
                    "state": config.state_name,
                    "state_code": config.state_code,
                    "fin_year": config.fin_year,
                    "houses_sanctioned": _parse_int(texts[2]),  # Target fixed by States
                    "registered": _parse_int(texts[3]),
                    "geo_tagged": _parse_int(texts[4]),
                    "sanctions_from_geo": _parse_int(texts[5]),
                    "sanctions_verified": _parse_int(texts[6]),
                    "installment_1st": _parse_int(texts[7]),
                    "installment_2nd": _parse_int(texts[8]) if len(texts) > 8 else 0,
                    "installment_3rd": _parse_int(texts[9]) if len(texts) > 9 else 0,
                    "installment_4th": _parse_int(texts[10]) if len(texts) > 10 else 0,
                    "houses_completed": _parse_int(texts[-1]) if len(texts) > 11 else _parse_int(texts[-1]),
                    "houses_occupied": 0,  # Not in this report
                    "funds_released_lakhs": 0,  # Financial report needed
                    "funds_utilized_lakhs": 0,
                    "completion_pct": 0.0,
                    "source_url": source_url,
                    "scraped_at": scraped_at,
                }

                # Calculate completion % from target
                if record["houses_sanctioned"] > 0:
                    record["completion_pct"] = round(record["houses_completed"] / record["houses_sanctioned"] * 100, 1)

                records.append(record)

        except Exception as e:
            print(f"    Error scraping {config.state_name}: {e}")
        finally:
            await browser.close()

    print(f"    Parsed {len(records)} districts")
    return records


def _parse_int(text: str) -> int:
    """Parse a number string, handling commas and empty values."""
    text = text.strip().replace(",", "")
    if not text or text == "-" or text == "0":
        return 0
    try:
        return int(float(text))
    except ValueError:
        return 0


def save_curated(records: list[dict[str, Any]], state_name: str) -> Path:
    """Save parsed records as JSON."""
    slug = state_slug(state_name)
    path = CURATED_DIR / f"pmayg_district_{slug}_latest.json"
    atomic_write_json(path, records)
    return path


async def scrape_states(
    states: list[str],
    fin_year: str = "2024-2025",
    delay_sec: int = 3,
) -> dict[str, int]:
    """Scrape PMAY-G data for multiple states."""
    ensure_dirs()
    results: dict[str, int] = {}

    for state_name in states:
        code = STATE_CODES.get(state_name.upper())
        if not code:
            print(f"  Unknown state: {state_name}")
            results[state_name] = 0
            continue

        config = PmaygConfig(
            state_name=state_name.upper(),
            state_code=code,
            fin_year=fin_year,
        )

        records = await scrape_state(config)
        if records:
            path = save_curated(records, state_name)
            print(f"    Saved {len(records)} records → {path.name}")
        results[state_name] = len(records)

        if delay_sec > 0 and state_name != states[-1]:
            print(f"    Waiting {delay_sec}s...")
            await asyncio.sleep(delay_sec)

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape PMAY-G housing data")
    parser.add_argument(
        "--states",
        required=True,
        help="Comma-separated state names (e.g. 'BIHAR,TAMIL NADU')",
    )
    parser.add_argument("--fin-year", default="2024-2025", help="Financial year")
    parser.add_argument("--delay-sec", type=int, default=3, help="Delay between states")
    args = parser.parse_args()

    states = [s.strip() for s in args.states.split(",")]
    print(f"PMAY-G Scraper — {len(states)} states, FY {args.fin_year}")

    results = asyncio.run(scrape_states(states, args.fin_year, args.delay_sec))

    print("\nResults:")
    for state, count in results.items():
        print(f"  {state}: {count} districts")
    print(f"Total: {sum(results.values())} records")

    return 0


if __name__ == "__main__":
    sys.exit(main())
