"""Citizen Action Brief endpoints."""
from __future__ import annotations

import re
import sqlite3
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from action_brief.card import generate_action_card
from action_brief.engine import build_action_brief

router = APIRouter()
_test_conn: sqlite3.Connection | None = None


def _set_test_conn(conn: sqlite3.Connection | None) -> None:
    global _test_conn
    _test_conn = conn


@router.get("/action/{pin_code}")
def action_brief(pin_code: str) -> dict[str, Any]:
    if not re.match(r"^\d{6}$", pin_code.strip()):
        raise HTTPException(status_code=400, detail="PIN code must be exactly 6 digits.")
    brief = build_action_brief(pin_code, conn=_test_conn)
    if not brief:
        raise HTTPException(status_code=404, detail="PIN code not found. Try a nearby PIN.")
    result = asdict(brief)
    result["generated_at"] = brief.generated_at.isoformat()
    for c in result["contacts"]:
        if c.get("last_verified"):
            c["last_verified"] = str(c["last_verified"])
    return result


@router.get("/action/{pin_code}/card")
def action_card(
    pin_code: str,
    format: str = Query(default="portrait"),
) -> Response:
    if not re.match(r"^\d{6}$", pin_code.strip()):
        raise HTTPException(status_code=400, detail="PIN code must be exactly 6 digits.")
    if format not in ("portrait", "landscape"):
        raise HTTPException(status_code=400, detail="format must be 'portrait' or 'landscape'")
    brief = build_action_brief(pin_code, conn=_test_conn)
    if not brief:
        raise HTTPException(status_code=404, detail="PIN code not found. Try a nearby PIN.")
    svg_bytes = generate_action_card(brief, fmt=format)
    return Response(
        content=svg_bytes,
        media_type="image/svg+xml",
        headers={
            "Content-Disposition": f'inline; filename="hisaab-{pin_code}-{format}.svg"',
            "Cache-Control": "public, max-age=3600",
        },
    )
