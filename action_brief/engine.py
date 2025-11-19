"""Orchestrator: PIN → ActionBrief."""
from __future__ import annotations

import re
import sqlite3
from datetime import datetime
from typing import Any

from action_brief.actions import build_actions
from action_brief.contacts import build_contacts
from action_brief.diagnosis import build_diagnosis
from action_brief.models import ActionBrief
from briefs.formatting import get_conn


def build_action_brief(
    pin: str,
    *,
    conn: sqlite3.Connection | None = None,
) -> ActionBrief | None:
    """Build a full ActionBrief for a 6-digit PIN code.

    Returns None if PIN is invalid or not found.
    """
    clean = pin.strip()
    if not re.match(r"^\d{6}$", clean):
        return None

    own_conn = conn is None
    if own_conn:
        conn = get_conn()

    try:
        row = conn.execute(
            "SELECT * FROM pin_district_mapping WHERE pin_code = ?",
            (clean,),
        ).fetchone()
        if not row:
            return None

        district = row["district"]
        state = row["state"]

        mp_info = _get_first_mp(conn, district, state)
        mla_info = _get_first_mla(conn, district, state)

        diagnosis = build_diagnosis(conn, district, state)
        flagged_schemes = list({d.scheme for d in diagnosis})

        contacts = build_contacts(
            conn, district, state,
            mp_info=mp_info, mla_info=mla_info,
            flagged_schemes=flagged_schemes,
        )

        actions = build_actions(conn, flagged_schemes)

        return ActionBrief(
            pin=clean, district=district, state=state,
            mp=mp_info, mla=mla_info,
            diagnosis=diagnosis, contacts=contacts, actions=actions,
            scheme_data={}, generated_at=datetime.now(),
        )
    finally:
        if own_conn:
            conn.close()


def _get_first_mp(conn: sqlite3.Connection, district: str, state: str) -> dict[str, Any] | None:
    row = conn.execute(
        """SELECT cd.constituency, m.mp_name, m.party, m.state,
                  m.elected_year, m.source_url
           FROM constituency_district cd
           JOIN mp_info m ON UPPER(cd.constituency) = UPPER(m.constituency)
           WHERE UPPER(cd.district) = UPPER(?)
             AND UPPER(cd.state) = UPPER(?)
           LIMIT 1""",
        (district, state),
    ).fetchone()
    return dict(row) if row else None


def _get_first_mla(conn: sqlite3.Connection, district: str, state: str) -> dict[str, Any] | None:
    row = conn.execute(
        """SELECT a.ac_name, m.mla_name, m.party, m.state, m.source_url
           FROM ac_district a
           JOIN mla_info m ON UPPER(a.ac_name) = UPPER(m.ac_name)
             AND UPPER(a.state) = UPPER(m.state)
           WHERE UPPER(a.district) = UPPER(?)
             AND UPPER(a.state) = UPPER(?)
           LIMIT 1""",
        (district, state),
    ).fetchone()
    return dict(row) if row else None
