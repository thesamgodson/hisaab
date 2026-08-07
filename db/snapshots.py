"""Neutral temporal snapshots for explicitly audited scheme metrics."""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from db.connection import get_connection
from db.snapshot_metrics import METRIC_SPECS, MetricSpec, audited_metric_names, is_audited_metric, metric_context


def _metric_rows(conn: sqlite3.Connection, spec: MetricSpec):
    _, table, district_col, state_col, year_col, _, value_col = spec
    district = district_col or "'ALL'"
    partition = f"{state_col}, {district_col}" if district_col else state_col
    value_filter = "metric_rank = 1" if district_col else "metric_rank = 1 AND metric_value > 0"
    output_filter = f"{value_filter} AND source_url IS NOT NULL AND source_url != ''"
    return conn.execute(
        f"""
        WITH ranked AS (
          SELECT {state_col} AS state, {district} AS district,
                 {year_col} AS fin_year, {value_col} AS metric_value,
                 source_url, ROW_NUMBER() OVER (
                   PARTITION BY {partition}
                   ORDER BY {year_col} DESC, scraped_at DESC
                 ) AS metric_rank
          FROM {table} WHERE {value_col} IS NOT NULL
        )
        SELECT state, district, fin_year, metric_value, source_url
        FROM ranked WHERE {output_filter}
        """
    ).fetchall()


def capture_snapshot(
    db_path: Path | None = None,
    snapshot_date: str | None = None,
) -> int:
    """Read key metrics from all scheme tables and store in metrics_snapshot.

    Args:
        db_path: Path to the SQLite database (defaults to DB_PATH).
        snapshot_date: ISO date string YYYY-MM-DD (defaults to today).

    Returns:
        Number of rows inserted.
    """
    snap_date = snapshot_date or date.today().isoformat()
    conn = get_connection(db_path)
    inserted = 0

    for spec in METRIC_SPECS:
        scheme, _, _, _, _, metric_name, _ = spec
        rows = _metric_rows(conn, spec)
        for row in rows:
            conn.execute(
                """INSERT OR IGNORE INTO metrics_snapshot
                   (snapshot_date, scheme, state, district, fin_year,
                    metric_name, metric_value, source_url)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    snap_date,
                    scheme,
                    row["state"],
                    row["district"],
                    row["fin_year"],
                    metric_name,
                    row["metric_value"],
                    row["source_url"],
                ),
            )
            inserted += conn.execute("SELECT changes()").fetchone()[0]

    conn.commit()
    conn.close()
    return inserted


def compute_deltas(
    state: str,
    district: str,
    scheme: str,
    weeks: int = 4,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Compute week-over-week metric changes for a specific location and scheme.

    Returns one dict per metric with current value, prior value, and absolute/pct delta.

    Args:
        state: State name (UPPER CASE).
        district: District name (UPPER CASE) or 'ALL' for state-level.
        scheme: Scheme name e.g. 'MGNREGA', 'JJM'.
        weeks: Look back this many weeks for the comparison snapshot.
        db_path: Path to the SQLite database (defaults to DB_PATH).

    Returns:
        List of dicts: {metric_name, current_value, prior_value, delta, delta_pct,
                        current_date, prior_date}.
    """
    conn = get_connection(db_path)
    cutoff = (date.today() - timedelta(weeks=weeks)).isoformat()

    # Latest snapshot date for this slice
    latest_row = conn.execute(
        """
        SELECT MAX(snapshot_date) AS snap
        FROM metrics_snapshot
        WHERE UPPER(scheme) = UPPER(?)
          AND UPPER(state) = UPPER(?)
          AND UPPER(district) = UPPER(?)
        """,
        (scheme, state, district),
    ).fetchone()

    if not latest_row or not latest_row["snap"]:
        conn.close()
        return []

    latest_date = latest_row["snap"]

    # Latest values
    current_rows = conn.execute(
        """
        SELECT scheme, metric_name, metric_value, fin_year, source_url
        FROM metrics_snapshot current
        WHERE snapshot_date = ?
          AND UPPER(scheme) = UPPER(?)
          AND UPPER(state) = UPPER(?)
          AND UPPER(district) = UPPER(?)
          AND source_url IS NOT NULL AND source_url != ''
          AND fin_year = (
            SELECT MAX(years.fin_year) FROM metrics_snapshot years
            WHERE years.snapshot_date = current.snapshot_date
              AND UPPER(years.scheme) = UPPER(current.scheme)
              AND UPPER(years.state) = UPPER(current.state)
              AND UPPER(years.district) = UPPER(current.district)
              AND years.metric_name = current.metric_name
          )
        """,
        (latest_date, scheme, state, district),
    ).fetchall()

    if not current_rows:
        conn.close()
        return []

    # Prior snapshot: closest date at or before cutoff
    prior_row = conn.execute(
        """
        SELECT MAX(snapshot_date) AS snap
        FROM metrics_snapshot
        WHERE snapshot_date <= ?
          AND UPPER(scheme) = UPPER(?)
          AND UPPER(state) = UPPER(?)
          AND UPPER(district) = UPPER(?)
        """,
        (cutoff, scheme, state, district),
    ).fetchone()

    prior_date = prior_row["snap"] if prior_row else None

    prior_lookup: dict[tuple[str, str], tuple[float, str]] = {}
    if prior_date:
        prior_rows = conn.execute(
            """
            SELECT metric_name, metric_value, fin_year, source_url
            FROM metrics_snapshot
            WHERE snapshot_date = ?
              AND UPPER(scheme) = UPPER(?)
              AND UPPER(state) = UPPER(?)
              AND UPPER(district) = UPPER(?)
              AND source_url IS NOT NULL AND source_url != ''
            """,
            (prior_date, scheme, state, district),
        ).fetchall()
        prior_lookup = {(r["metric_name"], r["fin_year"]): (r["metric_value"], r["source_url"]) for r in prior_rows}

    results: list[dict[str, Any]] = []
    for row in current_rows:
        metric = row["metric_name"]
        if not is_audited_metric(row["scheme"], metric):
            continue
        current_val = row["metric_value"]
        prior = prior_lookup.get((metric, row["fin_year"]))
        prior_val = prior[0] if prior else None
        prior_source = prior[1] if prior else None

        delta: float | None = None
        delta_pct: float | None = None
        if current_val is not None and prior_val is not None:
            delta = current_val - prior_val
            if prior_val != 0:
                delta_pct = round(delta / abs(prior_val) * 100, 2)

        results.append(
            {
                "metric_name": metric,
                "current_value": current_val,
                "prior_value": prior_val,
                "delta": delta,
                "delta_pct": delta_pct,
                "current_date": latest_date,
                "prior_date": prior_date,
                "fin_year": row["fin_year"],
                "current_source_url": row["source_url"],
                "prior_source_url": prior_source,
                **metric_context(row["scheme"], metric),
            }
        )

    conn.close()
    return results


def get_trend(
    state: str,
    district: str,
    scheme: str,
    metric: str,
    weeks: int = 12,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Return time-series data for a specific metric at a location.

    Args:
        state: State name (UPPER CASE).
        district: District name (UPPER CASE) or 'ALL'.
        scheme: Scheme name e.g. 'MGNREGA'.
        metric: Metric name e.g. 'utilization_pct'.
        weeks: Number of weeks of history to return (default 12).
        db_path: Path to the SQLite database (defaults to DB_PATH).

    Returns:
        List of {snapshot_date, metric_value, fin_year} ordered oldest→newest.
    """
    if metric not in audited_metric_names(scheme):
        return []
    cutoff = (date.today() - timedelta(weeks=weeks)).isoformat()
    conn = get_connection(db_path)

    rows = conn.execute(
        """
        SELECT snapshot_date, metric_value, fin_year, scheme, source_url
        FROM metrics_snapshot current
        WHERE snapshot_date >= ?
          AND UPPER(scheme) = UPPER(?)
          AND UPPER(state) = UPPER(?)
          AND UPPER(district) = UPPER(?)
          AND metric_name = ?
          AND source_url IS NOT NULL AND source_url != ''
          AND fin_year = (
            SELECT MAX(years.fin_year) FROM metrics_snapshot years
            WHERE UPPER(years.scheme) = UPPER(current.scheme)
              AND UPPER(years.state) = UPPER(current.state)
              AND UPPER(years.district) = UPPER(current.district)
              AND years.metric_name = current.metric_name
          )
        ORDER BY snapshot_date ASC
        """,
        (cutoff, scheme, state, district, metric),
    ).fetchall()

    conn.close()
    return [
        {
            "snapshot_date": r["snapshot_date"],
            "metric_value": r["metric_value"],
            "fin_year": r["fin_year"],
            "source_url": r["source_url"],
            **metric_context(r["scheme"], metric),
        }
        for r in rows
    ]


def get_biggest_changes(
    n: int = 20,
    weeks: int = 4,
    db_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Find districts with the largest absolute metric changes over the past N weeks.

    Only considers metrics where a prior snapshot exists for comparison.

    Args:
        n: Number of top movers to return (default 20).
        weeks: Comparison window in weeks (default 4).
        db_path: Path to the SQLite database (defaults to DB_PATH).

    Returns:
        List of dicts with scheme/state/district/metric and change info, sorted by
        abs(delta_pct) descending.
    """
    conn = get_connection(db_path)
    cutoff = (date.today() - timedelta(weeks=weeks)).isoformat()

    # For each (scheme, state, district, metric_name): latest value and best prior value
    sql = """
        WITH latest AS (
            SELECT
                scheme, state, district, metric_name, fin_year,
                metric_value AS current_value,
                source_url AS current_source_url,
                snapshot_date AS current_date,
                MAX(snapshot_date) OVER (
                    PARTITION BY scheme, state, district, metric_name
                ) AS max_date
            FROM metrics_snapshot
        ),
        current_vals AS (
            SELECT scheme, state, district, metric_name, fin_year,
                   current_value, current_source_url, current_date
            FROM latest current
            WHERE current_date = max_date
              AND fin_year = (
                SELECT MAX(years.fin_year) FROM metrics_snapshot years
                WHERE years.scheme = current.scheme
                  AND years.state = current.state
                  AND years.district = current.district
                  AND years.metric_name = current.metric_name
              )
        ),
        prior_vals AS (
            SELECT
                scheme, state, district, metric_name, fin_year,
                metric_value AS prior_value,
                source_url AS prior_source_url,
                snapshot_date AS prior_date,
                MAX(snapshot_date) OVER (
                    PARTITION BY scheme, state, district, metric_name, fin_year
                ) AS max_prior_date
            FROM metrics_snapshot
            WHERE snapshot_date <= ?
        ),
        prior_best AS (
            SELECT scheme, state, district, metric_name, fin_year,
                   prior_value, prior_source_url, prior_date
            FROM prior_vals
            WHERE prior_date = max_prior_date
        )
        SELECT
            c.scheme, c.state, c.district, c.metric_name, c.fin_year,
            c.current_value, c.current_date,
            c.current_source_url, p.prior_value, p.prior_source_url, p.prior_date,
            (c.current_value - p.prior_value) AS delta,
            CASE WHEN p.prior_value != 0
                 THEN ROUND((c.current_value - p.prior_value) / ABS(p.prior_value) * 100, 2)
                 ELSE NULL
            END AS delta_pct
        FROM current_vals c
        JOIN prior_best p
          ON c.scheme = p.scheme
         AND c.state = p.state
         AND c.district = p.district
         AND c.metric_name = p.metric_name
         AND c.fin_year = p.fin_year
        WHERE c.current_value IS NOT NULL
          AND p.prior_value IS NOT NULL
          AND c.current_source_url IS NOT NULL AND c.current_source_url != ''
          AND p.prior_source_url IS NOT NULL AND p.prior_source_url != ''
          AND c.current_value != p.prior_value
        ORDER BY ABS(delta_pct) DESC NULLS LAST
    """

    rows = conn.execute(sql, (cutoff,)).fetchall()
    conn.close()
    safe_rows = [r for r in rows if is_audited_metric(r["scheme"], r["metric_name"])]
    return [
        {
            "scheme": r["scheme"],
            "state": r["state"],
            "district": r["district"],
            "metric_name": r["metric_name"],
            "fin_year": r["fin_year"],
            "current_value": r["current_value"],
            "current_date": r["current_date"],
            "prior_value": r["prior_value"],
            "prior_date": r["prior_date"],
            "delta": r["delta"],
            "delta_pct": r["delta_pct"],
            "current_source_url": r["current_source_url"],
            "prior_source_url": r["prior_source_url"],
            **metric_context(r["scheme"], r["metric_name"]),
        }
        for r in safe_rows[:n]
    ]
