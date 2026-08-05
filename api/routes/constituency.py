"""Constituency endpoints: PIN lookup, MP report cards, SVG share images."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from constituency.mapper import (
    district_to_ac,
    district_to_constituency,
    get_mla_info,
    get_mp_candidates,
    get_mp_info,
    pin_to_district,
    search_constituency,
)
from constituency.report_card import (
    generate_mp_report_card,
    generate_report_card_image,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# PIN lookup
# ---------------------------------------------------------------------------

@router.get("/pin/{pin_code}")
def pin_lookup(pin_code: str) -> dict[str, Any]:
    """Resolve a 6-digit PIN code to district + constituencies + MP.

    Returns:
      - district, state from pin_district_mapping
      - list of Lok Sabha constituencies covering that district
      - MP info for each constituency (if available)

    Returns 404 if the PIN is not in the database.
    PIN codes are populated via `constituency/seed_data.py` or bulk CSV import.
    """
    district_info = pin_to_district(pin_code)
    if not district_info:
        raise HTTPException(
            status_code=404,
            detail=(
                f"PIN code {pin_code!r} not found. "
                "The PIN database is populated via India Post data — "
                "see constituency/seed_data.py for sample data or "
                "https://data.gov.in/dataset/all-india-pincode-directory for the full dataset."
            ),
        )

    district = district_info["district"]
    state = district_info["state"]
    constituencies = district_to_constituency(district, state)

    enriched: list[dict[str, Any]] = []
    for c in constituencies:
        mp = get_mp_info(c["constituency"], state=c["state"])
        enriched.append({**c, "mp": mp})

    acs = district_to_ac(district, state)
    assembly_constituencies: list[dict[str, Any]] = []
    for ac in acs:
        mla = get_mla_info(ac["ac_name"], state)
        assembly_constituencies.append(
            {
                "type": "VIDHAN_SABHA",
                "ac_name": ac["ac_name"],
                "ac_no": ac.get("ac_no"),
                "pc_name": ac.get("pc_name"),
                "mla": mla,
            }
        )

    return {
        "pin_code": pin_code,
        "district": district,
        "state": state,
        "office_name": district_info.get("office_name"),
        "constituencies": enriched,
        "constituency_count": len(enriched),
        "assembly_constituencies": assembly_constituencies,
        "assembly_constituency_count": len(assembly_constituencies),
    }


# ---------------------------------------------------------------------------
# Constituency report card
# ---------------------------------------------------------------------------

@router.get("/constituency/search")
def constituency_search(
    q: str = Query(description="Constituency or MP name (partial match)"),
) -> dict[str, Any]:
    """Search for constituencies by name or MP name."""
    results = search_constituency(q)
    return {"query": q, "results": results, "count": len(results)}


@router.get("/constituency/{name}")
def constituency_report(
    name: str,
    fin_year: str = Query(default="2024-2025", description="Financial year"),
    state: str | None = Query(
        default=None,
        description="Disambiguates PC names that exist in more than one state "
        "(AURANGABAD, MAHARAJGANJ, HAMIRPUR)",
    ),
) -> dict[str, Any]:
    """Full report card for a Lok Sabha constituency.

    Returns:
      - MP name, party, state
      - List of districts in constituency
      - Per-scheme performance (delivery + utilization) averaged across districts
      - Composite score and grade
      - Comparison to national average
      - Red flags

    If the constituency is not yet in the database, returns a stub with
    mp_name='Unknown' and empty scheme data (tables may be empty).
    """
    rc = generate_mp_report_card(name.upper(), fin_year=fin_year, scope_state=state)

    return {
        "constituency": rc.constituency,
        "state": rc.state,
        "mp_name": rc.mp_name,
        "party": rc.party,
        "elected_year": rc.elected_year,
        "districts": rc.districts,
        "fin_year": rc.fin_year,
        "composite_score": rc.composite_score,
        "composite_grade": rc.composite_grade,
        "national_avg_score": rc.national_avg_score,
        "red_flags": rc.red_flags,
        "schemes": [
            {
                "scheme": sp.scheme,
                "delivery_pct": sp.delivery_pct,
                "utilization_pct": sp.utilization_pct,
                "score": sp.score,
                "grade": sp.grade,
                "status": sp.status,
            }
            for sp in rc.schemes
        ],
        "source_note": rc.source_note,
    }


@router.get("/constituency/{name}/card")
def constituency_card(
    name: str,
    fin_year: str = Query(default="2024-2025"),
    fmt: str = Query(default="portrait", description="'portrait' (1080x1920) or 'landscape' (1200x630)"),
    state: str | None = Query(default=None, description="Disambiguates duplicate PC names"),
) -> Response:
    """Generate a shareable SVG report card for a constituency.

    Portrait (1080x1920): WhatsApp story format.
    Landscape (1200x630): OG / Twitter card format.

    Returns SVG as image/svg+xml.
    """
    if fmt not in ("portrait", "landscape"):
        raise HTTPException(status_code=400, detail="fmt must be 'portrait' or 'landscape'")

    rc = generate_mp_report_card(name.upper(), fin_year=fin_year, scope_state=state)
    svg_bytes = generate_report_card_image(rc, fmt=fmt)

    return Response(
        content=svg_bytes,
        media_type="image/svg+xml",
        headers={
            "Content-Disposition": f'inline; filename="hisaab-{name.lower()}-{fmt}.svg"',
            "Cache-Control": "public, max-age=3600",
        },
    )


# ---------------------------------------------------------------------------
# MP lookup
# ---------------------------------------------------------------------------

@router.get("/mp/{name}")
def mp_lookup(
    name: str,
    fin_year: str = Query(default="2024-2025"),
    state: str | None = Query(
        default=None,
        description="Required when the constituency name exists in more than "
        "one state (AURANGABAD, MAHARAJGANJ, HAMIRPUR)",
    ),
) -> dict[str, Any]:
    """Look up an MP by constituency name and return their report card.

    `name` is the constituency name (e.g., 'VARANASI', 'LUCKNOW').
    Case-insensitive. Duplicate names across states answer 300 with the
    candidate states — never another state's MP.
    """
    mp = get_mp_info(name, state=state)
    if not mp:
        candidates = get_mp_candidates(name)
        if state is None and len(candidates) > 1:
            raise HTTPException(
                status_code=300,
                detail={
                    "error": f"Constituency {name!r} exists in more than one state.",
                    "candidates": [
                        {
                            "constituency": c["constituency"],
                            "state": c["state"],
                            "mp_name": c["mp_name"],
                        }
                        for c in candidates
                    ],
                    "hint": "Retry with ?state=<STATE>.",
                },
            )
        raise HTTPException(
            status_code=404,
            detail=(
                f"MP for constituency {name!r} not found. "
                "Use /api/v1/constituency/search?q=... to find constituencies."
            ),
        )

    rc = generate_mp_report_card(name.upper(), fin_year=fin_year, scope_state=mp["state"])

    return {
        "mp_name": mp["mp_name"],
        "party": mp["party"],
        "constituency": mp["constituency"],
        "state": mp["state"],
        "elected_year": mp["elected_year"],
        "source_url": mp.get("source_url"),
        "report_card": {
            "composite_score": rc.composite_score,
            "composite_grade": rc.composite_grade,
            "national_avg_score": rc.national_avg_score,
            "districts": rc.districts,
            "red_flags": rc.red_flags,
            "schemes": [
                {
                    "scheme": sp.scheme,
                    "score": sp.score,
                    "grade": sp.grade,
                    "status": sp.status,
                }
                for sp in rc.schemes
            ],
        },
    }
