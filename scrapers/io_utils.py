"""Shared helper for scrapers — atomic curated/raw JSON writes.

Every scraper's save path routes through `atomic_write_json` instead of
calling `Path.write_text` directly. This closes two failure modes that have
each caused real data loss in this repo (see learnings.md):

1. A crash, timeout, or Ctrl-C mid-write used to leave a truncated/corrupt
   JSON file at the destination, because `write_text` truncates the target
   file in place before writing new content. This writes to a temp file in
   the same directory first, then `os.replace()`s over the destination — the
   rename is atomic at the filesystem level, so the destination is always
   either the complete old file or the complete new one, never a partial one.
2. A scraper that fetched nothing (portal timeout, layout change, API
   outage) used to silently overwrite a good "*_latest.json" with an empty
   list, destroying the last known-good data with no recovery but `git
   restore`. `atomic_write_json` is a no-op whenever `records` is empty — an
   existing file at `path`, if any, is left completely untouched.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# api.data.gov.in black-holes requests whose User-Agent is python-requests/*
# (connection accepted, response never sent → ReadTimeout). Verified across
# all 14 resource IDs on 2026-08-04; any browser-ish UA answers in <2s. The
# 2026-08-03/04 "platform outage" was this, not the platform.
DATAGOV_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

# Public demo key shared by every data.gov.in caller in this repo. It rate-limits
# hard (429s across ALL demo-key users, not just us) and is the fallback only —
# set DATA_GOV_IN_API_KEY in the environment to a registered project key to lift
# the ceiling before big pulls. Never commit a project key; the demo key is
# public by design (it ships in data.gov.in's own docs).
DATAGOV_DEMO_KEY = "579b464db66ec23bdd000001cdc3b564546246a772a26393094f5645"


def datagov_api_key() -> str:
    """Return the data.gov.in API key — DATA_GOV_IN_API_KEY env var if set,
    else the public demo key. Single source of truth so a project key can be
    threaded in via one env var without editing seven scrapers."""
    return os.environ.get("DATA_GOV_IN_API_KEY", "").strip() or DATAGOV_DEMO_KEY


# Indian financial year runs 1 April–31 March. Computed in IST (UTC+5:30) so the
# label doesn't flip a few hours early around the 1 April boundary.
_IST = timedelta(hours=5, minutes=30)


def current_indian_fy() -> str:
    """The running Indian FY label, e.g. '2026-2027'. Before April we are still
    in the FY that began the previous calendar year. Correct target for
    monthly-snapshot data (NSAP beneficiary counts) where 'latest' is best."""
    now = datetime.now(UTC) + _IST
    start = now.year if now.month >= 4 else now.year - 1
    return f"{start}-{start + 1}"


def last_complete_indian_fy() -> str:
    """The most recently COMPLETED Indian FY (current minus one). Correct default
    for cumulative annual scrapes (MGNREGA financial_statement, PMAY-G) run
    mid-year: the running FY holds only partial-year totals, so pulling it would
    replace a complete year with a smaller in-progress one."""
    start = int(current_indian_fy().split("-")[0]) - 1
    return f"{start}-{start + 1}"


def datagov_session(total_retries: int = 5, backoff_factor: float = 2.0) -> requests.Session:
    """Session pre-configured for api.data.gov.in's two platform quirks.

    1. Browser User-Agent (see DATAGOV_UA above — the default UA is
       black-holed).
    2. HTTP-level retries with backoff for 429/5xx, honouring Retry-After —
       the shared demo API key rate-limits hard, and a swallowed 429 once
       truncated an NSAP pull by 15% mid-pagination.

    Every scraper that touches data.gov.in must build its session here so
    neither fix can regress per-file.
    """
    session = requests.Session()
    retry = Retry(
        total=total_retries,
        status_forcelist=[429, 500, 502, 503, 504],
        backoff_factor=backoff_factor,
        respect_retry_after_header=True,
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({"User-Agent": DATAGOV_UA, "Accept": "application/json"})
    return session


def atomic_write_json(path: Path, records: list[Any]) -> bool:
    """Write `records` to `path` as JSON, atomically, on success only.

    Returns False and leaves any existing file at `path` untouched when
    `records` is empty. Returns True after a completed, atomic write.
    """
    if not records:
        return False

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise
    return True
