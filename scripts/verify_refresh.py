"""Acceptance gate for curated-data changes — diff working tree vs git HEAD.

A refresh (scheduled or manual) must never reduce granularity, coverage, or
money columns (learnings.md 2026-08-04). The per-scraper guards catch the
common cases at write time; this is the belt-and-suspenders backstop that runs
in the refresh workflow AFTER scraping and BEFORE load/publish, so a regressed
scrape fails the job instead of reaching production. It is also the mechanical
form of the manual "diff every subagent's curated output against
`git show HEAD:<path>`" rule — run it locally before any --load-only that could
sweep in freshly written curated files.

It fails (exit 1) only on the three documented regression signatures, so
legitimate refreshes (new rows, revised figures, small reorg churn) pass clean:

  1. GRANULARITY COLLAPSE — a file that held district-level rows now carries
     only district='ALL' (state-level) rows.
  2. COVERAGE COLLAPSE — distinct (state, district) pairs dropped by more than
     COVERAGE_TOLERANCE (default 15%).
  3. MONEY LOSS — a money column that was populated (sum > 0) in HEAD is now
     entirely zero.

Usage:
    python scripts/verify_refresh.py                     # gate all _latest.json (exit 1 on regression)
    python scripts/verify_refresh.py path/a.json ...      # gate specific files
    python scripts/verify_refresh.py --revert-regressions # revert offending files to HEAD, exit 0

--revert-regressions is for the unattended weekly job: a regressed file is
restored to its last-good HEAD version and the refresh proceeds for every clean
scheme (matching the workflow's "partial failures are tolerated" design), rather
than one bad file blocking the whole publish. Without it, the default is a
strict gate — report and exit 1 — for local pre-load use.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parent.parent
CURATED_GLOB = "data/curated/*_latest.json"
COVERAGE_TOLERANCE = 0.15  # allow ≤15% coverage churn (reorgs, upstream revisions)

# A numeric field is treated as "money" if its name matches any of these — a
# refresh that zeroes a populated money column is a regression even if row
# count and coverage are intact.
MONEY_HINTS = ("_lakhs", "amount", "allocat", "released", "utiliz", "expend", "offtake_mt")


def _rows(text: str) -> list[dict[str, Any]]:
    data = json.loads(text)
    return data if isinstance(data, list) else []


def _head_version(rel_path: str) -> str | None:
    """Return the file's content at git HEAD, or None if it didn't exist."""
    result = subprocess.run(
        ["git", "show", f"HEAD:{rel_path}"],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
    )
    return result.stdout if result.returncode == 0 else None


def _pairs(rows: list[dict[str, Any]]) -> set[tuple[str, str]]:
    return {(str(r.get("state", "")), str(r.get("district", ""))) for r in rows}


def _non_all_districts(rows: list[dict[str, Any]]) -> set[str]:
    return {str(r.get("district", "")) for r in rows if str(r.get("district", "")) not in ("", "ALL")}


def _money_fields(rows: list[dict[str, Any]]) -> set[str]:
    fields: set[str] = set()
    for r in rows:
        for k, v in r.items():
            if isinstance(v, (int, float)) and any(h in k.lower() for h in MONEY_HINTS):
                fields.add(k)
    return fields


def _money_sum(rows: list[dict[str, Any]], field: str) -> float:
    return sum(float(r.get(field) or 0) for r in rows)


def check_file(rel_path: str) -> list[str]:
    """Return a list of regression messages for one file (empty = clean)."""
    new_path = ROOT_DIR / rel_path
    if not new_path.exists():
        return [f"MISSING: {rel_path} exists at HEAD but not in the working tree (data would be lost on load)"]

    head_text = _head_version(rel_path)
    if head_text is None:
        return []  # net-new file — nothing to regress against

    try:
        old, new = _rows(head_text), _rows(new_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"UNREADABLE: {rel_path} — {exc}"]

    if not old:
        return []

    problems: list[str] = []

    # 1. Granularity collapse
    old_districts, new_districts = _non_all_districts(old), _non_all_districts(new)
    if old_districts and not new_districts:
        problems.append(
            f"GRANULARITY COLLAPSE: had {len(old_districts)} district rows, now all district='ALL'"
        )

    # 2. Coverage collapse
    old_pairs, new_pairs = _pairs(old), _pairs(new)
    if old_pairs:
        drop = (len(old_pairs) - len(new_pairs)) / len(old_pairs)
        if drop > COVERAGE_TOLERANCE:
            problems.append(
                f"COVERAGE COLLAPSE: {len(old_pairs)} → {len(new_pairs)} distinct "
                f"(state,district) pairs ({drop:.0%} drop, tolerance {COVERAGE_TOLERANCE:.0%})"
            )

    # 3. Money loss
    for field in _money_fields(old):
        if _money_sum(old, field) > 0 and _money_sum(new, field) == 0:
            problems.append(f"MONEY LOSS: column '{field}' was populated at HEAD, now all zero")

    return problems


def _revert(rel_path: str) -> bool:
    """Restore a file to its git HEAD version. Returns True on success."""
    result = subprocess.run(
        ["git", "checkout", "HEAD", "--", rel_path],
        cwd=ROOT_DIR,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Diff curated data vs HEAD for refresh regressions")
    parser.add_argument("paths", nargs="*", help="Specific files to check (default: all _latest.json)")
    parser.add_argument(
        "--revert-regressions",
        action="store_true",
        help="Restore each regressed file to its HEAD version and exit 0 (unattended refresh mode)",
    )
    args = parser.parse_args()

    if args.paths:
        rel_paths = [str(Path(a).resolve().relative_to(ROOT_DIR)) for a in args.paths]
    else:
        rel_paths = sorted(str(p.relative_to(ROOT_DIR)) for p in ROOT_DIR.glob(CURATED_GLOB))

    failures: dict[str, list[str]] = {}
    for rel in rel_paths:
        problems = check_file(rel)
        if problems:
            failures[rel] = problems

    print(f"verify_refresh: checked {len(rel_paths)} curated file(s) against HEAD")
    if not failures:
        print("  ✓ no granularity/coverage/money regressions")
        return 0

    print(f"  ✗ {len(failures)} file(s) with regressions:")
    for rel, problems in sorted(failures.items()):
        for p in problems:
            print(f"    {rel}: {p}")

    if args.revert_regressions:
        print("  Reverting regressed files to last-good HEAD version:")
        for rel in sorted(failures):
            ok = _revert(rel)
            print(f"    {'reverted' if ok else 'REVERT FAILED'}: {rel}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
