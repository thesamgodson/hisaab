"""MP Report Card generation — aggregated scheme performance per constituency.

Generates:
  - MPReportCard dataclass (structured data)
  - SVG report card image (shareable, WhatsApp-friendly)

Image formats:
  - Portrait 1080x1920 — WhatsApp story / mobile share
  - Landscape 1200x630 — OG / Twitter card
"""

from __future__ import annotations

import sqlite3
import textwrap
from dataclasses import dataclass, field
from typing import Any

from db.connection import DB_PATH, get_connection
from constituency.mapper import get_districts_for_constituency, get_mp_info
from queries.composite import get_district_score

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ALL_SCHEMES = [
    "MGNREGA",
    "PMGSY",
    "PMAY-G",
    "PM Kisan",
    "JJM",
    "PM POSHAN",
    "NSAP",
    "PDS/NFSA",
    "SBM-G",
    "DAY-NRLM",
    "UDISE+",
]

_GRADE_COLORS: dict[str, str] = {
    "A": "#16a34a",  # green-600
    "B": "#2563eb",  # blue-600
    "C": "#d97706",  # amber-600
    "D": "#ea580c",  # orange-600
    "F": "#dc2626",  # red-600
}

_SCORE_STATUS: list[tuple[float, str, str]] = [
    (75.0, "green", "#16a34a"),
    (50.0, "yellow", "#d97706"),
    (25.0, "orange", "#ea580c"),
    (0.0, "red", "#dc2626"),
]


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class SchemePerformance:
    scheme: str
    delivery_pct: float | None
    utilization_pct: float | None
    score: float | None
    grade: str | None
    status: str  # "green" | "yellow" | "orange" | "red" | "no_data"
    color: str


@dataclass
class MPReportCard:
    constituency: str
    state: str
    mp_name: str
    party: str
    elected_year: int
    districts: list[str]
    composite_score: float | None
    composite_grade: str | None
    national_avg_score: float | None
    schemes: list[SchemePerformance]
    red_flags: list[str]
    fin_year: str
    source_note: str = "Data sourced from official government portals via Hisaab."
    extra: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _conn():
    return get_connection(DB_PATH)


def _score_to_status(score: float | None) -> tuple[str, str]:
    """Return (status_label, hex_color) for a score."""
    if score is None:
        return ("no_data", "#9ca3af")
    for threshold, label, color in _SCORE_STATUS:
        if score >= threshold:
            return (label, color)
    return ("red", "#dc2626")


def _get_national_average(fin_year: str) -> float | None:
    """Return mean composite score across all districts with data."""
    conn = _conn()
    try:
        row = conn.execute(
            """
            SELECT AVG(delivery_pct) as avg_delivery
            FROM scheme_delivery
            WHERE delivery_pct IS NOT NULL
              AND delivery_pct <= 100
            """
        ).fetchone()
        if row and row["avg_delivery"] is not None:
            return round(float(row["avg_delivery"]), 1)
        return None
    finally:
        conn.close()


def _aggregate_scheme_performance(
    districts: list[str],
    state: str,
    fin_year: str,
) -> list[SchemePerformance]:
    """Aggregate delivery and finance metrics per scheme across all districts."""
    if not districts:
        return [
            SchemePerformance(
                scheme=s,
                delivery_pct=None,
                utilization_pct=None,
                score=None,
                grade=None,
                status="no_data",
                color="#9ca3af",
            )
            for s in ALL_SCHEMES
        ]

    conn = _conn()
    results: list[SchemePerformance] = []
    try:
        for scheme in ALL_SCHEMES:
            delivery_rows = conn.execute(
                """
                SELECT AVG(delivery_pct) as avg_d
                FROM scheme_delivery
                WHERE scheme = ?
                  AND UPPER(state) = UPPER(?)
                  AND UPPER(district) IN ({})
                  AND delivery_pct IS NOT NULL
                """.format(",".join("?" * len(districts))),
                [scheme, state] + [d.upper() for d in districts],
            ).fetchone()

            finance_rows = conn.execute(
                """
                SELECT AVG(utilization_pct) as avg_u
                FROM scheme_finance
                WHERE scheme = ?
                  AND UPPER(state) = UPPER(?)
                  AND UPPER(district) IN ({})
                  AND utilization_pct IS NOT NULL
                  AND utilization_pct > 0
                  AND utilization_pct <= 150
                """.format(",".join("?" * len(districts))),
                [scheme, state] + [d.upper() for d in districts],
            ).fetchone()

            delivery_pct = (
                round(float(delivery_rows["avg_d"]), 1)
                if delivery_rows and delivery_rows["avg_d"] is not None
                else None
            )
            utilization_pct = (
                round(min(100.0, float(finance_rows["avg_u"])), 1)
                if finance_rows and finance_rows["avg_u"] is not None
                else None
            )

            # Composite micro-score: 60% delivery, 40% utilization
            if delivery_pct is not None and utilization_pct is not None:
                score: float | None = round(delivery_pct * 0.6 + utilization_pct * 0.4, 1)
            elif delivery_pct is not None:
                score = round(delivery_pct, 1)
            elif utilization_pct is not None:
                score = round(utilization_pct, 1)
            else:
                score = None

            grade: str | None = None
            if score is not None:
                if score >= 80:
                    grade = "A"
                elif score >= 60:
                    grade = "B"
                elif score >= 40:
                    grade = "C"
                elif score >= 20:
                    grade = "D"
                else:
                    grade = "F"

            status, color = _score_to_status(score)
            results.append(
                SchemePerformance(
                    scheme=scheme,
                    delivery_pct=delivery_pct,
                    utilization_pct=utilization_pct,
                    score=score,
                    grade=grade,
                    status=status,
                    color=color,
                )
            )
    finally:
        conn.close()

    return results


def _compute_composite(schemes: list[SchemePerformance]) -> tuple[float | None, str | None]:
    """Compute constituency composite from scheme scores."""
    scores = [s.score for s in schemes if s.score is not None]
    if not scores:
        return None, None
    avg = round(sum(scores) / len(scores), 1)
    if avg >= 80:
        return avg, "A"
    if avg >= 60:
        return avg, "B"
    if avg >= 40:
        return avg, "C"
    if avg >= 20:
        return avg, "D"
    return avg, "F"


def _collect_red_flags(schemes: list[SchemePerformance]) -> list[str]:
    """Return human-readable red flags for the worst performers."""
    flags: list[str] = []
    for s in schemes:
        if s.delivery_pct is not None and s.delivery_pct < 40:
            flags.append(f"{s.scheme} delivery at {s.delivery_pct:.0f}%")
        elif s.utilization_pct is not None and s.utilization_pct < 30:
            flags.append(f"{s.scheme} fund utilization at {s.utilization_pct:.0f}%")
    return flags[:5]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_mp_report_card(
    constituency: str,
    fin_year: str = "2024-2025",
) -> MPReportCard:
    """Generate a full MP Report Card for a constituency.

    If constituency is not found in mp_info, a stub card is returned with
    mp_name='Unknown' so callers can still display district-level data.
    """
    mp = get_mp_info(constituency)
    districts = get_districts_for_constituency(constituency)

    if mp:
        mp_name = mp["mp_name"]
        party = mp.get("party", "")
        state = mp["state"]
        elected_year = int(mp.get("elected_year", 2024))
    else:
        mp_name = "Unknown"
        party = ""
        state = ""
        elected_year = 2024

    # If state is empty but we have districts, try to infer state from constituency_district
    if not state and districts:
        conn = _conn()
        try:
            row = conn.execute(
                "SELECT state FROM constituency_district "
                "WHERE UPPER(constituency) = UPPER(?) LIMIT 1",
                (constituency,),
            ).fetchone()
            if row:
                state = row["state"]
        finally:
            conn.close()

    schemes = _aggregate_scheme_performance(districts, state, fin_year)
    composite_score, composite_grade = _compute_composite(schemes)
    national_avg = _get_national_average(fin_year)
    red_flags = _collect_red_flags(schemes)

    return MPReportCard(
        constituency=constituency.upper(),
        state=state,
        mp_name=mp_name,
        party=party,
        elected_year=elected_year,
        districts=districts,
        composite_score=composite_score,
        composite_grade=composite_grade,
        national_avg_score=national_avg,
        schemes=schemes,
        red_flags=red_flags,
        fin_year=fin_year,
    )


# ---------------------------------------------------------------------------
# SVG image generation
# ---------------------------------------------------------------------------

_SCHEME_ICONS: dict[str, str] = {
    "MGNREGA": "👷",
    "PMGSY": "🛣️",
    "PMAY-G": "🏠",
    "PM Kisan": "🌾",
    "JJM": "💧",
    "PM POSHAN": "🍱",
    "NSAP": "❤️",
    "PDS/NFSA": "🌾",
    "SBM-G": "🚿",
    "DAY-NRLM": "👩",
    "UDISE+": "📚",
}


def _status_dot_color(status: str) -> str:
    return {
        "green": "#16a34a",
        "yellow": "#d97706",
        "orange": "#ea580c",
        "red": "#dc2626",
        "no_data": "#d1d5db",
    }.get(status, "#d1d5db")


def generate_report_card_image(
    report_card: MPReportCard,
    fmt: str = "portrait",
) -> bytes:
    """Generate an SVG report card image as bytes.

    fmt: 'portrait' (1080x1920 for WhatsApp) or 'landscape' (1200x630 for OG).
    Returns UTF-8 encoded SVG bytes.
    """
    if fmt == "landscape":
        return _render_landscape_svg(report_card)
    return _render_portrait_svg(report_card)


def _grade_color(grade: str | None) -> str:
    return _GRADE_COLORS.get(grade or "", "#6b7280")


def _render_portrait_svg(rc: MPReportCard) -> bytes:
    """1080×1920 portrait SVG — WhatsApp story format."""
    w, h = 1080, 1920
    grade_color = _grade_color(rc.composite_grade)
    score_text = f"{rc.composite_score:.0f}" if rc.composite_score is not None else "–"

    # Build scheme rows (2 columns)
    scheme_rows_svg = []
    col_w = 460
    row_h = 90
    start_y = 780
    for idx, sp in enumerate(rc.schemes):
        col = idx % 2
        row = idx // 2
        x = 60 + col * (col_w + 60)
        y = start_y + row * row_h
        dot_color = _status_dot_color(sp.status)
        score_label = f"{sp.score:.0f}%" if sp.score is not None else "N/A"
        scheme_rows_svg.append(
            f'<circle cx="{x + 16}" cy="{y + 20}" r="10" fill="{dot_color}"/>'
            f'<text x="{x + 36}" y="{y + 26}" font-size="26" fill="#1f2937" font-family="Inter,sans-serif">'
            f'{sp.scheme}</text>'
            f'<text x="{x + col_w - 10}" y="{y + 26}" font-size="24" fill="{dot_color}" '
            f'text-anchor="end" font-family="Inter,sans-serif" font-weight="600">'
            f'{score_label}</text>'
        )

    schemes_block = "\n".join(scheme_rows_svg)

    # Red flags
    flags_svg = ""
    if rc.red_flags:
        flags_svg = '<text x="60" y="1720" font-size="28" fill="#ef4444" font-family="Inter,sans-serif" font-weight="600">Red Flags</text>'
        for i, flag in enumerate(rc.red_flags[:3]):
            fy = 1760 + i * 44
            short = textwrap.shorten(flag, width=55, placeholder="…")
            flags_svg += (
                f'<text x="72" y="{fy}" font-size="24" fill="#374151" font-family="Inter,sans-serif">'
                f'• {short}</text>'
            )

    districts_str = ", ".join(rc.districts[:4])
    if len(rc.districts) > 4:
        districts_str += f" +{len(rc.districts) - 4} more"

    national_cmp = ""
    if rc.national_avg_score and rc.composite_score:
        diff = rc.composite_score - rc.national_avg_score
        sign = "+" if diff >= 0 else ""
        national_cmp = f"{sign}{diff:.0f} vs national avg ({rc.national_avg_score:.0f})"

    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <!-- Background -->
  <rect width="{w}" height="{h}" fill="#f9fafb"/>
  <rect x="0" y="0" width="{w}" height="320" fill="#1e3a5f"/>

  <!-- Header: Hisaab branding -->
  <text x="60" y="80" font-size="36" fill="#93c5fd" font-family="Inter,sans-serif" font-weight="400">हिसाब · Hisaab</text>
  <text x="60" y="130" font-size="28" fill="#bfdbfe" font-family="Inter,sans-serif">MP Report Card · {rc.fin_year}</text>

  <!-- MP Name -->
  <text x="60" y="210" font-size="56" fill="#ffffff" font-family="Inter,sans-serif" font-weight="700">{rc.mp_name}</text>
  <text x="60" y="268" font-size="34" fill="#93c5fd" font-family="Inter,sans-serif">{rc.constituency} · {rc.party}</text>

  <!-- Score badge -->
  <rect x="{w - 260}" y="60" width="200" height="200" rx="20" fill="{grade_color}" opacity="0.15"/>
  <text x="{w - 160}" y="180" font-size="100" fill="{grade_color}" text-anchor="middle"
        font-family="Inter,sans-serif" font-weight="700">{score_text}</text>
  <text x="{w - 160}" y="232" font-size="30" fill="{grade_color}" text-anchor="middle"
        font-family="Inter,sans-serif">Grade {rc.composite_grade or "–"}</text>

  <!-- Separator -->
  <line x1="60" y1="340" x2="{w - 60}" y2="340" stroke="#e5e7eb" stroke-width="2"/>

  <!-- Districts -->
  <text x="60" y="400" font-size="28" fill="#6b7280" font-family="Inter,sans-serif">Districts covered</text>
  <text x="60" y="444" font-size="30" fill="#1f2937" font-family="Inter,sans-serif" font-weight="600">{districts_str}</text>

  <!-- National comparison -->
  <text x="60" y="510" font-size="26" fill="#6b7280" font-family="Inter,sans-serif">{national_cmp}</text>

  <!-- Separator -->
  <line x1="60" y1="560" x2="{w - 60}" y2="560" stroke="#e5e7eb" stroke-width="2"/>

  <!-- Scheme heading -->
  <text x="60" y="620" font-size="32" fill="#1f2937" font-family="Inter,sans-serif" font-weight="700">Scheme Performance</text>
  <text x="60" y="660" font-size="24" fill="#6b7280" font-family="Inter,sans-serif">Average across {len(rc.districts)} district(s)</text>

  <!-- Legend -->
  <circle cx="60" cy="730" r="10" fill="#16a34a"/><text x="80" y="736" font-size="22" fill="#374151" font-family="Inter,sans-serif">75%+ Good</text>
  <circle cx="230" cy="730" r="10" fill="#d97706"/><text x="250" y="736" font-size="22" fill="#374151" font-family="Inter,sans-serif">50%+ Fair</text>
  <circle cx="390" cy="730" r="10" fill="#ea580c"/><text x="410" y="736" font-size="22" fill="#374151" font-family="Inter,sans-serif">25%+ Poor</text>
  <circle cx="545" cy="730" r="10" fill="#dc2626"/><text x="565" y="736" font-size="22" fill="#374151" font-family="Inter,sans-serif">Below 25%</text>
  <circle cx="700" cy="730" r="10" fill="#d1d5db"/><text x="720" y="736" font-size="22" fill="#374151" font-family="Inter,sans-serif">N/A</text>

  <!-- Scheme rows -->
  {schemes_block}

  <!-- Red flags -->
  {flags_svg}

  <!-- Footer -->
  <rect x="0" y="{h - 80}" width="{w}" height="80" fill="#1e3a5f"/>
  <text x="{w // 2}" y="{h - 34}" font-size="24" fill="#93c5fd" text-anchor="middle"
        font-family="Inter,sans-serif">hisaab.in · Data from official government portals</text>
</svg>"""

    return svg.encode("utf-8")


def _render_landscape_svg(rc: MPReportCard) -> bytes:
    """1200×630 landscape SVG — OG / Twitter card format."""
    w, h = 1200, 630
    grade_color = _grade_color(rc.composite_grade)
    score_text = f"{rc.composite_score:.0f}" if rc.composite_score is not None else "–"

    # Scheme dots (3 rows of 4)
    dots_svg = []
    dot_x_start = 480
    dot_spacing = 170
    for idx, sp in enumerate(rc.schemes):
        row = idx // 4
        col = idx % 4
        cx = dot_x_start + col * dot_spacing
        cy = 310 + row * 80
        color = _status_dot_color(sp.status)
        dots_svg.append(
            f'<circle cx="{cx + 12}" cy="{cy}" r="14" fill="{color}"/>'
            f'<text x="{cx + 12}" y="{cy + 40}" font-size="18" fill="#374151" '
            f'text-anchor="middle" font-family="Inter,sans-serif">{sp.scheme.replace("PDS/NFSA", "NFSA").replace("PM POSHAN", "POSHAN").replace("DAY-NRLM", "NRLM")}</text>'
        )
    dots_block = "\n".join(dots_svg)

    districts_str = ", ".join(rc.districts[:3])
    if len(rc.districts) > 3:
        districts_str += f" +{len(rc.districts) - 3}"

    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <rect width="{w}" height="{h}" fill="#f9fafb"/>
  <rect x="0" y="0" width="{w}" height="{h}" fill="#1e3a5f" opacity="0.03"/>

  <!-- Left panel -->
  <rect x="0" y="0" width="420" height="{h}" fill="#1e3a5f"/>
  <text x="40" y="60" font-size="22" fill="#93c5fd" font-family="Inter,sans-serif">हिसाब · Hisaab</text>
  <text x="40" y="100" font-size="18" fill="#bfdbfe" font-family="Inter,sans-serif">MP Report Card · {rc.fin_year}</text>

  <!-- Score -->
  <text x="210" y="230" font-size="120" fill="{grade_color}" text-anchor="middle"
        font-family="Inter,sans-serif" font-weight="700">{score_text}</text>
  <text x="210" y="280" font-size="30" fill="{grade_color}" text-anchor="middle"
        font-family="Inter,sans-serif">Grade {rc.composite_grade or "–"}</text>

  <text x="210" y="350" font-size="22" fill="#93c5fd" text-anchor="middle"
        font-family="Inter,sans-serif">Composite Score</text>

  <text x="40" y="430" font-size="18" fill="#bfdbfe" font-family="Inter,sans-serif">Districts: {districts_str}</text>

  <text x="210" y="{h - 30}" font-size="16" fill="#64748b" text-anchor="middle"
        font-family="Inter,sans-serif">hisaab.in</text>

  <!-- Right panel: MP info + scheme dots -->
  <text x="460" y="80" font-size="48" fill="#1f2937" font-family="Inter,sans-serif" font-weight="700">{rc.mp_name}</text>
  <text x="460" y="130" font-size="28" fill="#6b7280" font-family="Inter,sans-serif">{rc.constituency}</text>
  <text x="460" y="170" font-size="24" fill="#9ca3af" font-family="Inter,sans-serif">{rc.party} · {rc.state}</text>

  <line x1="460" y1="210" x2="{w - 60}" y2="210" stroke="#e5e7eb" stroke-width="1.5"/>

  <text x="460" y="260" font-size="22" fill="#374151" font-family="Inter,sans-serif" font-weight="600">Scheme Performance (11 schemes)</text>

  <!-- Dots -->
  {dots_block}

  <!-- Legend -->
  <circle cx="480" cy="{h - 60}" r="8" fill="#16a34a"/>
  <text x="496" y="{h - 55}" font-size="14" fill="#6b7280" font-family="Inter,sans-serif">75%+ Good</text>
  <circle cx="610" cy="{h - 60}" r="8" fill="#d97706"/>
  <text x="626" y="{h - 55}" font-size="14" fill="#6b7280" font-family="Inter,sans-serif">50%+ Fair</text>
  <circle cx="730" cy="{h - 60}" r="8" fill="#ea580c"/>
  <text x="746" y="{h - 55}" font-size="14" fill="#6b7280" font-family="Inter,sans-serif">25%+ Poor</text>
  <circle cx="855" cy="{h - 60}" r="8" fill="#dc2626"/>
  <text x="871" y="{h - 55}" font-size="14" fill="#6b7280" font-family="Inter,sans-serif">&lt;25%</text>
  <circle cx="945" cy="{h - 60}" r="8" fill="#d1d5db"/>
  <text x="961" y="{h - 55}" font-size="14" fill="#6b7280" font-family="Inter,sans-serif">N/A</text>

  <!-- Footer right -->
  <text x="460" y="{h - 20}" font-size="14" fill="#9ca3af"
        font-family="Inter,sans-serif">Data from official government portals</text>
</svg>"""

    return svg.encode("utf-8")
