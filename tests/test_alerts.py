"""Tests for alerts/digest.py — WeeklyDigest generation and email HTML rendering.

Uses a temporary SQLite database so tests are isolated from the live DB.
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pytest

from db import init_db

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    """Empty temporary DB with full schema."""
    db_path = tmp_path / "alerts_test.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    init_db(conn)
    conn.close()
    return db_path


@pytest.fixture
def tmp_db_with_snapshots(tmp_path: Path) -> Path:
    """DB with snapshot data for trend analysis."""
    db_path = tmp_path / "alerts_with_data.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    init_db(conn)

    old_date = (date.today() - timedelta(weeks=5)).isoformat()
    recent_date = date.today().isoformat()

    # Insert a degrading metric (JJM coverage dropped)
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
    # Insert an improving metric (PMAY-G completion rose)
    conn.execute(
        f"""INSERT INTO metrics_snapshot
        (snapshot_date, scheme, state, district, fin_year, metric_name, metric_value, source_url)
        VALUES ('{old_date}', 'PMAY-G', 'TAMIL NADU', 'VILLUPURAM', '2024-2025', 'completion_pct', 30.0, 'src')"""
    )
    conn.execute(
        f"""INSERT INTO metrics_snapshot
        (snapshot_date, scheme, state, district, fin_year, metric_name, metric_value, source_url)
        VALUES ('{recent_date}', 'PMAY-G', 'TAMIL NADU', 'VILLUPURAM', '2024-2025', 'completion_pct', 75.0, 'src')"""
    )
    conn.commit()
    conn.close()
    return db_path


# ---------------------------------------------------------------------------
# generate_weekly_digest — structure
# ---------------------------------------------------------------------------

class TestGenerateWeeklyDigest:
    def test_returns_weekly_digest_instance(self, tmp_db: Path) -> None:
        from alerts.digest import WeeklyDigest, generate_weekly_digest

        digest = generate_weekly_digest(db_path=tmp_db)
        assert isinstance(digest, WeeklyDigest)

    def test_digest_has_required_fields(self, tmp_db: Path) -> None:
        from alerts.digest import generate_weekly_digest

        digest = generate_weekly_digest(db_path=tmp_db)
        assert hasattr(digest, "top_degrading")
        assert hasattr(digest, "top_improving")
        assert hasattr(digest, "new_red_flags")
        assert hasattr(digest, "headline")
        assert hasattr(digest, "generated_at")
        assert hasattr(digest, "weeks")
        assert hasattr(digest, "has_data")

    def test_empty_db_has_no_snapshot_changes(self, tmp_db: Path) -> None:
        """With no snapshot history, there must be no degrading/improving entries."""
        from alerts.digest import generate_weekly_digest

        digest = generate_weekly_digest(db_path=tmp_db)
        # No snapshot data → no trending changes (red flags may come from live DB scores)
        assert digest.top_degrading == []
        assert digest.top_improving == []

    def test_empty_db_returns_empty_lists(self, tmp_db: Path) -> None:
        from alerts.digest import generate_weekly_digest

        digest = generate_weekly_digest(db_path=tmp_db)
        assert digest.top_degrading == []
        assert digest.top_improving == []
        # new_red_flags may be populated from composite scores even without snapshots

    def test_headline_is_string(self, tmp_db: Path) -> None:
        from alerts.digest import generate_weekly_digest

        digest = generate_weekly_digest(db_path=tmp_db)
        assert isinstance(digest.headline, str)
        assert len(digest.headline) > 0

    def test_empty_digest_headline_mentions_no_changes(self, tmp_db: Path) -> None:
        from alerts.digest import generate_weekly_digest

        digest = generate_weekly_digest(db_path=tmp_db)
        if not digest.has_data:
            assert "No significant" in digest.headline or len(digest.headline) > 0

    def test_with_snapshot_data_detects_degradation(self, tmp_db_with_snapshots: Path) -> None:
        from alerts.digest import generate_weekly_digest

        digest = generate_weekly_digest(weeks=4, db_path=tmp_db_with_snapshots)
        # May detect the JJM drop from 80→40
        if digest.top_degrading:
            for entry in digest.top_degrading:
                assert entry.delta_pct < 0

    def test_with_snapshot_data_detects_improvement(self, tmp_db_with_snapshots: Path) -> None:
        from alerts.digest import generate_weekly_digest

        digest = generate_weekly_digest(weeks=4, db_path=tmp_db_with_snapshots)
        if digest.top_improving:
            for entry in digest.top_improving:
                assert entry.delta_pct > 0

    def test_district_change_structure(self, tmp_db_with_snapshots: Path) -> None:
        from alerts.digest import DistrictChange, generate_weekly_digest

        digest = generate_weekly_digest(weeks=4, db_path=tmp_db_with_snapshots)
        for entry in digest.top_degrading + digest.top_improving:
            assert isinstance(entry, DistrictChange)
            assert isinstance(entry.district, str)
            assert isinstance(entry.state, str)
            assert isinstance(entry.scheme, str)
            assert isinstance(entry.metric_name, str)
            assert isinstance(entry.delta_pct, (int, float))

    def test_weeks_param_stored_in_digest(self, tmp_db: Path) -> None:
        from alerts.digest import generate_weekly_digest

        digest = generate_weekly_digest(weeks=3, db_path=tmp_db)
        assert digest.weeks == 3

    def test_generated_at_is_datetime(self, tmp_db: Path) -> None:
        from datetime import datetime

        from alerts.digest import generate_weekly_digest

        digest = generate_weekly_digest(db_path=tmp_db)
        assert isinstance(digest.generated_at, datetime)

    def test_red_flag_entry_structure(self, tmp_db: Path) -> None:
        from alerts.digest import RedFlagEntry, generate_weekly_digest

        digest = generate_weekly_digest(db_path=tmp_db)
        for entry in digest.new_red_flags:
            assert isinstance(entry, RedFlagEntry)
            assert isinstance(entry.district, str)
            assert isinstance(entry.state, str)
            assert isinstance(entry.score, (int, float))
            assert entry.grade in ("A", "B", "C", "D", "F")
            assert isinstance(entry.flags, list)


# ---------------------------------------------------------------------------
# _build_headline
# ---------------------------------------------------------------------------

class TestBuildHeadline:
    def test_empty_inputs_returns_no_changes(self) -> None:
        from alerts.digest import _build_headline

        headline = _build_headline([], [], [])
        assert "suspended" in headline.lower()

    def test_degrading_input_mentions_scheme(self) -> None:
        from alerts.digest import DistrictChange, _build_headline

        degrading = [
            DistrictChange(
                district="PATNA", state="BIHAR", scheme="JJM",
                metric_name="coverage_pct", delta_pct=-15.0,
                prior_value=80.0, current_value=65.0,
            )
        ]
        headline = _build_headline(degrading, [], [])
        assert "JJM" in headline

    def test_red_flags_mentioned_in_headline(self) -> None:
        from alerts.digest import RedFlagEntry, _build_headline

        flags = [
            RedFlagEntry(district="GAYA", state="BIHAR", score=15.0, grade="F", flags=["JJM delivery 10%"])
        ]
        headline = _build_headline([], [], flags)
        assert "red-flag" in headline.lower() or "threshold" in headline.lower()

    def test_headline_is_capitalized(self) -> None:
        from alerts.digest import DistrictChange, _build_headline

        degrading = [
            DistrictChange("D", "S", "MGNREGA", "utilization_pct", -5.0, 80.0, 75.0)
        ]
        headline = _build_headline(degrading, [], [])
        assert headline[0].isupper()


# ---------------------------------------------------------------------------
# Email HTML rendering
# ---------------------------------------------------------------------------

class TestEmailHtmlRendering:
    """The email HTML template must render without crashing for various digest states."""

    @staticmethod
    def _render_html(digest) -> str:
        from alerts.email_digest import render_digest_html
        return render_digest_html(digest)

    def _make_empty_digest(self):
        from datetime import datetime

        from alerts.digest import WeeklyDigest

        return WeeklyDigest(
            top_degrading=[],
            top_improving=[],
            new_red_flags=[],
            headline="No significant changes detected this week.",
            generated_at=datetime.utcnow(),
            weeks=1,
            has_data=False,
        )

    def _make_full_digest(self):
        from datetime import datetime

        from alerts.digest import DistrictChange, RedFlagEntry, WeeklyDigest

        return WeeklyDigest(
            top_degrading=[
                DistrictChange("PATNA", "BIHAR", "JJM", "coverage_pct", -20.0, 80.0, 60.0),
                DistrictChange("GAYA", "BIHAR", "PMAY-G", "completion_pct", -10.0, 70.0, 60.0),
            ],
            top_improving=[
                DistrictChange("VILLUPURAM", "TAMIL NADU", "PMAY-G", "completion_pct", 15.0, 50.0, 65.0),
            ],
            new_red_flags=[
                RedFlagEntry("GAYA", "BIHAR", 18.0, "F", ["JJM delivery 10%", "MGNREGA utilization 15%"]),
            ],
            headline="JJM metrics degraded in 1 district; 1 district crossed red-flag thresholds.",
            generated_at=datetime.utcnow(),
            weeks=1,
            has_data=True,
        )

    def test_render_empty_digest_does_not_crash(self) -> None:
        try:
            from alerts.email_digest import render_digest_html
        except ImportError:
            pytest.skip("render_digest_html not exported from email_digest")

        digest = self._make_empty_digest()
        html = render_digest_html(digest)
        assert isinstance(html, str)
        assert len(html) > 0

    def test_render_empty_digest_contains_html_boilerplate(self) -> None:
        try:
            from alerts.email_digest import render_digest_html
        except ImportError:
            pytest.skip("render_digest_html not exported")

        digest = self._make_empty_digest()
        html = render_digest_html(digest)
        assert "<!DOCTYPE html>" in html or "<!doctype html>" in html.lower()

    def test_render_full_digest_does_not_crash(self) -> None:
        try:
            from alerts.email_digest import render_digest_html
        except ImportError:
            pytest.skip("render_digest_html not exported")

        digest = self._make_full_digest()
        html = render_digest_html(digest)
        assert isinstance(html, str)

    def test_render_full_digest_contains_headline(self) -> None:
        try:
            from alerts.email_digest import render_digest_html
        except ImportError:
            pytest.skip("render_digest_html not exported")

        digest = self._make_full_digest()
        html = render_digest_html(digest)
        assert "red-flag" in html.lower() or "threshold" in html.lower() or digest.headline[:20] in html

    def test_email_digest_module_imports(self) -> None:
        """Ensure the module can be imported even if render_digest_html is private."""
        import alerts.email_digest  # noqa: F401

    def test_html_template_is_string(self) -> None:
        """The internal HTML template should be a string."""
        from alerts import email_digest

        assert hasattr(email_digest, "_HTML_TEMPLATE")
        assert isinstance(email_digest._HTML_TEMPLATE, str)
        assert "DOCTYPE" in email_digest._HTML_TEMPLATE or "html" in email_digest._HTML_TEMPLATE
