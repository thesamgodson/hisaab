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
from constituency.mapper import PC_NAME_NORM_SQL
from db.normalize_states import candidate_states


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


# Names join through the shared normalizer (datameet keeps reservation
# suffixes, OpenCity/MyNeta drop them) and states through candidate_states
# (constituency_district/ac_district carry vintage pre-bifurcation labels;
# PC names repeat across states). Mirrors web/src/lib/action-brief.ts.
def _get_first_mp(conn: sqlite3.Connection, district: str, state: str) -> dict[str, Any] | None:
    states = candidate_states(state)
    slots = ", ".join("?" for _ in states)
    m_norm = PC_NAME_NORM_SQL.format(col="m.constituency")
    cd_norm = PC_NAME_NORM_SQL.format(col="cd.constituency")
    row = conn.execute(
        f"""SELECT cd.constituency, m.mp_name, m.party, m.state,
                  m.elected_year, m.source_url
           FROM constituency_district cd
           JOIN mp_info m ON {m_norm} = {cd_norm}
            AND UPPER(m.state) IN ({slots})
           WHERE UPPER(cd.district) = UPPER(?)
             AND UPPER(cd.state) IN ({slots})
           LIMIT 1""",
        (*states, district, *states),
    ).fetchone()
    return dict(row) if row else None


def _get_first_mla(conn: sqlite3.Connection, district: str, state: str) -> dict[str, Any] | None:
    states = candidate_states(state)
    slots = ", ".join("?" for _ in states)
    m_norm = PC_NAME_NORM_SQL.format(col="m.ac_name")
    a_norm = PC_NAME_NORM_SQL.format(col="a.ac_name")
    row = conn.execute(
        f"""SELECT a.ac_name, m.mla_name, m.party, m.state, m.source_url
           FROM ac_district a
           JOIN mla_info m ON {m_norm} = {a_norm}
            AND UPPER(m.state) IN ({slots})
           WHERE UPPER(a.district) = UPPER(?)
             AND UPPER(a.state) IN ({slots})
           LIMIT 1""",
        (*states, district, *states),
    ).fetchone()
    return dict(row) if row else None
