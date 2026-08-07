from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pytest

from db import init_db
from db.snapshot_metrics import METRIC_SPECS
from db.snapshots import capture_snapshot, compute_deltas, get_biggest_changes, get_trend
from queries.trends import district_trend, trending_better, trending_worse


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    path = tmp_path / "snapshot-honesty.db"
    with sqlite3.connect(path) as connection:
        init_db(connection)
    return path


def _insert_snapshot(
    connection: sqlite3.Connection,
    snapshot_date: str,
    scheme: str,
    metric: str,
    value: float,
    fin_year: str = "2025-2026",
) -> None:
    connection.execute(
        """INSERT INTO metrics_snapshot
           (snapshot_date, scheme, state, district, fin_year,
            metric_name, metric_value, source_url)
           VALUES (?, ?, 'BIHAR', 'PATNA', ?, ?, ?, 'src')""",
        (snapshot_date, scheme, fin_year, metric, value),
    )


def test_unsafe_metrics_are_absent_from_capture_catalog():
    pairs = {(spec[0], spec[5]) for spec in METRIC_SPECS}
    assert ("PM Kisan", "amount_paid_lakhs") not in pairs
    assert ("PM POSHAN", "utilization_pct") not in pairs
    assert ("NSAP", "amount_paid_lakhs") not in pairs
    assert ("PDS/NFSA", "offtake_pct") not in pairs
    assert ("MGNREGA", "amount_unrecovered_lakhs") not in pairs
    assert ("MGNREGA", "amount_unrecovered_rupees") in pairs


def test_capture_uses_rupees_name_and_omits_placeholder_metrics(tmp_db: Path):
    with sqlite3.connect(tmp_db) as connection:
        connection.execute(
            """INSERT INTO misappropriation
               (district, state, state_code, fin_year, amount_unrecovered,
                source_url, scraped_at)
               VALUES ('PATNA', 'BIHAR', '05', '2024-2025', 12345, 'mgnrega', '2026-01-01')"""
        )
        seeds = (
            ("pmkisan_district", "amount_paid_lakhs", 99),
            ("pmposhan_district", "utilization_pct", 88),
            ("nsap_district", "amount_paid_lakhs", 77),
            ("nfsa_district", "offtake_pct", 66),
        )
        for table, field, value in seeds:
            connection.execute(
                f"""INSERT INTO {table}
                    (district, state, fin_year, {field}, source_url, scraped_at)
                    VALUES ('PATNA', 'BIHAR', '2025-2026', ?, 'unsafe', '2026-01-01')""",
                (value,),
            )
    capture_snapshot(tmp_db, "2026-01-02")
    with sqlite3.connect(tmp_db) as connection:
        rows = connection.execute("SELECT scheme, metric_name, metric_value FROM metrics_snapshot").fetchall()
    pairs = {(row[0], row[1]) for row in rows}
    assert ("MGNREGA", "amount_unrecovered_rupees") in pairs
    assert not pairs & {
        ("PM Kisan", "amount_paid_lakhs"),
        ("PM POSHAN", "utilization_pct"),
        ("NSAP", "amount_paid_lakhs"),
        ("PDS/NFSA", "offtake_pct"),
    }


def test_capture_keeps_row_source_and_latest_period_only(tmp_db: Path):
    with sqlite3.connect(tmp_db) as connection:
        connection.executemany(
            """INSERT INTO pmayg_finance
               (state, fin_year, utilized_lakhs, source_url, scraped_at)
               VALUES (?, ?, ?, ?, ?)""",
            [
                ("BIHAR", "2024-2025", 10, "old-source", "2025-01-01"),
                ("BIHAR", "2025-2026", 20, "current-source", "2026-01-01"),
                ("JHARKHAND", "2024-2025", 10, "old-positive", "2025-01-01"),
                ("JHARKHAND", "2025-2026", 0, "current-ambiguous", "2026-01-01"),
            ],
        )
    capture_snapshot(tmp_db, "2026-01-02")
    with sqlite3.connect(tmp_db) as connection:
        rows = connection.execute(
            """SELECT fin_year, metric_value, source_url FROM metrics_snapshot
               WHERE scheme = 'PMAY-G' AND district = 'ALL'
                 AND metric_name = 'utilized_lakhs'"""
        ).fetchall()
    assert rows == [("2025-2026", 20.0, "current-source")]


def test_capture_fails_closed_when_an_audited_table_is_missing(tmp_db: Path):
    with sqlite3.connect(tmp_db) as connection:
        connection.execute("DROP TABLE pmgsy_district")
    with pytest.raises(sqlite3.OperationalError):
        capture_snapshot(tmp_db, "2026-01-02")


def test_legacy_unsafe_rows_are_filtered_from_all_trend_access(tmp_db: Path):
    old = (date.today() - timedelta(weeks=5)).isoformat()
    current = date.today().isoformat()
    with sqlite3.connect(tmp_db) as connection:
        _insert_snapshot(connection, old, "PM Kisan", "amount_paid_lakhs", 10)
        _insert_snapshot(connection, current, "PM Kisan", "amount_paid_lakhs", 20)
        _insert_snapshot(connection, old, "JJM", "coverage_pct", 40)
        _insert_snapshot(connection, current, "JJM", "coverage_pct", 50)

    changes = get_biggest_changes(n=10, weeks=4, db_path=tmp_db)
    assert [(item["scheme"], item["metric_name"]) for item in changes] == [("JJM", "coverage_pct")]
    assert changes[0]["current_source_url"] == changes[0]["prior_source_url"] == "src"
    deltas = compute_deltas("BIHAR", "PATNA", "JJM", 4, tmp_db)
    assert deltas[0]["current_source_url"] == deltas[0]["prior_source_url"] == "src"
    series = get_trend("BIHAR", "PATNA", "JJM", "coverage_pct", 12, tmp_db)
    assert series and all(point["source_url"] == "src" for point in series)
    assert get_trend("BIHAR", "PATNA", "PM Kisan", "amount_paid_lakhs", 12, tmp_db) == []
    result = district_trend("PATNA", "BIHAR", "PM Kisan", 12, tmp_db)
    assert result["metrics"] == {}


def test_neutral_changes_match_financial_year_and_publish_units(tmp_db: Path):
    old = (date.today() - timedelta(weeks=5)).isoformat()
    current = date.today().isoformat()
    with sqlite3.connect(tmp_db) as connection:
        for year, before, after in (("2024-2025", 10, 90), ("2025-2026", 20, 30)):
            _insert_snapshot(connection, old, "PMAY-G", "utilized_lakhs", before, year)
            _insert_snapshot(connection, current, "PMAY-G", "utilized_lakhs", after, year)

    changes = get_biggest_changes(n=10, weeks=4, db_path=tmp_db)
    assert len(changes) == 1
    assert changes[0]["fin_year"] == "2025-2026"
    assert changes[0]["unit"] == "INR lakh"
    assert changes[0]["direction_judgment"] == "not_audited"


def test_better_worse_and_digest_judgments_are_suspended(tmp_db: Path):
    old = (date.today() - timedelta(weeks=5)).isoformat()
    current = date.today().isoformat()
    with sqlite3.connect(tmp_db) as connection:
        _insert_snapshot(connection, old, "JJM", "coverage_pct", 80)
        _insert_snapshot(connection, current, "JJM", "coverage_pct", 40)

    worse = trending_worse(db_path=tmp_db)
    better = trending_better(db_path=tmp_db)
    assert worse["data"] == better["data"] == []
    assert worse["judgment_status"] == better["judgment_status"] == "suspended"

    from alerts.digest import generate_weekly_digest

    digest = generate_weekly_digest(db_path=tmp_db)
    assert digest.top_degrading == digest.top_improving == []
    assert digest.new_red_flags == []
    assert "suspended" in digest.headline.lower()
    assert digest.trend_judgments_suspended is True
    assert digest.red_flag_crossings_suspended is True
