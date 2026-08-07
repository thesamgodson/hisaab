"""Neutral trend access over the audited metrics snapshot catalog."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from db.connection import get_connection
from db.snapshot_metrics import audited_metric_names
from db.snapshots import compute_deltas, get_trend

_SUSPENDED_REASON = (
    "Better/worse judgment is suspended: metric polarity has not been audited. "
    "Use neutral changes and exact time series instead."
)


def _suspended_direction(weeks: int) -> dict[str, Any]:
    return {
        "answer": _SUSPENDED_REASON,
        "data": [],
        "weeks": weeks,
        "judgment_status": "suspended",
    }


def trending_worse(
    n: int = 10,
    weeks: int = 4,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Suspend unaudited degradation judgments while keeping API compatibility.

    Args:
        n: Number of results to return.
        weeks: Comparison window in weeks.
        db_path: Path to the SQLite database (defaults to DB_PATH).

    Returns:
        dict with 'answer' (human-readable summary), 'data' (list of change dicts),
        and 'weeks' context.
    """
    del n, db_path
    return _suspended_direction(weeks)


def trending_better(
    n: int = 10,
    weeks: int = 4,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Suspend unaudited improvement judgments while keeping API compatibility.

    Args:
        n: Number of results to return.
        weeks: Comparison window in weeks.
        db_path: Path to the SQLite database (defaults to DB_PATH).

    Returns:
        dict with 'answer', 'data', and 'weeks'.
    """
    del n, db_path
    return _suspended_direction(weeks)


def district_trend(
    district: str,
    state: str,
    scheme: str,
    weeks: int = 12,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Return full metric trend for a specific district + scheme.

    Collects all tracked metrics for the location and builds a time-series
    dict keyed by metric name.

    Args:
        district: District name (UPPER CASE) or 'ALL' for state-level.
        state: State name (UPPER CASE).
        scheme: Scheme name e.g. 'MGNREGA', 'JJM'.
        weeks: Weeks of history to include (default 12).
        db_path: Path to the SQLite database.

    Returns:
        dict with 'answer', 'district', 'state', 'scheme', 'weeks',
        'metrics' (dict of metric_name → list of {snapshot_date, metric_value}).
        Also includes 'deltas' from compute_deltas() for the most recent comparison.
    """
    conn = get_connection(db_path)

    # Discover which metrics exist for this slice
    metric_rows = conn.execute(
        """
        SELECT DISTINCT metric_name
        FROM metrics_snapshot
        WHERE UPPER(scheme) = UPPER(?)
          AND UPPER(state) = UPPER(?)
          AND UPPER(district) = UPPER(?)
          AND source_url IS NOT NULL AND source_url != ''
        ORDER BY metric_name
        """,
        (scheme, state, district),
    ).fetchall()
    conn.close()

    allowed = audited_metric_names(scheme)
    metric_names = [r["metric_name"] for r in metric_rows if r["metric_name"] in allowed]

    if not metric_names:
        return {
            "answer": f"No audited snapshot data found for {scheme} in {district}, {state}.",
            "district": district,
            "state": state,
            "scheme": scheme,
            "weeks": weeks,
            "metrics": {},
            "deltas": [],
            "direction_judgment": "suspended",
        }

    metrics: dict[str, list[dict[str, Any]]] = {}
    for metric_name in metric_names:
        series = get_trend(
            state=state,
            district=district,
            scheme=scheme,
            metric=metric_name,
            weeks=weeks,
            db_path=db_path,
        )
        metrics[metric_name] = series

    deltas = compute_deltas(
        state=state,
        district=district,
        scheme=scheme,
        weeks=min(weeks, 4),
        db_path=db_path,
    )

    # Build human-readable summary
    snap_count = max((len(v) for v in metrics.values()), default=0)
    lines = [f"{scheme} trend for {district}, {state} (past {weeks} weeks, {snap_count} snapshots):"]
    for d in deltas:
        if d["delta_pct"] is not None:
            direction = "up" if d["delta_pct"] > 0 else "down" if d["delta_pct"] < 0 else "unchanged"
            lines.append(
                f"  {d['metric_name']}: {direction} {abs(d['delta_pct']):.1f}% "
                f"({d['prior_value']} → {d['current_value']})"
            )

    return {
        "answer": "\n".join(lines),
        "district": district,
        "state": state,
        "scheme": scheme,
        "weeks": weeks,
        "metrics": metrics,
        "deltas": deltas,
        "direction_judgment": "suspended",
        "judgment_note": _SUSPENDED_REASON,
    }
