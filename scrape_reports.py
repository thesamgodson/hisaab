"""
Unified MGNREGA report scraper via MIS portal.

Uses Playwright headless browser to:
1. Navigate to the MIS report portal (nreganarep.nic.in)
2. Solve the client-side captcha (answer is in a hidden field)
3. Select financial year and state to generate Digest-authenticated URLs
4. Fetch report pages and parse district-level HTML tables

Reports scraped:
- Financial Misappropriation Recovery (R.9.2.6)
- FTO Status Report (R8)
- FTO Pendency Day-wise (R8)
- Social Audit Issues Reported by Category (R.9.2.3)

Output: JSON files in data/curated/ with raw HTML snapshots in data/raw/.
"""

from __future__ import annotations

import argparse
import html as htmllib
import json
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

MIS_URL = "https://nreganarep.nic.in/netnrega/MISreport4.aspx"

ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
CURATED_DIR = DATA_DIR / "curated"
META_DIR = DATA_DIR / "metadata"
LOG_DIR = DATA_DIR / "logs"


@dataclass(frozen=True)
class ReportURL:
    name: str
    url: str
    pattern: str


@dataclass(frozen=True)
class StateConfig:
    state_name: str
    state_code: str
    mis_option_value: str  # e.g. "29RTNY" for Tamil Nadu


# Known MIS dropdown values per state. Extend as needed.
# Format: {state_code}{R|S}{short_name}{Y}
# The MIS portal uses a specific encoding for each state.
STATE_CONFIGS: dict[str, StateConfig] = {}


REPORT_PATTERNS: dict[str, str] = {
    "misappropriation": r"SAU_FMRecoveryReport\.aspx",
    "fto_status": r"FTO/FTOReport\.aspx",
    "fto_pendency": r"FTO/fto_bnkwise\.aspx",
    "issues_reported": r"SA-CatWise-IssueReported\.aspx",
    "financial_statement": r"fundstreportMtemp\.aspx",
}


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
# MIS Portal session
# ---------------------------------------------------------------------------
def discover_mis_option_value(page: Any, state_name: str) -> str | None:
    """Find the MIS dropdown option value for a state by name matching."""
    state_sel = page.locator("#ContentPlaceHolder1_ddl_States")
    options = state_sel.locator("option").all()
    for opt in options:
        txt = opt.text_content().strip().upper()
        if txt == state_name.upper():
            return opt.get_attribute("value")
    return None


def open_mis_session(page: Any, fin_year: str, state_name: str) -> dict[str, str]:
    """
    Navigate MIS portal, solve captcha, select year/state.
    Returns dict of {report_name: authenticated_url}.
    """
    page.goto(MIS_URL, timeout=30000)
    page.wait_for_timeout(3000)

    # Solve client-side captcha (answer is in hidden field)
    hf = page.locator('[id*="hfCaptcha"]').get_attribute("value")
    if not hf:
        raise RuntimeError("Could not find captcha hidden field")

    page.locator('[id*="txtCaptcha"]').last.fill(hf)
    page.locator('[id*="btnLogin"]').click()
    page.wait_for_timeout(2000)

    # Select financial year
    page.locator("#ContentPlaceHolder1_ddlfinyr").select_option(fin_year)
    page.wait_for_timeout(500)

    # Find and select state
    option_value = discover_mis_option_value(page, state_name)
    if not option_value:
        raise RuntimeError(f"State '{state_name}' not found in MIS dropdown")

    page.locator("#ContentPlaceHolder1_ddl_States").select_option(option_value)
    page.wait_for_timeout(3000)

    # Extract all report URLs with Digest tokens
    content = page.content()
    report_urls: dict[str, str] = {}

    for name, pattern in REPORT_PATTERNS.items():
        for m in re.finditer(
            rf'href="(https://mnregaweb4\.nic\.in[^"]*{pattern}[^"]*)"', content
        ):
            url = htmllib.unescape(m.group(1))
            if name not in report_urls:
                report_urls[name] = url

    return report_urls


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

        record["amount_unrecovered"] = round(
            record["amount_to_recover"] - record["amount_recovered"], 2
        )
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

    # Extract header labels for day ranges
    # Typical: 1-7 Days, 8-15 Days, 16-30 Days, > 30 Days (repeated for different account types)
    day_ranges = []
    for row in rows[:4]:
        cells = row.find_all(["th", "td"])
        texts = [c.get_text(strip=True) for c in cells]
        if any("Days" in t for t in texts):
            day_ranges = texts
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


# Reports that use DataTables client-side pagination — need page size expansion
DATATABLES_REPORTS = {"issues_reported"}


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
    curated_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    latest_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

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
    from playwright.sync_api import sync_playwright

    ensure_dirs()
    run_id = now_utc().strftime("%Y%m%d_%H%M%S")
    state_slug = slugify(state_name)

    print(f"Opening MIS portal for {state_name} (FY {fin_year})...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            report_urls = open_mis_session(page, fin_year, state_name)
        except Exception as exc:
            print(f"Failed to open MIS session: {exc}")
            append_run_log({
                "run_id": run_id,
                "state": state_name,
                "status": "failed_session",
                "error": str(exc),
                "timestamp": utc_iso(),
            })
            browser.close()
            return 2

        print(f"Found {len(report_urls)} report URLs with valid Digest tokens")
        for name, url in report_urls.items():
            print(f"  {name}: {url[:100]}...")

        results: dict[str, dict[str, Any]] = {}

        for report_name in reports:
            if report_name not in report_urls:
                print(f"\n  {report_name}: URL not found in MIS portal")
                continue

            url = report_urls[report_name]
            parser = PARSERS.get(report_name)
            if not parser:
                print(f"\n  {report_name}: No parser available")
                continue

            print(f"\n  Fetching {report_name}...")
            time.sleep(delay_sec)

            try:
                page.goto(url, timeout=30000)
                page.wait_for_timeout(5000)

                # Expand DataTables pagination to show all rows
                if report_name in DATATABLES_REPORTS:
                    try:
                        expanded = page.evaluate('''() => {
                            const selects = document.querySelectorAll('select');
                            for (const s of selects) {
                                const opts = Array.from(s.options).map(o => o.value);
                                if (opts.includes('100')) {
                                    s.value = '100';
                                    s.dispatchEvent(new Event('change'));
                                    return true;
                                }
                            }
                            return false;
                        }''')
                        if expanded:
                            page.wait_for_timeout(3000)
                    except Exception:
                        pass  # Not a DataTables page, continue

                html = page.content()
            except Exception as exc:
                print(f"    Failed to fetch: {exc}")
                results[report_name] = {"status": "failed_fetch", "error": str(exc)}
                continue

            tampered = "url tampered" in html.lower()
            if tampered:
                print(f"    URL Tampered response — Digest token may have expired")
                results[report_name] = {"status": "tampered"}
                continue

            records = parser(html, state_name, state_code, url)
            paths = save_report(report_name, state_slug, run_id, html, records, url)

            print(f"    Parsed {len(records)} district records")
            print(f"    Saved: {paths['latest']}")

            results[report_name] = {
                "status": "success" if records else "empty",
                "record_count": len(records),
                "paths": paths,
            }

        browser.close()

    # Summary
    print(f"\n{'=' * 60}")
    print(f"Run complete: {state_name} (FY {fin_year})")
    print(f"Run ID: {run_id}")
    for name, result in results.items():
        status = result.get("status", "unknown")
        count = result.get("record_count", 0)
        print(f"  {name}: {status} ({count} records)")

    append_run_log({
        "run_id": run_id,
        "state": state_name,
        "state_code": state_code,
        "fin_year": fin_year,
        "results": results,
        "timestamp": utc_iso(),
    })

    failed = sum(1 for r in results.values() if r.get("status") not in ("success",))
    return 0 if failed == 0 else 1


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scrape MGNREGA reports via MIS portal (Playwright headless)"
    )
    parser.add_argument("--state-name", default="TAMIL NADU")
    parser.add_argument("--state-code", default="29")
    parser.add_argument("--fin-year", default="2024-2025")
    parser.add_argument(
        "--reports",
        nargs="+",
        default=["misappropriation", "fto_status", "fto_pendency", "issues_reported", "financial_statement"],
        choices=list(REPORT_PATTERNS.keys()),
        help="Which reports to scrape",
    )
    parser.add_argument("--delay-sec", type=float, default=2.0, help="Delay between report fetches")
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
