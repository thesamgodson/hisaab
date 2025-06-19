"""
DAY-NRLM (National Rural Livelihoods Mission) scraper.

Scrapes SHG (Self-Help Group) formation and revolving fund (RF) data from
nrlm.gov.in using Playwright. The portal uses JavaScript-driven drill-downs
that require a real browser to interact with.

Reports scraped:
  G1 — SHG formation: state/district counts (new, revived, pre-NRLM, total)
        and total member count.
  F1a — RF disbursement: SHGs provided revolving fund and amount (Rs in lakh)
         by district.

Data is cumulative (no fin_year breakdown on the portal).

Output: data/curated/nrlm_district_all_latest.json

Usage:
    python scrape_nrlm.py                         # All states
    python scrape_nrlm.py --states "BIHAR"        # Single state
    python scrape_nrlm.py --states "BIHAR,TAMIL NADU"
    python scrape_nrlm.py --skip-rf               # SHG data only, no RF drill-down
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
CURATED_DIR = DATA_DIR / "curated"

SHG_REPORT_URL = "https://nrlm.gov.in/shgOuterReports.do?methodName=showShgreport"
RF_REPORT_URL = "https://nrlm.gov.in/RevolvingFundDisbursementAction.do?methodName=showView"

CURATED_FILENAME = "nrlm_district_all_latest.json"

# Wait times in ms
WAIT_AFTER_CLICK = 3000
WAIT_AFTER_NAVIGATE = 5000
PAGE_TIMEOUT = 30000


def utc_iso() -> str:
    return datetime.now(UTC).isoformat()


def state_slug(name: str) -> str:
    return name.lower().replace(" ", "-").replace("&", "and").replace("/", "-")


def ensure_dirs() -> None:
    for d in (RAW_DIR, CURATED_DIR):
        d.mkdir(parents=True, exist_ok=True)


def _parse_int(text: str) -> int:
    """Parse a number string, handling commas and empty/dash values."""
    cleaned = str(text).strip().replace(",", "").replace(" ", "")
    if not cleaned or cleaned in ("-", "N/A", "NA", "0"):
        return 0
    try:
        return int(float(cleaned))
    except ValueError:
        return 0


def _parse_float(text: str) -> float:
    """Parse a float string, handling commas and empty/dash values."""
    cleaned = str(text).strip().replace(",", "").replace(" ", "")
    if not cleaned or cleaned in ("-", "N/A", "NA"):
        return 0.0
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


@dataclass
class StateEntry:
    state_id: str
    state_name: str


@dataclass
class ShgRecord:
    district: str
    state: str
    state_code: str
    shgs_new: int
    shgs_revived: int
    shgs_pre_nrlm: int
    shgs_total: int
    members_total: int
    source_url: str
    scraped_at: str
    fin_year: str = "cumulative"
    rf_shgs_provided: int = 0
    rf_amount_lakhs: float = 0.0


def to_dict(r: ShgRecord) -> dict[str, Any]:
    return {
        "district": r.district,
        "state": r.state,
        "state_code": r.state_code,
        "fin_year": r.fin_year,
        "shgs_total": r.shgs_total,
        "shgs_new": r.shgs_new,
        "shgs_revived": r.shgs_revived,
        "shgs_pre_nrlm": r.shgs_pre_nrlm,
        "members_total": r.members_total,
        "rf_shgs_provided": r.rf_shgs_provided,
        "rf_amount_lakhs": r.rf_amount_lakhs,
        "source_url": r.source_url,
        "scraped_at": r.scraped_at,
    }


async def _get_state_list(page: Any) -> list[StateEntry]:
    """Parse the state-level G1 table to extract state IDs and names."""
    rows = await page.query_selector_all("table tr")
    states: list[StateEntry] = []

    for row in rows:
        cells = await row.query_selector_all("td")
        if len(cells) < 2:
            continue

        # Look for cells containing javascript:districtList calls
        onclick_el = await row.query_selector("td a[href*='districtList']")
        if not onclick_el:
            # Also check for onclick in the row itself or any td
            onclick_el = await row.query_selector("[onclick*='districtList']")

        if not onclick_el:
            continue

        href = await onclick_el.get_attribute("href") or ""
        onclick = await onclick_el.get_attribute("onclick") or ""
        js_src = href if "districtList" in href else onclick

        # Extract: javascript:districtList('05','BIHAR')
        # or onclick="districtList('05','BIHAR')"
        import re

        match = re.search(r"districtList\s*\(\s*'([^']+)'\s*,\s*'([^']+)'\s*\)", js_src)
        if not match:
            continue

        state_id = match.group(1).strip()
        state_name = match.group(2).strip().upper()
        if state_id and state_name:
            states.append(StateEntry(state_id=state_id, state_name=state_name))

    return states


async def _parse_district_table(
    page: Any,
    state: StateEntry,
    source_url: str,
    scraped_at: str,
) -> list[ShgRecord]:
    """Parse district rows from the currently-rendered G1 table."""
    # DataTable defaults to 10 rows — show all by setting length to 100
    await page.evaluate(
        """() => {
            var sel = document.querySelector('select[name="example_length"]');
            if (sel) { sel.value = '100'; sel.dispatchEvent(new Event('change')); }
            if (typeof jQuery !== 'undefined' && jQuery.fn.DataTable) {
                try { jQuery('#example').DataTable().page.len(100).draw(); } catch(e) {}
            }
        }""",
    )
    await page.wait_for_timeout(1000)

    records: list[ShgRecord] = []
    rows = await page.query_selector_all("table#example tr, table tr")

    for row in rows:
        cells = await row.query_selector_all("td")
        if len(cells) < 7:
            continue

        texts = [(await c.inner_text()).strip() for c in cells]

        # Skip header, total, and grand-total rows
        first = texts[0].lower()
        if not first or first in ("sl.no", "s.no", "sno", "#"):
            continue

        # Row format varies but typically:
        # [serial, district, new_shgs, revived_shgs, pre_nrlm_shgs, total_shgs, members]
        # Some tables have an extra column; detect by checking if col 0 is a number
        if not texts[0].replace(".", "").isdigit():
            continue

        district_name = texts[1].strip().upper()
        if not district_name or district_name.lower() in (
            "total",
            "grand total",
            "state total",
        ):
            continue

        # Flexible column mapping: find total_shgs as the largest plausible column
        # Typical ordering: serial | district | new | revived | pre_nrlm | total | members
        if len(texts) >= 7:
            shgs_new = _parse_int(texts[2])
            shgs_revived = _parse_int(texts[3])
            shgs_pre_nrlm = _parse_int(texts[4])
            shgs_total = _parse_int(texts[5])
            members_total = _parse_int(texts[6])
        elif len(texts) >= 6:
            # Condensed table without pre-NRLM breakdown
            shgs_new = _parse_int(texts[2])
            shgs_revived = _parse_int(texts[3])
            shgs_pre_nrlm = 0
            shgs_total = _parse_int(texts[4])
            members_total = _parse_int(texts[5])
        else:
            continue

        records.append(
            ShgRecord(
                district=district_name,
                state=state.state_name,
                state_code=state.state_id,
                shgs_new=shgs_new,
                shgs_revived=shgs_revived,
                shgs_pre_nrlm=shgs_pre_nrlm,
                shgs_total=shgs_total,
                members_total=members_total,
                source_url=source_url,
                scraped_at=scraped_at,
            )
        )

    return records


async def _parse_rf_district_table(
    page: Any,
    state: StateEntry,
) -> dict[str, tuple[int, float]]:
    """
    Parse RF disbursement district table.

    Returns a mapping of district_name -> (rf_shgs_provided, rf_amount_lakhs).
    """
    result: dict[str, tuple[int, float]] = {}
    # Expand DataTable pagination
    await page.evaluate(
        """() => {
            var sel = document.querySelector('select[name="example_length"]');
            if (sel) { sel.value = '100'; sel.dispatchEvent(new Event('change')); }
            if (typeof jQuery !== 'undefined' && jQuery.fn.DataTable) {
                try { jQuery('#example').DataTable().page.len(100).draw(); } catch(e) {}
            }
        }""",
    )
    await page.wait_for_timeout(1000)
    rows = await page.query_selector_all("table tr")

    for row in rows:
        cells = await row.query_selector_all("td")
        if len(cells) < 4:
            continue

        texts = [(await c.inner_text()).strip() for c in cells]

        first = texts[0].lower()
        if not first or not texts[0].replace(".", "").isdigit():
            continue

        district_name = texts[1].strip().upper()
        if not district_name or district_name.lower() in (
            "total",
            "grand total",
            "state total",
        ):
            continue

        # RF table format: serial | district | no_of_shgs | amount (lakh)
        # Some tables may have multiple fund-source columns — sum them
        if len(texts) >= 4:
            rf_shgs = _parse_int(texts[2])
            rf_amount = _parse_float(texts[-1])  # Last column is typically total
        else:
            continue

        result[district_name] = (rf_shgs, rf_amount)

    return result


async def scrape_shg_state(
    page: Any,
    state: StateEntry,
    scraped_at: str,
) -> list[ShgRecord]:
    """Trigger district drill-down for one state and parse its table."""
    try:
        await page.evaluate(
            "(args) => { districtList(args[0], args[1]); }",
            [state.state_id, state.state_name],
        )
        await page.wait_for_timeout(WAIT_AFTER_CLICK)
    except Exception as exc:
        print(f"    JS evaluation failed for {state.state_name}: {exc}")
        return []

    records = await _parse_district_table(
        page,
        state,
        source_url=SHG_REPORT_URL,
        scraped_at=scraped_at,
    )
    return records


async def scrape_rf_state(
    page: Any,
    state: StateEntry,
) -> dict[str, tuple[int, float]]:
    """Trigger RF district drill-down for one state and parse the table."""
    try:
        await page.evaluate(
            "(args) => { getDetail(args[0], args[1]); }",
            [state.state_id, state.state_name],
        )
        await page.wait_for_timeout(WAIT_AFTER_CLICK)
    except Exception as exc:
        print(f"    RF JS failed for {state.state_name}: {exc}")
        return {}

    return await _parse_rf_district_table(page, state)


async def _merge_rf_data(
    records: list[ShgRecord],
    rf_map: dict[str, tuple[int, float]],
) -> list[ShgRecord]:
    """Return new list of ShgRecords with RF fields filled from rf_map."""
    merged: list[ShgRecord] = []
    for r in records:
        rf_shgs, rf_amount = rf_map.get(r.district, (0, 0.0))
        merged.append(
            ShgRecord(
                district=r.district,
                state=r.state,
                state_code=r.state_code,
                fin_year=r.fin_year,
                shgs_new=r.shgs_new,
                shgs_revived=r.shgs_revived,
                shgs_pre_nrlm=r.shgs_pre_nrlm,
                shgs_total=r.shgs_total,
                members_total=r.members_total,
                rf_shgs_provided=rf_shgs,
                rf_amount_lakhs=rf_amount,
                source_url=r.source_url,
                scraped_at=r.scraped_at,
            )
        )
    return merged


async def scrape_all_states(
    states_filter: list[str] | None = None,
    include_rf: bool = True,
    delay_sec: int = 2,
) -> list[dict[str, Any]]:
    """
    Scrape SHG and optional RF data for all (or filtered) states.

    Returns list of record dicts ready for JSON serialisation.
    """
    from playwright.async_api import async_playwright

    ensure_dirs()
    scraped_at = utc_iso()
    all_records: list[ShgRecord] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # ── Step 1: SHG formation data ────────────────────────────────────
        print("  Loading SHG G1 report page...")
        page = await browser.new_page()
        try:
            await page.goto(SHG_REPORT_URL, timeout=PAGE_TIMEOUT)
            await page.wait_for_load_state("networkidle", timeout=PAGE_TIMEOUT)
            await page.wait_for_timeout(WAIT_AFTER_NAVIGATE)
        except Exception as exc:
            print(f"  Failed to load G1 page: {exc}")
            await browser.close()
            return []

        states = await _get_state_list(page)
        print(f"  Found {len(states)} states on G1 report")

        if not states:
            print("  No states found — page structure may have changed")
            # Save raw HTML for debugging
            raw_html = await page.content()
            debug_path = RAW_DIR / "nrlm_g1_debug.html"
            debug_path.write_text(raw_html, encoding="utf-8")
            print(f"  Saved raw HTML to {debug_path}")
            await browser.close()
            return []

        if states_filter:
            upper_filter = {s.upper() for s in states_filter}
            states = [s for s in states if s.state_name.upper() in upper_filter]
            print(f"  Filtered to {len(states)} states")

        for state in states:
            print(f"    Scraping SHG data: {state.state_name} (id={state.state_id})...")
            records = await scrape_shg_state(page, state, scraped_at)
            print(f"      {len(records)} districts parsed")
            all_records.extend(records)

            if delay_sec > 0 and state is not states[-1]:
                await asyncio.sleep(delay_sec)

        await page.close()

        # ── Step 2: RF disbursement data (optional) ───────────────────────
        if include_rf and all_records:
            print("\n  Loading RF F1a report page...")
            rf_page = await browser.new_page()
            try:
                await rf_page.goto(RF_REPORT_URL, timeout=PAGE_TIMEOUT)
                await rf_page.wait_for_load_state("networkidle", timeout=PAGE_TIMEOUT)
                await rf_page.wait_for_timeout(WAIT_AFTER_NAVIGATE)
            except Exception as exc:
                print(f"  Failed to load RF page: {exc}")
                await rf_page.close()
                await browser.close()
                return [to_dict(r) for r in all_records]

            # Build state lookup by name for RF merging
            states_for_rf = {r.state: StateEntry(state_id=r.state_code, state_name=r.state) for r in all_records}
            records_by_state: dict[str, list[ShgRecord]] = {}
            for r in all_records:
                records_by_state.setdefault(r.state, []).append(r)

            merged_all: list[ShgRecord] = []
            for state_name, state_records in records_by_state.items():
                se = states_for_rf[state_name]
                print(f"    Scraping RF data: {state_name}...")
                rf_map = await scrape_rf_state(rf_page, se)
                merged = await _merge_rf_data(state_records, rf_map)
                merged_all.extend(merged)
                if delay_sec > 0:
                    await asyncio.sleep(delay_sec)

            all_records = merged_all
            await rf_page.close()

        await browser.close()

    return [to_dict(r) for r in all_records]


def save_curated(records: list[dict[str, Any]]) -> Path:
    """Save all records to a single national JSON file."""
    path = CURATED_DIR / CURATED_FILENAME
    path.write_text(
        json.dumps(records, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape DAY-NRLM SHG formation and RF data")
    parser.add_argument(
        "--states",
        help="Comma-separated state names (default: all states)",
    )
    parser.add_argument(
        "--skip-rf",
        action="store_true",
        help="Skip revolving fund (F1a) drill-down — SHG data only",
    )
    parser.add_argument(
        "--delay-sec",
        type=int,
        default=2,
        help="Delay in seconds between state requests (default: 2)",
    )
    args = parser.parse_args()

    states_filter = [s.strip().upper() for s in args.states.split(",")] if args.states else None
    include_rf = not args.skip_rf

    label = f"{len(states_filter)} states" if states_filter else "all states"
    print(f"DAY-NRLM Scraper — {label}, RF={'yes' if include_rf else 'no'}")

    records = asyncio.run(
        scrape_all_states(
            states_filter=states_filter,
            include_rf=include_rf,
            delay_sec=args.delay_sec,
        )
    )

    if not records:
        print("No records scraped — check portal connectivity or page structure.")
        return 1

    path = save_curated(records)
    print(f"\nSaved {len(records)} district records → {path.name}")

    # Summary by state
    by_state: dict[str, int] = {}
    for r in records:
        by_state[r["state"]] = by_state.get(r["state"], 0) + 1
    print("\nBy state:")
    for state, count in sorted(by_state.items()):
        print(f"  {state}: {count} districts")

    return 0


if __name__ == "__main__":
    sys.exit(main())
