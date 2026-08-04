"""
National Food Security Act (NFSA) / PDS data importer.

Imports district-level ration distribution data from CSV files.
The nfsa.gov.in portal provides state-level dashboards. Data sources:
  1. data.gov.in Open Government Data CSV downloads
  2. Manual CSV files placed in data/raw/nfsa/
  3. State FCS (Food & Civil Supplies) department portals

Data includes: ration cards, grain allocation vs offtake, beneficiary counts.

Expected CSV format:
    District, Ration Cards Total, Ration Cards Active, Allocation (MT),
    Offtake (MT), Beneficiaries Total

Usage:
    python scrape_nfsa.py --csv data/raw/nfsa/bihar_2024.csv --state BIHAR
    python scrape_nfsa.py --dir data/raw/nfsa/
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from scrapers.io_utils import atomic_write_json, datagov_session
except ImportError:
    from io_utils import atomic_write_json, datagov_session

ROOT_DIR = Path(__file__).resolve().parent.parent  # repo root (scrapers/ is a package)
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw" / "nfsa"
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
    """Parse an NFSA/PDS CSV file into records."""
    text = csv_path.read_text(encoding="utf-8-sig")
    reader = csv.reader(text.strip().splitlines())
    rows = list(reader)

    if len(rows) < 2:
        return []

    header = [h.strip().lower() for h in rows[0]]
    records: list[dict[str, Any]] = []
    scraped_at = utc_iso()
    source_url = f"data.gov.in/nfsa/{csv_path.name}"

    dist_col = _find_col(header, ["district", "district name"])
    state_col = _find_col(header, ["state", "state name"])
    cards_total_col = _find_col(header, ["ration cards total", "total cards", "cards total", "ration cards"])
    cards_active_col = _find_col(header, ["ration cards active", "active cards", "cards active"])
    alloc_col = _find_col(header, ["allocation", "allocation (mt)", "allotment", "allotment (mt)"])
    offtake_col = _find_col(header, ["offtake", "offtake (mt)", "lifting", "distribution"])
    benef_col = _find_col(header, ["beneficiaries", "beneficiaries total", "total beneficiaries", "covered population"])

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

        allocation = _parse_float(_get(row, alloc_col, "0"))
        offtake = _parse_float(_get(row, offtake_col, "0"))
        offtake_pct = (offtake / allocation * 100) if allocation > 0 else 0.0

        record = {
            "district": district,
            "state": state,
            "state_code": "",
            "fin_year": fin_year,
            "ration_cards_total": _parse_int(_get(row, cards_total_col, "0")),
            "ration_cards_active": _parse_int(_get(row, cards_active_col, "0")),
            "allocation_mt": allocation,
            "offtake_mt": offtake,
            "offtake_pct": round(offtake_pct, 1),
            "beneficiaries_total": _parse_int(_get(row, benef_col, "0")),
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
    path = CURATED_DIR / f"nfsa_district_{slug}_latest.json"
    if path.exists():
        old_districts = {r.get("district") for r in json.loads(path.read_text(encoding="utf-8"))}
        new_districts = {r.get("district") for r in records}
        if len(new_districts) < len(old_districts):
            raise ValueError(
                f"Refusing to save {path.name}: {len(new_districts)} districts "
                f"< existing {len(old_districts)} — a refresh must never reduce coverage"
            )
    atomic_write_json(path, records)
    return path


# ---------------------------------------------------------------------------
# Live fetch — nfsa.gov.in public dashboard AJAX handler
# ---------------------------------------------------------------------------
# The dashboard the repo's source_url has always pointed at
# (PublicRCDashboard.aspx) is backed by this handler: one un-gated POST
# returns every district's current ration-card registry counts (no captcha,
# no cookie, no session; `random=` must be present but is unvalidated).
# The official RC *report* page (frmPublicReportPage.aspx?rid=00073) is
# captcha-gated and therefore out of scope by standing decision.
NFSA_RC_HANDLER = (
    "https://nfsa.gov.in/handlers/public/nfsadashboard/hndDashboardFactDetails.ashx"
    "?act=getrcdistrictcounts&random=00000000-0000-0000-0000-000000000000"
)


def fetch_live() -> list[dict[str, Any]]:
    """Fetch current district ration-card counts for the whole country.

    Returns curated-shape records. `fin_year` is "cumulative" — this is a
    point-in-time registry snapshot, not FY-scoped data; the per-state
    reporting vintage travels in `date_of_data` (heterogeneous at source:
    some states report June 2026, a few still 2021 — see DATA_CLAIMS.md).
    """
    session = datagov_session()  # browser UA + 429/5xx retries
    resp = session.post(NFSA_RC_HANDLER, json={}, timeout=60)
    resp.raise_for_status()
    rows = resp.json()
    if not isinstance(rows, list):
        raise ValueError(f"Unexpected handler response type: {type(rows)}")

    scraped_at = utc_iso()
    records: list[dict[str, Any]] = []
    for row in rows:
        district = str(row.get("District", {}).get("DistrictName") or "").strip().upper()
        if not district or district in ("NA", "NULL"):
            # Placeholder rows (all-zero, DistrictName "NA") — not districts.
            continue
        state = str(row.get("State", {}).get("StateName") or "").strip().upper()
        total = row.get("Total", {})
        aay = row.get("AAY", {})
        phh = row.get("PHH", {})
        records.append(
            {
                "district": district,
                "state": state,
                "state_code": str(row.get("State", {}).get("StateCode") or ""),
                "fin_year": "cumulative",
                "ration_cards_total": int(total.get("RCCount") or 0),
                # active == total by construction at this source (CLAIM-2026-0008)
                "ration_cards_active": int(total.get("RCCount") or 0),
                "allocation_mt": 0.0,
                "offtake_mt": 0.0,
                "offtake_pct": 0.0,
                "beneficiaries_total": int(total.get("MemberCount") or 0),
                "aay_ration_cards": int(aay.get("RCCount") or 0),
                "aay_beneficiaries": int(aay.get("MemberCount") or 0),
                "phh_ration_cards": int(phh.get("RCCount") or 0),
                "phh_beneficiaries": int(phh.get("MemberCount") or 0),
                "date_of_data": str(row.get("DateOfData") or ""),
                "source_url": NFSA_RC_HANDLER,
                "scraped_at": scraped_at,
            }
        )
    return records


def process_live() -> int:
    """Fetch live district counts and write the per-state curated files."""
    records = fetch_live()
    if not records:
        print("  Live fetch returned no district rows — curated files untouched")
        return 0

    by_state: dict[str, list[dict[str, Any]]] = {}
    for r in records:
        by_state.setdefault(r["state"], []).append(r)

    total = 0
    for state_name, state_records in sorted(by_state.items()):
        path = save_curated(state_records, state_name)
        print(f"  {state_name}: {len(state_records)} districts -> {path.name}")
        total += len(state_records)
    return total


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
        print(f"  {state_name}: {len(state_records)} districts -> {path.name}")
        total += len(state_records)
    return total


def process_directory(dir_path: Path, fin_year: str = "2024-2025") -> int:
    total = 0
    for csv_path in sorted(dir_path.glob("*.csv")):
        print(f"Processing {csv_path.name}...")
        total += process_csv(csv_path, fin_year=fin_year)
    return total


def main() -> int:
    parser = argparse.ArgumentParser(description="Import NFSA/PDS ration data from CSV or the live dashboard")
    parser.add_argument("--csv", help="Path to a single CSV file")
    parser.add_argument("--dir", help="Path to directory of CSV files")
    parser.add_argument("--live", action="store_true", help="Fetch current district counts from the nfsa.gov.in dashboard handler")
    parser.add_argument("--state", help="Override state name")
    parser.add_argument("--fin-year", default="2024-2025")
    args = parser.parse_args()

    ensure_dirs()

    if args.live:
        count = process_live()
    elif args.csv:
        count = process_csv(Path(args.csv), state=args.state, fin_year=args.fin_year)
    elif args.dir:
        count = process_directory(Path(args.dir), fin_year=args.fin_year)
    else:
        print("Provide --live, --csv, or --dir. See --help.")
        return 1

    print(f"\nTotal: {count} records")
    return 0


if __name__ == "__main__":
    sys.exit(main())
