"""Contract tests for production database publishing."""

from __future__ import annotations

import sqlite3

import pytest

from scripts.sync_turso import _append_table_statements, _verify_metrics_snapshot

CREATE_SQL = """CREATE TABLE metrics_snapshot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_date TEXT NOT NULL,
    scheme TEXT NOT NULL,
    state TEXT NOT NULL,
    district TEXT NOT NULL,
    fin_year TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL,
    source_url TEXT,
    UNIQUE(snapshot_date, scheme, state, district, fin_year, metric_name)
)"""


def _local_snapshot() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute(CREATE_SQL)
    conn.execute(
        """INSERT INTO metrics_snapshot
           (snapshot_date, scheme, state, district, fin_year,
            metric_name, metric_value, source_url)
           VALUES ('2026-08-06', 'JJM', 'BIHAR', 'PATNA', '2025-2026',
                   'coverage_pct', 81.5, 'https://example.gov.in')"""
    )
    return conn


class _Result:
    def __init__(self, rows: list[list[object]]) -> None:
        self.rows = rows


class _Client:
    def __init__(self, rows: list[list[object]], remote_total: int | None = None) -> None:
        self.payload = rows
        self.remote_total = remote_total if remote_total is not None else len(rows)

    def execute(self, sql: str) -> _Result:
        if "COUNT(*)" in sql:
            return _Result([[self.remote_total]])
        return _Result(self.payload)


def test_append_statements_never_drop_history() -> None:
    conn = _local_snapshot()

    statements = _append_table_statements(conn, "metrics_snapshot", CREATE_SQL)

    assert not any("DROP TABLE" in statement for statement in statements)
    assert statements[0].startswith("CREATE TABLE IF NOT EXISTS metrics_snapshot")
    assert statements[1].startswith("INSERT OR IGNORE INTO metrics_snapshot")
    assert "(id," not in statements[1]


def test_append_verification_accepts_matching_local_payload() -> None:
    conn = _local_snapshot()
    local_payload = [
        list(
            conn.execute(
                """SELECT snapshot_date, scheme, state, district, fin_year,
                          metric_name, metric_value, source_url
                   FROM metrics_snapshot"""
            ).fetchone()
        )
    ]

    assert _verify_metrics_snapshot(conn, _Client(local_payload)) == (1, 1)


def test_append_verification_preserves_other_remote_dates() -> None:
    conn = _local_snapshot()
    local_payload = [
        list(
            conn.execute(
                """SELECT snapshot_date, scheme, state, district, fin_year,
                          metric_name, metric_value, source_url
                   FROM metrics_snapshot"""
            ).fetchone()
        )
    ]

    assert _verify_metrics_snapshot(conn, _Client(local_payload, remote_total=9)) == (1, 9)


def test_append_verification_rejects_conflicting_same_date_payload() -> None:
    conn = _local_snapshot()
    conflicting = [
        [
            "2026-08-06",
            "JJM",
            "BIHAR",
            "PATNA",
            "2025-2026",
            "coverage_pct",
            12.0,
            "https://example.gov.in",
        ]
    ]

    with pytest.raises(ValueError, match="payload mismatch"):
        _verify_metrics_snapshot(conn, _Client(conflicting))
