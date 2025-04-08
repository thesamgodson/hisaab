"""Scheme-level endpoints: list schemes, per-scheme queries, data quality, red flags."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from query import (
    data_quality_warnings,
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
    return fn(state=state, fin_year=fin_year)


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
