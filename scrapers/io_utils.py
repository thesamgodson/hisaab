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
