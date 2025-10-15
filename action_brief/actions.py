"""Build ActionItem list from grievance_channels for flagged schemes."""
from __future__ import annotations

import sqlite3

from action_brief.models import ActionItem
from directory.grievances import get_grievance_channels

_CPGRAMS_URL = "https://pgportal.gov.in/"

_SCHEME_ACTIONS: dict[str, str] = {
    "MGNREGA": "File a complaint about MGNREGA fund misuse or delayed wages",
    "PMAY-G": "File a complaint about housing scheme delays or irregularities",
    "JJM": "File a complaint about missing or non-functional tap water connections",
    "PM Kisan": "File a complaint about missing PM Kisan payments",
    "PM POSHAN": "File a complaint about mid-day meal scheme issues",
    "NSAP": "File a complaint about missing pension payments",
    "PDS/NFSA": "File a complaint about ration distribution problems",
    "PMGSY": "File a complaint about incomplete or poor-quality rural roads",
}


def build_actions(
    conn: sqlite3.Connection,
    flagged_schemes: list[str],
) -> list[ActionItem]:
    """Build action items for flagged schemes. CPGRAMS is always escalation."""
    if not flagged_schemes:
        return []

    channels = get_grievance_channels(conn, flagged_schemes)
    best_per_scheme: dict[str, dict] = {}
    for ch in channels:
        scheme = ch["scheme"]
        if scheme not in best_per_scheme:
            best_per_scheme[scheme] = ch

    universal = get_grievance_channels(conn, ["ALL"])
    cpgrams_url = _CPGRAMS_URL
    for ch in universal:
        if ch["portal_name"] == "CPGRAMS":
            cpgrams_url = ch["portal_url"]
            break

    actions: list[ActionItem] = []
    for scheme in flagged_schemes:
        ch = best_per_scheme.get(scheme)
        if not ch:
            continue
        actions.append(ActionItem(
            scheme=scheme,
            action=_SCHEME_ACTIONS.get(scheme, f"File a complaint about {scheme}"),
            portal_name=ch["portal_name"],
            portal_url=ch["portal_url"],
            escalation="If no response in 30 days, escalate to CPGRAMS",
            escalation_url=cpgrams_url,
        ))
    return actions
