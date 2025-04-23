"""Scheme-level endpoints: list schemes, per-scheme queries, data quality, red flags."""

from __future__ import annotations

import inspect
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from query import (
    data_quality_warnings,
    district_trend,
    jjm_state_summary,
    jjm_worst_coverage,
    misappropriation_state_summary,
    nfsa_state_summary,
    nfsa_worst_coverage,
    nsap_state_summary,
    nsap_worst_coverage,
    pmayg_state_summary,
    pmayg_worst_completion,
    pmgsy_state_summary,
    pmgsy_worst_completion,
    pmkisan_state_summary,
    pmkisan_worst_coverage,
    pmposhan_state_summary,
    pmposhan_worst_feeding,
    trending_better,
    trending_worse,
    worst_misappropriation_districts,
)

router = APIRouter()

SCHEME_NAMES = ["MGNREGA", "PMGSY", "PMAY-G", "PM Kisan", "JJM", "PM POSHAN", "NSAP", "PDS/NFSA"]

SCHEME_STATE_SUMMARIES = {
    "MGNREGA": misappropriation_state_summary,
    "PMGSY": pmgsy_state_summary,
    "PMAY-G": pmayg_state_summary,
    "PM Kisan": pmkisan_state_summary,
    "JJM": jjm_state_summary,
    "PM POSHAN": pmposhan_state_summary,
    "NSAP": nsap_state_summary,
    "PDS/NFSA": nfsa_state_summary,
}

SCHEME_WORST = {
    "MGNREGA": worst_misappropriation_districts,
    "PMGSY": pmgsy_worst_completion,
    "PMAY-G": pmayg_worst_completion,
    "PM Kisan": pmkisan_worst_coverage,
    "JJM": jjm_worst_coverage,
    "PM POSHAN": pmposhan_worst_feeding,
    "NSAP": nsap_worst_coverage,
    "PDS/NFSA": nfsa_worst_coverage,
}


@router.get("/schemes")
def list_schemes() -> dict[str, Any]:
    """List all 8 schemes with data quality status."""
    warnings = data_quality_warnings()
    return {
        "schemes": [{"name": name, "warnings": warnings.get(name, [])} for name in SCHEME_NAMES],
        "count": len(SCHEME_NAMES),
    }


@router.get("/scheme/{scheme}")
def scheme_summary(
    scheme: str,
    state: str = Query(default="TAMIL NADU", description="State name (UPPER CASE)"),
    fin_year: str = Query(default="2024-2025", description="Financial year"),
) -> dict[str, Any]:
    """State-level summary for a specific scheme."""
    fn = SCHEME_STATE_SUMMARIES.get(scheme)
    if not fn:
        raise HTTPException(status_code=404, detail=f"Unknown scheme: {scheme}. Valid: {SCHEME_NAMES}")
    params = inspect.signature(fn).parameters
    kwargs: dict[str, str] = {"state": state}
    if "fin_year" in params:
        kwargs["fin_year"] = fin_year
    return fn(**kwargs)


@router.get("/scheme/{scheme}/worst")
def scheme_worst(
    scheme: str,
    state: str = Query(default="TAMIL NADU", description="State name (UPPER CASE)"),
    limit: int = Query(default=10, ge=1, le=100),
) -> dict[str, Any]:
    """Worst-performing districts for a scheme."""
    fn = SCHEME_WORST.get(scheme)
    if not fn:
        raise HTTPException(status_code=404, detail=f"Unknown scheme: {scheme}. Valid: {SCHEME_NAMES}")
    if scheme == "MGNREGA":
        return fn(limit=limit)
    return fn(state=state, limit=limit)


@router.get("/data-quality")
def data_quality() -> dict[str, list[str]]:
    """Per-scheme data quality warnings."""
    return data_quality_warnings()


@router.get("/red-flags")
def red_flags(
    state: str = Query(default="TAMIL NADU"),
    limit: int = Query(default=10, ge=1, le=50),
) -> dict[str, Any]:
    """Worst districts across key indicators."""
    return {
        "misappropriation": worst_misappropriation_districts(limit=limit),
        "pmgsy_completion": pmgsy_worst_completion(state=state, limit=limit),
        "jjm_coverage": jjm_worst_coverage(state=state, limit=limit),
    }


@router.get("/trends/biggest-changes")
def trends_biggest_changes(
    n: int = Query(default=20, ge=1, le=100, description="Number of top movers to return"),
    weeks: int = Query(default=4, ge=1, le=52, description="Comparison window in weeks"),
) -> dict[str, Any]:
    """Districts with the largest metric changes over the past N weeks.

    Returns both improving and degrading metrics sorted by magnitude of change.
    Requires at least two snapshots separated by the requested number of weeks.
    """
    from db.snapshots import get_biggest_changes

    changes = get_biggest_changes(n=n, weeks=weeks)
    return {
        "changes": changes,
        "count": len(changes),
        "weeks": weeks,
    }


@router.get("/trends/{district}")
def trends_district(
    district: str,
    state: str = Query(description="State name (UPPER CASE)"),
    scheme: str = Query(description="Scheme name e.g. MGNREGA, JJM"),
    weeks: int = Query(default=12, ge=1, le=52, description="Weeks of history"),
) -> dict[str, Any]:
    """Trend data for a specific district and scheme.

    Returns time-series for all tracked metrics and week-over-week deltas.
    Requires snapshots to have been captured via `run_all.py --snapshot`.
    """
    return district_trend(
        district=district.upper(),
        state=state.upper(),
        scheme=scheme,
        weeks=weeks,
    )


@router.get("/trends")
def trends_overview(
    n: int = Query(default=10, ge=1, le=50),
    weeks: int = Query(default=4, ge=1, le=52),
) -> dict[str, Any]:
    """Overview of improving and degrading metrics across all districts."""
    return {
        "trending_worse": trending_worse(n=n, weeks=weeks),
        "trending_better": trending_better(n=n, weeks=weeks),
        "weeks": weeks,
    }
