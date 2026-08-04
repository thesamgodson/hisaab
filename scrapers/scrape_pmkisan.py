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
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    from scrapers.io_utils import atomic_write_json, datagov_api_key, datagov_session
except ImportError:
    from io_utils import atomic_write_json, datagov_api_key, datagov_session

ROOT_DIR = Path(__file__).resolve().parent.parent  # repo root (scrapers/ is a package)
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw" / "pmkisan"
CURATED_DIR = DATA_DIR / "curated"


def utc_iso() -> str:
    return datetime.now(UTC).isoformat()


def state_slug(name: str) -> str:
    # Collapse runs of whitespace before slugging so a UT that arrives
    # double-spaced from one source (the homepage's "…HAVELI AND  DAMAN…")
    # slugs identically to its single-spaced form from the village dataset —
    # otherwise the same state writes two curated files and the loader, which
    # globs pmkisan_district_*_latest.json, counts it twice. Every
    # single-spaced name is byte-for-byte unchanged, so existing per-state
    # filenames stay stable.
    return re.sub(r"\s+", "-", name.strip().lower())


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

        state = state_override or (
            row[state_col].strip().upper() if state_col is not None and state_col < len(row) else ""
        )

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
    atomic_write_json(path, records)
    return path


# ---------------------------------------------------------------------------
# Live fetch — pmkisan.gov.in homepage (state) + data.gov.in village dataset
# (district). Both un-gated; no captcha anywhere on this path.
# ---------------------------------------------------------------------------
HOMEPAGE_URL = "https://pmkisan.gov.in/"
# "Village and Gender-wise Beneficiaries Count" — Ministry of Agriculture's
# own dataset, ~13M village rows, filterable server-side. District data lags
# the homepage by one installment.
VILLAGE_RESOURCE = "388208c6-d82a-4190-90df-91aa2c326fec"
VILLAGE_API = f"https://api.data.gov.in/resource/{VILLAGE_RESOURCE}"
API_KEY = datagov_api_key()
PAGE_LIMIT = 5000


def _fy_canonical(fy: str) -> str:
    """'2026-27' -> '2026-2027' (repo convention)."""
    parts = str(fy).strip().split("-")
    if len(parts) == 2 and len(parts[1]) == 2:
        return f"{parts[0]}-{parts[0][:2]}{parts[1]}"
    return fy


def fetch_live_state() -> list[dict[str, Any]]:
    """State totals from the homepage's server-rendered inline JSON.

    One row per state: eligible farmers vs fund-transferred for the CURRENT
    period (e.g. FinYear 2026-27, Period April-July). Mid-cycle numbers —
    states still paying out show low transfer ratios; see DATA_CLAIMS.md.
    """
    import re as _re

    session = datagov_session()
    resp = session.get(HOMEPAGE_URL, timeout=60)
    resp.raise_for_status()
    m = _re.search(r'\[\s*\{\s*"STNAME".*?\}\s*\]', resp.text, _re.DOTALL)
    if not m:
        raise ValueError("Homepage inline state JSON not found — page layout changed")
    rows = json.loads(m.group(0))

    scraped_at = utc_iso()
    fin_year = _fy_canonical(rows[0].get("FinYear", "")) if rows else ""
    period = str(rows[0].get("Period") or "") if rows else ""
    generated = str(rows[0].get("DataGeneratedOn") or "") if rows else ""
    records = []
    for r in rows:
        records.append(
            {
                "district": "ALL",
                "state": str(r.get("STNAME") or "").strip().upper(),
                "state_code": str(r.get("StateCode") or ""),
                "fin_year": fin_year,
                "beneficiaries_registered": int(r.get("EligibleFarmers") or 0),
                "beneficiaries_paid": int(r.get("FundTransferred") or 0),
                "amount_paid_lakhs": 0,
                "beneficiaries_rejected": 0,
                "installment": period,
                "data_generated_on": generated,
                "source_url": HOMEPAGE_URL,
                "scraped_at": scraped_at,
            }
        )
    return records


def detect_latest_installment(session: Any, start: int = 40) -> int:
    """Latest installment with data, by direct probing (sort[] is unreliable)."""
    for inst in range(start, 0, -1):
        params = {
            "api-key": API_KEY,
            "format": "json",
            "limit": 1,
            "offset": 0,
            "filters[InstallmentReleaseNo]": str(inst),
        }
        resp = session.get(VILLAGE_API, params=params, timeout=60)
        resp.raise_for_status()
        if resp.json().get("records"):
            return inst
        time.sleep(0.5)
    raise ValueError("No installment with data found")


def fetch_district_installment(installment: int) -> list[dict[str, Any]]:
    """Aggregate the village rows of one installment to districts.

    Pulled per census StateCode because the API silently stops paginating at
    offset 500,000 (verified 2026-08-04: a national stream returned exactly
    500k of 636,731 rows, then got=0/total=None) — a single national pull can
    never be complete. Individual states stay far below the ceiling; the
    guard below turns any state that ever reaches it into a hard error
    instead of silently truncated counts.
    """
    session = datagov_session()
    rows: list[dict[str, Any]] = []
    for state_code in range(1, 41):
        offset = 0
        state_rows = 0
        while True:
            params = {
                "api-key": API_KEY,
                "format": "json",
                "limit": PAGE_LIMIT,
                "offset": offset,
                "filters[StateCode]": str(state_code),
                "filters[InstallmentReleaseNo]": str(installment),
            }
            resp = session.get(VILLAGE_API, params=params, timeout=180)
            resp.raise_for_status()
            recs = resp.json().get("records", [])
            if offset == 0 and not recs:
                break  # no such state code
            rows.extend(recs)
            state_rows += len(recs)
            if len(recs) < PAGE_LIMIT:
                break
            offset += PAGE_LIMIT
            if offset >= 500_000:
                raise RuntimeError(
                    f"StateCode {state_code} hit the API's 500k offset ceiling — "
                    "counts would be silently truncated; pull a finer filter instead"
                )
            time.sleep(1)
        if state_rows:
            print(f"    StateCode {state_code}: {state_rows} village rows", flush=True)
        time.sleep(1)
    if not rows:
        raise RuntimeError(f"Installment {installment}: no village rows from any state")
    return aggregate_villages(rows, installment)


def aggregate_villages(rows: list[dict[str, Any]], installment: int) -> list[dict[str, Any]]:
    """Village rows -> one record per (state, district). Counts only — the
    dataset has no money field; amount_paid_lakhs stays 0 (see DATA_CLAIMS)."""
    agg: dict[tuple[str, str], dict[str, int]] = {}
    quads: set[str] = set()
    for r in rows:
        key = (
            str(r.get("StateName") or "").strip().upper(),
            str(r.get("DistrictName") or "").strip().upper(),
        )
        a = agg.setdefault(key, {"m": 0, "f": 0, "t": 0, "v": 0})
        a["m"] += r.get("MaleCount") or 0
        a["f"] += r.get("FemaleCount") or 0
        a["t"] += r.get("TransGenderCount") or 0
        a["v"] += 1
        if r.get("QuadFromDate"):
            quads.add(f"{r['QuadFromDate']}..{r.get('QuadEndDate', '')}")

    scraped_at = utc_iso()
    period = sorted(quads)[0] if quads else ""
    records = []
    for (state, district), a in sorted(agg.items()):
        if not district or district in ("NA", "NULL"):
            continue
        records.append(
            {
                "district": district,
                "state": state,
                "state_code": "",
                # Installment 22 pays Dec 2025 - Mar 2026 -> FY2025-26.
                "fin_year": "2025-2026" if installment == 22 else "",
                "beneficiaries_registered": 0,
                "beneficiaries_paid": a["m"] + a["f"] + a["t"],
                "amount_paid_lakhs": 0,
                "beneficiaries_rejected": 0,
                "installment": str(installment),
                "male": a["m"],
                "female": a["f"],
                "transgender": a["t"],
                "villages": a["v"],
                "period": period,
                "source_url": f"{VILLAGE_API}?filters[InstallmentReleaseNo]={installment}",
                "scraped_at": scraped_at,
            }
        )
    return records


def assemble_state_files(
    district_records: list[dict[str, Any]],
    state_records: list[dict[str, Any]],
) -> int:
    """Merge new district + state rows into the per-state curated files.

    Carry-forward rule: every existing row survives verbatim EXCEPT
    district='ALL' rows, which the fresh homepage row replaces (an old ALL
    row next to same-year district rows would double-count state sums).
    The frozen FY2024-25 district money rows (Rajya Sabha resources — the
    only district-level PM-KISAN money we have) are untouchable: this
    function refuses to write any state file that would lose one.
    """
    by_state: dict[str, list[dict[str, Any]]] = {}
    for r in district_records:
        by_state.setdefault(r["state"], []).append(r)
    all_rows = {r["state"]: r for r in state_records}

    total = 0
    for state in sorted(set(by_state) | set(all_rows)):
        slug = state_slug(state)
        path = CURATED_DIR / f"pmkisan_district_{slug}_latest.json"
        existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []

        carried = [r for r in existing if r.get("district") != "ALL"]
        new_districts = by_state.get(state, [])
        new_keys = {(r["district"], r["fin_year"]) for r in new_districts}
        # Same-key new rows replace carried rows (a re-run of the same
        # installment refreshes itself); different fin_years coexist.
        carried = [r for r in carried if (r.get("district"), r.get("fin_year")) not in new_keys]

        merged = carried + new_districts + ([all_rows[state]] if state in all_rows else [])

        money_old = sum(1 for r in existing if (r.get("amount_paid_lakhs") or 0) > 0)
        money_new = sum(1 for r in merged if (r.get("amount_paid_lakhs") or 0) > 0)
        if money_new < money_old:
            raise ValueError(
                f"Refusing to write {path.name}: would drop {money_old - money_new} "
                "district money rows (frozen FY2024-25 Rajya Sabha data)"
            )
        old_pairs = {(r.get("district"), r.get("fin_year")) for r in existing if r.get("district") != "ALL"}
        new_pairs = {(r.get("district"), r.get("fin_year")) for r in merged if r.get("district") != "ALL"}
        if not old_pairs <= new_pairs:
            raise ValueError(
                f"Refusing to write {path.name}: would lose district rows {sorted(old_pairs - new_pairs)[:5]}"
            )

        atomic_write_json(path, merged)
        print(f"  {state}: {len(merged)} rows ({len(new_districts)} district, "
              f"{'1 state total' if state in all_rows else 'no state total'}, {len(carried)} carried)")
        total += len(merged)
    return total


def process_live(agg_file: Path | None = None, installment: int | None = None) -> int:
    """Full live refresh: homepage state totals + district village rollup."""
    print("Fetching state totals from pmkisan.gov.in homepage...")
    state_records = fetch_live_state()
    print(f"  {len(state_records)} states, FY {state_records[0]['fin_year']}, "
          f"period {state_records[0]['installment']}")

    if agg_file:
        district_records = json.loads(agg_file.read_text(encoding="utf-8"))
        print(f"  District aggregate from {agg_file.name}: {len(district_records)} rows")
    else:
        session = datagov_session()
        inst = installment or detect_latest_installment(session)
        print(f"Pulling village dataset for installment {inst} (this takes ~10-20 min)...")
        district_records = fetch_district_installment(inst)
        print(f"  {len(district_records)} district aggregates")

    return assemble_state_files(district_records, state_records)


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
    parser = argparse.ArgumentParser(description="Import PM Kisan data from CSV or fetch live")
    parser.add_argument("--csv", help="Path to a single CSV file")
    parser.add_argument("--dir", help="Path to directory of CSV files")
    parser.add_argument("--live", action="store_true", help="Fetch homepage state totals + district village rollup")
    parser.add_argument("--agg-file", help="Reuse an existing district-aggregate JSON instead of re-pulling the village dataset")
    parser.add_argument("--state", help="Override state name")
    parser.add_argument("--fin-year", default="2024-2025")
    parser.add_argument("--installment", default="", help="Installment number (CSV label, or numeric for --live)")
    args = parser.parse_args()

    ensure_dirs()

    if args.live:
        count = process_live(
            agg_file=Path(args.agg_file) if args.agg_file else None,
            installment=int(args.installment) if args.installment.isdigit() else None,
        )
    elif args.csv:
        count = process_csv(Path(args.csv), state=args.state, fin_year=args.fin_year, installment=args.installment)
    elif args.dir:
        count = process_directory(Path(args.dir), fin_year=args.fin_year)
    else:
        print("Provide --live, --csv, or --dir. See --help.")
        return 1

    print(f"\nTotal: {count} records")
    return 0


if __name__ == "__main__":
    sys.exit(main())
