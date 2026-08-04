"""Temporal snapshot engine — capture, delta, and trend queries for Hisaab.

Captures key metrics from all scheme tables into metrics_snapshot,
then computes week-over-week deltas and trends for accountability reporting.

Table: metrics_snapshot
  (snapshot_date, scheme, state, district, fin_year, metric_name, metric_value)
"""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from db.connection import get_connection

# ---------------------------------------------------------------------------
# Metric extraction specs
# Each entry: (scheme, table, district_col, state_col, fin_year_col, metric_name, value_col)
# district_col = None means state-level only → district defaults to 'ALL'
# ---------------------------------------------------------------------------

_METRIC_SPECS: list[tuple[str, str, str | None, str, str, str, str]] = [
    # scheme, table, district_col, state_col, fin_year_col, metric_name, value_col
    ("MGNREGA", "financial_statement", "district", "state", "fin_year", "utilization_pct", "utilization_pct"),
    ("MGNREGA", "financial_statement", "district", "state", "fin_year", "cumulative_expenditure_lakhs", "cumulative_expenditure"),
    ("MGNREGA", "misappropriation", "district", "state", "fin_year", "amount_unrecovered_lakhs", "amount_unrecovered"),
    ("PMGSY", "pmgsy_district", "district", "state", "fin_year", "roads_completed", "roads_completed"),
    ("PMGSY", "pmgsy_district", "district", "state", "fin_year", "expenditure_cr", "expenditure_cr"),
    ("PMAY-G", "pmayg_district", "district", "state", "fin_year", "completion_pct", "completion_pct"),
    ("PMAY-G", "pmayg_district", "district", "state", "fin_year", "houses_completed", "houses_completed"),
    ("PM Kisan", "pmkisan_district", "district", "state", "fin_year", "amount_paid_lakhs", "amount_paid_lakhs"),
    ("JJM", "jjm_district", "district", "state", "fin_year", "coverage_pct", "coverage_pct"),
    ("JJM", "jjm_district", "district", "state", "fin_year", "households_with_tap", "households_with_tap"),
    ("PM POSHAN", "pmposhan_district", "district", "state", "fin_year", "utilization_pct", "utilization_pct"),
    ("PM POSHAN", "pmposhan_district", "district", "state", "fin_year", "children_fed", "children_fed"),
    ("NSAP", "nsap_district", "district", "state", "fin_year", "amount_paid_lakhs", "amount_paid_lakhs"),
    ("PDS/NFSA", "nfsa_district", "district", "state", "fin_year", "offtake_pct", "offtake_pct"),
    ("SBM-G", "sbm_district", "district", "state", "fin_year", "odf_plus_pct", "odf_plus_pct"),
    ("DAY-NRLM", "nrlm_district", "district", "state", "fin_year", "shgs_total", "shgs_total"),
    ("DAY-NRLM", "nrlm_district", "district", "state", "fin_year", "rf_amount_lakhs", "rf_amount_lakhs"),
    # State-level finance tables (district='ALL')
    ("PMAY-G", "pmayg_finance", None, "state", "fin_year", "utilized_lakhs", "utilized_lakhs"),
    ("PM POSHAN", "pmposhan_finance", None, "state", "fin_year", "utilized_lakhs", "utilized_lakhs"),
    ("NSAP", "nsap_finance", None, "state", "fin_year", "released_lakhs", "released_lakhs"),
    ("JJM", "jjm_allocation", None, "state", "fin_year", "expended_crores", "expended_crores"),
]


def _source_url_for_table(conn: sqlite3.Connection, table: str) -> str:
    """Return a representative source_url from the given table, or empty string."""
    try:
        row = conn.execute(
            f"SELECT source_url FROM {table} WHERE source_url IS NOT NULL LIMIT 1"
        ).fetchone()
        return row[0] if row and row[0] else ""
    except Exception:
        return ""


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

    for scheme, table, district_col, state_col, fin_year_col, metric_name, value_col in _METRIC_SPECS:
        source_url = _source_url_for_table(conn, table)

        if district_col is not None:
            sql = f"""
                SELECT
                    {state_col} AS state,
                    {district_col} AS district,
                    {fin_year_col} AS fin_year,
                    {value_col} AS metric_value
                FROM {table}
                WHERE {value_col} IS NOT NULL
            """
        else:
            # State-level table — district fixed to 'ALL'
            sql = f"""
                SELECT
                    {state_col} AS state,
                    'ALL' AS district,
                    {fin_year_col} AS fin_year,
                    {value_col} AS metric_value
                FROM {table}
                WHERE {value_col} IS NOT NULL
            """

        try:
            rows = conn.execute(sql).fetchall()
        except Exception:
            continue

        for row in rows:
            try:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO metrics_snapshot
                        (snapshot_date, scheme, state, district, fin_year,
                         metric_name, metric_value, source_url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        snap_date,
                        scheme,
                        row["state"],
                        row["district"],
                        row["fin_year"],
                        metric_name,
                        row["metric_value"],
                        source_url,
                    ),
                )
                inserted += conn.execute("SELECT changes()").fetchone()[0]
            except Exception:
                continue

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
        SELECT metric_name, metric_value, fin_year
        FROM metrics_snapshot
        WHERE snapshot_date = ?
          AND UPPER(scheme) = UPPER(?)
          AND UPPER(state) = UPPER(?)
          AND UPPER(district) = UPPER(?)
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

    prior_lookup: dict[str, float] = {}
    if prior_date:
        prior_rows = conn.execute(
            """
            SELECT metric_name, metric_value
            FROM metrics_snapshot
            WHERE snapshot_date = ?
              AND UPPER(scheme) = UPPER(?)
              AND UPPER(state) = UPPER(?)
              AND UPPER(district) = UPPER(?)
            """,
            (prior_date, scheme, state, district),
        ).fetchall()
        prior_lookup = {r["metric_name"]: r["metric_value"] for r in prior_rows}

    results: list[dict[str, Any]] = []
    for row in current_rows:
        metric = row["metric_name"]
        current_val = row["metric_value"]
        prior_val = prior_lookup.get(metric)

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
    cutoff = (date.today() - timedelta(weeks=weeks)).isoformat()
    conn = get_connection(db_path)

    rows = conn.execute(
        """
        SELECT snapshot_date, metric_value, fin_year
        FROM metrics_snapshot
        WHERE snapshot_date >= ?
          AND UPPER(scheme) = UPPER(?)
          AND UPPER(state) = UPPER(?)
          AND UPPER(district) = UPPER(?)
          AND metric_name = ?
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
                snapshot_date AS current_date,
                MAX(snapshot_date) OVER (
                    PARTITION BY scheme, state, district, metric_name
                ) AS max_date
            FROM metrics_snapshot
        ),
        current_vals AS (
            SELECT scheme, state, district, metric_name, fin_year,
                   current_value, current_date
            FROM latest
            WHERE snapshot_date = max_date
        ),
        prior_vals AS (
            SELECT
                scheme, state, district, metric_name,
                metric_value AS prior_value,
                snapshot_date AS prior_date,
                MAX(snapshot_date) OVER (
                    PARTITION BY scheme, state, district, metric_name
                ) AS max_prior_date
            FROM metrics_snapshot
            WHERE snapshot_date <= ?
        ),
        prior_best AS (
            SELECT scheme, state, district, metric_name, prior_value, prior_date
            FROM prior_vals
            WHERE prior_date = max_prior_date
        )
        SELECT
            c.scheme, c.state, c.district, c.metric_name, c.fin_year,
            c.current_value, c.current_date,
            p.prior_value, p.prior_date,
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
        WHERE c.current_value IS NOT NULL
          AND p.prior_value IS NOT NULL
          AND c.current_value != p.prior_value
        ORDER BY ABS(delta_pct) DESC NULLS LAST
        LIMIT ?
    """

    try:
        rows = conn.execute(sql, (cutoff, n)).fetchall()
    except Exception:
        conn.close()
        return []

    conn.close()
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
        }
        for r in rows
    ]
