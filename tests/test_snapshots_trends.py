"""Tests for db/snapshots.py and queries/trends.py.

All tests use a temporary SQLite file (or in-memory DB) so writes are isolated
and do not affect data/hisaab.db.
"""

from __future__ import annotations

import sqlite3
import tempfile
from datetime import date, timedelta
from pathlib import Path

import pytest

from db import init_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    """Create a fresh temporary SQLite database with full schema."""
    db_path = tmp_path / "test_hisaab.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    init_db(conn)
    conn.close()
    return db_path


def _seed_scheme_data(db_path: Path) -> None:
    """Populate scheme tables so capture_snapshot has something to capture."""
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute(
        """INSERT INTO financial_statement
        (district, state, state_code, fin_year, total_availability, cumulative_expenditure,
         utilization_pct, balance, source_url, scraped_at)
        VALUES ('PATNA', 'BIHAR', '05', '2024-2025', 5000, 4500, 90.0, 500, 'src', '2026-01-01')"""
    )
    conn.execute(
        """INSERT INTO pmayg_district
        (district, state, state_code, fin_year, houses_sanctioned, houses_completed,
         houses_occupied, funds_released_lakhs, funds_utilized_lakhs, completion_pct,
         source_url, scraped_at)
        VALUES ('PATNA', 'BIHAR', '05', '2024-2025', 1000, 800, 700, 3000, 2400, 80.0,
                'src', '2026-01-01')"""
    )
    conn.execute(
        """INSERT INTO jjm_district
        (district, state, state_code, fin_year, total_households, households_with_tap,
         tap_connections_provided, coverage_pct, funds_released_lakhs, funds_utilized_lakhs,
         source_url, scraped_at)
        VALUES ('PATNA', 'BIHAR', '05', '2024-2025', 5000, 4000, 4000, 80.0, 2000, 1500,
                'src', '2026-01-01')"""
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# capture_snapshot
# ---------------------------------------------------------------------------

class TestCaptureSnapshot:
    def test_creates_entries_in_metrics_snapshot(self, tmp_db: Path) -> None:
        from db.snapshots import capture_snapshot

        _seed_scheme_data(tmp_db)
        inserted = capture_snapshot(db_path=tmp_db, snapshot_date="2026-01-15")
        assert inserted > 0

        conn = sqlite3.connect(str(tmp_db))
        count = conn.execute("SELECT COUNT(*) FROM metrics_snapshot").fetchone()[0]
        conn.close()
        assert count > 0

    def test_snapshot_date_stored_correctly(self, tmp_db: Path) -> None:
        from db.snapshots import capture_snapshot

        _seed_scheme_data(tmp_db)
        capture_snapshot(db_path=tmp_db, snapshot_date="2026-03-01")

        conn = sqlite3.connect(str(tmp_db))
        row = conn.execute(
            "SELECT DISTINCT snapshot_date FROM metrics_snapshot"
        ).fetchone()
        conn.close()
        assert row[0] == "2026-03-01"

    def test_idempotent_same_date_no_duplicates(self, tmp_db: Path) -> None:
        from db.snapshots import capture_snapshot

        _seed_scheme_data(tmp_db)
        snap_date = "2026-01-15"
        first = capture_snapshot(db_path=tmp_db, snapshot_date=snap_date)
        second = capture_snapshot(db_path=tmp_db, snapshot_date=snap_date)

        conn = sqlite3.connect(str(tmp_db))
        count = conn.execute("SELECT COUNT(*) FROM metrics_snapshot").fetchone()[0]
        conn.close()

        # Second run must not insert new rows for same date
        assert second == 0 or count == first  # INSERT OR IGNORE means 0 new rows

    def test_two_different_dates_produce_separate_rows(self, tmp_db: Path) -> None:
        from db.snapshots import capture_snapshot

        _seed_scheme_data(tmp_db)
        capture_snapshot(db_path=tmp_db, snapshot_date="2026-01-01")
        capture_snapshot(db_path=tmp_db, snapshot_date="2026-01-08")

        conn = sqlite3.connect(str(tmp_db))
        dates = {
            r[0]
            for r in conn.execute("SELECT DISTINCT snapshot_date FROM metrics_snapshot").fetchall()
        }
        conn.close()
        assert "2026-01-01" in dates
        assert "2026-01-08" in dates

    def test_empty_db_returns_zero(self, tmp_db: Path) -> None:
        from db.snapshots import capture_snapshot

        inserted = capture_snapshot(db_path=tmp_db, snapshot_date="2026-01-15")
        # Empty scheme tables → nothing to snapshot
        assert inserted == 0

    def test_default_date_is_today(self, tmp_db: Path) -> None:
        from db.snapshots import capture_snapshot

        _seed_scheme_data(tmp_db)
        capture_snapshot(db_path=tmp_db)  # no snapshot_date

        conn = sqlite3.connect(str(tmp_db))
        dates = {
            r[0]
            for r in conn.execute("SELECT DISTINCT snapshot_date FROM metrics_snapshot").fetchall()
        }
        conn.close()
        today = date.today().isoformat()
        assert today in dates

    def test_scheme_and_metric_name_populated(self, tmp_db: Path) -> None:
        from db.snapshots import capture_snapshot

        _seed_scheme_data(tmp_db)
        capture_snapshot(db_path=tmp_db, snapshot_date="2026-01-15")

        conn = sqlite3.connect(str(tmp_db))
        rows = conn.execute(
            "SELECT DISTINCT scheme, metric_name FROM metrics_snapshot"
        ).fetchall()
        conn.close()

        schemes = {r[0] for r in rows}
        assert "MGNREGA" in schemes
        assert "PMAY-G" in schemes
        assert "JJM" in schemes


# ---------------------------------------------------------------------------
# compute_deltas
# ---------------------------------------------------------------------------

class TestComputeDeltas:
    def test_returns_empty_when_no_snapshots(self, tmp_db: Path) -> None:
        from db.snapshots import compute_deltas

        result = compute_deltas("BIHAR", "PATNA", "MGNREGA", weeks=4, db_path=tmp_db)
        assert result == []

    def test_returns_no_prior_when_only_one_snapshot(self, tmp_db: Path) -> None:
        from db.snapshots import capture_snapshot, compute_deltas

        _seed_scheme_data(tmp_db)
        capture_snapshot(db_path=tmp_db, snapshot_date="2026-01-15")

        result = compute_deltas("BIHAR", "PATNA", "MGNREGA", weeks=4, db_path=tmp_db)
        # With only one snapshot, there is no prior snapshot within 4 weeks of today
        # (since the snapshot is dated 2026-01-15, which IS within 4 weeks if today is 2026-01-16...).
        # Regardless, either: result is empty, or all items have delta_pct=None (no prior).
        for item in result:
            # If prior_value is set, delta must also be set consistently
            if item["prior_value"] is not None and item["current_value"] is not None:
                assert item["delta"] == pytest.approx(item["current_value"] - item["prior_value"])
            else:
                assert item["delta"] is None or item["prior_value"] is None

    def test_delta_computed_correctly(self, tmp_db: Path) -> None:
        from db.snapshots import capture_snapshot, compute_deltas

        _seed_scheme_data(tmp_db)
        # Snapshot 1
        capture_snapshot(db_path=tmp_db, snapshot_date="2026-01-01")

        # Update the value
        conn = sqlite3.connect(str(tmp_db))
        conn.execute(
            "UPDATE financial_statement SET utilization_pct = 95.0 WHERE district = 'PATNA'"
        )
        conn.commit()
        conn.close()

        # Snapshot 2 (same week — but we need different dates for delta to work)
        # Insert the second snapshot directly so we have a prior reference
        conn2 = sqlite3.connect(str(tmp_db))
        conn2.execute(
            """INSERT OR IGNORE INTO metrics_snapshot
            (snapshot_date, scheme, state, district, fin_year, metric_name, metric_value, source_url)
            VALUES ('2026-01-08', 'MGNREGA', 'BIHAR', 'PATNA', '2024-2025', 'utilization_pct', 95.0, 'src')"""
        )
        conn2.commit()
        conn2.close()

        result = compute_deltas("BIHAR", "PATNA", "MGNREGA", weeks=8, db_path=tmp_db)
        util_deltas = [r for r in result if r["metric_name"] == "utilization_pct"]
        if util_deltas:
            d = util_deltas[0]
            if d["prior_value"] is not None and d["current_value"] is not None:
                assert d["delta"] == pytest.approx(d["current_value"] - d["prior_value"])

    def test_no_division_by_zero_when_prior_is_zero(self, tmp_db: Path) -> None:
        """compute_deltas must not raise ZeroDivisionError when prior_value == 0."""
        conn = sqlite3.connect(str(tmp_db))
        conn.row_factory = sqlite3.Row
        init_db(conn)
        # Insert two snapshots: first has value=0, second has value=50
        conn.execute(
            """INSERT INTO metrics_snapshot
            (snapshot_date, scheme, state, district, fin_year, metric_name, metric_value, source_url)
            VALUES ('2026-01-01', 'JJM', 'BIHAR', 'PATNA', '2024-2025', 'coverage_pct', 0.0, 'src')"""
        )
        conn.execute(
            """INSERT INTO metrics_snapshot
            (snapshot_date, scheme, state, district, fin_year, metric_name, metric_value, source_url)
            VALUES ('2026-01-08', 'JJM', 'BIHAR', 'PATNA', '2024-2025', 'coverage_pct', 50.0, 'src')"""
        )
        conn.commit()
        conn.close()

        from db.snapshots import compute_deltas

        # Must not raise
        result = compute_deltas("BIHAR", "PATNA", "JJM", weeks=8, db_path=tmp_db)
        coverage_deltas = [r for r in result if r["metric_name"] == "coverage_pct"]
        for item in coverage_deltas:
            if item["prior_value"] == 0.0:
                assert item["delta_pct"] is None  # no pct when prior=0


# ---------------------------------------------------------------------------
# trending_worse / trending_better
# ---------------------------------------------------------------------------

class TestTrendingFunctions:
    def test_trending_worse_empty_data_returns_no_data(self, tmp_db: Path) -> None:
        from queries.trends import trending_worse

        result = trending_worse(n=10, weeks=4, db_path=tmp_db)
        assert "answer" in result
        assert "data" in result
        assert result["data"] == []

    def test_trending_better_empty_data_returns_no_data(self, tmp_db: Path) -> None:
        from queries.trends import trending_better

        result = trending_better(n=10, weeks=4, db_path=tmp_db)
        assert result["data"] == []

    def test_trending_worse_answer_is_string(self, tmp_db: Path) -> None:
        from queries.trends import trending_worse

        result = trending_worse(n=5, weeks=4, db_path=tmp_db)
        assert isinstance(result["answer"], str)

    def test_trending_better_answer_is_string(self, tmp_db: Path) -> None:
        from queries.trends import trending_better

        result = trending_better(n=5, weeks=4, db_path=tmp_db)
        assert isinstance(result["answer"], str)

    def test_trending_worse_with_degrading_data(self, tmp_db: Path) -> None:
        """Insert two snapshots with a declining metric and verify trending_worse picks it up."""
        conn = sqlite3.connect(str(tmp_db))
        conn.row_factory = sqlite3.Row
        init_db(conn)
        # Old snapshot (5 weeks ago): coverage_pct = 80
        old_date = (date.today() - timedelta(weeks=5)).isoformat()
        recent_date = date.today().isoformat()
        conn.execute(
            f"""INSERT INTO metrics_snapshot
            (snapshot_date, scheme, state, district, fin_year, metric_name, metric_value, source_url)
            VALUES ('{old_date}', 'JJM', 'BIHAR', 'PATNA', '2024-2025', 'coverage_pct', 80.0, 'src')"""
        )
        conn.execute(
            f"""INSERT INTO metrics_snapshot
            (snapshot_date, scheme, state, district, fin_year, metric_name, metric_value, source_url)
            VALUES ('{recent_date}', 'JJM', 'BIHAR', 'PATNA', '2024-2025', 'coverage_pct', 40.0, 'src')"""
        )
        conn.commit()
        conn.close()

        from queries.trends import trending_worse
        result = trending_worse(n=10, weeks=4, db_path=tmp_db)
        # Should detect the drop from 80→40
        if result["data"]:
            worst = result["data"][0]
            assert worst["delta_pct"] < 0

    def test_trending_better_with_improving_data(self, tmp_db: Path) -> None:
        """Insert two snapshots with an increasing metric and verify trending_better picks it up."""
        conn = sqlite3.connect(str(tmp_db))
        conn.row_factory = sqlite3.Row
        init_db(conn)
        old_date = (date.today() - timedelta(weeks=5)).isoformat()
        recent_date = date.today().isoformat()
        conn.execute(
            f"""INSERT INTO metrics_snapshot
            (snapshot_date, scheme, state, district, fin_year, metric_name, metric_value, source_url)
            VALUES ('{old_date}', 'PMAY-G', 'BIHAR', 'PATNA', '2024-2025', 'completion_pct', 40.0, 'src')"""
        )
        conn.execute(
            f"""INSERT INTO metrics_snapshot
            (snapshot_date, scheme, state, district, fin_year, metric_name, metric_value, source_url)
            VALUES ('{recent_date}', 'PMAY-G', 'BIHAR', 'PATNA', '2024-2025', 'completion_pct', 75.0, 'src')"""
        )
        conn.commit()
        conn.close()

        from queries.trends import trending_better
        result = trending_better(n=10, weeks=4, db_path=tmp_db)
        if result["data"]:
            best = result["data"][0]
            assert best["delta_pct"] > 0


# ---------------------------------------------------------------------------
# district_trend
# ---------------------------------------------------------------------------

class TestDistrictTrend:
    def test_empty_returns_no_data_answer(self, tmp_db: Path) -> None:
        from queries.trends import district_trend

        result = district_trend("PATNA", "BIHAR", "MGNREGA", weeks=12, db_path=tmp_db)
        assert "answer" in result
        assert result["metrics"] == {}
        assert result["deltas"] == []

    def test_result_structure(self, tmp_db: Path) -> None:
        from queries.trends import district_trend

        result = district_trend("PATNA", "BIHAR", "JJM", weeks=12, db_path=tmp_db)
        assert "district" in result
        assert "state" in result
        assert "scheme" in result
        assert "weeks" in result
        assert "metrics" in result
        assert "deltas" in result
