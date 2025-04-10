"""CLI entry point for journalist brief generation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from briefs.district import brief, resolve_district
from briefs.formatting import BRIEFS_DIR, FIN_YEAR
from briefs.red_flags import scan_red_flags
from briefs.state import state_brief


def save_brief(text: str, filename: str) -> Path:
    """Save a brief to the data/briefs/ directory."""
    BRIEFS_DIR.mkdir(parents=True, exist_ok=True)
    path = BRIEFS_DIR / filename
    path.write_text(text, encoding="utf-8")
    return path


def main() -> int:
    """Parse arguments and generate the requested brief."""
    parser = argparse.ArgumentParser(description="Hisaab journalist briefing generator")
    parser.add_argument("district", nargs="*", help="District name (fuzzy match supported)")
    parser.add_argument("--state", type=str, help="Generate state-level brief instead")
    parser.add_argument("--scan", action="store_true", help="Scan all districts for red flags (story finder)")
    parser.add_argument("--limit", type=int, default=25, help="Number of results for --scan (default: 25)")
    parser.add_argument("--save", action="store_true", help="Save briefing to data/briefs/")
    args = parser.parse_args()

    if args.scan:
        text = scan_red_flags(limit=args.limit, state_filter=args.state)
        print(text)
        if args.save:
            scope = args.state.strip().lower().replace(" ", "-") if args.state else "india"
            path = save_brief(text, f"scan_{scope}_{FIN_YEAR}.txt")
            print(f"\nSaved to: {path}")
        return 0

    if args.state:
        text = state_brief(args.state)
        print(text)
        if args.save:
            slug = args.state.strip().lower().replace(" ", "-")
            path = save_brief(text, f"state_{slug}_{FIN_YEAR}.txt")
            print(f"\nSaved to: {path}")
        return 0

    if not args.district:
        parser.print_help()
        return 1

    query = " ".join(args.district)
    text = brief(query)
    print(text)

    if args.save:
        match = resolve_district(query)
        if match:
            slug = match["district"].lower().replace(" ", "-")
            path = save_brief(text, f"district_{slug}_{FIN_YEAR}.txt")
            print(f"\nSaved to: {path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
