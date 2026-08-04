"""Scrape all current MLAs from MyNeta.info.

Downloads winners for all 31 state assembly elections and saves to
data/curated/mla_winners_all_latest.json.

MyNeta renders winner rows via obfuscated JavaScript, so Playwright is
required to execute the page before extracting data.

Responses are cached in data/raw/myneta/ to avoid re-scraping during
development.  Delete the cache directory to force a full re-fetch.

Usage:
    python scrapers/scrape_mla_myneta.py
    python scrapers/scrape_mla_myneta.py --state "TAMIL NADU"
    python scrapers/scrape_mla_myneta.py --dry-run
    python scrapers/scrape_mla_myneta.py --no-cache
"""

from __future__ import annotations

import argparse
import json
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = _PROJECT_ROOT / "data" / "curated" / "mla_winners_all_latest.json"
_CACHE_DIR = _PROJECT_ROOT / "data" / "raw" / "myneta"

# ---------------------------------------------------------------------------
# State election index
# ---------------------------------------------------------------------------

STATE_ELECTIONS: list[tuple[str, str, int]] = [
    ("ANDHRA PRADESH", "AndhraPradesh2024", 2024),
    ("ARUNACHAL PRADESH", "ArunachalPradesh2024", 2024),
    ("ASSAM", "assam2021", 2021),
    ("BIHAR", "Bihar2025", 2025),
    ("CHHATTISGARH", "chhattisgarh2023", 2023),
    ("DELHI", "Delhi2025", 2025),
    ("GOA", "goa2022", 2022),
    ("GUJARAT", "gujarat2022", 2022),
    ("HARYANA", "Haryana2024", 2024),
    ("HIMACHAL PRADESH", "himachalpradesh2022", 2022),
    ("JAMMU AND KASHMIR", "JammuKashmir2024", 2024),
    ("JHARKHAND", "Jharkhand2024", 2024),
    ("KARNATAKA", "Karnataka2023", 2023),
    ("KERALA", "kerala2021", 2021),
    ("MADHYA PRADESH", "MadhyaPradesh2023", 2023),
    ("MAHARASHTRA", "Maharashtra2024", 2024),
    ("MANIPUR", "manipur2022", 2022),
    ("MEGHALAYA", "meghalaya2023", 2023),
    ("MIZORAM", "mizoram2023", 2023),
    ("NAGALAND", "nagaland2023", 2023),
    ("ODISHA", "Odisha2024", 2024),
    ("PUDUCHERRY", "puducherry2021", 2021),
    ("PUNJAB", "punjab2022", 2022),
    ("RAJASTHAN", "rajasthan2023", 2023),
    ("SIKKIM", "Sikkim2024", 2024),
    ("TAMIL NADU", "tamilnadu2021", 2021),
    ("TELANGANA", "Telangana2023", 2023),
    ("TRIPURA", "tripura2023", 2023),
    ("UTTARAKHAND", "uttarakhand2022", 2022),
    ("UTTAR PRADESH", "UttarPradesh2022", 2022),
    ("WEST BENGAL", "westbengal2021", 2021),
]

# ---------------------------------------------------------------------------
# Asset parsing helper
# ---------------------------------------------------------------------------

_RS_RE = re.compile(r"Rs[\s\xa0]*([\d,]+)", re.IGNORECASE)


def _parse_rupees(text: str) -> int | None:
    """Convert MyNeta asset text to integer rupees.

    Examples:
        "Rs 1,34,59,578~ 1 Cr"  → 13459578
        "Rs 8,55,000~ 8 Lacs+"  → 855000
        "Rs 0~"                  → 0
    """
    if not text or text.strip() in ("", "Nil", "-"):
        return None
    m = _RS_RE.search(text)
    if m:
        digits = m.group(1).replace(",", "")
        try:
            return int(digits)
        except ValueError:
            pass
    return None


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------


def _cache_path(slug: str) -> Path:
    return _CACHE_DIR / f"{slug}_winners.json"


def _load_cache(slug: str) -> list[dict[str, Any]] | None:
    """Return cached rows if available, else None."""
    path = _cache_path(slug)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
    return None


def _save_cache(slug: str, rows: list[dict[str, Any]]) -> None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _cache_path(slug).write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Row extraction (shared between browser and test paths)
# ---------------------------------------------------------------------------

_RESERVATION_RE = re.compile(r"\s*\((?:SC|ST|GEN)\)\s*$")


def _parse_rows(
    table_rows: list[list[str]],
    state_name: str,
    year: int,
    source_url: str,
    scraped_at: str,
) -> list[dict[str, Any]]:
    """Convert a list of cell-text rows into MLA dicts.

    table_rows[0] must be the header row.
    """
    if len(table_rows) < 2:
        return []

    # Detect column positions from header
    header = [h.lower().strip() for h in table_rows[0]]
    col: dict[str, int] = {}
    for i, h in enumerate(header):
        if "candidate" in h:
            col.setdefault("candidate", i)
        elif "constituency" in h:
            col.setdefault("constituency", i)
        elif "party" in h:
            col.setdefault("party", i)
        elif "criminal" in h:
            col.setdefault("criminal", i)
        elif "education" in h:
            col.setdefault("education", i)
        elif "total asset" in h or ("asset" in h and "liab" not in h):
            col.setdefault("assets", i)
        elif "liabilit" in h:
            col.setdefault("liabilities", i)

    # Positional fallback
    col.setdefault("candidate", 1)
    col.setdefault("constituency", 2)
    col.setdefault("party", 3)
    col.setdefault("criminal", 4)
    col.setdefault("education", 5)
    col.setdefault("assets", 6)
    col.setdefault("liabilities", 7)

    results: list[dict[str, Any]] = []
    for cells in table_rows[1:]:
        if len(cells) < 4:
            continue

        def _get(key: str, default: str = "", _cells: list = cells) -> str:
            idx = col.get(key)
            if idx is None or idx >= len(_cells):
                return default
            return (_cells[idx] or "").strip()

        candidate = _get("candidate")
        constituency_raw = _get("constituency").upper()
        if not candidate or not constituency_raw:
            continue

        # Strip BYE ELECTION suffix — these are not the general election winners
        if "BYE EL" in constituency_raw or "BY EL" in constituency_raw:
            continue

        ac_name = _RESERVATION_RE.sub("", constituency_raw).strip()

        criminal_raw = _get("criminal", "0").split("\n")[0].strip()
        try:
            criminal_cases = int(criminal_raw) if criminal_raw.isdigit() else 0
        except ValueError:
            criminal_cases = 0

        results.append(
            {
                "ac_name": ac_name,
                "state": state_name,
                "mla_name": candidate.split("\n")[0].strip(),
                "party": _get("party").split("\n")[0].strip(),
                "elected_year": year,
                "criminal_cases": criminal_cases,
                "education": _get("education").split("\n")[0].strip(),
                "total_assets_rs": _parse_rupees(_get("assets")),
                "liabilities_rs": _parse_rupees(_get("liabilities")),
                "source_url": source_url,
                "scraped_at": scraped_at,
            }
        )
    return results


# ---------------------------------------------------------------------------
# Per-state scraper (Playwright)
# ---------------------------------------------------------------------------


def scrape_state(
    state_name: str,
    slug: str,
    year: int,
    use_cache: bool = True,
    page: Any = None,
) -> list[dict[str, Any]]:
    """Scrape winners for one state. Returns list of MLA dicts.

    page: an open playwright Page object (required when use_cache is False
          or no cache exists).
    """
    if use_cache:
        cached = _load_cache(slug)
        if cached is not None:
            return cached

    if page is None:
        raise RuntimeError(
            f"No cache for {slug} and no Playwright page provided. "
            "Pass a Playwright Page object or delete the cache."
        )

    url = (
        f"https://www.myneta.info/{slug}/index.php"
        "?action=show_winners&sort=default"
    )
    scraped_at = datetime.now(UTC).isoformat()

    page.goto(url, wait_until="networkidle", timeout=60_000)

    # Extract rows from all w3-bordered tables via JS
    raw_tables: list[list[list[str]]] = page.evaluate(
        """() => {
            const results = [];
            const tables = document.querySelectorAll('table.w3-bordered');
            tables.forEach(table => {
                const rows = [];
                table.querySelectorAll('tr').forEach(tr => {
                    const cells = [];
                    tr.querySelectorAll('th, td').forEach(cell => {
                        cells.push(cell.innerText.trim());
                    });
                    rows.push(cells);
                });
                results.push(rows);
            });
            return results;
        }"""
    )

    if not raw_tables:
        print(f"  WARNING: No w3-bordered table found for {state_name} ({slug})")
        return []

    source_url = page.url

    # Pick the largest table (main election) — bye-election table is smaller
    main_table = max(raw_tables, key=len)

    mlas = _parse_rows(main_table, state_name, year, source_url, scraped_at)

    if use_cache:
        _save_cache(slug, mlas)

    return mlas


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> list[dict[str, Any]]:
    parser = argparse.ArgumentParser(
        description="Scrape all current MLA winners from MyNeta.info"
    )
    parser.add_argument(
        "--state",
        help="Scrape only this state (e.g. 'TAMIL NADU')",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scrape and print counts but do not write output file",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Force fresh HTTP requests, ignoring cached JSON",
    )
    args = parser.parse_args()

    use_cache = not args.no_cache
    filter_state = args.state.upper().strip() if args.state else None

    elections = [
        (state, slug, year)
        for state, slug, year in STATE_ELECTIONS
        if not filter_state or state == filter_state
    ]

    # Check which states need live fetching
    need_fetch = [
        (state, slug, year)
        for state, slug, year in elections
        if not use_cache or _load_cache(slug) is None
    ]

    all_mlas: list[dict[str, Any]] = []
    state_counts: dict[str, int] = {}
    errors: list[str] = []

    # Open Playwright only if we have states to fetch
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent="Hisaab/1.0 (civic-data-project; public-accountability)"
        )
        page = ctx.new_page() if need_fetch else None

        for state_name, slug, year in elections:
            cached_exists = use_cache and _load_cache(slug) is not None
            cache_note = " [cache]" if cached_exists else ""
            print(f"Scraping {state_name} ({slug}){cache_note}...")

            try:
                mlas = scrape_state(
                    state_name,
                    slug,
                    year,
                    use_cache=use_cache,
                    page=page,
                )
                count = len(mlas)
                state_counts[state_name] = count
                print(f"  → {count} MLAs")
                all_mlas.extend(mlas)
            except Exception as exc:  # noqa: BLE001
                msg = f"  ERROR: {state_name} ({slug}): {exc}"
                print(msg)
                errors.append(msg)

            # Rate limit — MyNeta is run by ADR, a nonprofit
            if not cached_exists:
                time.sleep(1.5)

        browser.close()

    # Summary
    print(f"\n{'='*60}")
    print("State-by-state MLA counts:")
    for state, count in sorted(state_counts.items()):
        print(f"  {state:<30} {count:>4}")
    print(f"{'='*60}")
    total = len(all_mlas)
    states_found = len([s for s, c in state_counts.items() if c > 0])
    print(f"Total: {total} MLAs across {states_found} states with data")

    if errors:
        print(f"\nErrors ({len(errors)}):")
        for e in errors:
            print(f"  {e}")

    if not args.dry_run:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT, "w", encoding="utf-8") as fh:
            json.dump(all_mlas, fh, indent=2, ensure_ascii=False)
        print(f"\nSaved {total} records → {OUTPUT}")

    return all_mlas


if __name__ == "__main__":
    main()
