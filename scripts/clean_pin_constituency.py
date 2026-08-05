"""Drop electorally-impossible rows from the pin_constituency curated file.

Lok Sabha constituencies never cross state lines, so a PIN whose postal
directory places it in state X cannot belong to a constituency in state Y.
The March-2026 spatial join produced ~2% such rows (bad GeoNames coordinates
landing a PIN inside another state's PC polygon — e.g. 823001 GAYAJI/BIHAR
mapped to KARIMGANJ/ASSAM), which the PIN route then served as a "precise"
constituency with the wrong state's MP.

Two mismatch families are legitimate and are KEPT:
  * vintage labels — the datameet source predates Telangana (2014) and
    Ladakh (2019), so its polygons carry the parent state's name; the same
    labels flow through constituency_district/ac_district, so the join
    stays internally consistent (VINTAGE_STATE_EQUIV, mirrored in the web
    PIN route);
  * PINs absent from pin_district_mapping — no directory evidence to
    contradict the spatial join (and the route 404s before reading them).

Dropped PINs fall back to the route's district-level constituency list
(precise: false) — honest imprecision instead of a wrong MP.

Usage:
    python scripts/clean_pin_constituency.py            # report only
    python scripts/clean_pin_constituency.py --write    # rewrite curated file
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from db.connection import DB_PATH  # noqa: E402
from db.normalize_states import normalize_state  # noqa: E402

CURATED_PATH = ROOT_DIR / "data" / "curated" / "pin_constituency_all_latest.json"

# States whose PC polygons predate a bifurcation and carry the parent
# state's label. Keep in lockstep with VINTAGE_STATE_EQUIV in
# web/src/app/api/v1/pin/[pin_code]/route.ts.
VINTAGE_STATE_EQUIV: dict[str, frozenset[str]] = {
    "ANDHRA PRADESH": frozenset({"TELANGANA"}),
    "TELANGANA": frozenset({"ANDHRA PRADESH"}),
    "JAMMU AND KASHMIR": frozenset({"LADAKH"}),
    "LADAKH": frozenset({"JAMMU AND KASHMIR"}),
}


def is_electorally_consistent(pc_state: str, pin_states: set[str] | None) -> bool:
    """True when a constituency's state can represent a PIN's directory states.

    `pin_states` is None when the PIN is absent from the directory — kept,
    because there is no evidence of a contradiction.
    """
    if not pin_states:
        return True
    if pc_state in pin_states:
        return True
    equiv = VINTAGE_STATE_EQUIV.get(pc_state, frozenset())
    return bool(equiv & pin_states)


def _pin_states_from_db(conn: sqlite3.Connection) -> dict[str, set[str]]:
    directory: dict[str, set[str]] = {}
    for pin, state in conn.execute("SELECT pin_code, state FROM pin_district_mapping"):
        directory.setdefault(pin, set()).add(normalize_state(state))
    return directory


def clean(write: bool = False) -> int:
    rows = json.loads(CURATED_PATH.read_text(encoding="utf-8"))

    conn = sqlite3.connect(str(DB_PATH))
    try:
        directory = _pin_states_from_db(conn)
    finally:
        conn.close()
    if not directory:
        # An empty directory would validate nothing and a --write would be a
        # meaningless no-op mistaken for a clean pass. Seed civic tables first.
        print("ABORT: pin_district_mapping is empty — run `python -m constituency.ingest` first.")
        return 2

    kept: list[dict] = []
    dropped: list[dict] = []
    for r in rows:
        pc_state = normalize_state(r.get("state", ""))
        if is_electorally_consistent(pc_state, directory.get(str(r.get("pin_code")))):
            kept.append({**r, "state": pc_state})
        else:
            dropped.append(r)

    print(f"pin_constituency: {len(rows)} rows -> keep {len(kept)}, drop {len(dropped)}")
    pair_counts = Counter(
        (r["state"], "/".join(sorted(directory.get(str(r["pin_code"]), set()))))
        for r in dropped
    )
    for (pc_state, pin_states), n in pair_counts.most_common():
        print(f"  drop {n:4d}  constituency-state {pc_state} vs directory {pin_states}")

    if not dropped:
        print("Nothing to drop — file already consistent.")
        return 0
    if not write:
        print("Dry run — pass --write to rewrite the curated file.")
        return 0

    CURATED_PATH.write_text(
        json.dumps(kept, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Wrote {len(kept)} rows to {CURATED_PATH.name}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="rewrite the curated file")
    args = parser.parse_args()
    return clean(write=args.write)


if __name__ == "__main__":
    raise SystemExit(main())
