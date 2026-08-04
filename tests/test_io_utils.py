"""Unit tests for scrapers.io_utils.atomic_write_json.

Covers the two failure modes this helper exists to close (see learnings.md,
"Delete-then-scrape loses data when the scrape dies"):
  1. Empty results must never overwrite a previously-good file.
  2. A write that dies partway must never leave a truncated/corrupt file at
     the destination — the destination is always the old complete file or
     the new complete file.
"""

from __future__ import annotations

import contextlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scrapers.io_utils import atomic_write_json


class TestAtomicWriteJsonEmptyGuard:
    def test_empty_list_does_not_create_file(self, tmp_path):
        path = tmp_path / "curated.json"

        wrote = atomic_write_json(path, [])

        assert wrote is False
        assert not path.exists()

    def test_empty_list_leaves_existing_good_file_untouched(self, tmp_path):
        path = tmp_path / "curated.json"
        good_payload = [{"district": "PATNA", "state": "BIHAR"}]
        path.write_text(json.dumps(good_payload), encoding="utf-8")

        wrote = atomic_write_json(path, [])

        assert wrote is False
        assert json.loads(path.read_text(encoding="utf-8")) == good_payload

    def test_no_stray_temp_file_left_behind_on_empty_input(self, tmp_path):
        path = tmp_path / "curated.json"

        atomic_write_json(path, [])

        assert list(tmp_path.iterdir()) == []


class TestAtomicWriteJsonSuccess:
    def test_writes_records_as_json(self, tmp_path):
        path = tmp_path / "curated.json"
        records = [{"district": "PATNA", "state": "BIHAR"}, {"district": "GAYA", "state": "BIHAR"}]

        wrote = atomic_write_json(path, records)

        assert wrote is True
        assert json.loads(path.read_text(encoding="utf-8")) == records

    def test_overwrites_previous_content_on_new_success(self, tmp_path):
        path = tmp_path / "curated.json"
        atomic_write_json(path, [{"district": "OLD"}])

        atomic_write_json(path, [{"district": "NEW"}])

        assert json.loads(path.read_text(encoding="utf-8")) == [{"district": "NEW"}]

    def test_creates_parent_directories(self, tmp_path):
        path = tmp_path / "nested" / "dir" / "curated.json"

        atomic_write_json(path, [{"district": "PATNA"}])

        assert path.exists()

    def test_no_stray_temp_file_left_behind_on_success(self, tmp_path):
        path = tmp_path / "curated.json"

        atomic_write_json(path, [{"district": "PATNA"}])

        assert list(tmp_path.iterdir()) == [path]


class TestAtomicWriteJsonCrashSafety:
    def test_mid_write_crash_leaves_previous_good_file_intact(self, tmp_path, monkeypatch):
        path = tmp_path / "curated.json"
        good_payload = [{"district": "PATNA", "state": "BIHAR"}]
        atomic_write_json(path, good_payload)

        def boom(*args, **kwargs):
            raise OSError("simulated mid-scrape crash")

        monkeypatch.setattr(json, "dump", boom)

        # The crash is expected to propagate — the point is what survives on disk.
        with contextlib.suppress(OSError):
            atomic_write_json(path, [{"district": "CORRUPTED"}])

        assert json.loads(path.read_text(encoding="utf-8")) == good_payload

    def test_mid_write_crash_leaves_no_stray_temp_file(self, tmp_path, monkeypatch):
        path = tmp_path / "curated.json"
        atomic_write_json(path, [{"district": "PATNA"}])

        monkeypatch.setattr(json, "dump", lambda *a, **k: (_ for _ in ()).throw(OSError("boom")))

        with contextlib.suppress(OSError):
            atomic_write_json(path, [{"district": "CORRUPTED"}])

        assert list(tmp_path.iterdir()) == [path]

    def test_crash_propagates_to_caller(self, tmp_path, monkeypatch):
        path = tmp_path / "curated.json"

        def boom(*args, **kwargs):
            raise OSError("simulated crash")

        monkeypatch.setattr(json, "dump", boom)

        try:
            atomic_write_json(path, [{"district": "X"}])
            raised = False
        except OSError:
            raised = True

        assert raised, "a mid-write failure must propagate, not be swallowed"
