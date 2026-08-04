"""
PM POSHAN (Mid-Day Meal) data importer.

Imports district-level school nutrition data from CSV files.
The PM POSHAN MIS (pmposhan.education.gov.in) requires login and does not
expose public APIs. Data sources:
  1. data.gov.in Open Government Data CSV downloads
  2. Manual CSV files placed in data/raw/pmposhan/
  3. State-level PM POSHAN portals (e.g. pmposhan.ap.gov.in)

Expected CSV format:
    District, Schools Covered, Children Enrolled, Children Fed,
    Funds Released (Lakhs), Funds Utilized (Lakhs)

Usage:
    python scrape_pmposhan.py --csv data/raw/pmposhan/bihar_2024.csv --state BIHAR
    python scrape_pmposhan.py --dir data/raw/pmposhan/
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent  # repo root (scrapers/ is a package)
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw" / "pmposhan"
CURATED_DIR = DATA_DIR / "curated"


def utc_iso() -> str:
    return datetime.now(UTC).isoformat()


def state_slug(name: str) -> str:
    return name.lower().replace(" ", "-")


def ensure_dirs() -> None:
    for d in (RAW_DIR, CURATED_DIR):
        d.mkdir(parents=True, exist_ok=True)


def parse_csv(
    csv_path: Path,
    state_override: str | None = None,
    fin_year: str = "2024-2025",
) -> list[dict[str, Any]]:
    """Parse a PM POSHAN CSV file into records."""
    text = csv_path.read_text(encoding="utf-8-sig")
    reader = csv.reader(text.strip().splitlines())
    rows = list(reader)

    if len(rows) < 2:
        return []

    header = [h.strip().lower() for h in rows[0]]
    records: list[dict[str, Any]] = []
    scraped_at = utc_iso()
    source_url = f"data.gov.in/pm-poshan/{csv_path.name}"

    dist_col = _find_col(header, ["district", "district name"])
    state_col = _find_col(header, ["state", "state name"])
    schools_col = _find_col(header, ["schools", "schools covered", "no. of schools"])
    enrolled_col = _find_col(header, ["enrolled", "children enrolled", "enrolment"])
    fed_col = _find_col(header, ["fed", "children fed", "children availing", "meals served"])
    released_col = _find_col(header, ["released", "funds released", "allocation"])
    utilized_col = _find_col(header, ["utilized", "funds utilized", "expenditure"])

    if dist_col is None:
        print(f"  Cannot find 'district' column in {csv_path.name}")
        return []

    for row in rows[1:]:
        if len(row) <= dist_col:
            continue

        district = row[dist_col].strip().upper()
        if not district or district in ("TOTAL", "GRAND TOTAL"):
            continue

        state = state_override or (_get(row, state_col, "").strip().upper())

        enrolled = _parse_int(_get(row, enrolled_col, "0"))
        fed = _parse_int(_get(row, fed_col, "0"))
        released = _parse_float(_get(row, released_col, "0"))
        utilized = _parse_float(_get(row, utilized_col, "0"))
        util_pct = (utilized / released * 100) if released > 0 else 0.0

        record = {
            "district": district,
            "state": state,
            "state_code": "",
            "fin_year": fin_year,
            "schools_covered": _parse_int(_get(row, schools_col, "0")),
            "children_enrolled": enrolled,
            "children_fed": fed,
            "funds_released_lakhs": released,
            "funds_utilized_lakhs": utilized,
            "utilization_pct": round(util_pct, 1),
            "source_url": source_url,
            "scraped_at": scraped_at,
        }
        records.append(record)

    return records


def _find_col(header: list[str], candidates: list[str]) -> int | None:
    for i, h in enumerate(header):
        for c in candidates:
            if c in h:
                return i
    return None


def _get(row: list[str], idx: int | None, default: str = "") -> str:
    if idx is None or idx >= len(row):
        return default
    return row[idx]


def _parse_int(text: str) -> int:
    text = text.strip().replace(",", "").replace('"', "")
    if not text or text == "-":
        return 0
    try:
        return int(float(text))
    except ValueError:
        return 0


def _parse_float(text: str) -> float:
    text = text.strip().replace(",", "").replace('"', "")
    if not text or text == "-":
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def save_curated(records: list[dict[str, Any]], state_name: str) -> Path:
    slug = state_slug(state_name)
    path = CURATED_DIR / f"pmposhan_district_{slug}_latest.json"
    path.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def process_csv(csv_path: Path, state: str | None = None, fin_year: str = "2024-2025") -> int:
    records = parse_csv(csv_path, state_override=state, fin_year=fin_year)
    if not records:
        return 0

    by_state: dict[str, list[dict[str, Any]]] = {}
    for r in records:
        by_state.setdefault(r["state"] or "UNKNOWN", []).append(r)

    total = 0
    for state_name, state_records in by_state.items():
        path = save_curated(state_records, state_name)
        print(f"  {state_name}: {len(state_records)} districts → {path.name}")
        total += len(state_records)
    return total


def process_directory(dir_path: Path, fin_year: str = "2024-2025") -> int:
    total = 0
    for csv_path in sorted(dir_path.glob("*.csv")):
        print(f"Processing {csv_path.name}...")
        total += process_csv(csv_path, fin_year=fin_year)
    return total


def main() -> int:
    parser = argparse.ArgumentParser(description="Import PM POSHAN data from CSV")
    parser.add_argument("--csv", help="Path to a single CSV file")
    parser.add_argument("--dir", help="Path to directory of CSV files")
    parser.add_argument("--state", help="Override state name")
    parser.add_argument("--fin-year", default="2024-2025")
    args = parser.parse_args()

    ensure_dirs()

    if args.csv:
        count = process_csv(Path(args.csv), state=args.state, fin_year=args.fin_year)
    elif args.dir:
        count = process_directory(Path(args.dir), fin_year=args.fin_year)
    else:
        print("Provide --csv or --dir. See --help.")
        return 1

    print(f"\nTotal: {count} records")
    return 0


if __name__ == "__main__":
    sys.exit(main())
