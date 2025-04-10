"""Journalist briefing package for Hisaab transparency data."""

from briefs.cli import main, save_brief
from briefs.district import brief, resolve_district
from briefs.red_flags import detect_flags, scan_red_flags
from briefs.state import state_brief

__all__ = [
    "brief",
    "detect_flags",
    "main",
    "resolve_district",
    "save_brief",
    "scan_red_flags",
    "state_brief",
]
