"""
PMAY-G state-level financial scraper (report.pmayg.dord.gov.in).

Scrapes the B.3 High Level Financial Progress report which shows:
  Opening Balance, Central/State Allocation, Release, Utilization — all in lakhs.
  Available for FY 2010-2011 through 2026-2027.

UN-GATED as of 2026-08-04: the arithmetic captcha that used to guard this report
is GONE — `Report_HighLevel_FinancialProgress.aspx` renders no captcha control
and carries no `__EVENTVALIDATION`, so plain stateless `requests` form POSTs
work. This scraper was rewritten off the Playwright + Tesseract OCR path (which
the no-captcha-automation decision forbade); the table is no longer frozen.

Flow (per FY, a mandatory 3-POST chain — a single combined POST resets the
scheme dropdown and returns 0 rows):
  GET  page                                   -> __VIEWSTATE / __VIEWSTATEGENERATOR
  POST __EVENTTARGET=ddlFinYear (scheme=0)    -> FY postback
  POST __EVENTTARGET=ddlScheme  (scheme=PMAYG)-> scheme postback
  POST __EVENTTARGET=''         (btnSubmit)   -> renders the gvData grid
Each POST relays the __VIEWSTATE / __VIEWSTATEGENERATOR from the PREVIOUS
response. No cookies, no login, no captcha. A browser User-Agent is required.

Output: data/curated/pmayg_finance_all_latest.json

Usage:
    python3 scrape_pmayg_finance.py
    python3 scrape_pmayg_finance.py --years 2023-2024,2024-2025
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

try:
    from scrapers.io_utils import atomic_write_json
except ImportError:
    from io_utils import atomic_write_json

ROOT_DIR = Path(__file__).resolve().parent.parent  # repo root (scrapers/ is a package)
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
CURATED_DIR = DATA_DIR / "curated"

REPORT_URL = (
    "https://report.pmayg.dord.gov.in/netiay/"
    "FinancialProgressReport/Report_HighLevel_FinancialProgress.aspx"
)

# Browser UA required — the portal does not black-hole python-requests like
# data.gov.in, but a bare UA still gets a plain (non-report) shell.
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
GRID_ID = "ctl00_ContentPlaceHolder1_gvData"
TIMEOUT = 40
DELAY_SEC = 1.0

DEFAULT_FIN_YEARS = [
    "2019-2020",
    "2020-2021",
    "2021-2022",
    "2022-2023",
    "2023-2024",
    "2024-2025",
    "2025-2026",
    "2026-2027",
]


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


def _hidden(html: str, name: str) -> str:
    """Extract an ASP.NET hidden field value (e.g. __VIEWSTATE) from a response."""
    m = re.search(rf'name="{re.escape(name)}"[^>]*value="([^"]*)"', html)
    return m.group(1) if m else ""


def _grid_rows(html: str) -> list[list[str]]:
    """Return the gvData table as a list of <td>-cell-text rows.

    Header bands are <th> (no <td>) and drop out; the two 'Total' rows survive
    here but are filtered in _parse_rows (non-numeric SNo)."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", {"id": GRID_ID})
    if table is None:
        return []
    rows: list[list[str]] = []
    for tr in table.find_all("tr"):
        tds = tr.find_all("td")
        if tds:
            rows.append([td.get_text(strip=True) for td in tds])
    return rows


def _parse_rows(
    rows: list[list[str]],
    fin_year: str,
    scraped_at: str,
) -> list[dict[str, Any]]:
    """Parse B.3 table rows.

    12-column layout (confirmed live 2026-08-04):
      0:SNo 1:State 2:OB 3:CentralAlloc 4:StateAlloc 5:TotalAlloc
      6:CentralRelease 7:StateRelease 8:TotalRelease 9:TotalAvailable
      10:Utilization 11:%Utilized
    """
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
                "source_url": REPORT_URL,
                "scraped_at": scraped_at,
            })

    return records


def _post(
    session: requests.Session, prev_html: str, target: str, scheme: str, fin_year: str, submit: bool
) -> str:
    data = {
        "__EVENTTARGET": target,
        "__EVENTARGUMENT": "",
        "__LASTFOCUS": "",
        "__VIEWSTATE": _hidden(prev_html, "__VIEWSTATE"),
        "__VIEWSTATEGENERATOR": _hidden(prev_html, "__VIEWSTATEGENERATOR"),
        "ctl00$ContentPlaceHolder1$ddlFinYear": fin_year,
        "ctl00$ContentPlaceHolder1$ddlScheme": scheme,
        "ctl00$ContentPlaceHolder1$ddlState": "0",
    }
    if submit:
        data["ctl00$ContentPlaceHolder1$btnSubmit"] = "Submit"
    resp = session.post(REPORT_URL, data=data, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.text


def _scrape_year(session: requests.Session, fy: str, scraped_at: str) -> list[dict[str, Any]]:
    """Scrape one FY via the GET -> 3-POST VIEWSTATE-relay chain."""
    h0 = session.get(REPORT_URL, timeout=TIMEOUT)
    h0.raise_for_status()
    if "captcha" in h0.text.lower():
        raise RuntimeError(f"{fy}: a captcha control reappeared on the B.3 report — refusing to proceed (no-captcha policy)")
    h1 = _post(session, h0.text, "ctl00$ContentPlaceHolder1$ddlFinYear", "0", fy, submit=False)
    h2 = _post(session, h1, "ctl00$ContentPlaceHolder1$ddlScheme", "PMAYG", fy, submit=False)
    h3 = _post(session, h2, "", "PMAYG", fy, submit=True)
    (RAW_DIR / f"pmayg_finance_{fy}.html").write_text(h3, encoding="utf-8")
    records = _parse_rows(_grid_rows(h3), fy, scraped_at)
    print(f"  {fy}: {len(records)} states")
    return records


def scrape_all(fin_years: list[str] | None = None) -> list[dict[str, Any]]:
    """Scrape B.3 finance for each FY. Plain requests, no captcha, no browser."""
    fin_years = fin_years or DEFAULT_FIN_YEARS
    for d in (RAW_DIR, CURATED_DIR):
        d.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Referer": REPORT_URL})
    scraped_at = utc_iso()

    all_records: list[dict[str, Any]] = []
    for fy in fin_years:
        try:
            all_records.extend(_scrape_year(session, fy, scraped_at))
        except (requests.RequestException, RuntimeError) as exc:
            print(f"  {fy}: FAILED — {exc}")
        time.sleep(DELAY_SEC)

    return sorted(all_records, key=lambda x: (x["state"], x["fin_year"]))


def save_curated(records: list[dict[str, Any]]) -> Path:
    """Save records, refusing a state-coverage regression (guard mirrors the
    other re-sourced scrapers — a bad scrape must never shrink the table)."""
    path = CURATED_DIR / "pmayg_finance_all_latest.json"
    new_states = {r["state"] for r in records}
    if path.exists():
        old_states = {r["state"] for r in json.loads(path.read_text(encoding="utf-8"))}
        if old_states and len(new_states) < len(old_states):
            raise ValueError(
                f"Refusing to save PMAY-G finance: {len(new_states)} states < existing "
                f"{len(old_states)} — a refresh must never reduce coverage"
            )
    atomic_write_json(path, records)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape PMAY-G B.3 financial data (un-gated)")
    parser.add_argument("--years", help="Comma-separated fin years (default: 2019-2027)")
    args = parser.parse_args()

    fin_years = [y.strip() for y in args.years.split(",")] if args.years else DEFAULT_FIN_YEARS
    print(f"PMAY-G Financial Scraper (un-gated B.3) — {len(fin_years)} years")

    records = scrape_all(fin_years)
    if not records:
        print("\nNo records scraped.")
        return 1

    path = save_curated(records)
    years = sorted({r["fin_year"] for r in records})
    states = sorted({r["state"] for r in records})
    print(f"\nSaved {len(records)} records to {path}")
    print(f"Years: {', '.join(years)}  |  States: {len(states)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
