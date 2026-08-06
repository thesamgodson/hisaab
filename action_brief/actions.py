"""Build sourced legacy ActionItem records from the grievance registry."""
from __future__ import annotations

import sqlite3

from action_brief.models import ActionItem
from directory.grievances import get_grievance_channels


def build_actions(
    conn: sqlite3.Connection,
    flagged_schemes: list[str],
) -> list[ActionItem]:
    """Keep the legacy field sourced without inventing a universal escalation."""
    if not flagged_schemes:
        return []

    channels = get_grievance_channels(conn, flagged_schemes)
    best_per_scheme: dict[str, dict] = {}
    for ch in channels:
        scheme = ch["scheme"]
        if scheme not in best_per_scheme:
            best_per_scheme[scheme] = ch

    actions: list[ActionItem] = []
    for scheme in flagged_schemes:
        ch = best_per_scheme.get(scheme)
        if not ch:
            continue
        actions.append(ActionItem(
            scheme=scheme,
            action=ch.get("description") or ch["portal_name"],
            portal_name=ch["portal_name"],
            portal_url=ch["portal_url"],
            source_url=ch["source_url"],
            verified_at=ch["scraped_at"],
        ))
    return actions
