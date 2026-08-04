"""
PMAY-G state-level financial scraper (report.pmayg.dord.gov.in).

Scrapes the B.3 High Level Financial Progress report which shows:
  Opening Balance, Central/State Allocation, Release, Utilization — all in lakhs.
  Available for FY 2010-2011 through 2025-2026.

Form interaction: FY postback → Scheme postback → Captcha solve → Submit.
The captcha is an arithmetic image (e.g., "51 - 40") solved via Tesseract OCR.

This replaces/supplements scrape_pmayg_dashboard.py (data.gov.in, 2 years only).

Output: data/curated/pmayg_finance_all_latest.json

Usage:
    python3 scrape_pmayg_finance.py
    python3 scrape_pmayg_finance.py --years 2022-2023,2023-2024,2024-2025

Requires: playwright, pytesseract, Pillow, tesseract (brew install tesseract)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
CURATED_DIR = DATA_DIR / "curated"

REPORT_URL = (
    "https://report.pmayg.dord.gov.in/netiay/"
    "FinancialProgressReport/Report_HighLevel_FinancialProgress.aspx"
)

DEFAULT_FIN_YEARS = [
    "2019-2020",
    "2020-2021",
    "2021-2022",
    "2022-2023",
    "2023-2024",
    "2024-2025",
    "2025-2026",
]

DELAY_MS = 3000
MAX_CAPTCHA_ATTEMPTS = 5


def utc_iso() -> str:
    return datetime.now(UTC).isoformat()


def _parse_amount(text: str) -> float:
    text = text.strip().replace(",", "")
    if not text or text in ("-", "0.00", "0"):
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


_CANONICAL_STATES = {
    "TAMILNADU": "TAMIL NADU",
    "JAMMU & KASHMIR": "JAMMU AND KASHMIR",
    "ANDAMAN & NICOBAR ISLANDS": "ANDAMAN AND NICOBAR ISLANDS",
    "DADRA & NAGAR HAVELI": "DADRA AND NAGAR HAVELI",
    "DADRA & NAGAR HAVELI AND DAMAN & DIU": "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
    "D & N HAVELI AND DAMAN & DIU": "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
    "DAMAN & DIU": "DAMAN AND DIU",
}


def _normalize_state(name: str) -> str:
    upper = name.strip().upper()
    return _CANONICAL_STATES.get(upper, upper)


def _is_total_row(state: str) -> bool:
    if not state:
        return True
    return state.upper() in ("TOTAL", "GRAND TOTAL", "ALL INDIA", "INDIA")


async def _solve_captcha(page: Any) -> str | None:
    """Screenshot captcha image, OCR the arithmetic, solve it."""
    try:
        import pytesseract
        from PIL import Image

        captcha_img = page.locator("#ctl00_ContentPlaceHolder1_imgCaptcha")
        path = RAW_DIR / "captcha_temp.png"
        await captcha_img.screenshot(path=str(path))

        img = Image.open(path)
        text = pytesseract.image_to_string(
            img,
            config="--psm 7 -c tessedit_char_whitelist=0123456789+-x */",
        ).strip()

        text = text.replace("x", "*").replace("X", "*").replace("×", "*")
        text = re.sub(r"[^0-9+\-*/\s]", "", text).strip()

        if not text:
            return None

        result = eval(text)  # noqa: S307 — trusted captcha arithmetic
        return str(int(result))
    except Exception as e:
        print(f"    Captcha OCR error: {e}")
        return None


async def _scrape_year(page: Any, fy: str, scraped_at: str) -> list[dict[str, Any]]:
    """Scrape one financial year. Returns parsed records or empty list."""

    for attempt in range(MAX_CAPTCHA_ATTEMPTS):
        # Fresh page load each attempt (ASP.NET viewstate must be clean)
        await page.goto(REPORT_URL, timeout=30000)
        await page.wait_for_load_state("load", timeout=15000)
        await page.wait_for_timeout(DELAY_MS)

        # Step 1: Select FY via postback (populates scheme dropdown)
        await page.evaluate(
            """(fy) => {
                document.getElementById('ctl00_ContentPlaceHolder1_ddlFinYear').value = fy;
                __doPostBack('ctl00$ContentPlaceHolder1$ddlFinYear', '');
            }""",
            fy,
        )
        await page.wait_for_load_state("load", timeout=15000)
        await page.wait_for_timeout(DELAY_MS)

        # Step 2: Select scheme via postback (loads state data)
        await page.evaluate(
            """() => {
                var s = document.getElementById('ctl00_ContentPlaceHolder1_ddlScheme');
                s.disabled = false;
                s.value = 'PMAYG';
                __doPostBack('ctl00$ContentPlaceHolder1$ddlScheme', '');
            }""",
        )
        await page.wait_for_load_state("load", timeout=15000)
        await page.wait_for_timeout(DELAY_MS)

        # Step 3: Solve captcha
        answer = await _solve_captcha(page)
        if not answer:
            print(f"    Attempt {attempt + 1}: OCR failed")
            continue

        print(f"    Attempt {attempt + 1}: captcha={answer}")

        # Step 4: Fill and submit
        await page.fill("#ctl00_ContentPlaceHolder1_txtCaptcha", answer)
        await page.click("#ctl00_ContentPlaceHolder1_btnSubmit")
        await page.wait_for_load_state("load", timeout=30000)
        await page.wait_for_timeout(DELAY_MS)

        # Step 5: Check if table loaded
        table_rows = await page.evaluate(
            """() => {
                var gv = document.getElementById('ctl00_ContentPlaceHolder1_gvData');
                return gv ? gv.querySelectorAll('tr').length : 0;
            }""",
        )

        if table_rows > 3:
            # Parse the table
            raw_rows = await page.evaluate(
                """() => {
                    var gv = document.getElementById('ctl00_ContentPlaceHolder1_gvData');
                    var result = [];
                    var rows = gv.querySelectorAll('tr');
                    for (var i = 0; i < rows.length; i++) {
                        var cells = rows[i].querySelectorAll('td');
                        if (cells.length < 5) continue;
                        result.push(Array.from(cells, c => c.innerText.trim()));
                    }
                    return result;
                }""",
            )

            # Save raw HTML
            html = await page.content()
            (RAW_DIR / f"pmayg_finance_{fy}.html").write_text(html, encoding="utf-8")

            records = _parse_rows(raw_rows, fy, scraped_at)
            print(f"  {len(records)} states scraped")
            return records

        status = await page.evaluate(
            """() => {
                var lbl = document.getElementById('ctl00_ContentPlaceHolder1_lblStatus');
                return lbl ? lbl.innerText : '';
            }""",
        )
        if status:
            print(f"    Status: {status}")

    print(f"  FAILED after {MAX_CAPTCHA_ATTEMPTS} attempts")
    return []


def _parse_rows(
    rows: list[list[str]],
    fin_year: str,
    scraped_at: str,
) -> list[dict[str, Any]]:
    """Parse B.3 table rows.

    12-column layout (confirmed):
      0:SNo 1:State 2:OB 3:CentralAlloc 4:StateAlloc 5:TotalAlloc
      6:CentralRelease 7:StateRelease 8:TotalRelease 9:TotalAvailable
      10:Utilization 11:%Utilized
    """
    source_url = "report.pmayg.dord.gov.in B.3 HighLevel FinancialProgress"
    records: list[dict[str, Any]] = []

    for row in rows:
        if len(row) < 12:
            continue

        sno = row[0].strip()
        if not sno or not sno.isdigit():
            continue

        state_name = row[1].strip()
        if not state_name or _is_total_row(state_name):
            continue

        state = _normalize_state(state_name)
        total_alloc = _parse_amount(row[5])
        total_release = _parse_amount(row[8])
        utilization = _parse_amount(row[10])

        if total_alloc > 0 or total_release > 0 or utilization > 0:
            records.append({
                "state": state,
                "fin_year": fin_year,
                "allocated_lakhs": total_alloc,
                "released_lakhs": total_release,
                "utilized_lakhs": utilization,
                "source_url": source_url,
                "scraped_at": scraped_at,
            })

    return records


async def scrape_all(fin_years: list[str]) -> list[dict[str, Any]]:
    from playwright.async_api import async_playwright

    all_records: list[dict[str, Any]] = []
    scraped_at = utc_iso()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            for fy in fin_years:
                print(f"\n--- {fy} ---")
                records = await _scrape_year(page, fy, scraped_at)
                all_records.extend(records)
        except Exception as e:
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()

    return sorted(all_records, key=lambda x: (x["state"], x["fin_year"]))


def save_curated(records: list[dict[str, Any]]) -> Path:
    CURATED_DIR.mkdir(parents=True, exist_ok=True)
    path = CURATED_DIR / "pmayg_finance_all_latest.json"
    path.write_text(
        json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8",
    )
    return path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scrape PMAY-G financial data from portal",
    )
    parser.add_argument(
        "--years",
        help="Comma-separated fin years (default: 2019-2026)",
    )
    args = parser.parse_args()

    fin_years = (
        [y.strip() for y in args.years.split(",")]
        if args.years
        else DEFAULT_FIN_YEARS
    )

    for d in (RAW_DIR, CURATED_DIR):
        d.mkdir(parents=True, exist_ok=True)

    print(f"PMAY-G Financial Scraper — {len(fin_years)} years")
    print(f"Years: {', '.join(fin_years)}")

    records = asyncio.run(scrape_all(fin_years))
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
