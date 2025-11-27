"""SVG generation for shareable action brief cards."""
from __future__ import annotations

import textwrap

from action_brief.models import ActionBrief

_SEVERITY_COLORS = {"high": "#dc2626", "medium": "#d97706", "low": "#6b7280"}


def generate_action_card(brief: ActionBrief, fmt: str = "portrait") -> bytes:
    """Generate a shareable SVG card for the given action brief.

    Args:
        brief: The action brief data.
        fmt: Either "portrait" (1080x1920) or "landscape" (1200x630).

    Returns:
        UTF-8 encoded SVG bytes.
    """
    if fmt == "landscape":
        return _render_landscape(brief)
    return _render_portrait(brief)


def _escape(text: str) -> str:
    """Escape XML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _mp_label(brief: ActionBrief) -> str:
    if brief.mp:
        name = _escape(brief.mp.get("mp_name") or "")
        party = _escape(brief.mp.get("party") or "")
        return f"{name} ({party})" if party else name
    return "MP: —"


def _mla_label(brief: ActionBrief) -> str:
    if brief.mla:
        name = _escape(brief.mla.get("mla_name") or "")
        party = _escape(brief.mla.get("party") or "")
        return f"{name} ({party})" if party else name
    return "MLA: —"


def _render_portrait(brief: ActionBrief) -> bytes:
    """1080×1920 portrait SVG — WhatsApp story format."""
    w, h = 1080, 1920

    district = _escape(brief.district)
    state = _escape(brief.state)
    date_str = brief.generated_at.strftime("%d %b %Y")
    mp_label = _mp_label(brief)
    mla_label = _mla_label(brief)

    # Build diagnosis rows (max 4)
    diag_svg_parts: list[str] = []
    for idx, item in enumerate(brief.diagnosis[:4]):
        y = 520 + idx * 200
        dot_color = _SEVERITY_COLORS.get(item.severity, "#6b7280")
        scheme_text = _escape(item.scheme)
        summary = _escape(textwrap.shorten(item.summary, width=60, placeholder="…"))
        detail = _escape(textwrap.shorten(item.detail, width=70, placeholder="…")) if item.detail else ""

        diag_svg_parts.append(
            f'  <!-- Diagnosis item {idx + 1} -->'
            f'\n  <circle cx="80" cy="{y + 14}" r="12" fill="{dot_color}"/>'
            f'\n  <text x="108" y="{y + 20}" font-size="26" fill="#374151" font-weight="600"'
            f' font-family="Inter,sans-serif">{scheme_text}</text>'
            f'\n  <text x="108" y="{y + 56}" font-size="24" fill="#1f2937"'
            f' font-family="Inter,sans-serif">{summary}</text>'
        )
        if detail:
            diag_svg_parts.append(
                f'  <text x="108" y="{y + 90}" font-size="20" fill="#6b7280"'
                f' font-family="Inter,sans-serif">{detail}</text>'
            )

    diag_block = "\n".join(diag_svg_parts)

    # Contacts section
    contact_y = 520 + min(len(brief.diagnosis), 4) * 200 + 60
    contacts_block = (
        f'  <line x1="60" y1="{contact_y}" x2="{w - 60}" y2="{contact_y}" stroke="#e5e7eb" stroke-width="2"/>'
        f'\n  <text x="60" y="{contact_y + 50}" font-size="30" fill="#1f2937" font-weight="700"'
        f' font-family="Inter,sans-serif">Your Representatives</text>'
        f'\n  <text x="60" y="{contact_y + 96}" font-size="26" fill="#374151"'
        f' font-family="Inter,sans-serif">MP: {mp_label}</text>'
        f'\n  <text x="60" y="{contact_y + 140}" font-size="26" fill="#374151"'
        f' font-family="Inter,sans-serif">MLA: {mla_label}</text>'
    )

    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <!-- Background -->
  <rect width="{w}" height="{h}" fill="#f9fafb"/>
  <rect x="0" y="0" width="{w}" height="380" fill="#1e3a5f"/>

  <!-- Header: Hisaab branding -->
  <text x="60" y="80" font-size="36" fill="#93c5fd" font-family="Inter,sans-serif" font-weight="400">हिसाब · Hisaab</text>
  <text x="60" y="128" font-size="28" fill="#bfdbfe" font-family="Inter,sans-serif">Citizen Action Brief</text>

  <!-- District + State -->
  <text x="60" y="220" font-size="60" fill="#ffffff" font-family="Inter,sans-serif" font-weight="700">{district}</text>
  <text x="60" y="278" font-size="34" fill="#93c5fd" font-family="Inter,sans-serif">{state}</text>

  <!-- Separator -->
  <line x1="60" y1="400" x2="{w - 60}" y2="400" stroke="#e5e7eb" stroke-width="2"/>

  <!-- Diagnosis heading -->
  <text x="60" y="466" font-size="32" fill="#1f2937" font-family="Inter,sans-serif" font-weight="700">Issues Found in Your District</text>

  <!-- Diagnosis items -->
{diag_block}

  <!-- Contacts -->
{contacts_block}

  <!-- Footer -->
  <rect x="0" y="{h - 80}" width="{w}" height="80" fill="#1e3a5f"/>
  <text x="{w // 2}" y="{h - 44}" font-size="22" fill="#bfdbfe" text-anchor="middle"
        font-family="Inter,sans-serif">Enter your PIN at hisaab.info</text>
  <text x="{w // 2}" y="{h - 14}" font-size="20" fill="#93c5fd" text-anchor="middle"
        font-family="Inter,sans-serif">{date_str}</text>
</svg>"""

    return svg.encode("utf-8")


def _render_landscape(brief: ActionBrief) -> bytes:
    """1200×630 landscape SVG — OG / Twitter card format."""
    w, h = 1200, 630

    district = _escape(brief.district)
    state = _escape(brief.state)
    date_str = brief.generated_at.strftime("%d %b %Y")
    mp_label = _mp_label(brief)
    mla_label = _mla_label(brief)

    # Build diagnosis rows (max 3)
    diag_svg_parts: list[str] = []
    for idx, item in enumerate(brief.diagnosis[:3]):
        y = 270 + idx * 76
        dot_color = _SEVERITY_COLORS.get(item.severity, "#6b7280")
        scheme_text = _escape(item.scheme)
        summary = _escape(textwrap.shorten(item.summary, width=55, placeholder="…"))
        diag_svg_parts.append(
            f'  <circle cx="468" cy="{y}" r="10" fill="{dot_color}"/>'
            f'\n  <text x="490" y="{y + 6}" font-size="20" fill="#374151"'
            f' font-family="Inter,sans-serif"><tspan font-weight="600">{scheme_text}:</tspan>'
            f' {summary}</text>'
        )

    diag_block = "\n".join(diag_svg_parts)

    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <rect width="{w}" height="{h}" fill="#f9fafb"/>

  <!-- Left panel -->
  <rect x="0" y="0" width="420" height="{h}" fill="#1e3a5f"/>
  <text x="40" y="60" font-size="22" fill="#93c5fd" font-family="Inter,sans-serif">हिसाब · Hisaab</text>
  <text x="40" y="98" font-size="17" fill="#bfdbfe" font-family="Inter,sans-serif">Citizen Action Brief</text>

  <!-- District + State (left panel) -->
  <text x="40" y="200" font-size="52" fill="#ffffff" font-family="Inter,sans-serif" font-weight="700">{district}</text>
  <text x="40" y="248" font-size="26" fill="#93c5fd" font-family="Inter,sans-serif">{state}</text>

  <!-- Representatives -->
  <text x="40" y="340" font-size="18" fill="#bfdbfe" font-family="Inter,sans-serif">MP: {mp_label}</text>
  <text x="40" y="372" font-size="18" fill="#bfdbfe" font-family="Inter,sans-serif">MLA: {mla_label}</text>

  <!-- Footer left -->
  <text x="210" y="{h - 20}" font-size="16" fill="#64748b" text-anchor="middle"
        font-family="Inter,sans-serif">hisaab.info</text>

  <!-- Right panel: issues + header -->
  <text x="460" y="80" font-size="38" fill="#1f2937" font-family="Inter,sans-serif" font-weight="700">Issues in Your District</text>
  <text x="460" y="120" font-size="22" fill="#6b7280" font-family="Inter,sans-serif">Enter your PIN at hisaab.info to act</text>

  <line x1="460" y1="150" x2="{w - 60}" y2="150" stroke="#e5e7eb" stroke-width="1.5"/>

  <text x="460" y="210" font-size="22" fill="#374151" font-family="Inter,sans-serif" font-weight="600">Top Flagged Schemes</text>

  <!-- Diagnosis items -->
{diag_block}

  <!-- Footer right -->
  <text x="460" y="{h - 20}" font-size="14" fill="#9ca3af"
        font-family="Inter,sans-serif">Data from official government portals · {date_str}</text>
</svg>"""

    return svg.encode("utf-8")
