"""District-level endpoints: overview, per-scheme, brief generation."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from query import (
    district_overview,
    fto_status_by_district,
    fund_utilization_by_district,
    jjm_by_district,
    list_districts,
    misappropriation_by_district,
    money_flow_by_district,
    nfsa_by_district,
    nsap_by_district,
    pmayg_by_district,
    pmgsy_district_summary,
    pmkisan_by_district,
    pmposhan_by_district,
    schemes_in_district,
    social_audit_by_district,
)

router = APIRouter()


@router.get("/district/{name}")
def district_detail(
    name: str,
    state: str = Query(default=None, description="State name (auto-detected if omitted)"),
    fin_year: str = Query(default="2024-2025"),
) -> dict[str, Any]:
    """Full overview of a district across all schemes."""
    resolved_state = state or _resolve_state(name)
    return district_overview(name, state=resolved_state, fin_year=fin_year)


@router.get("/district/{name}/schemes")
def district_schemes(name: str) -> dict[str, Any]:
    """Which schemes have data for this district."""
    return schemes_in_district(name)


@router.get("/district/{name}/money-flow")
def district_money_flow(
    name: str,
    state: str = Query(default=None),
) -> dict[str, Any]:
    """Cross-scheme money flow for a district."""
    return money_flow_by_district(name, state=state)


@router.get("/district/{name}/{scheme}")
def district_scheme(
    name: str,
    scheme: str,
    state: str = Query(default=None),
    fin_year: str = Query(default="2024-2025"),
) -> dict[str, Any]:
    """Per-scheme data for a district."""
    resolved_state = state or _resolve_state(name)
    fns = {
        "mgnrega": lambda: misappropriation_by_district(name, state=resolved_state, fin_year=fin_year),
        "misappropriation": lambda: misappropriation_by_district(name, state=resolved_state, fin_year=fin_year),
        "funds": lambda: fund_utilization_by_district(name, state=resolved_state, fin_year=fin_year),
        "audit": lambda: social_audit_by_district(name, state=resolved_state, fin_year=fin_year),
        "fto": lambda: fto_status_by_district(name, state=resolved_state, fin_year=fin_year),
        "pmgsy": lambda: pmgsy_district_summary(name, state=resolved_state),
        "pmayg": lambda: pmayg_by_district(name, state=resolved_state, fin_year=fin_year),
        "pmkisan": lambda: pmkisan_by_district(name, state=resolved_state, fin_year=fin_year),
        "jjm": lambda: jjm_by_district(name, state=resolved_state, fin_year=fin_year),
        "pmposhan": lambda: pmposhan_by_district(name, state=resolved_state, fin_year=fin_year),
        "nsap": lambda: nsap_by_district(name, state=resolved_state, fin_year=fin_year),
        "nfsa": lambda: nfsa_by_district(name, state=resolved_state, fin_year=fin_year),
    }
    fn = fns.get(scheme.lower())
    if not fn:
        raise HTTPException(status_code=404, detail=f"Unknown scheme: {scheme}")
    return fn()


@router.get("/brief/{district}")
def generate_brief(
    district: str,
    state: str = Query(default=None),
) -> dict[str, Any]:
    """Generate a journalist brief for a district (plain text)."""
    from journalist_brief import brief as generate_brief

    resolved_state = state or _resolve_state(district)
    brief_text = generate_brief(district)
    return {
        "district": district.upper(),
        "state": resolved_state,
        "brief": brief_text,
        "format": "plain_text",
    }


@router.get("/districts")
def list_all_districts(
    state: str = Query(default=None, description="Filter by state"),
) -> dict[str, Any]:
    """List all districts with data."""
    districts = list_districts(state=state) if state else list_districts()
    return {"districts": districts, "count": len(districts)}


def _resolve_state(district: str) -> str:
    """Look up the state for a district from loaded data."""
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
    return "TAMIL NADU"
