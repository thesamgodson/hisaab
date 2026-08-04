"""
PMGSY (Pradhan Mantri Gram Sadak Yojana) scraper.

Scrapes rural road construction data from pmgsy.dord.gov.in using Playwright.
The portal uses SSRS (SQL Server Reporting Services) for reports served via
MvcReportViewer.aspx.  We navigate to the SSRS report URL, wait for it to
render, then export as CSV.  District names are absent from the CSV but rows
appear in alphabetical order matching the district catalog, so we zip them.

Reports scraped:
- District Brief (district-level road construction detail per scheme/year)

Output: JSON files in data/curated/ with raw CSV snapshots in data/raw/.

Usage:
    python scrape_pmgsy.py --states "BIHAR"
    python scrape_pmgsy.py --states "BIHAR,RAJASTHAN" --delay-sec 5
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

try:
    from scrapers.io_utils import atomic_write_json
except ImportError:
    from io_utils import atomic_write_json

BASE_URL = "https://pmgsy.dord.gov.in"

ROOT_DIR = Path(__file__).resolve().parent.parent  # repo root (scrapers/ is a package)
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
CURATED_DIR = DATA_DIR / "curated"
META_DIR = DATA_DIR / "metadata"
LOG_DIR = DATA_DIR / "logs"
CATALOG_DIR = DATA_DIR / "catalog"


@dataclass(frozen=True)
class PmgsyStateConfig:
    state_name: str
    pmgsy_state_id: str


def now_utc() -> datetime:
    return datetime.now(UTC)


def utc_iso() -> str:
    return now_utc().isoformat()


def slugify(text: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower())
    return value.strip("-") or "unknown"


def ensure_dirs() -> None:
    for d in (DATA_DIR, RAW_DIR, CURATED_DIR, META_DIR, LOG_DIR, CATALOG_DIR):
        d.mkdir(parents=True, exist_ok=True)


def parse_amount(raw: str) -> float:
    cleaned = raw.replace(",", "").replace("₹", "").replace('"', "").strip()
    cleaned = re.sub(r"[^0-9.\-]", "", cleaned)
    try:
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0


# ---------------------------------------------------------------------------
# Catalog loading
# ---------------------------------------------------------------------------
def load_catalog() -> dict[str, PmgsyStateConfig]:
    """Load PMGSY geo catalog. Returns {STATE_NAME_UPPER: PmgsyStateConfig}."""
    catalog_path = CATALOG_DIR / "pmgsy_geo.json"
    if not catalog_path.exists():
        return {}

    data = json.loads(catalog_path.read_text(encoding="utf-8"))
    states_list = data.get("states", [])
    configs: dict[str, PmgsyStateConfig] = {}
    for s in states_list:
        name = s["state_name"].upper()
        config = PmgsyStateConfig(
            state_name=s["state_name"],
            pmgsy_state_id=s["pmgsy_state_id"],
        )
        configs[name] = config
        normalized = re.sub(r"\s*\(UT\)\s*$", "", name)
        if normalized != name:
            configs[normalized] = config
        alt = normalized.replace(" AND ", " & ")
        if alt != normalized:
            configs[alt] = config
    return configs


def fetch_districts(state_id: str) -> list[dict[str, str]]:
    """Fetch district list for a state from PMGSY API (alphabetically sorted)."""
    url = f"{BASE_URL}/Home/PopulateDistricts"
    resp = requests.post(url, data={"stateCode": state_id}, timeout=30)
    resp.raise_for_status()
    items = resp.json()
    # Filter out "All Districts" (Value=0) and return sorted
    districts = [{"name": d["Text"], "id": d["Value"]} for d in items if d["Value"] != "0"]
    return sorted(districts, key=lambda d: d["name"])


# ---------------------------------------------------------------------------
# SSRS Report URLs
# ---------------------------------------------------------------------------
def district_brief_ssrs_url(state_id: str) -> str:
    """Build the SSRS iframe URL for District Brief (state-level, all districts)."""
    return (
        f"{BASE_URL}/MvcReportViewer.aspx"
        f"?_r=%2fPMGSYCitizen%2fDistrictBriefDetailsNew"
        f"&Level=2&STATE={state_id}&DISTRICT=0"
        f"&PMGSY=0&BLOCK=0&ROADSTATUS=0&SCHEME=0&CYEAR=2025"
    )


# ---------------------------------------------------------------------------
# CSV Parsing
# ---------------------------------------------------------------------------
def extract_state_totals(
    csv_text: str,
    state_name: str,
    source_url: str,
) -> list[dict[str, Any]]:
    """Extract state-level totals from the SSRS CSV.

    State totals appear in columns 9-16 of every data row (repeated).
    They represent cumulative totals across all years and districts.
    """
    lines = csv_text.strip().split("\n")
    for line in lines:
        if not re.match(r"\d{4}-\d{4}", line.strip()):
            continue
        reader = csv.reader(io.StringIO(line))
        for row in reader:
            if len(row) >= 17:
                return [
                    {
                        "state": state_name,
                        "state_code": "",
                        "fin_year": "cumulative",
                        "roads_completed": round(parse_amount(row[13])),
                        "length_completed_km": round(parse_amount(row[14]), 2),
                        "habitations_connected": round(parse_amount(row[15])),
                        "expenditure_programme_cr": round(parse_amount(row[16]), 2),
                        "expenditure_admin_cr": 0.0,
                        "source_url": source_url,
                        "scraped_at": utc_iso(),
                    }
                ]
    return []


def parse_district_csv(
    csv_text: str,
    districts: list[dict[str, str]],
    state_name: str,
    source_url: str,
) -> list[dict[str, Any]]:
    """Parse SSRS CSV export of District Brief into per-district records.

    The CSV has year-level rows grouped by scheme (PMGSY-I, PMGSY-II, etc.).
    Within each year group, rows are in alphabetical district order (matching
    the districts list).  We aggregate sanctioned/completed totals per district.
    """
    lines = csv_text.strip().split("\n")
    n_districts = len(districts)
    if n_districts == 0:
        return []

    # Find all scheme data sections (start with IMS_YEAR header)
    scheme_sections: list[tuple[str, int]] = []
    scheme_names = ["PMGSY-I", "PMGSY-II", "PMGSY-III", "RCPLWEA", "PMGSY-IV", "VVP", "PM-JANMAN"]
    for i, line in enumerate(lines):
        if line.startswith("IMS_YEAR"):
            scheme_idx = len(scheme_sections)
            scheme_name = scheme_names[scheme_idx] if scheme_idx < len(scheme_names) else f"Scheme-{scheme_idx + 1}"
            scheme_sections.append((scheme_name, i))

    # Aggregate per district: sum across all years and schemes
    district_totals: dict[str, dict[str, float]] = {}
    for d in districts:
        district_totals[d["name"]] = {
            "roads_sanctioned": 0.0,
            "roads_completed": 0.0,
            "length_sanctioned_km": 0.0,
            "length_completed_km": 0.0,
            "lsbs_sanctioned": 0.0,
            "lsbs_completed": 0.0,
            "value_of_projects_cr": 0.0,
            "expenditure_cr": 0.0,
        }

    for sec_idx, (_scheme_name, header_line_idx) in enumerate(scheme_sections):
        # Determine end of this section
        end_idx = scheme_sections[sec_idx + 1][1] if sec_idx + 1 < len(scheme_sections) else len(lines)

        # Parse data rows (lines after header that start with a year like 2000-2001)
        data_rows: list[list[str]] = []
        for line_idx in range(header_line_idx + 1, end_idx):
            line = lines[line_idx].strip()
            if re.match(r"\d{4}-\d{4}", line):
                reader = csv.reader(io.StringIO(line))
                for row in reader:
                    data_rows.append(row)

        if not data_rows:
            continue

        # Group by year, then assign districts by position within each year.
        # Districts in the CSV are alphabetical.  Because states reorganise
        # (new districts carved out), older years may have fewer rows than
        # the current district count.  We accept any year group whose size
        # exactly matches n_districts OR matches a "stable" historical count
        # (the most common group size in this section, if it differs).
        year_groups: dict[str, list[list[str]]] = {}
        for row in data_rows:
            year = row[0]
            year_groups.setdefault(year, []).append(row)

        # Determine acceptable group sizes
        from collections import Counter

        size_counts = Counter(len(rows) for rows in year_groups.values())
        most_common_size = size_counts.most_common(1)[0][0] if size_counts else 0
        acceptable_sizes = {n_districts}
        if most_common_size > 0:
            acceptable_sizes.add(most_common_size)

        for _year, rows in year_groups.items():
            n_rows = len(rows)
            if n_rows not in acceptable_sizes:
                continue
            # Only map positions up to min(n_rows, n_districts)
            mappable = min(n_rows, n_districts)
            for dist_idx in range(mappable):
                row = rows[dist_idx]
                dist_name = districts[dist_idx]["name"]
                totals = district_totals[dist_name]

                # CSV columns for main section (IMS_YEAR):
                # 0:Year, 1:RoadsSanctioned, 2:LengthSanctioned, 3:LSBsSanctioned,
                # 4:VoP, 5:RoadsCompleted, 6:LengthCompleted, 7:LSBsCompleted, 8:Expenditure
                if len(row) >= 9:
                    totals["roads_sanctioned"] += parse_amount(row[1])
                    totals["length_sanctioned_km"] += parse_amount(row[2])
                    totals["lsbs_sanctioned"] += parse_amount(row[3])
                    totals["value_of_projects_cr"] += parse_amount(row[4])
                    totals["roads_completed"] += parse_amount(row[5])
                    totals["length_completed_km"] += parse_amount(row[6])
                    totals["lsbs_completed"] += parse_amount(row[7])
                    totals["expenditure_cr"] += parse_amount(row[8])

    # Build output records
    scraped_at = utc_iso()
    records: list[dict[str, Any]] = []
    for d in districts:
        totals = district_totals[d["name"]]
        # Only include districts that have non-zero data
        if totals["roads_sanctioned"] == 0 and totals["expenditure_cr"] == 0:
            continue
        records.append(
            {
                "district": d["name"],
                "state": state_name,
                "state_code": "",
                "fin_year": "cumulative",
                "scheme": "All",
                "roads_sanctioned": round(totals["roads_sanctioned"]),
                "roads_completed": round(totals["roads_completed"]),
                "length_sanctioned_km": round(totals["length_sanctioned_km"], 2),
                "length_completed_km": round(totals["length_completed_km"], 2),
                "habitations_covered": round(totals["lsbs_completed"]),
                "value_of_projects_cr": round(totals["value_of_projects_cr"], 2),
                "expenditure_cr": round(totals["expenditure_cr"], 2),
                "source_url": source_url,
                "scraped_at": scraped_at,
            }
        )

    return records


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------
def save_report(
    report_name: str,
    state_slug: str,
    run_id: str,
    raw_text: str,
    records: list[dict[str, Any]],
    source_url: str,
) -> dict[str, str]:
    raw_path = RAW_DIR / f"{report_name}_{state_slug}_{run_id}.csv"
    curated_path = CURATED_DIR / f"{report_name}_{state_slug}_{run_id}.json"
    latest_path = CURATED_DIR / f"{report_name}_{state_slug}_latest.json"

    raw_path.write_text(raw_text, encoding="utf-8")
    # Only touch the curated JSON files when the parse produced records — an
    # empty parse (portal layout change, mid-scrape failure) must never
    # truncate the last known-good "latest" snapshot.
    atomic_write_json(curated_path, records)
    atomic_write_json(latest_path, records)

    return {
        "raw": str(raw_path),
        "curated": str(curated_path),
        "latest": str(latest_path),
    }


def append_run_log(entry: dict[str, Any]) -> None:
    fp = LOG_DIR / "pmgsy_runs.ndjson"
    with fp.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Scrape District Brief via Playwright + CSV export
# ---------------------------------------------------------------------------
def scrape_district_brief(
    page: Any,
    state_id: str,
    state_name: str,
    run_id: str,
    districts: list[dict[str, str]],
) -> dict[str, Any]:
    """Navigate to SSRS report, wait for render, export CSV, parse."""
    state_slug = slugify(state_name)
    ssrs_url = district_brief_ssrs_url(state_id)

    print("\n  Fetching District Brief (SSRS CSV export)...")
    print(f"    URL: {ssrs_url}")

    page.goto(ssrs_url, timeout=60000)
    # SSRS reports take time to render — wait for the export links to appear
    page.wait_for_timeout(15000)

    # Check if report rendered (look for export function)
    has_export = page.evaluate("""() => {
        try { return typeof $find === 'function' && $find('ReportViewer') !== null; }
        catch(e) { return false; }
    }""")

    if not has_export:
        # Wait more
        page.wait_for_timeout(10000)
        has_export = page.evaluate("""() => {
            try { return typeof $find === 'function' && $find('ReportViewer') !== null; }
            catch(e) { return false; }
        }""")

    if not has_export:
        print("    SSRS report did not render (no ReportViewer found)")
        return {"status": "render_failed"}

    # Export as CSV
    try:
        with page.expect_download(timeout=60000) as download_info:
            page.evaluate("$find('ReportViewer').exportReport('CSV');")
        download = download_info.value
        csv_path = f"/tmp/pmgsy_{state_slug}_{run_id}.csv"
        download.save_as(csv_path)
        csv_text = Path(csv_path).read_text(encoding="utf-8-sig")
    except Exception as exc:
        print(f"    CSV export failed: {exc}")
        return {"status": "export_failed", "error": str(exc)}

    print(f"    CSV downloaded: {len(csv_text)} bytes")

    records = parse_district_csv(csv_text, districts, state_name, ssrs_url)
    paths = save_report("pmgsy_district", state_slug, run_id, csv_text, records, ssrs_url)
    print(f"    Parsed {len(records)} district records")
    print(f"    Saved: {paths['latest']}")

    # Also extract and save state-level progress
    progress = extract_state_totals(csv_text, state_name, ssrs_url)
    if progress:
        progress_paths = save_report("pmgsy_progress", state_slug, run_id, csv_text, progress, ssrs_url)
        print(
            f"    State progress: {progress[0]['roads_completed']} roads, "
            f"{progress[0]['length_completed_km']} km, "
            f"{progress[0]['expenditure_programme_cr']} Cr"
        )
        print(f"    Saved: {progress_paths['latest']}")

    return {
        "status": "success" if records else "empty",
        "record_count": len(records),
        "paths": paths,
    }


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------
def run_for_state(
    state_name: str,
    pmgsy_state_id: str,
    delay_sec: float = 3.0,
) -> int:
    from playwright.sync_api import sync_playwright

    ensure_dirs()
    run_id = now_utc().strftime("%Y%m%d_%H%M%S")

    print(f"Scraping PMGSY data for {state_name} (id={pmgsy_state_id})...")

    # Fetch district list for positional mapping
    print("  Fetching district catalog from API...")
    try:
        districts = fetch_districts(pmgsy_state_id)
        print(f"    Got {len(districts)} districts")
    except Exception as exc:
        print(f"    Failed to fetch districts: {exc}")
        return 1

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        result = scrape_district_brief(page, pmgsy_state_id, state_name, run_id, districts)

        browser.close()

    # Summary
    print(f"\n{'=' * 60}")
    print(f"PMGSY run complete: {state_name}")
    print(f"Run ID: {run_id}")
    status = result.get("status", "unknown")
    count = result.get("record_count", 0)
    print(f"  pmgsy_district: {status} ({count} records)")

    append_run_log(
        {
            "run_id": run_id,
            "state": state_name,
            "pmgsy_state_id": pmgsy_state_id,
            "result": result,
            "timestamp": utc_iso(),
        }
    )

    return 0 if status == "success" else 1


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scrape PMGSY rural road data (Playwright headless + CSV export)")
    parser.add_argument(
        "--states",
        type=str,
        default="",
        help="Comma-separated state names (e.g. 'BIHAR,RAJASTHAN')",
    )
    parser.add_argument("--delay-sec", type=float, default=3.0)
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()

    catalog = load_catalog()
    if not catalog:
        print("No PMGSY catalog found. Run scrape_pmgsy_catalog.py first.")
        return 1

    state_names = [s.strip().upper() for s in args.states.split(",")] if args.states else list(catalog.keys())

    failed_count = 0
    for i, name in enumerate(state_names, 1):
        config = catalog.get(name)
        if not config:
            print(f"[{i}/{len(state_names)}] {name}: not found in PMGSY catalog, skipping")
            failed_count += 1
            continue

        print(f"\n[{i}/{len(state_names)}] {name}")
        exit_code = run_for_state(
            state_name=config.state_name,
            pmgsy_state_id=config.pmgsy_state_id,
            delay_sec=args.delay_sec,
        )
        if exit_code != 0:
            failed_count += 1

        if i < len(state_names):
            time.sleep(args.delay_sec)

    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
