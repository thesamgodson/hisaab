"""Composite accountability score per district.

THE single implementation of the scoring formula. Scores are persisted to the
district_scores table at load time (persist_district_scores) and every serving
surface — web, CLI, briefs — reads that table. Do not port this formula.

Scoring methodology (0-100):
  - Delivery metrics (60%): average delivery_pct across all schemes with data
  - Financial utilization (30%): average utilization_pct from scheme_finance VIEW
  - Governance / recovery (10%): MGNREGA recovery_rate_pct (if available)

Confidence rule: a district needs data from at least MIN_SCHEMES_FOR_SCORE
schemes to receive a score/grade. One scheme's bad quarter must not brand a
district "F" on the public map.

Grades: A=80+, B=60-80, C=40-60, D=20-40, F=<20
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from db.connection import get_connection

MIN_SCHEMES_FOR_SCORE = 3

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_GRADE_THRESHOLDS: list[tuple[float, str]] = [
    (80.0, "A"),
    (60.0, "B"),
    (40.0, "C"),
    (20.0, "D"),
    (0.0, "F"),
]

_DELIVERY_WEIGHT = 0.60
_FINANCE_WEIGHT = 0.30
_GOVERNANCE_WEIGHT = 0.10


def _conn():
    return get_connection()


def _grade(score: float) -> str:
    for threshold, letter in _GRADE_THRESHOLDS:
        if score >= threshold:
            return letter
    return "F"


def _avg(values: list[float]) -> float | None:
    valid = [v for v in values if v is not None and 0 <= v <= 100]
    return sum(valid) / len(valid) if valid else None


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def _fetch_delivery_scores(conn: sqlite3.Connection, fin_year: str) -> dict[tuple[str, str], dict[str, Any]]:
    """Return {(district, state): {scheme: delivery_pct, ...}} from scheme_delivery VIEW."""
    rows = conn.execute(
        """
        SELECT scheme, state, district, delivery_pct
        FROM scheme_delivery
        WHERE delivery_pct IS NOT NULL
          AND delivery_pct > 0
          AND district != 'ALL'
          AND fin_year = ?
        """,
        (fin_year,),
    ).fetchall()

    result: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (row["district"].upper(), row["state"].upper())
        if key not in result:
            result[key] = {}
        existing = result[key].get(row["scheme"])
        # Keep highest value if multiple fin_years exist
        if existing is None or row["delivery_pct"] > existing:
            result[key][row["scheme"]] = row["delivery_pct"]
    return result


def _fetch_finance_scores(conn: sqlite3.Connection, fin_year: str) -> dict[tuple[str, str], dict[str, Any]]:
    """Return {(district, state): {scheme: utilization_pct, ...}} from scheme_finance VIEW."""
    rows = conn.execute(
        """
        SELECT scheme, state, district, utilization_pct
        FROM scheme_finance
        WHERE utilization_pct IS NOT NULL
          AND utilization_pct > 0
          AND utilization_pct <= 150
          AND fin_year = ?
        """,
        (fin_year,),
    ).fetchall()

    result: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        key = (row["district"].upper(), row["state"].upper())
        if key not in result:
            result[key] = {}
        existing = result[key].get(row["scheme"])
        if existing is None or row["utilization_pct"] > existing:
            result[key][row["scheme"]] = min(100.0, float(row["utilization_pct"]))
    return result


def _fetch_recovery_rates(conn: sqlite3.Connection, fin_year: str) -> dict[tuple[str, str], float]:
    """Return {(district, state): recovery_rate_pct} from misappropriation table."""
    rows = conn.execute(
        """
        SELECT district, state, recovery_rate_pct
        FROM misappropriation
        WHERE fin_year = ?
          AND recovery_rate_pct IS NOT NULL
        """,
        (fin_year,),
    ).fetchall()

    result: dict[tuple[str, str], float] = {}
    for row in rows:
        key = (row["district"].upper(), row["state"].upper())
        existing = result.get(key)
        if existing is None or row["recovery_rate_pct"] > existing:
            result[key] = float(row["recovery_rate_pct"])
    return result


def _fetch_all_districts(conn: sqlite3.Connection) -> set[tuple[str, str]]:
    """Return all (district, state) pairs from any scheme table."""
    tables = [
        "misappropriation",
        "financial_statement",
        "pmgsy_district",
        "pmayg_district",
        "pmkisan_district",
        "jjm_district",
        "pmposhan_district",
        "nsap_district",
        "nfsa_district",
        "sbm_district",
        "nrlm_district",
    ]
    pairs: set[tuple[str, str]] = set()
    for table in tables:
        try:
            rows = conn.execute(
                f"SELECT DISTINCT UPPER(district) as d, UPPER(state) as s FROM {table} WHERE district != 'ALL'"
            ).fetchall()
            pairs.update((r["d"], r["s"]) for r in rows)
        except Exception:
            pass
    return pairs


def _build_score_record(
    district: str,
    state: str,
    delivery: dict[str, float],
    finance: dict[str, float],
    recovery_rate: float | None,
) -> dict[str, Any]:
    """Compute the composite score and return a score record."""
    delivery_scores = list(delivery.values())
    finance_scores = list(finance.values())

    delivery_avg = _avg(delivery_scores)
    finance_avg = _avg(finance_scores)
    governance_score = min(100.0, recovery_rate) if recovery_rate is not None else None

    # Confidence rule: too little data -> no score, but keep the breakdown
    # visible so the page can say WHY there is no grade.
    schemes_with_data = sorted(set(delivery.keys()) | set(finance.keys()))
    if len(schemes_with_data) < MIN_SCHEMES_FOR_SCORE:
        record = _null_score_record(district, state)
        record["schemes_with_data"] = schemes_with_data
        record["schemes_count"] = len(schemes_with_data)
        # Red flags are factual per-scheme statements — keep them even when
        # there is too little data for a composite grade.
        record["red_flags"] = _compute_red_flags(delivery, finance, recovery_rate)
        record["breakdown"] = {
            "delivery_avg": round(delivery_avg, 1) if delivery_avg is not None else None,
            "delivery_schemes": sorted(delivery.keys()),
            "finance_avg": round(finance_avg, 1) if finance_avg is not None else None,
            "finance_schemes": sorted(finance.keys()),
            "governance_score": round(governance_score, 1) if governance_score is not None else None,
        }
        return record

    # Determine weights dynamically based on data availability
    components: list[tuple[float, float]] = []
    if delivery_avg is not None:
        components.append((_DELIVERY_WEIGHT, delivery_avg))
    if finance_avg is not None:
        components.append((_FINANCE_WEIGHT, finance_avg))
    if governance_score is not None:
        components.append((_GOVERNANCE_WEIGHT, governance_score))

    if not components:
        return _null_score_record(district, state)

    # Renormalize weights so they sum to 1
    total_weight = sum(w for w, _ in components)
    score = sum((w / total_weight) * v for w, v in components)
    score = round(min(100.0, max(0.0, score)), 1)

    red_flags = _compute_red_flags(delivery, finance, recovery_rate)

    return {
        "district": district,
        "state": state,
        "score": score,
        "grade": _grade(score),
        "schemes_with_data": schemes_with_data,
        "schemes_count": len(schemes_with_data),
        "red_flags": red_flags,
        "breakdown": {
            "delivery_avg": round(delivery_avg, 1) if delivery_avg is not None else None,
            "delivery_schemes": sorted(delivery.keys()),
            "finance_avg": round(finance_avg, 1) if finance_avg is not None else None,
            "finance_schemes": sorted(finance.keys()),
            "governance_score": round(governance_score, 1) if governance_score is not None else None,
        },
    }


def _null_score_record(district: str, state: str) -> dict[str, Any]:
    return {
        "district": district,
        "state": state,
        "score": None,
        "grade": None,
        "schemes_with_data": [],
        "schemes_count": 0,
        "red_flags": [],
        "breakdown": {
            "delivery_avg": None,
            "delivery_schemes": [],
            "finance_avg": None,
            "finance_schemes": [],
            "governance_score": None,
        },
    }


def _compute_red_flags(
    delivery: dict[str, float],
    finance: dict[str, float],
    recovery_rate: float | None,
) -> list[str]:
    """Return human-readable red flag strings for the worst indicators."""
    flags: list[str] = []

    for scheme, pct in delivery.items():
        if pct < 40:
            flags.append(f"{scheme} delivery only {pct:.0f}%")

    for scheme, pct in finance.items():
        if pct < 30:
            flags.append(f"{scheme} utilization only {pct:.0f}%")

    if recovery_rate is not None and recovery_rate < 20:
        flags.append(f"MGNREGA recovery rate {recovery_rate:.0f}%")

    return flags[:5]  # Cap at 5 most salient flags


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_district_scores(fin_year: str = "2024-2025") -> list[dict[str, Any]]:
    """Compute composite accountability scores for all districts.

    Returns a list of score records sorted descending by score (scored districts
    first, then unscored districts with score=None at the end).
    """
    conn = _conn()
    try:
        all_districts = _fetch_all_districts(conn)
        delivery_map = _fetch_delivery_scores(conn, fin_year)
        finance_map = _fetch_finance_scores(conn, fin_year)
        recovery_map = _fetch_recovery_rates(conn, fin_year)
    finally:
        conn.close()

    records: list[dict[str, Any]] = []
    for district, state in sorted(all_districts):
        key = (district, state)
        delivery = delivery_map.get(key, {})
        finance = finance_map.get(key, {})
        recovery = recovery_map.get(key)
        records.append(_build_score_record(district, state, delivery, finance, recovery))

    # Sort: scored districts descending, then unscored
    scored = sorted(
        [r for r in records if r["score"] is not None],
        key=lambda r: r["score"],
        reverse=True,
    )
    unscored = [r for r in records if r["score"] is None]
    return scored + unscored


def get_district_score(district: str, state: str, fin_year: str = "2024-2025") -> dict[str, Any]:
    """Compute composite score for a single district."""
    conn = _conn()
    try:
        delivery_map = _fetch_delivery_scores(conn, fin_year)
        finance_map = _fetch_finance_scores(conn, fin_year)
        recovery_map = _fetch_recovery_rates(conn, fin_year)
    finally:
        conn.close()

    key = (district.upper(), state.upper())
    delivery = delivery_map.get(key, {})
    finance = finance_map.get(key, {})
    recovery = recovery_map.get(key)

    return _build_score_record(district.upper(), state.upper(), delivery, finance, recovery)


def get_state_rankings(fin_year: str = "2024-2025") -> list[dict[str, Any]]:
    """Return average composite score per state, sorted descending."""
    all_scores = compute_district_scores(fin_year=fin_year)
    scored = [r for r in all_scores if r["score"] is not None]

    state_buckets: dict[str, list[float]] = {}
    for record in scored:
        state_buckets.setdefault(record["state"], []).append(record["score"])

    rankings: list[dict[str, Any]] = []
    for state, scores in state_buckets.items():
        avg = round(sum(scores) / len(scores), 1)
        rankings.append({
            "state": state,
            "avg_score": avg,
            "grade": _grade(avg),
            "district_count": len(scores),
            "best_district_score": round(max(scores), 1),
            "worst_district_score": round(min(scores), 1),
        })

    return sorted(rankings, key=lambda r: r["avg_score"], reverse=True)


def get_worst_districts(n: int = 50, fin_year: str = "2024-2025") -> list[dict[str, Any]]:
    """Return the bottom N districts by composite score."""
    all_scores = compute_district_scores(fin_year=fin_year)
    scored = [r for r in all_scores if r["score"] is not None]
    return list(reversed(scored[-n:]))


def persist_district_scores(conn: sqlite3.Connection, fin_year: str = "2024-2025") -> int:
    """Compute all district scores and write them to the district_scores table.

    Called at load time (run_all.py). The web app, CLI, and briefs read this
    table — the formula runs in exactly one place.
    """
    records = compute_district_scores(fin_year=fin_year)
    computed_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    conn.execute("DELETE FROM district_scores WHERE fin_year = ?", (fin_year,))
    conn.executemany(
        """
        INSERT OR REPLACE INTO district_scores (
            district, state, fin_year, score, grade,
            schemes_count, schemes_with_data, red_flags,
            delivery_avg, delivery_schemes, finance_avg, finance_schemes,
            governance_score, computed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                r["district"],
                r["state"],
                fin_year,
                r["score"],
                r["grade"],
                r["schemes_count"],
                json.dumps(r["schemes_with_data"]),
                json.dumps(r["red_flags"]),
                r["breakdown"]["delivery_avg"],
                json.dumps(r["breakdown"]["delivery_schemes"]),
                r["breakdown"]["finance_avg"],
                json.dumps(r["breakdown"]["finance_schemes"]),
                r["breakdown"]["governance_score"],
                computed_at,
            )
            for r in records
        ],
    )
    conn.commit()
    return len(records)
