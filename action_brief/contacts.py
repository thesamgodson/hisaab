"""Build ContactCard list from MP/MLA info + district_officials table."""
from __future__ import annotations

import sqlite3
from datetime import date, datetime
from typing import Any

from action_brief.models import ContactCard
from directory.officials import get_officials

_ALWAYS_ROLES = {"District Collector"}

_SCHEME_ROLES: dict[str, list[str]] = {
    "MGNREGA": ["MGNREGA Programme Officer", "BDO"],
    "PMAY-G": ["PMAY-G Programme Officer"],
    "JJM": ["JJM Programme Officer"],
    "PMGSY": ["PMGSY Programme Officer"],
    "PM POSHAN": ["PM POSHAN Nodal Officer"],
    "NSAP": ["NSAP Nodal Officer"],
    "PDS/NFSA": ["Food & Civil Supplies Officer"],
    "PM Kisan": ["PM Kisan Nodal Officer"],
}


def build_contacts(
    conn: sqlite3.Connection,
    district: str,
    state: str,
    *,
    mp_info: dict[str, Any] | None = None,
    mla_info: dict[str, Any] | None = None,
    flagged_schemes: list[str] | None = None,
) -> list[ContactCard]:
    """Build ordered list: MP → MLA → DC → scheme officers (flagged only)."""
    contacts: list[ContactCard] = []
    today = date.today()

    if mp_info:
        contacts.append(ContactCard(
            role="Member of Parliament",
            name=mp_info.get("mp_name", "Unknown"),
            phone=mp_info.get("phone"),
            email=mp_info.get("email"),
            office_address=mp_info.get("office_address"),
            relevance=f"Elected representative for {mp_info.get('constituency', district)} constituency",
            source_url=mp_info.get("source_url", "https://eci.gov.in"),
            last_verified=today,
            freshness="fresh",
        ))

    if mla_info:
        contacts.append(ContactCard(
            role="MLA",
            name=mla_info.get("mla_name", "Unknown"),
            phone=mla_info.get("phone"),
            email=mla_info.get("email"),
            office_address=mla_info.get("office_address"),
            relevance=f"MLA for {mla_info.get('ac_name', '')} assembly constituency",
            source_url=mla_info.get("source_url", "https://myneta.info"),
            last_verified=today,
            freshness="fresh",
        ))

    officials = get_officials(conn, district, state)
    allowed_roles = set(_ALWAYS_ROLES)
    for scheme in (flagged_schemes or []):
        for role in _SCHEME_ROLES.get(scheme, []):
            allowed_roles.add(role)

    for off in officials:
        if off["role"] not in allowed_roles:
            continue
        scraped_date = datetime.fromisoformat(off["scraped_at"]).date() if off.get("scraped_at") else today
        contacts.append(ContactCard(
            role=off["role"],
            name=off["name"],
            phone=off["phone"],
            email=off["email"],
            office_address=off["office_address"],
            relevance=_role_relevance(off["role"]),
            source_url=off["source_url"],
            last_verified=scraped_date,
            freshness=off["freshness"],
        ))

    return contacts


def _role_relevance(role: str) -> str:
    relevance_map = {
        "District Collector": "Oversees all district-level government schemes",
        "BDO": "Block Development Officer — local scheme implementation",
        "MGNREGA Programme Officer": "Manages MGNREGA implementation in the district",
    }
    return relevance_map.get(role, f"Responsible for {role} duties")
