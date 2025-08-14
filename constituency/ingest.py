"""Download and load real constituency data from public sources.

Data sources:
  1. PIN → District: data.gov.in API (paginated JSON)
  2. Constituency → District: datameet AC GeoJSON (~17MB, cached)
  3. MP data: OpenCity CSV (2024 Lok Sabha results)

Usage:
    python -m constituency.ingest              # Download + load all
    python -m constituency.ingest --dry-run    # Count records without inserting
    python -m constituency.ingest --pins-only  # Only PIN data
    python -m constituency.ingest --mp-only    # Only MP data
    python -m constituency.ingest --pc-only    # Only constituency-district mapping
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import time
from pathlib import Path
from typing import Any

import requests

from constituency.fuzzy_match import build_canonical_districts, match_district, normalize_district
from constituency.mapper import load_ac_data, load_constituency_data, load_mla_data, load_mp_data, load_pin_data
from db import init_db, get_connection
from db.normalize_states import normalize_state

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_RAW_DIR = _PROJECT_ROOT / "data" / "raw"
_PIN_PAGES_DIR = _RAW_DIR / "pin_pages"
_AC_GEOJSON_PATH = _RAW_DIR / "ac.geojson"
_MP_CSV_PATH = _RAW_DIR / "mp_2024.csv"
_MLA_CSV_PATH = _RAW_DIR / "mla_sample.csv"
_REPORT_PATH = _RAW_DIR / "district_match_report.json"

# ---------------------------------------------------------------------------
# Data source URLs
# ---------------------------------------------------------------------------

PIN_API_URL = "https://api.data.gov.in/resource/5c2f62fe-5afa-4119-a499-fec9d604d5bd"
PIN_API_KEY = "579b464db66ec23bdd000001cdc3b564546246a772a26393094f5645"
PIN_PAGE_SIZE = 1000
# Total PIN records ~155,000 — over-estimate at 166 pages for safety
PIN_MAX_PAGES = 200

AC_GEOJSON_URL = (
    "https://raw.githubusercontent.com/datameet/maps/master/"
    "docs/data/geojson/ac.geojson"
)

MP_CSV_URL = (
    "https://data.opencity.in/dataset/85a345c6-78c0-4f57-adfc-236c726c5456/"
    "resource/3e96ed32-9b97-4c5b-9201-7807d90b20e5/download/"
    "2a4e0925-0903-4857-902b-9a57cfb78094.csv"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_dirs() -> None:
    _RAW_DIR.mkdir(parents=True, exist_ok=True)
    _PIN_PAGES_DIR.mkdir(parents=True, exist_ok=True)


def _download(url: str, dest: Path, label: str) -> Path:
    """Download a file to dest if it doesn't already exist. Returns dest."""
    if dest.exists():
        print(f"  [cache] {label} already at {dest.name}")
        return dest
    print(f"  Downloading {label}...")
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    print(f"  Saved {dest.stat().st_size // 1024} KB → {dest.name}")
    return dest


# ---------------------------------------------------------------------------
# 1. PIN ingestion
# ---------------------------------------------------------------------------


def _fetch_pin_page(offset: int) -> dict[str, Any]:
    """Fetch one page from the PIN API."""
    params = {
        "api-key": PIN_API_KEY,
        "format": "json",
        "limit": PIN_PAGE_SIZE,
        "offset": offset,
    }
    resp = requests.get(PIN_API_URL, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def ingest_pins(dry_run: bool = False) -> int:
    """Download PIN data from data.gov.in and load into pin_district_mapping.

    Pages are cached in data/raw/pin_pages/ so re-runs skip downloads.
    Returns number of records loaded (or would-be loaded in dry_run mode).
    """
    _ensure_dirs()

    seen: set[tuple[str, str]] = set()  # (pin_code, district) dedup
    records: list[dict[str, Any]] = []

    # Probe total record count from the API
    print("PIN ingestion: probing total record count...")
    try:
        first_page = _fetch_pin_page(0)
        total_records = int(first_page.get("total", 165000))
    except Exception as exc:  # noqa: BLE001
        print(f"  Warning: could not probe total ({exc}), defaulting to 165000")
        total_records = 165000

    total_pages = (total_records + PIN_PAGE_SIZE - 1) // PIN_PAGE_SIZE
    total_pages = min(total_pages, PIN_MAX_PAGES)
    print(f"  Total records: {total_records}, pages to fetch: {total_pages}")

    for page_num in range(total_pages):
        offset = page_num * PIN_PAGE_SIZE
        page_file = _PIN_PAGES_DIR / f"page_{page_num:04d}.json"

        if page_file.exists():
            data = json.loads(page_file.read_text())
        else:
            print(f"  Downloading PIN page {page_num + 1}/{total_pages}...")
            try:
                data = _fetch_pin_page(offset)
                page_file.write_text(json.dumps(data))
                time.sleep(0.5)
            except Exception as exc:  # noqa: BLE001
                print(f"  Warning: page {page_num} failed ({exc}), skipping")
                continue

        for entry in data.get("records", []):
            # Field names vary by dataset version
            pin = str(
                entry.get("pincode") or entry.get("pin_code") or entry.get("Pincode", "")
            ).strip()
            district = str(
                entry.get("district") or entry.get("districtname") or entry.get("District", "")
            ).strip().upper()
            state_raw = str(
                entry.get("statename") or entry.get("state") or entry.get("StateName", "")
            ).strip()
            office = str(
                entry.get("officename") or entry.get("OfficeName", "")
            ).strip()

            if not pin or not pin.isdigit() or len(pin) != 6:
                continue
            if not district:
                continue

            key = (pin, district)
            if key in seen:
                continue
            seen.add(key)

            records.append(
                {
                    "pin_code": pin,
                    "district": normalize_district(district),
                    "state": normalize_state(state_raw),
                    "office_name": office,
                }
            )

    print(f"  PIN records collected: {len(records)}")
    if dry_run:
        return len(records)

    loaded = load_pin_data(records)
    print(f"  PIN records inserted/replaced: {loaded}")
    return loaded


# ---------------------------------------------------------------------------
# 2. Constituency → District ingestion
# ---------------------------------------------------------------------------


def ingest_constituencies(dry_run: bool = False) -> int:
    """Download datameet AC GeoJSON and extract constituency→district mappings.

    Returns number of records loaded (or would-be loaded in dry_run mode).
    """
    _ensure_dirs()

    _download(AC_GEOJSON_URL, _AC_GEOJSON_PATH, "datameet AC GeoJSON")

    print("Parsing AC GeoJSON...")
    geojson = json.loads(_AC_GEOJSON_PATH.read_text())
    features = geojson.get("features", [])
    print(f"  Features: {len(features)}")

    # Extract unique (PC_NAME, DIST_NAME, ST_NAME) tuples
    seen: set[tuple[str, str, str]] = set()
    records: list[dict[str, Any]] = []

    for feat in features:
        props = feat.get("properties") or {}

        # Field names in datameet GeoJSON
        pc_name = (
            props.get("PC_NAME") or props.get("pc_name") or
            props.get("CONSTITUENCY") or props.get("constituency") or ""
        ).strip().upper()

        dist_name = (
            props.get("DIST_NAME") or props.get("dist_name") or
            props.get("DISTRICT") or props.get("district") or ""
        ).strip().upper()

        st_name = (
            props.get("ST_NAME") or props.get("st_name") or
            props.get("STATE") or props.get("state") or ""
        ).strip()

        if not pc_name:
            continue
        if not dist_name:
            continue

        state_norm = normalize_state(st_name)
        dist_norm = normalize_district(dist_name)

        key = (pc_name, dist_norm, state_norm)
        if key in seen:
            continue
        seen.add(key)

        records.append(
            {
                "constituency": pc_name,
                "state": state_norm,
                "district": dist_norm,
                "constituency_type": "LOK_SABHA",
            }
        )

    print(f"  Constituency-district pairs collected: {len(records)}")
    if dry_run:
        return len(records)

    loaded = load_constituency_data(records)
    print(f"  Constituency-district records inserted/replaced: {loaded}")
    return loaded


# ---------------------------------------------------------------------------
# 3. MP data ingestion
# ---------------------------------------------------------------------------


def ingest_mps(dry_run: bool = False) -> int:
    """Download 2024 Lok Sabha MP data from OpenCity and load into mp_info.

    Returns number of records loaded (or would-be loaded in dry_run mode).
    """
    _ensure_dirs()

    _download(MP_CSV_URL, _MP_CSV_PATH, "2024 Lok Sabha MP CSV")

    print("Parsing MP CSV...")
    text = _MP_CSV_PATH.read_text(encoding="utf-8-sig")  # handle BOM
    reader = csv.DictReader(io.StringIO(text))

    records: list[dict[str, Any]] = []
    for row in reader:
        # Normalize field names — OpenCity CSV may vary
        state_raw = (
            row.get("State") or row.get("state") or row.get("STATE") or ""
        ).strip()
        pc_name = (
            row.get("PC Name") or row.get("pc_name") or
            row.get("Constituency") or row.get("PC NAME") or ""
        ).strip().upper()
        mp_name = (
            row.get("Winning Candidate") or row.get("winning_candidate") or
            row.get("MP Name") or row.get("mp_name") or ""
        ).strip()
        party = (
            row.get("Winning Party") or row.get("winning_party") or
            row.get("Party") or row.get("party") or ""
        ).strip()
        margin_raw = (
            row.get("Margin Votes") or row.get("margin_votes") or
            row.get("Margin") or row.get("margin") or ""
        ).strip()

        if not pc_name or not mp_name:
            continue

        try:
            margin_votes = int(str(margin_raw).replace(",", "")) if margin_raw else None
        except ValueError:
            margin_votes = None

        records.append(
            {
                "constituency": pc_name,
                "mp_name": mp_name,
                "party": party,
                "state": normalize_state(state_raw),
                "elected_year": 2024,
                "source_url": MP_CSV_URL,
                "margin_votes": margin_votes,
            }
        )

    print(f"  MP records collected: {len(records)}")
    if dry_run:
        return len(records)

    loaded = load_mp_data(records)
    print(f"  MP records inserted/replaced: {loaded}")
    return loaded


# ---------------------------------------------------------------------------
# 4. Assembly Constituency ingestion
# ---------------------------------------------------------------------------


def ingest_assembly_constituencies(dry_run: bool = False) -> int:
    """Parse the existing datameet AC GeoJSON and load AC→district mappings.

    Uses the cached data/raw/ac.geojson (already downloaded by ingest_constituencies).
    Extracts unique (AC_NAME, AC_NO, ST_NAME, DIST_NAME, PC_NAME) tuples.
    Returns number of records loaded (or would-be loaded in dry_run mode).
    """
    _ensure_dirs()

    if not _AC_GEOJSON_PATH.exists():
        print(f"  AC GeoJSON not found at {_AC_GEOJSON_PATH}. Run --pc-only first to download it.")
        return 0

    print("Parsing AC GeoJSON for assembly constituencies...")
    geojson = json.loads(_AC_GEOJSON_PATH.read_text())
    features = geojson.get("features", [])
    print(f"  Features: {len(features)}")

    seen: set[tuple[str, str, str]] = set()
    records: list[dict[str, Any]] = []

    for feat in features:
        props = feat.get("properties") or {}

        ac_name = str(props.get("AC_NAME") or props.get("ac_name") or "").strip()
        ac_no_raw = props.get("AC_NO") or props.get("ac_no")
        dist_name = str(
            props.get("DIST_NAME") or props.get("dist_name") or ""
        ).strip().upper()
        st_name = str(props.get("ST_NAME") or props.get("st_name") or "").strip()
        pc_name = str(props.get("PC_NAME") or props.get("pc_name") or "").strip().upper()

        if not ac_name or not dist_name or not st_name:
            continue

        state_norm = normalize_state(st_name)
        dist_norm = normalize_district(dist_name)
        ac_upper = ac_name.upper()

        key = (ac_upper, state_norm, dist_norm)
        if key in seen:
            continue
        seen.add(key)

        try:
            ac_no = int(ac_no_raw) if ac_no_raw is not None else None
        except (ValueError, TypeError):
            ac_no = None

        records.append(
            {
                "ac_name": ac_upper,
                "ac_no": ac_no,
                "state": state_norm,
                "district": dist_norm,
                "pc_name": pc_name or None,
            }
        )

    print(f"  AC→district pairs collected: {len(records)}")
    if dry_run:
        return len(records)

    loaded = load_ac_data(records)
    print(f"  AC→district records inserted/replaced: {loaded}")
    return loaded


# ---------------------------------------------------------------------------
# 5. MLA data ingestion
# ---------------------------------------------------------------------------


def ingest_mlas(dry_run: bool = False) -> int:
    """Load MLA data from data/raw/mla_sample.csv into mla_info table.

    The CSV must have columns: ac_name, state, mla_name, party, elected_year.
    Optional columns: ac_no, source_url.

    Returns number of records loaded (or would-be loaded in dry_run mode).
    """
    _ensure_dirs()

    if not _MLA_CSV_PATH.exists():
        print(f"  MLA CSV not found at {_MLA_CSV_PATH}. Skipping MLA ingestion.")
        print("  Create data/raw/mla_sample.csv with columns: ac_name, state, mla_name, party, elected_year")
        return 0

    print(f"Parsing MLA CSV from {_MLA_CSV_PATH.name}...")
    text = _MLA_CSV_PATH.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    records: list[dict[str, Any]] = []
    for row in reader:
        ac_name = (row.get("ac_name") or row.get("AC_NAME") or "").strip()
        state_raw = (row.get("state") or row.get("STATE") or "").strip()
        mla_name = (row.get("mla_name") or row.get("MLA_NAME") or "").strip()
        party = (row.get("party") or row.get("PARTY") or "").strip()
        elected_year_raw = (row.get("elected_year") or row.get("ELECTED_YEAR") or "2024").strip()
        ac_no_raw = (row.get("ac_no") or row.get("AC_NO") or "").strip()
        source_url = (row.get("source_url") or row.get("SOURCE_URL") or "").strip()

        if not ac_name or not mla_name or not state_raw:
            continue

        try:
            elected_year = int(elected_year_raw)
        except ValueError:
            elected_year = 2024

        try:
            ac_no: int | None = int(ac_no_raw) if ac_no_raw else None
        except ValueError:
            ac_no = None

        records.append(
            {
                "ac_name": ac_name.upper(),
                "ac_no": ac_no,
                "state": normalize_state(state_raw),
                "mla_name": mla_name,
                "party": party,
                "elected_year": elected_year,
                "source_url": source_url or None,
            }
        )

    print(f"  MLA records collected: {len(records)}")
    if dry_run:
        return len(records)

    loaded = load_mla_data(records)
    print(f"  MLA records inserted/replaced: {loaded}")
    return loaded


# ---------------------------------------------------------------------------
# District match report
# ---------------------------------------------------------------------------


def _generate_match_report() -> None:
    """Compare constituency_district table against scheme_delivery districts.

    Writes data/raw/district_match_report.json with matched and unmatched pairs.
    """
    import sqlite3 as _sqlite3

    from db.connection import DB_PATH

    conn = _sqlite3.connect(str(DB_PATH))
    try:
        cd_rows = conn.execute(
            "SELECT DISTINCT constituency, state, district FROM constituency_district"
        ).fetchall()
    finally:
        conn.close()

    canonical = build_canonical_districts()

    matched: list[dict[str, str]] = []
    unmatched: list[dict[str, str]] = []

    for constituency, state, district in cd_rows:
        result = match_district(district, state, canonical)
        entry = {
            "constituency": constituency,
            "state": state,
            "constituency_district": district,
        }
        if result:
            matched.append({**entry, "canonical_district": result})
        else:
            unmatched.append(entry)

    report = {
        "total_constituency_district_pairs": len(cd_rows),
        "matched": len(matched),
        "unmatched": len(unmatched),
        "match_rate_pct": round(len(matched) / max(len(cd_rows), 1) * 100, 1),
        "matched_pairs": matched,
        "unmatched_pairs": unmatched,
    }

    _REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(
        f"\nDistrict match report: {len(matched)} matched, "
        f"{len(unmatched)} unmatched "
        f"({report['match_rate_pct']}%) → {_REPORT_PATH}"
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download and load constituency data into Hisaab DB"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count records without inserting into DB",
    )
    parser.add_argument("--pins-only", action="store_true", help="Only ingest PIN data")
    parser.add_argument("--mp-only", action="store_true", help="Only ingest MP data")
    parser.add_argument(
        "--pc-only",
        action="store_true",
        help="Only ingest constituency-district mapping",
    )
    parser.add_argument(
        "--ac-only",
        action="store_true",
        help="Only ingest Assembly Constituency → district mapping from GeoJSON",
    )
    parser.add_argument(
        "--mla-only",
        action="store_true",
        help="Only ingest MLA data from data/raw/mla_sample.csv",
    )
    args = parser.parse_args()

    # Ensure DB schema is initialized
    if not args.dry_run:
        conn = get_connection()
        init_db(conn)
        conn.close()

    exclusive_flags = [args.pins_only, args.mp_only, args.pc_only, args.ac_only, args.mla_only]
    run_all = not any(exclusive_flags)

    totals: dict[str, int] = {}

    if run_all or args.pins_only:
        print("\n=== PIN → District ===")
        totals["pins"] = ingest_pins(dry_run=args.dry_run)

    if run_all or args.pc_only:
        print("\n=== Constituency → District (Lok Sabha) ===")
        totals["constituencies"] = ingest_constituencies(dry_run=args.dry_run)

    if run_all or args.mp_only:
        print("\n=== MP Info ===")
        totals["mps"] = ingest_mps(dry_run=args.dry_run)

    if run_all or args.ac_only:
        print("\n=== Assembly Constituency → District ===")
        totals["assembly_constituencies"] = ingest_assembly_constituencies(dry_run=args.dry_run)

    if run_all or args.mla_only:
        print("\n=== MLA Info ===")
        totals["mlas"] = ingest_mlas(dry_run=args.dry_run)

    if not args.dry_run and (run_all or args.pc_only):
        _generate_match_report()

    print("\n=== Summary ===")
    for key, count in totals.items():
        label = "would insert" if args.dry_run else "inserted/replaced"
        print(f"  {key}: {count} records {label}")


if __name__ == "__main__":
    main()
