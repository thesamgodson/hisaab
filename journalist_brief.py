"""Backward-compatible wrapper — all logic lives in briefs/ package."""

from __future__ import annotations

import sys

from briefs.cli import main, save_brief
from briefs.district import brief, resolve_district
from briefs.formatting import BRIEFS_DIR, FIN_YEAR
from briefs.red_flags import detect_flags as _detect_flags
from briefs.red_flags import scan_red_flags
from briefs.state import state_brief

__all__ = [
    "BRIEFS_DIR",
    "FIN_YEAR",
    "_detect_flags",
    "brief",
    "main",
    "resolve_district",
    "save_brief",
    "scan_red_flags",
    "state_brief",
]

if __name__ == "__main__":
    sys.exit(main())
