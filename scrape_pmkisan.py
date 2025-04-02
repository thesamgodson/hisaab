"""
PM Kisan Samman Nidhi scraper.

Imports district-level PM Kisan beneficiary data from CSV files.
The pmkisan.gov.in portal does not expose aggregated district-level reports
publicly. Data comes from:
  1. data.gov.in Open Government Data CSV downloads
  2. Manual CSV files placed in data/raw/pmkisan/

Expected CSV format (from data.gov.in):
    State, District, Beneficiaries Registered, Beneficiaries Paid, Amount (Lakhs)

Usage:
    python scrape_pmkisan.py --csv data/raw/pmkisan/bihar_2024.csv --state BIHAR
    python scrape_pmkisan.py --dir data/raw/pmkisan/  # Process all CSVs in dir
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw" / "pmkisan"
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
    installment: str = "",
) -> list[dict[str, Any]]:
    """Parse a PM Kisan CSV file into records.

    Handles multiple CSV formats from data.gov.in:
    - Format 1: State, District, Beneficiaries, Amount
    - Format 2: District, Registered, Paid, Amount, Rejected
    """
    text = csv_path.read_text(encoding="utf-8-sig")  # Handle BOM
    reader = csv.reader(text.strip().splitlines())
    rows = list(reader)

    if len(rows) < 2:
        print(f"  Empty CSV: {csv_path.name}")
        return []

    # Detect format from header
    header = [h.strip().lower() for h in rows[0]]
    records: list[dict[str, Any]] = []
    scraped_at = utc_iso()
    source_url = f"data.gov.in/pm-kisan/{csv_path.name}"

    # Try to find column indices
    dist_col = _find_col(header, ["district", "district name", "dist"])
    state_col = _find_col(header, ["state", "state name"])
    reg_col = _find_col(header, ["registered", "beneficiaries registered", "total beneficiaries", "beneficiaries"])
    paid_col = _find_col(header, ["paid", "beneficiaries paid", "beneficiary paid"])
    amt_col = _find_col(header, ["amount", "amount paid", "amount (lakhs)", "amount(lakhs)", "amount_paid"])
    rej_col = _find_col(header, ["rejected", "beneficiaries rejected"])

    if dist_col is None:
        print(f"  Cannot find 'district' column in {csv_path.name}")
        print(f"  Headers: {header}")
        return []

    for row in rows[1:]:
        if len(row) <= dist_col:
            continue

        district = row[dist_col].strip().upper()
        if not district or district in ("TOTAL", "GRAND TOTAL", "ALL"):
            continue

        state = state_override or (row[state_col].strip().upper() if state_col is not None and state_col < len(row) else "")

        record = {
            "district": district,
            "state": state,
            "state_code": "",
            "fin_year": fin_year,
            "beneficiaries_registered": _parse_int(row[reg_col]) if reg_col is not None and reg_col < len(row) else 0,
            "beneficiaries_paid": _parse_int(row[paid_col]) if paid_col is not None and paid_col < len(row) else 0,
            "amount_paid_lakhs": _parse_float(row[amt_col]) if amt_col is not None and amt_col < len(row) else 0,
            "beneficiaries_rejected": _parse_int(row[rej_col]) if rej_col is not None and rej_col < len(row) else 0,
            "installment": installment,
            "source_url": source_url,
            "scraped_at": scraped_at,
        }
        records.append(record)

    return records


def _find_col(header: list[str], candidates: list[str]) -> int | None:
    """Find the index of a column matching any candidate name."""
    for i, h in enumerate(header):
        for c in candidates:
            if c in h:
                return i
    return None


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
    path = CURATED_DIR / f"pmkisan_district_{slug}_latest.json"
    path.write_text(
        json.dumps(records, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def process_csv(
    csv_path: Path,
    state: str | None = None,
    fin_year: str = "2024-2025",
    installment: str = "",
) -> int:
    """Process a single CSV file."""
    records = parse_csv(csv_path, state_override=state, fin_year=fin_year, installment=installment)
    if not records:
        return 0

    # Group by state and save
    states: dict[str, list[dict[str, Any]]] = {}
    for r in records:
        s = r["state"] or "UNKNOWN"
        states.setdefault(s, []).append(r)

    total = 0
    for state_name, state_records in states.items():
        path = save_curated(state_records, state_name)
        print(f"  {state_name}: {len(state_records)} districts → {path.name}")
        total += len(state_records)

    return total


def process_directory(
    dir_path: Path,
    fin_year: str = "2024-2025",
) -> int:
    """Process all CSV files in a directory."""
    total = 0
    for csv_path in sorted(dir_path.glob("*.csv")):
        print(f"Processing {csv_path.name}...")
        total += process_csv(csv_path, fin_year=fin_year)
    return total


def main() -> int:
    parser = argparse.ArgumentParser(description="Import PM Kisan data from CSV")
    parser.add_argument("--csv", help="Path to a single CSV file")
    parser.add_argument("--dir", help="Path to directory of CSV files")
    parser.add_argument("--state", help="Override state name")
    parser.add_argument("--fin-year", default="2024-2025")
    parser.add_argument("--installment", default="", help="Installment number (e.g. '17th')")
    args = parser.parse_args()

    ensure_dirs()

    if args.csv:
        count = process_csv(Path(args.csv), state=args.state, fin_year=args.fin_year, installment=args.installment)
    elif args.dir:
        count = process_directory(Path(args.dir), fin_year=args.fin_year)
    else:
        print("Provide --csv or --dir. See --help.")
        return 1

    print(f"\nTotal: {count} records")
    return 0


if __name__ == "__main__":
    sys.exit(main())
