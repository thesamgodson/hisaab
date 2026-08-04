"""
MGNREGA report scraper via the public (un-gated) state citizen portal.

The national MIS report index (mnregaweb4.dord.gov.in/netnrega/MISreport4.aspx)
became CAPTCHA-gated when MGNREGA moved from *.nic.in to *.dord.gov.in in
Aug 2026 — it renders zero report links before the captcha is answered, so it
is off limits. This scraper uses the state citizen home page instead, which is
public, needs no captcha, and emits the same Digest-signed report URLs:

    https://mnregaweb2.dord.gov.in/netnrega/homestciti.aspx?state_code=..&state_name=..

Flow: GET the citizen page -> ASP.NET postback on its `fin_year` dropdown to
select the target financial year -> harvest the Digest-signed report hrefs ->
fetch and parse each report's HTML table.

Reachable from the citizen portal:
- Financial Statement (R7)     -> financial_statement (district-level)
- FTO Status Report (R8)       -> fto_status          (district-level)
- FTO Pendency Day-wise (R8)   -> fto_pendency        (bank-level by design)

NOT reachable un-gated (see UNAVAILABLE_REPORTS): Financial Misappropriation
Recovery (R.9.2.6) and Social Audit Issues Reported by Category (R.9.2.3).
Both exist only on the captcha-gated MIS index. Their parsers are retained so
the datasets can be revived the moment an un-gated route reappears.

Output: JSON files in data/curated/ with raw HTML snapshots in data/raw/.
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
from urllib.parse import urlencode, urljoin

import requests
from bs4 import BeautifulSoup

try:
    from scrapers.io_utils import atomic_write_json
except ImportError:
    from io_utils import atomic_write_json

# nreganarep.nic.in died and MISreport4.aspx went behind a captcha when MGNREGA
# moved to *.dord.gov.in (Aug 2026). The state citizen page is the public route.
CITIZEN_BASE = "https://mnregaweb2.dord.gov.in/netnrega/"
CITIZEN_PAGE = CITIZEN_BASE + "homestciti.aspx"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT = 120

ROOT_DIR = Path(__file__).resolve().parent.parent  # repo root (scrapers/ is a package)
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
CURATED_DIR = DATA_DIR / "curated"
META_DIR = DATA_DIR / "metadata"
LOG_DIR = DATA_DIR / "logs"


# href fragments identifying each report on the citizen page (matched case-insensitively)
REPORT_PATTERNS: dict[str, str] = {
    "misappropriation": r"SAU_FMRecoveryReport\.aspx",
    "fto_status": r"FTO/FTOReport\.aspx",
    "fto_pendency": r"FTO/fto_bnkwise\.aspx",
    "issues_reported": r"SA-CatWise-IssueReported\.aspx",
    "financial_statement": r"fundstreportMtemp\.aspx",
}

# Datasets that exist only behind the captcha-gated national MIS index.
# Requesting one is not a crash — it reports the limitation and skips.
UNAVAILABLE_REPORTS: dict[str, str] = {
    "misappropriation": "captcha-gated MIS index only (MISreport4.aspx) — no un-gated route",
    "issues_reported": "captcha-gated MIS index only (MISreport4.aspx) — no un-gated route",
}

AVAILABLE_REPORTS: list[str] = [name for name in REPORT_PATTERNS if name not in UNAVAILABLE_REPORTS]

# The portal signs each report URL with a `Digest` over its query string and
# serves this page when the signature does not match the parameters.
TAMPER_MARKERS = ("url tempered", "url tampered")


def now_utc() -> datetime:
    return datetime.now(UTC)


def utc_iso() -> str:
    return now_utc().isoformat()


def slugify(text: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower())
    return value.strip("-") or "unknown"


def ensure_dirs() -> None:
    for d in (DATA_DIR, RAW_DIR, CURATED_DIR, META_DIR, LOG_DIR):
        d.mkdir(parents=True, exist_ok=True)


def parse_amount(raw: str) -> float:
    cleaned = raw.replace("₹", "").replace(",", "").strip()
    cleaned = re.sub(r"[^0-9.\-]", "", cleaned)
    try:
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0


def parse_number(raw: str) -> int:
    cleaned = raw.replace(",", "").strip()
    cleaned = re.sub(r"[^0-9\-]", "", cleaned)
    try:
        return int(cleaned) if cleaned else 0
    except ValueError:
        return 0


# ---------------------------------------------------------------------------
# Citizen portal session (public — no captcha anywhere in this path)
# ---------------------------------------------------------------------------
def new_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9"})
    return session


def citizen_url(state_name: str, state_code: str) -> str:
    query = urlencode(
        {"state_code": state_code, "state_name": state_name, "lflag": "eng", "labels": "labels"}
    )
    return f"{CITIZEN_PAGE}?{query}"


def _aspnet_form_fields(soup: BeautifulSoup) -> dict[str, str]:
    """Collect the hidden __VIEWSTATE / __EVENTVALIDATION etc. of the page form."""
    form = soup.find("form")
    if form is None:
        raise RuntimeError("Citizen page has no <form> — portal layout changed")
    return {i["name"]: i.get("value", "") for i in form.find_all("input") if i.get("name")}


def available_fin_years(soup: BeautifulSoup) -> list[str]:
    select = soup.find("select", {"name": "fin_year"})
    if select is None:
        return []
    return [o.get("value", "") for o in select.find_all("option") if o.get("value")]


def extract_report_urls(html: str, page_url: str) -> dict[str, str]:
    """Map report name -> absolute Digest-signed URL found on the citizen page."""
    soup = BeautifulSoup(html, "html.parser")
    urls: dict[str, str] = {}
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        for name, pattern in REPORT_PATTERNS.items():
            if name not in urls and re.search(pattern, href, re.IGNORECASE):
                urls[name] = urljoin(page_url, href)
    return urls


def open_citizen_session(
    session: requests.Session, state_name: str, state_code: str, fin_year: str, delay_sec: float
) -> tuple[dict[str, str], str]:
    """
    Load the public state citizen page and switch it to `fin_year`, returning
    ({report_name: Digest-signed url}, citizen_page_url).

    The Digest signs the financial year, so the year must be selected through
    the page's own ASP.NET postback — hand-editing fin_year in a report URL
    yields the portal's "URL TEMPERED" page.
    """
    page_url = citizen_url(state_name, state_code)
    response = session.get(page_url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")

    years = available_fin_years(soup)
    if years and fin_year not in years:
        raise RuntimeError(f"FY {fin_year} not offered for {state_name}; portal lists {', '.join(years)}")

    if years and years[0] != fin_year:
        fields = _aspnet_form_fields(soup)
        fields.update({"__EVENTTARGET": "fin_year", "__EVENTARGUMENT": "", "fin_year": fin_year})
        time.sleep(delay_sec)
        response = session.post(page_url, data=fields, timeout=REQUEST_TIMEOUT, headers={"Referer": page_url})
        response.raise_for_status()

    urls = extract_report_urls(response.text, page_url)
    # Guard against a silent year mismatch leaving us with last year's numbers.
    stale = {name: url for name, url in urls.items() if fin_year not in url}
    for name in stale:
        del urls[name]
    if stale:
        print(f"  Dropped {len(stale)} report URL(s) not carrying FY {fin_year}: {', '.join(sorted(stale))}")

    return urls, page_url


def fetch_report(session: requests.Session, url: str, referer: str) -> str:
    response = session.get(url, timeout=REQUEST_TIMEOUT, headers={"Referer": referer})
    response.raise_for_status()
    return response.text


def is_tampered(html: str) -> bool:
    lowered = html.lower()
    return any(marker in lowered for marker in TAMPER_MARKERS)


# ---------------------------------------------------------------------------
# Parsers for each report type
# ---------------------------------------------------------------------------
def _is_column_index_row(cells: list[Any]) -> bool:
    """Detect rows like [1, 2, 3, 4, ...] that are column index headers, not data."""
    if len(cells) < 4:
        return False
    values = []
    for c in cells:
        txt = c.get_text(strip=True)
        if txt.isdigit():
            values.append(int(txt))
        else:
            return False
    # Check if values are sequential starting from 1
    return values == list(range(1, len(values) + 1))


def find_data_table(soup: BeautifulSoup, min_rows: int = 5) -> tuple[list[str], list[Any]] | None:
    """Find the largest table with data rows (cells starting with digit serial numbers)."""
    best_headers: list[str] = []
    best_rows: list[Any] = []

    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if len(rows) < min_rows:
            continue

        data_rows = []
        header_cells: list[str] = []

        for row in rows:
            cells = row.find_all("td")
            if not cells:
                # Header row
                ths = row.find_all(["th", "td"])
                if ths:
                    header_cells = [c.get_text(strip=True) for c in ths]
                continue
            first = cells[0].get_text(strip=True)
            if not first.isdigit():
                continue
            # Skip column index rows (1, 2, 3, 4, ...)
            if _is_column_index_row(cells):
                continue
            data_rows.append(cells)

        if len(data_rows) > len(best_rows):
            best_rows = data_rows
            best_headers = header_cells

    if not best_rows:
        return None
    return best_headers, best_rows


def parse_misappropriation(html: str, state_name: str, state_code: str, source_url: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    parsed = find_data_table(soup)
    if not parsed:
        return []

    _headers, rows = parsed
    records: list[dict[str, Any]] = []

    for cells in rows:
        if len(cells) < 10:
            continue
        district = cells[1].get_text(strip=True)
        if district.lower() in ("total", "district name", ""):
            continue

        record = {
            "district": district,
            "state": state_name,
            "state_code": state_code,
            "cases_reported": parse_number(cells[2].get_text(strip=True)),
            "amount_reported": parse_amount(cells[3].get_text(strip=True)),
            "cases_decided": parse_number(cells[4].get_text(strip=True)),
            "amount_decided": parse_amount(cells[5].get_text(strip=True)),
            "cases_pending_recovery": parse_number(cells[6].get_text(strip=True)),
            "amount_to_recover": parse_amount(cells[7].get_text(strip=True)),
            "cases_recovered": parse_number(cells[8].get_text(strip=True)),
            "amount_recovered": parse_amount(cells[9].get_text(strip=True)),
            "source_url": source_url,
            "scraped_at": utc_iso(),
        }

        record["amount_unrecovered"] = round(record["amount_to_recover"] - record["amount_recovered"], 2)
        record["recovery_rate_pct"] = round(
            (record["amount_recovered"] / record["amount_to_recover"] * 100)
            if record["amount_to_recover"] > 0
            else 0.0,
            2,
        )
        records.append(record)

    return records


def parse_fto_status(html: str, state_name: str, state_code: str, source_url: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "html.parser")
    parsed = find_data_table(soup, min_rows=5)
    if not parsed:
        return []

    _headers, rows = parsed
    records: list[dict[str, Any]] = []

    for cells in rows:
        if len(cells) < 10:
            continue
        district = cells[1].get_text(strip=True)
        if district.lower() in ("total", "district", ""):
            continue

        record = {
            "district": district,
            "state": state_name,
            "state_code": state_code,
            "total_fto_generated": parse_number(cells[2].get_text(strip=True)),
            "first_signatory_signed": parse_number(cells[3].get_text(strip=True)),
            "first_signatory_pending": parse_number(cells[4].get_text(strip=True)),
            "second_signatory_signed": parse_number(cells[5].get_text(strip=True)),
            "second_signatory_pending": parse_number(cells[6].get_text(strip=True)),
            "fto_sent_to_bank": parse_number(cells[7].get_text(strip=True)),
            "source_url": source_url,
            "scraped_at": utc_iso(),
        }

        # Additional columns if available
        if len(cells) > 12:
            record["fto_processed_by_bank"] = parse_number(cells[8].get_text(strip=True))
            record["transactions_processed"] = parse_number(cells[9].get_text(strip=True))

        records.append(record)

    return records


def parse_fto_pendency(html: str, state_name: str, state_code: str, source_url: str) -> list[dict[str, Any]]:
    """
    FTO Pendency Day-wise report is bank-level, not district-level.
    Table columns: S.No, State, Bank Name, then day-wise pending counts.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Find the table with bank data — look for "Sub Total" or "Bank Name"
    best_table = None
    best_row_count = 0
    for table in soup.find_all("table"):
        text = table.get_text()
        if "Bank Name" in text or "Sub Total" in text:
            rows = table.find_all("tr")
            if len(rows) > best_row_count:
                best_table = table
                best_row_count = len(rows)

    if not best_table:
        return []

    rows = best_table.find_all("tr")
    records: list[dict[str, Any]] = []

    # Find header row with day range labels to locate start of data rows
    for row in rows[:4]:
        cells = row.find_all(["th", "td"])
        texts = [c.get_text(strip=True) for c in cells]
        if any("Days" in t for t in texts):
            break

    for row in rows:
        cells = row.find_all("td")
        if not cells or len(cells) < 4:
            continue

        if _is_column_index_row(cells):
            continue

        # Identify row type: bank data row or total row
        texts = [c.get_text(strip=True) for c in cells]
        first = texts[0]

        # Look for "Sub Total", "Grand Total", or serial number rows
        row_label = ""
        is_total = False
        if first.isdigit():
            # Bank data row: S.No, State, Bank Name, ...
            row_label = texts[2] if len(texts) > 2 else ""
        elif any("total" in t.lower() for t in texts[:3]):
            is_total = True
            row_label = next((t for t in texts[:3] if "total" in t.lower()), "TOTAL")
        else:
            continue

        if not row_label:
            continue

        record = {
            "bank_name": row_label,
            "is_total": is_total,
            "state": state_name,
            "state_code": state_code,
            "source_url": source_url,
            "scraped_at": utc_iso(),
        }

        # Parse pending counts from columns after the label columns
        start_col = 3
        numeric_cells = cells[start_col:] if len(cells) > start_col else []
        pending_values = [parse_number(c.get_text(strip=True)) for c in numeric_cells]

        # Map to day ranges (3 account types x 4 day ranges = 12 columns typical)
        if len(pending_values) >= 4:
            record["pending_1_7_days"] = pending_values[0]
            record["pending_8_15_days"] = pending_values[1]
            record["pending_16_30_days"] = pending_values[2]
            record["pending_over_30_days"] = pending_values[3]
            record["total_pending"] = sum(pending_values[:4])

        for k, val in enumerate(pending_values):
            record[f"pending_col_{k}"] = val

        records.append(record)

    return records


def parse_issues_reported(html: str, state_name: str, state_code: str, source_url: str) -> list[dict[str, Any]]:
    """
    Social Audit Issues by Category report.
    Columns: SR#, District, Total GPs, GPs Audited,
    then pairs of (Issues, Amount) for each issue category:
    Financial Misappropriation, Financial Deviation, Process Violation, Grievances.
    """
    soup = BeautifulSoup(html, "html.parser")
    parsed = find_data_table(soup, min_rows=3)
    if not parsed:
        return []

    _headers, rows = parsed
    records: list[dict[str, Any]] = []

    for cells in rows:
        if len(cells) < 6:
            continue
        district = cells[1].get_text(strip=True)
        if district.lower() in ("total", "district", ""):
            continue

        record = {
            "district": district,
            "state": state_name,
            "state_code": state_code,
            "total_gps": parse_number(cells[2].get_text(strip=True)),
            "gps_audited": parse_number(cells[3].get_text(strip=True)),
            "source_url": source_url,
            "scraped_at": utc_iso(),
        }

        # Issue categories come in pairs: (count, amount)
        categories = [
            ("misappropriation", 4),
            ("financial_deviation", 6),
            ("process_violation", 8),
            ("grievances", 10),
        ]
        for cat_name, start_idx in categories:
            if len(cells) > start_idx + 1:
                record[f"{cat_name}_issues"] = parse_number(cells[start_idx].get_text(strip=True))
                record[f"{cat_name}_amount"] = parse_amount(cells[start_idx + 1].get_text(strip=True))

        # Total issues and amount (last two columns)
        if len(cells) > 12:
            record["total_issues"] = parse_number(cells[12].get_text(strip=True))
            record["total_amount"] = parse_amount(cells[13].get_text(strip=True))

        records.append(record)

    return records


def parse_financial_statement(html: str, state_name: str, state_code: str, source_url: str) -> list[dict[str, Any]]:
    """
    Financial Performance report (R7).
    Multi-header table with fund release, expenditure, and utilization data.
    Amounts are in Lakhs.
    """
    soup = BeautifulSoup(html, "html.parser")
    parsed = find_data_table(soup, min_rows=5)
    if not parsed:
        return []

    _headers, rows = parsed
    records: list[dict[str, Any]] = []

    for cells in rows:
        if len(cells) < 8:
            continue
        district = cells[1].get_text(strip=True)
        if district.lower() in ("total", "district", ""):
            continue
        # Skip column index rows where "district" cell is a number (e.g. "2")
        if district.replace(".", "").isdigit():
            continue

        record = {
            "district": district,
            "state": state_name,
            "state_code": state_code,
            "source_url": source_url,
            "scraped_at": utc_iso(),
            "amounts_in_lakhs": True,
        }

        # Column mapping varies by table layout — capture all numeric values
        # Typical columns: Opening Balance, Release (Centre/State), Expenditure, etc.
        for k, cell in enumerate(cells[2:], start=2):
            raw = cell.get_text(strip=True)
            record[f"col_{k}"] = raw
            record[f"col_{k}_num"] = parse_amount(raw)

        records.append(record)

    return records


PARSERS: dict[str, Any] = {
    "misappropriation": parse_misappropriation,
    "fto_status": parse_fto_status,
    "fto_pendency": parse_fto_pendency,
    "issues_reported": parse_issues_reported,
    "financial_statement": parse_financial_statement,
}


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
def save_report(
    report_name: str,
    state_slug: str,
    run_id: str,
    html: str,
    records: list[dict[str, Any]],
    source_url: str,
) -> dict[str, str]:
    raw_path = RAW_DIR / f"{report_name}_{state_slug}_{run_id}.html"
    curated_path = CURATED_DIR / f"{report_name}_{state_slug}_{run_id}.json"
    latest_path = CURATED_DIR / f"{report_name}_{state_slug}_latest.json"

    raw_path.write_text(html, encoding="utf-8")
    # Only touch the curated JSON files when the parse produced records — an
    # empty parse (captcha/tamper block, portal layout change) must never
    # truncate the last known-good "latest" snapshot.
    atomic_write_json(curated_path, records)
    atomic_write_json(latest_path, records)

    return {
        "raw": str(raw_path),
        "curated": str(curated_path),
        "latest": str(latest_path),
    }


def append_run_log(entry: dict[str, Any]) -> None:
    fp = LOG_DIR / "report_runs.ndjson"
    with fp.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------
def run_for_state(
    state_name: str,
    state_code: str,
    fin_year: str,
    reports: list[str],
    delay_sec: float,
) -> int:
    ensure_dirs()
    run_id = now_utc().strftime("%Y%m%d_%H%M%S")
    state_slug = slugify(state_name)
    results: dict[str, dict[str, Any]] = {}

    requested = list(reports)
    for report_name in requested:
        if report_name in UNAVAILABLE_REPORTS:
            print(f"  {report_name}: SKIPPED — {UNAVAILABLE_REPORTS[report_name]}")
            results[report_name] = {"status": "unavailable_ungated", "reason": UNAVAILABLE_REPORTS[report_name]}
    obtainable = [r for r in requested if r not in UNAVAILABLE_REPORTS]
    if not obtainable:
        return 0

    print(f"Opening public citizen portal for {state_name} (FY {fin_year})...")
    session = new_session()

    try:
        report_urls, page_url = open_citizen_session(session, state_name, state_code, fin_year, delay_sec)
    except Exception as exc:
        print(f"Failed to open citizen session: {exc}")
        append_run_log(
            {
                "run_id": run_id,
                "state": state_name,
                "status": "failed_session",
                "error": str(exc),
                "timestamp": utc_iso(),
            }
        )
        return 2

    print(f"Found {len(report_urls)} Digest-signed report URLs")
    for name, url in report_urls.items():
        print(f"  {name}: {url[:110]}...")

    for report_name in obtainable:
        if report_name not in report_urls:
            print(f"\n  {report_name}: URL not present on the citizen page for this state/year")
            results[report_name] = {"status": "url_missing"}
            continue

        url = report_urls[report_name]
        parser = PARSERS[report_name]

        print(f"\n  Fetching {report_name}...")
        time.sleep(delay_sec)

        try:
            html = fetch_report(session, url, page_url)
        except Exception as exc:
            print(f"    Failed to fetch: {exc}")
            results[report_name] = {"status": "failed_fetch", "error": str(exc)}
            continue

        if is_tampered(html):
            print("    URL Tampered response — Digest no longer matches these parameters")
            results[report_name] = {"status": "tampered"}
            continue

        records = parser(html, state_name, state_code, url)
        for record in records:
            record["fin_year"] = fin_year
        paths = save_report(report_name, state_slug, run_id, html, records, url)

        print(f"    Parsed {len(records)} records")
        if records:
            print(f"    Saved: {paths['latest']}")
        else:
            print("    Nothing parsed — curated JSON left untouched")

        results[report_name] = {
            "status": "success" if records else "empty",
            "record_count": len(records),
            "paths": paths,
        }

    # Summary
    print(f"\n{'=' * 60}")
    print(f"Run complete: {state_name} (FY {fin_year})")
    print(f"Run ID: {run_id}")
    for name, result in results.items():
        status = result.get("status", "unknown")
        count = result.get("record_count", 0)
        print(f"  {name}: {status} ({count} records)")

    append_run_log(
        {
            "run_id": run_id,
            "state": state_name,
            "state_code": state_code,
            "fin_year": fin_year,
            "results": results,
            "timestamp": utc_iso(),
        }
    )

    # "unavailable_ungated" is a documented portal limitation, not a run failure.
    failed = sum(1 for r in results.values() if r.get("status") not in ("success", "unavailable_ungated"))
    return 0 if failed == 0 else 1


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scrape MGNREGA reports from the public state citizen portal (no captcha, requests only)"
    )
    parser.add_argument("--state-name", default="BIHAR")
    parser.add_argument("--state-code", default="05")
    parser.add_argument("--fin-year", default="2025-2026")
    parser.add_argument(
        "--reports",
        nargs="+",
        default=AVAILABLE_REPORTS,
        choices=list(REPORT_PATTERNS.keys()),
        help=(
            "Which reports to scrape. Default: the ones reachable un-gated. "
            f"Never obtainable without a captcha: {', '.join(sorted(UNAVAILABLE_REPORTS))}"
        ),
    )
    parser.add_argument("--delay-sec", type=float, default=2.0, help="Delay between requests (>=2s, be polite)")
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    return run_for_state(
        state_name=args.state_name,
        state_code=args.state_code,
        fin_year=args.fin_year,
        reports=args.reports,
        delay_sec=args.delay_sec,
    )


if __name__ == "__main__":
    sys.exit(main())
