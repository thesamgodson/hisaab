"""Trend query functions — surfaces metric degradation and improvement over time.

Reads from the metrics_snapshot table populated by db.snapshots.capture_snapshot().
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from db.connection import get_connection
from db.snapshots import compute_deltas, get_biggest_changes, get_trend


def trending_worse(
    n: int = 10,
    weeks: int = 4,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Return districts where key metrics degraded most over the past N weeks.

    Degradation is defined as a negative delta_pct (metric fell).

    Args:
        n: Number of results to return.
        weeks: Comparison window in weeks.
        db_path: Path to the SQLite database (defaults to DB_PATH).

    Returns:
        dict with 'answer' (human-readable summary), 'data' (list of change dicts),
        and 'weeks' context.
    """
    all_changes = get_biggest_changes(n=n * 5, weeks=weeks, db_path=db_path)

    worse = [
        c for c in all_changes
        if c["delta_pct"] is not None and c["delta_pct"] < 0
    ]
    # Sort by most negative delta_pct
    worse.sort(key=lambda c: c["delta_pct"])
    worse = worse[:n]

    if not worse:
        return {
            "answer": f"No degrading metrics found in the past {weeks} weeks.",
            "data": [],
            "weeks": weeks,
        }

    lines = [f"Top {len(worse)} degrading metrics (past {weeks} weeks):"]
    for item in worse:
        lines.append(
            f"  {item['scheme']} — {item['district']}, {item['state']}: "
            f"{item['metric_name']} dropped {item['delta_pct']:.1f}% "
            f"({item['prior_value']} → {item['current_value']})"
        )

    return {
        "answer": "\n".join(lines),
        "data": worse,
        "weeks": weeks,
    }


def trending_better(
    n: int = 10,
    weeks: int = 4,
    db_path: Path | None = None,
) -> dict[str, Any]:
    """Return districts where key metrics improved most over the past N weeks.

    Improvement is defined as a positive delta_pct (metric rose).

    Args:
        n: Number of results to return.
        weeks: Comparison window in weeks.
        db_path: Path to the SQLite database (defaults to DB_PATH).

    Returns:
        dict with 'answer', 'data', and 'weeks'.
    """
    all_changes = get_biggest_changes(n=n * 5, weeks=weeks, db_path=db_path)

    better = [
        c for c in all_changes
        if c["delta_pct"] is not None and c["delta_pct"] > 0
    ]
    # Sort by most positive delta_pct
    better.sort(key=lambda c: c["delta_pct"], reverse=True)
    better = better[:n]

    if not better:
        return {
            "answer": f"No improving metrics found in the past {weeks} weeks.",
            "data": [],
            "weeks": weeks,
        }

    lines = [f"Top {len(better)} improving metrics (past {weeks} weeks):"]
    for item in better:
        lines.append(
            f"  {item['scheme']} — {item['district']}, {item['state']}: "
            f"{item['metric_name']} rose {item['delta_pct']:.1f}% "
            f"({item['prior_value']} → {item['current_value']})"
        )

    return {
        "answer": "\n".join(lines),
        "data": better,
        "weeks": weeks,
    }


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
        ORDER BY metric_name
        """,
        (scheme, state, district),
    ).fetchall()
    conn.close()

    metric_names = [r["metric_name"] for r in metric_rows]

    if not metric_names:
        return {
            "answer": f"No snapshot data found for {scheme} in {district}, {state}.",
            "district": district,
            "state": state,
            "scheme": scheme,
            "weeks": weeks,
            "metrics": {},
            "deltas": [],
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
    lines = [
        f"{scheme} trend for {district}, {state} (past {weeks} weeks, {snap_count} snapshots):"
    ]
    for d in deltas:
        if d["delta_pct"] is not None:
            direction = "up" if d["delta_pct"] > 0 else "down"
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
    }
