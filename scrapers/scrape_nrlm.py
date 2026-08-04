"""
DAY-NRLM (National Rural Livelihoods Mission) scraper — LokOS CDN.

nrlm.gov.in's report tree died in the Aug 2026 platform migration (the whole
domain is unreachable at the TCP level). The ministry's SHG ecosystem moved to
LokOS (lokos.in), whose public Community Funds dashboard is backed by
un-authenticated, district-level JSON on cdn.lokos.in:

    https://cdn.lokos.in/lokos-in/fdm/prod/{SC}/DISTRICT_FDM_OVERALL.json
    https://cdn.lokos.in/lokos-in/fdm/prod/{SC}/DISTRICT_FDM_REVOLVINGFUND.json

{SC} is LokOS's own 2-letter state code (NOT ISO/census: Bihar=BH, Kerala=KR,
Punjab=PJ, Puducherry=PO). The mapping ships in lokos.in's Angular bundle
(chunk-UA3272OP.js, keyed by state LGD code) and is pinned below. Discovered
and validated 2026-08-04: 34/34 states, 757 districts, sum(totalDistricts)
from the national feed matches exactly.

Semantics:
  - shgs_total        <- totalShgs        (DISTRICT_FDM_OVERALL)
  - rf_amount_lakhs   <- rfReceived / 1e5 (DISTRICT_FDM_REVOLVINGFUND; rupees)
  - rf_shgs_provided  <- shgReceivingRf   (DISTRICT_FDM_REVOLVINGFUND)
  - cif_amount_lakhs  <- cifReceived / 1e5 (DISTRICT_FDM_COMMUNITYINVESTMENTFUND)
  - cif_shgs_provided <- shgReceivingCif  (DISTRICT_FDM_COMMUNITYINVESTMENTFUND)
  - cif_shgs_eligible <- cifEligibleShg   (DISTRICT_FDM_COMMUNITYINVESTMENTFUND)
    CIF (Community Investment Fund) is a second district-level SHG money stream
    alongside the Revolving Fund — a district money metric almost no other
    scheme provides. The eligible-vs-received gap (cif_shgs_eligible vs
    cif_shgs_provided) is itself an accountability signal.
  - shgs_new / shgs_revived / shgs_pre_nrlm / members_total exist ONLY on the
    dead nrlm.gov.in report — LokOS does not publish the formation breakdown.
    They are carried forward from the previous curated snapshot (frozen at
    their 2026-03-21 scrape) so a refresh cannot silently zero real data.
    DATA_CLAIMS.md records the column-level vintage split.

Granularity guard: save_curated() refuses to replace the curated file with a
snapshot covering fewer distinct (state, district) pairs — a coarser or
partial feed must never overwrite a finer one (learnings.md 2026-08-04).

Data is cumulative (no fin_year breakdown on the portal).

Output: data/curated/nrlm_district_all_latest.json (+ timestamped snapshot)

Usage:
    python -m scrapers.scrape_nrlm                    # All states
    python -m scrapers.scrape_nrlm --states "BIHAR"   # Single state
    python -m scrapers.scrape_nrlm --skip-rf          # SHG counts only
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

ROOT_DIR = Path(__file__).resolve().parent.parent  # repo root (scrapers/ is a package)
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
CURATED_DIR = DATA_DIR / "curated"

try:
    from scrapers.io_utils import atomic_write_json
except ImportError:  # direct script invocation from scrapers/
    from io_utils import atomic_write_json

FDM_BASE = "https://cdn.lokos.in/lokos-in/fdm/prod/"
CURATED_FILENAME = "nrlm_district_all_latest.json"

# chunk-UA3272OP.js: {stateLgdCode: (lokosCode, stateName)}. lokosCode is the
# 2-letter CDN path segment. Delhi and Chandigarh do not participate in
# DAY-NRLM (rural programme) and have no LokOS feed.
STATE_CODES: dict[int, tuple[str, str]] = {
    35: ("AN", "ANDAMAN AND NICOBAR"),
    28: ("AP", "ANDHRA PRADESH"),
    12: ("AR", "ARUNACHAL PRADESH"),
    18: ("AS", "ASSAM"),
    10: ("BH", "BIHAR"),
    22: ("CG", "CHHATTISGARH"),
    38: ("DN", "DD & DNH"),
    30: ("GO", "GOA"),
    24: ("GJ", "GUJARAT"),
    6: ("HA", "HARYANA"),
    2: ("HP", "HIMACHAL PRADESH"),
    1: ("JK", "JAMMU AND KASHMIR"),
    20: ("JH", "JHARKHAND"),
    29: ("KN", "KARNATAKA"),
    32: ("KR", "KERALA"),
    37: ("LD", "LAKSHADWEEP"),
    31: ("LA", "LADAKH"),
    23: ("MP", "MADHYA PRADESH"),
    27: ("MH", "MAHARASHTRA"),
    14: ("MN", "MANIPUR"),
    17: ("MG", "MEGHALAYA"),
    15: ("MZ", "MIZORAM"),
    13: ("NG", "NAGALAND"),
    21: ("OR", "ODISHA"),
    34: ("PO", "PUDUCHERRY"),
    3: ("PJ", "PUNJAB"),
    8: ("RJ", "RAJASTHAN"),
    11: ("SK", "SIKKIM"),
    33: ("TN", "TAMIL NADU"),
    36: ("TS", "TELANGANA"),
    16: ("TR", "TRIPURA"),
    5: ("UK", "UTTARAKHAND"),
    9: ("UP", "UTTAR PRADESH"),
    19: ("WB", "WEST BENGAL"),
}

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"
TIMEOUT = 30
MAX_ATTEMPTS = 3


def utc_iso() -> str:
    return datetime.now(UTC).isoformat()


def ensure_dirs() -> None:
    for d in (RAW_DIR, CURATED_DIR):
        d.mkdir(parents=True, exist_ok=True)


def _get_json(session: requests.Session, url: str) -> Any:
    last_exc: Exception | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            resp = session.get(url, timeout=TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as exc:
            last_exc = exc
            if attempt < MAX_ATTEMPTS:
                time.sleep(2 * attempt)
    raise RuntimeError(f"GET {url} failed after {MAX_ATTEMPTS} attempts: {last_exc}")


def _carry_forward_map() -> dict[tuple[str, str], dict[str, int]]:
    """Formation-breakdown columns from the previous curated snapshot.

    Keyed by canonical (state, district) so LokOS spelling variants still
    inherit their district's frozen 2026-03 formation data. Normalizer import
    failure is a hard error — a silent {} here would zero the breakdown for
    every district, exactly the silent-degradation this map exists to prevent.
    """
    if str(ROOT_DIR) not in sys.path:
        sys.path.insert(0, str(ROOT_DIR))
    from db.normalize_districts import normalize_district
    from db.normalize_states import normalize_state

    path = CURATED_DIR / CURATED_FILENAME
    if not path.exists():
        return {}

    carried: dict[tuple[str, str], dict[str, int]] = {}
    for r in json.loads(path.read_text(encoding="utf-8")):
        state = normalize_state(str(r.get("state", "")).upper())
        district = normalize_district(str(r.get("district", "")).upper(), state)
        carried[(state, district)] = {
            "shgs_new": int(r.get("shgs_new") or 0),
            "shgs_revived": int(r.get("shgs_revived") or 0),
            "shgs_pre_nrlm": int(r.get("shgs_pre_nrlm") or 0),
            "members_total": int(r.get("members_total") or 0),
        }
    return carried


def scrape_state(
    session: requests.Session,
    lokos_code: str,
    include_rf: bool,
    scraped_at: str,
    carried: dict[tuple[str, str], dict[str, int]],
) -> list[dict[str, Any]]:
    """Fetch one state's district rows and merge OVERALL + REVOLVINGFUND."""
    if str(ROOT_DIR) not in sys.path:
        sys.path.insert(0, str(ROOT_DIR))
    from db.normalize_districts import normalize_district
    from db.normalize_states import normalize_state

    overall_url = f"{FDM_BASE}{lokos_code}/DISTRICT_FDM_OVERALL.json"
    rf_url = f"{FDM_BASE}{lokos_code}/DISTRICT_FDM_REVOLVINGFUND.json"
    cif_url = f"{FDM_BASE}{lokos_code}/DISTRICT_FDM_COMMUNITYINVESTMENTFUND.json"

    overall = _get_json(session, overall_url)

    rf_by_district: dict[int, dict[str, Any]] = {}
    cif_by_district: dict[int, dict[str, Any]] = {}
    if include_rf:
        for row in _get_json(session, rf_url):
            rf_by_district[int(row["districtId"])] = row
        for row in _get_json(session, cif_url):
            cif_by_district[int(row["districtId"])] = row

    records: list[dict[str, Any]] = []
    for row in overall:
        district_id = int(row["districtId"])
        rf = rf_by_district.get(district_id, {})
        cif = cif_by_district.get(district_id, {})
        state_name = str(row["stateName"]).upper().strip()
        district_name = str(row["districtName"]).upper().strip()
        canon_key = (
            normalize_state(state_name),
            normalize_district(district_name, normalize_state(state_name)),
        )
        frozen = carried.get(canon_key, {})
        records.append(
            {
                "district": district_name,
                "state": state_name,
                "state_code": lokos_code,
                "state_lgd_code": int(row.get("stateLgdCode") or 0),
                "district_lgd_code": int(row.get("districtLgdCode") or 0),
                "fin_year": "cumulative",
                "shgs_total": int(row.get("totalShgs") or 0),
                # Frozen at 2026-03-21 (source dead) — see module docstring.
                "shgs_new": frozen.get("shgs_new", 0),
                "shgs_revived": frozen.get("shgs_revived", 0),
                "shgs_pre_nrlm": frozen.get("shgs_pre_nrlm", 0),
                "members_total": frozen.get("members_total", 0),
                "rf_shgs_provided": int(rf.get("shgReceivingRf") or 0),
                "rf_amount_lakhs": round(float(rf.get("rfReceived") or 0.0) / 1e5, 2),
                "cif_shgs_provided": int(cif.get("shgReceivingCif") or 0),
                "cif_shgs_eligible": int(cif.get("cifEligibleShg") or 0),
                "cif_amount_lakhs": round(float(cif.get("cifReceived") or 0.0) / 1e5, 2),
                "source_url": overall_url,
                "rf_source_url": rf_url if include_rf else None,
                "cif_source_url": cif_url if include_rf else None,
                "scraped_at": scraped_at,
            }
        )
    return records


def scrape_all_states(
    states_filter: list[str] | None = None,
    include_rf: bool = True,
    delay_sec: float = 1.0,
) -> list[dict[str, Any]]:
    """Scrape district rows for all (or filtered) states. Plain requests."""
    ensure_dirs()
    scraped_at = utc_iso()
    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept": "application/json"})

    carried = _carry_forward_map()
    upper_filter = {s.upper() for s in states_filter} if states_filter else None

    all_records: list[dict[str, Any]] = []
    failed: list[str] = []
    for lokos_code, state_name in sorted(STATE_CODES.values(), key=lambda t: t[1]):
        if upper_filter and state_name not in upper_filter:
            continue
        try:
            records = scrape_state(session, lokos_code, include_rf, scraped_at, carried)
        except RuntimeError as exc:
            print(f"    {state_name}: FAILED — {exc}")
            failed.append(state_name)
            continue
        print(f"    {state_name}: {len(records)} districts")
        all_records.extend(records)
        time.sleep(delay_sec)

    if failed:
        print(f"  WARNING: {len(failed)} state(s) failed: {', '.join(failed)}")
    return all_records


def _distinct_pairs(records: list[dict[str, Any]]) -> set[tuple[str, str]]:
    return {(str(r.get("state", "")), str(r.get("district", ""))) for r in records}


def save_curated(records: list[dict[str, Any]]) -> Path:
    """Atomically save records — refusing any granularity regression."""
    path = CURATED_DIR / CURATED_FILENAME

    new_pairs = _distinct_pairs(records)
    if any(d == "ALL" for _, d in new_pairs):
        raise ValueError(
            "Refusing to save: batch contains district='ALL' (state-level) rows; "
            "state-level data must never enter the district table"
        )
    if path.exists():
        old_pairs = _distinct_pairs(json.loads(path.read_text(encoding="utf-8")))
        if len(new_pairs) < len(old_pairs):
            raise ValueError(
                f"Refusing to save: new snapshot has {len(new_pairs)} distinct "
                f"(state, district) pairs, existing has {len(old_pairs)} — "
                "a refresh must never reduce granularity or coverage"
            )

    run_id = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    atomic_write_json(CURATED_DIR / f"nrlm_district_all_{run_id}.json", records)
    atomic_write_json(path, records)
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Scrape DAY-NRLM SHG + RF data from the LokOS CDN")
    parser.add_argument("--states", help="Comma-separated state names (default: all states)")
    parser.add_argument(
        "--skip-rf",
        action="store_true",
        help="Skip the REVOLVINGFUND feed — SHG counts only",
    )
    parser.add_argument(
        "--delay-sec",
        type=float,
        default=1.0,
        help="Delay in seconds between states (default: 1.0)",
    )
    args = parser.parse_args()

    states_filter = [s.strip().upper() for s in args.states.split(",")] if args.states else None
    include_rf = not args.skip_rf

    label = f"{len(states_filter)} states" if states_filter else "all states"
    print(f"DAY-NRLM Scraper (LokOS CDN) — {label}, RF={'yes' if include_rf else 'no'}")

    records = scrape_all_states(
        states_filter=states_filter,
        include_rf=include_rf,
        delay_sec=args.delay_sec,
    )

    if not records:
        print("No records scraped — check CDN connectivity.")
        return 1

    path = save_curated(records)
    print(f"\nSaved {len(records)} district records → {path.name}")

    by_state: dict[str, int] = {}
    for r in records:
        by_state[r["state"]] = by_state.get(r["state"], 0) + 1
    print("\nBy state:")
    for state, count in sorted(by_state.items()):
        print(f"  {state}: {count} districts")

    return 0


if __name__ == "__main__":
    sys.exit(main())
