"""
One-time migration script for curated JSON files.

Fixes:
1. PM POSHAN: renames scraper fields to match DB schema
2. PM Kisan: renames fields + converts crores to lakhs
3. All schemes: normalizes state names to canonical form

Run once:
    python migrate_curated.py
    python migrate_curated.py --dry-run   # Preview changes without writing
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from normalize_states import normalize_state

CURATED_DIR = Path(__file__).resolve().parent / "data" / "curated"


def migrate_pmposhan(record: dict) -> dict:
    """Rename PM POSHAN scraper fields to DB-compatible names.

    Mapping:
        total_schools    -> schools_covered
        student_enrolment -> children_enrolled
        meals_served     -> children_fed
        meals_served_pct -> utilization_pct
    Also adds funds_released_lakhs and funds_utilized_lakhs (portal doesn't provide).
    """
    migrated = dict(record)

    renames = {
        "total_schools": "schools_covered",
        "student_enrolment": "children_enrolled",
        "meals_served": "children_fed",
        "meals_served_pct": "utilization_pct",
    }
    for old_key, new_key in renames.items():
        if old_key in migrated and new_key not in migrated:
            migrated[new_key] = migrated.pop(old_key)

    # Add missing financial fields (not available from AMS portal)
    migrated.setdefault("funds_released_lakhs", 0)
    migrated.setdefault("funds_utilized_lakhs", 0)

    return migrated


def migrate_pmkisan(record: dict) -> dict:
    """Rename PM Kisan scraper fields to DB-compatible names.

    Mapping:
        registered_farmers -> beneficiaries_registered
        amount_paid_cr     -> amount_paid_lakhs (multiply by 100)
    Also adds beneficiaries_rejected if missing.
    """
    migrated = dict(record)

    if "registered_farmers" in migrated and "beneficiaries_registered" not in migrated:
        migrated["beneficiaries_registered"] = migrated.pop("registered_farmers")

    if "amount_paid_cr" in migrated and "amount_paid_lakhs" not in migrated:
        migrated["amount_paid_lakhs"] = round(migrated.pop("amount_paid_cr") * 100, 2)

    migrated.setdefault("beneficiaries_rejected", 0)

    return migrated


def normalize_state_in_record(record: dict) -> dict:
    """Normalize the state name field to canonical form."""
    if "state" not in record:
        return record
    normalized = normalize_state(record["state"])
    if normalized == record["state"]:
        return record
    return {**record, "state": normalized}


def migrate_file(path: Path, dry_run: bool = False) -> tuple[int, int]:
    """Migrate a single curated JSON file. Returns (records_processed, records_changed)."""
    records = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(records, list):
        return 0, 0

    name = path.name
    changed = 0
    migrated_records = []

    for record in records:
        original = record
        migrated = dict(record)

        # Apply scheme-specific migrations
        if name.startswith("pmposhan_district_"):
            migrated = migrate_pmposhan(migrated)
        elif name.startswith("pmkisan_district_"):
            migrated = migrate_pmkisan(migrated)

        # Normalize state name for all schemes
        migrated = normalize_state_in_record(migrated)

        if migrated != original:
            changed += 1

        migrated_records.append(migrated)

    if changed > 0 and not dry_run:
        path.write_text(
            json.dumps(migrated_records, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    return len(records), changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate curated JSON files")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()

    if not CURATED_DIR.exists():
        print(f"Curated directory not found: {CURATED_DIR}")
        return 1

    files = sorted(CURATED_DIR.glob("*_latest.json"))
    print(f"Found {len(files)} curated files")
    if args.dry_run:
        print("DRY RUN — no files will be modified\n")

    total_processed = 0
    total_changed = 0
    files_modified = 0

    for path in files:
        processed, changed = migrate_file(path, dry_run=args.dry_run)
        total_processed += processed
        total_changed += changed
        if changed > 0:
            files_modified += 1
            print(f"  {path.name}: {changed}/{processed} records migrated")

    print("\nSummary:")
    print(f"  Files scanned:  {len(files)}")
    print(f"  Files modified: {files_modified}")
    print(f"  Records total:  {total_processed}")
    print(f"  Records changed:{total_changed}")

    if args.dry_run and total_changed > 0:
        print("\nRe-run without --dry-run to apply changes.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
