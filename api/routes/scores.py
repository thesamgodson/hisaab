"""Composite accountability score endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from queries.composite import (
    compute_district_scores,
    get_district_score,
    get_state_rankings,
    get_worst_districts,
)

router = APIRouter()


@router.get("/scores")
def all_scores(
    fin_year: str = Query(default="2024-2025", description="Financial year"),
) -> dict[str, Any]:
    """All district composite accountability scores (for map rendering).

    Returns scored districts sorted descending by score, then unscored districts.
    """
    scores = compute_district_scores(fin_year=fin_year)
    return {
        "fin_year": fin_year,
        "count": len(scores),
        "scored_count": sum(1 for s in scores if s["score"] is not None),
        "scores": scores,
    }


@router.get("/scores/states")
def state_rankings(
    fin_year: str = Query(default="2024-2025", description="Financial year"),
) -> dict[str, Any]:
    """State-level accountability rankings (average of district scores)."""
    rankings = get_state_rankings(fin_year=fin_year)
    return {
        "fin_year": fin_year,
        "count": len(rankings),
        "rankings": rankings,
    }


@router.get("/scores/worst")
def worst_districts(
    n: int = Query(default=50, ge=1, le=200, description="Number of worst districts"),
    fin_year: str = Query(default="2024-2025", description="Financial year"),
) -> dict[str, Any]:
    """Bottom N districts by composite score."""
    worst = get_worst_districts(n=n, fin_year=fin_year)
    return {
        "fin_year": fin_year,
        "count": len(worst),
        "districts": worst,
    }


@router.get("/scores/{district}")
def district_score(
    district: str,
    state: str = Query(default=None, description="State name (UPPER CASE). Required if district name is ambiguous."),
    fin_year: str = Query(default="2024-2025", description="Financial year"),
) -> dict[str, Any]:
    """Composite accountability score breakdown for a single district."""
    if not state:
        # Auto-resolve state from DB
        resolved = _resolve_state(district)
        if not resolved:
            raise HTTPException(
                status_code=404,
                detail=f"District '{district}' not found. Provide ?state= to disambiguate.",
            )
        state = resolved

    result = get_district_score(district=district, state=state, fin_year=fin_year)
    if result["score"] is None and result["schemes_count"] == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No data found for district '{district}' in state '{state}'.",
        )
    return result


def _resolve_state(district: str) -> str | None:
    """Look up the state for a district from the DB."""
    import sqlite3

    from db import DB_PATH

    conn = sqlite3.connect(str(DB_PATH))
    for table in ("pmgsy_district", "misappropriation", "financial_statement"):
        try:
            row = conn.execute(
                f"SELECT state FROM {table} WHERE UPPER(district) = UPPER(?) LIMIT 1",
                (district,),
            ).fetchone()
            if row:
                conn.close()
                return row[0]
        except Exception:
            pass
    conn.close()
    return None
