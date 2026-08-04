"""Embeddable accountability widget endpoints for news organizations.

Endpoints:
    GET /api/v1/embed/{district}       — Self-contained HTML card
    GET /api/v1/embed/{district}/svg   — SVG accountability card
    GET /api/v1/embed/{district}/json  — Raw JSON for custom rendering

Query params (all endpoints):
    scheme  — optional, filter to one scheme slug
    theme   — "light" (default) or "dark"
    width   — card width in px (default 400)
"""

from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, Response

from db import DB_PATH

router = APIRouter()

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_SCHEME_LABELS: dict[str, str] = {
    "mgnrega": "MGNREGA",
    "pmgsy": "PMGSY",
    "pmayg": "PMAY-G",
    "pmkisan": "PM Kisan",
    "jjm": "JJM",
    "pmposhan": "PM POSHAN",
    "nsap": "NSAP",
    "nfsa": "PDS/NFSA",
}


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _resolve_state(district: str) -> str | None:
    conn = _conn()
    for table in ("pmgsy_district", "misappropriation", "financial_statement", "pmayg_district"):
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


def _indicator(value: float, warn_below: float = 50.0, ok_above: float = 75.0) -> str:
    """Return red/yellow/green based on a percentage value."""
    if value >= ok_above:
        return "green"
    if value >= warn_below:
        return "yellow"
    return "red"


def _fetch_district_metrics(
    district: str,
    state: str | None,
    scheme_filter: str | None,
    fin_year: str = "2024-2025",
) -> dict[str, Any]:
    """Collect key metrics across schemes for a district. Returns dict with 'metrics' list."""
    conn = _conn()
    d = district.upper()
    s = (state or "").upper()
    metrics: list[dict[str, Any]] = []

    def _try(fn: Any) -> Any:
        try:
            return fn()
        except Exception:
            return None

    def _row(table: str, extra_where: str = "", params: tuple = ()) -> sqlite3.Row | None:
        where = "UPPER(district) = UPPER(?)"
        p: list[Any] = [d]
        if s:
            where += " AND UPPER(state) = UPPER(?)"
            p.append(s)
        if extra_where:
            where += f" AND {extra_where}"
        p.extend(params)
        return _try(
            lambda: conn.execute(
                f"SELECT * FROM {table} WHERE {where} ORDER BY fin_year DESC LIMIT 1", p
            ).fetchone()
        )

    # MGNREGA
    if not scheme_filter or scheme_filter == "mgnrega":
        row = _row("financial_statement", "fin_year = ?", (fin_year,))
        if not row:
            row = _row("financial_statement")
        if row:
            r = dict(row)
            utilised = r.get("cumulative_expenditure") or 0
            released = r.get("total_availability") or 0
            pct = (utilised / released * 100) if released > 0 else 0
            metrics.append(
                {
                    "scheme": "MGNREGA",
                    "metric": "Fund utilisation",
                    "value": f"{pct:.0f}%",
                    "indicator": _indicator(pct),
                    "detail": f"₹{utilised:.0f}L used of ₹{released:.0f}L",
                }
            )

        mis_row = _row("misappropriation", "fin_year = ?", (fin_year,))
        if not mis_row:
            mis_row = _row("misappropriation")
        if mis_row:
            r = dict(mis_row)
            cases = r.get("cases_reported") or 0
            if cases > 0:
                metrics.append(
                    {
                        "scheme": "MGNREGA",
                        "metric": "Misappropriation cases",
                        "value": str(cases),
                        "indicator": "red" if cases > 5 else "yellow",
                        "detail": f"₹{r.get('amount_reported', 0):.1f}L implicated",
                    }
                )

    # PMGSY
    if not scheme_filter or scheme_filter == "pmgsy":
        row = _try(
            lambda: conn.execute(
                "SELECT * FROM pmgsy_district WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?) LIMIT 1",
                (d, s),
            ).fetchone()
        )
        if not row and not s:
            row = _try(
                lambda: conn.execute(
                    "SELECT * FROM pmgsy_district WHERE UPPER(district) = UPPER(?) LIMIT 1", (d,)
                ).fetchone()
            )
        if row:
            r = dict(row)
            sanctioned = r.get("roads_sanctioned") or 0
            completed = r.get("roads_completed") or 0
            pct = (completed / sanctioned * 100) if sanctioned > 0 else 0
            metrics.append(
                {
                    "scheme": "PMGSY",
                    "metric": "Road completion",
                    "value": f"{pct:.0f}%",
                    "indicator": _indicator(pct),
                    "detail": f"{completed} of {sanctioned} roads done",
                }
            )

    # PMAY-G
    if not scheme_filter or scheme_filter == "pmayg":
        row = _row("pmayg_district", "fin_year = ?", (fin_year,))
        if not row:
            row = _row("pmayg_district")
        if row:
            r = dict(row)
            pct = r.get("completion_pct") or 0
            metrics.append(
                {
                    "scheme": "PMAY-G",
                    "metric": "House completion",
                    "value": f"{pct:.0f}%",
                    "indicator": _indicator(pct),
                    "detail": f"{r.get('houses_completed', 0):,} of {r.get('houses_sanctioned', 0):,} houses",
                }
            )

    # JJM
    if not scheme_filter or scheme_filter == "jjm":
        row = _row("jjm_district", "fin_year = ?", (fin_year,))
        if not row:
            row = _row("jjm_district")
        if row:
            r = dict(row)
            pct = r.get("coverage_pct") or 0
            metrics.append(
                {
                    "scheme": "JJM",
                    "metric": "Tap water coverage",
                    "value": f"{pct:.0f}%",
                    "indicator": _indicator(pct),
                    "detail": f"{r.get('households_with_tap', 0):,} households with tap",
                }
            )

    # PM POSHAN
    if not scheme_filter or scheme_filter == "pmposhan":
        row = _row("pmposhan_district", "fin_year = ?", (fin_year,))
        if not row:
            row = _row("pmposhan_district")
        if row:
            r = dict(row)
            enrolled = r.get("children_enrolled") or 0
            fed = r.get("children_fed") or 0
            pct = (fed / enrolled * 100) if enrolled > 0 else 0
            metrics.append(
                {
                    "scheme": "PM POSHAN",
                    "metric": "Meal coverage",
                    "value": f"{pct:.0f}%",
                    "indicator": _indicator(pct),
                    "detail": f"{fed:,} of {enrolled:,} children",
                }
            )

    # NSAP
    if not scheme_filter or scheme_filter == "nsap":
        row = _row("nsap_district", "fin_year = ?", (fin_year,))
        if not row:
            row = _row("nsap_district")
        if row:
            r = dict(row)
            total_bene = (r.get("beneficiaries_eligible") or 0)
            if total_bene > 0:
                metrics.append(
                    {
                        "scheme": "NSAP",
                        "metric": "Pension beneficiaries",
                        "value": f"{total_bene:,}",
                        "indicator": "green",
                        "detail": "IGNOAPS + IGNWPS",
                    }
                )

    # NFSA
    if not scheme_filter or scheme_filter == "nfsa":
        row = _row("nfsa_district", "fin_year = ?", (fin_year,))
        if not row:
            row = _row("nfsa_district")
        if row:
            r = dict(row)
            active = r.get("ration_cards_active") or 0
            total = r.get("ration_cards_total") or 0
            pct = (active / total * 100) if total > 0 else 0
            if total > 0:
                metrics.append(
                    {
                        "scheme": "PDS/NFSA",
                        "metric": "Active ration cards",
                        "value": f"{pct:.0f}%",
                        "indicator": _indicator(pct),
                        "detail": f"{active:,} of {total:,} active",
                    }
                )

    conn.close()
    return {"metrics": metrics}


# ---------------------------------------------------------------------------
# Theme palettes
# ---------------------------------------------------------------------------

_THEMES: dict[str, dict[str, str]] = {
    "light": {
        "bg": "#ffffff",
        "surface": "#f7f7f8",
        "border": "#e4e4e7",
        "text_primary": "#18181b",
        "text_secondary": "#71717a",
        "text_muted": "#a1a1aa",
        "accent": "#2563eb",
        "accent_light": "#eff6ff",
        "green": "#16a34a",
        "green_bg": "#f0fdf4",
        "yellow": "#ca8a04",
        "yellow_bg": "#fefce8",
        "red": "#dc2626",
        "red_bg": "#fef2f2",
        "shadow": "0 2px 12px rgba(0,0,0,0.08)",
    },
    "dark": {
        "bg": "#18181b",
        "surface": "#27272a",
        "border": "#3f3f46",
        "text_primary": "#fafafa",
        "text_secondary": "#a1a1aa",
        "text_muted": "#71717a",
        "accent": "#60a5fa",
        "accent_light": "#1e3a5f",
        "green": "#4ade80",
        "green_bg": "#14532d",
        "yellow": "#fbbf24",
        "yellow_bg": "#451a03",
        "red": "#f87171",
        "red_bg": "#450a0a",
        "shadow": "0 2px 12px rgba(0,0,0,0.40)",
    },
}


def _t(theme: str, key: str) -> str:
    return _THEMES.get(theme, _THEMES["light"])[key]


# ---------------------------------------------------------------------------
# HTML card builder
# ---------------------------------------------------------------------------

def _build_html_card(
    district: str,
    state: str | None,
    metrics: list[dict[str, Any]],
    theme: str,
    width: int,
) -> str:
    import html as html_mod

    t = theme if theme in _THEMES else "light"
    c = _THEMES[t]
    district = html_mod.escape(district)
    state_label = html_mod.escape(state or "India")
    scheme_count = len({m["scheme"] for m in metrics})

    rows_html = ""
    if not metrics:
        rows_html = (
            f'<div style="color:{c["text_muted"]};text-align:center;padding:16px 0;font-size:13px;">'
            f"No scheme data available for this district.</div>"
        )
    else:
        for m in metrics:
            ind = m["indicator"]
            ind_color = c[ind]
            ind_bg = c[f"{ind}_bg"]
            rows_html += f"""
        <div style="display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid {c['border']};">
          <div style="flex:1;min-width:0;">
            <div style="font-size:11px;color:{c['text_muted']};text-transform:uppercase;letter-spacing:0.06em;margin-bottom:2px;">{m['scheme']}</div>
            <div style="font-size:13px;color:{c['text_secondary']};white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{m['metric']}</div>
            <div style="font-size:11px;color:{c['text_muted']};margin-top:1px;">{m['detail']}</div>
          </div>
          <div style="background:{ind_bg};color:{ind_color};border-radius:8px;padding:4px 10px;font-size:13px;font-weight:600;white-space:nowrap;">{m['value']}</div>
        </div>"""

    empty_last = '<div style="border-bottom:none!important;"></div>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Hisaab — {district.title()}</title>
<style>
  *,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
  body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:transparent;}}
  a{{color:{c['accent']};text-decoration:none;}}
  a:hover{{text-decoration:underline;}}
</style>
</head>
<body>
<div style="width:{width}px;max-width:100%;background:{c['bg']};border:1px solid {c['border']};border-radius:12px;box-shadow:{c['shadow']};overflow:hidden;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">

  <!-- Header -->
  <div style="background:{c['surface']};padding:14px 16px;border-bottom:1px solid {c['border']};">
    <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:8px;">
      <div>
        <div style="font-size:16px;font-weight:700;color:{c['text_primary']};line-height:1.2;">{district.upper()}</div>
        <div style="font-size:12px;color:{c['text_secondary']};margin-top:2px;">{state_label} &middot; {scheme_count} scheme{'s' if scheme_count != 1 else ''}</div>
      </div>
      <div style="background:{c['accent_light']};color:{c['accent']};border-radius:6px;padding:3px 8px;font-size:11px;font-weight:600;white-space:nowrap;">LIVE DATA</div>
    </div>
  </div>

  <!-- Metrics -->
  <div style="padding:0 16px;">
    {rows_html}
    {empty_last}
  </div>

  <!-- Footer -->
  <div style="padding:10px 16px;border-top:1px solid {c['border']};display:flex;align-items:center;justify-content:space-between;">
    <a href="https://hisaab.in/district/{district.lower()}" style="font-size:11px;color:{c['accent']};font-weight:500;">View full report →</a>
    <span style="font-size:10px;color:{c['text_muted']};">Powered by <a href="https://hisaab.in" style="color:{c['text_muted']};text-decoration:underline;">Hisaab</a></span>
  </div>

</div>
</body>
</html>"""
    return html


# ---------------------------------------------------------------------------
# SVG card builder
# ---------------------------------------------------------------------------

def _build_svg_card(
    district: str,
    state: str | None,
    metrics: list[dict[str, Any]],
    theme: str,
    width: int,
) -> str:
    t = theme if theme in _THEMES else "light"
    c = _THEMES[t]
    state_label = state or "India"

    row_h = 52
    header_h = 64
    footer_h = 36
    padding = 16
    empty_msg_h = 60

    visible = metrics[:6]  # cap at 6 rows to keep SVG manageable
    content_h = (row_h * len(visible)) if visible else empty_msg_h
    total_h = header_h + content_h + footer_h

    rows_svg = ""
    for i, m in enumerate(visible):
        y = header_h + i * row_h
        ind = m["indicator"]
        ind_color = c[ind]
        ind_bg = c[f"{ind}_bg"]
        scheme_esc = m["scheme"].replace("&", "&amp;").replace("<", "&lt;")
        metric_esc = m["metric"].replace("&", "&amp;").replace("<", "&lt;")
        detail_esc = m["detail"].replace("&", "&amp;").replace("<", "&lt;")
        value_esc = m["value"].replace("&", "&amp;").replace("<", "&lt;")

        # badge width estimate: ~8px per char + 20px padding
        badge_w = max(40, len(m["value"]) * 8 + 20)
        badge_x = width - padding - badge_w

        rows_svg += f"""
  <!-- row {i} -->
  <rect x="{padding}" y="{y + row_h - 1}" width="{width - padding * 2}" height="1" fill="{c['border']}"/>
  <text x="{padding}" y="{y + 14}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="10" font-weight="600" fill="{c['text_muted']}" letter-spacing="0.8">{scheme_esc}</text>
  <text x="{padding}" y="{y + 29}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="12" fill="{c['text_secondary']}">{metric_esc}</text>
  <text x="{padding}" y="{y + 44}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="10" fill="{c['text_muted']}">{detail_esc}</text>
  <rect x="{badge_x}" y="{y + 16}" width="{badge_w}" height="22" rx="6" fill="{ind_bg}"/>
  <text x="{badge_x + badge_w // 2}" y="{y + 31}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="12" font-weight="700" fill="{ind_color}" text-anchor="middle">{value_esc}</text>"""

    if not visible:
        rows_svg = f"""
  <text x="{width // 2}" y="{header_h + 35}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="12" fill="{c['text_muted']}" text-anchor="middle">No scheme data available.</text>"""

    district_esc = district.upper().replace("&", "&amp;")
    state_esc = state_label.replace("&", "&amp;")
    scheme_count = len({m["scheme"] for m in metrics})

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{total_h}" viewBox="0 0 {width} {total_h}">
  <defs>
    <clipPath id="card"><rect rx="12" ry="12" width="{width}" height="{total_h}"/></clipPath>
  </defs>
  <rect width="{width}" height="{total_h}" rx="12" fill="{c['bg']}" stroke="{c['border']}"/>

  <!-- Header -->
  <rect width="{width}" height="{header_h}" rx="12" fill="{c['surface']}" clip-path="url(#card)"/>
  <rect y="{header_h - 1}" width="{width}" height="1" fill="{c['border']}"/>
  <text x="{padding}" y="26" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="16" font-weight="700" fill="{c['text_primary']}">{district_esc}</text>
  <text x="{padding}" y="46" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="11" fill="{c['text_secondary']}">{state_esc} · {scheme_count} scheme{'s' if scheme_count != 1 else ''}</text>
  <!-- LIVE badge -->
  <rect x="{width - 70}" y="16" width="54" height="20" rx="5" fill="{c['accent_light']}"/>
  <text x="{width - 43}" y="30" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="10" font-weight="700" fill="{c['accent']}" text-anchor="middle">LIVE DATA</text>

  <!-- Rows -->
  {rows_svg}

  <!-- Footer -->
  <rect y="{header_h + content_h}" width="{width}" height="{footer_h}" fill="{c['surface']}" clip-path="url(#card)"/>
  <rect y="{header_h + content_h}" width="{width}" height="1" fill="{c['border']}"/>
  <text x="{padding}" y="{header_h + content_h + 22}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="11" fill="{c['accent']}">View full report →</text>
  <text x="{width - padding}" y="{header_h + content_h + 22}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif" font-size="10" fill="{c['text_muted']}" text-anchor="end">Powered by Hisaab</text>
</svg>"""
    return svg


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/embed/{district}", response_class=HTMLResponse)
def embed_html(
    district: str,
    scheme: str = Query(default=None, description="Filter to one scheme slug"),
    theme: str = Query(default="light", description="light or dark"),
    width: int = Query(default=400, ge=200, le=800),
    state: str = Query(default=None),
    fin_year: str = Query(default="2024-2025"),
) -> HTMLResponse:
    """Self-contained HTML accountability card for embedding."""
    resolved_state = state or _resolve_state(district)
    if not resolved_state:
        raise HTTPException(status_code=404, detail=f"District not found: {district}")

    result = _fetch_district_metrics(district, resolved_state, scheme, fin_year)
    html = _build_html_card(district, resolved_state, result["metrics"], theme, width)
    return HTMLResponse(
        content=html,
        headers={"X-Frame-Options": "ALLOWALL", "Cache-Control": "public, max-age=3600"},
    )


@router.get("/embed/{district}/svg")
def embed_svg(
    district: str,
    scheme: str = Query(default=None),
    theme: str = Query(default="light"),
    width: int = Query(default=400, ge=200, le=800),
    state: str = Query(default=None),
    fin_year: str = Query(default="2024-2025"),
) -> Response:
    """SVG accountability card — suitable for direct img src embedding."""
    resolved_state = state or _resolve_state(district)
    if not resolved_state:
        raise HTTPException(status_code=404, detail=f"District not found: {district}")

    result = _fetch_district_metrics(district, resolved_state, scheme, fin_year)
    svg = _build_svg_card(district, resolved_state, result["metrics"], theme, width)
    return Response(
        content=svg,
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.get("/embed/{district}/json")
def embed_json(
    district: str,
    scheme: str = Query(default=None),
    state: str = Query(default=None),
    fin_year: str = Query(default="2024-2025"),
) -> dict[str, Any]:
    """Raw JSON for custom rendering of accountability widgets."""
    resolved_state = state or _resolve_state(district)
    if not resolved_state:
        raise HTTPException(status_code=404, detail=f"District not found: {district}")

    result = _fetch_district_metrics(district, resolved_state, scheme, fin_year)
    return {
        "district": district.upper(),
        "state": resolved_state,
        "fin_year": fin_year,
        "metrics": result["metrics"],
        "embed_url": f"https://hisaab.in/api/v1/embed/{district.lower()}",
        "report_url": f"https://hisaab.in/district/{district.lower()}",
    }
