"""Orchestrator: PIN → ActionBrief."""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime
from typing import Any

from action_brief.actions import build_actions
from action_brief.contacts import build_contacts
from action_brief.diagnosis import build_diagnosis, schemes_with_district_data
from action_brief.models import ActionBrief, DistrictBrief
from briefs.formatting import get_conn
from constituency.mapper import PC_NAME_NORM_SQL
from constituency.pc_name_registry import strip_reservation
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

        mp_info = _get_first_mp(conn, district, state) or _get_mp_by_pin(conn, clean)
        mla_info = _get_first_mla(conn, district, state)

        diagnosis = build_diagnosis(conn, district, state)
        flagged_schemes = list({d.scheme for d in diagnosis})
        schemes_checked = schemes_with_district_data(conn, district, state)

        contacts = build_contacts(
            conn, district, state,
            mp_info=mp_info, mla_info=mla_info,
            flagged_schemes=flagged_schemes,
        )

        actions = build_actions(conn, flagged_schemes)
        kits, universal = _build_complaint_kits(conn, district, state, flagged_schemes)

        return ActionBrief(
            pin=clean, district=district, state=state,
            mp=mp_info, mla=mla_info,
            diagnosis=diagnosis, contacts=contacts, actions=actions,
            scheme_data={}, generated_at=datetime.now(),
            schemes_checked=schemes_checked,
            complaint_kits=kits, universal_channels=universal,
        )
    finally:
        if own_conn:
            conn.close()


def build_district_brief(
    district: str,
    state: str,
    *,
    conn: sqlite3.Connection | None = None,
) -> DistrictBrief:
    """District-grain brief for map/search entry — same sections as the PIN
    brief, honestly-plural MPs. Twin of buildDistrictBrief in action-brief.ts."""
    own_conn = conn is None
    if own_conn:
        conn = get_conn()
    try:
        lineage = conn.execute(
            """SELECT parent_district, split_year FROM district_lineage
               WHERE UPPER(new_district)=UPPER(?) AND UPPER(state)=UPPER(?)""",
            (district, state),
        ).fetchone()
        diagnosis = build_diagnosis(conn, district, state)
        flagged = list({d.scheme for d in diagnosis})
        kits, universal = _build_complaint_kits(conn, district, state, flagged)
        return DistrictBrief(
            district=district, state=state,
            formerly_part_of=dict(lineage) if lineage else None,
            mps=_get_district_mps(conn, district, state),
            ac_count=_get_ac_count(conn, district, state),
            diagnosis=diagnosis,
            schemes_checked=schemes_with_district_data(conn, district, state),
            complaint_kits=kits, universal_channels=universal,
            generated_at=datetime.now(),
        )
    finally:
        if own_conn:
            conn.close()


def _get_district_mps(conn: sqlite3.Connection, district: str, state: str) -> list[dict[str, Any]]:
    states = candidate_states(state)
    slots = ", ".join("?" for _ in states)
    m_norm = PC_NAME_NORM_SQL.format(col="m.constituency")
    cd_norm = PC_NAME_NORM_SQL.format(col="cd.constituency")
    rows = conn.execute(
        f"""SELECT DISTINCT m.constituency, m.mp_name, m.party, m.state,
                  m.elected_year, m.source_url
           FROM constituency_district cd
           JOIN mp_info m ON {m_norm} = {cd_norm}
            AND UPPER(m.state) IN ({slots})
           WHERE UPPER(cd.district) = UPPER(?)
             AND UPPER(cd.state) IN ({slots})
           ORDER BY m.constituency""",
        (*states, district, *states),
    ).fetchall()
    return [dict(r) for r in rows]


def _get_ac_count(conn: sqlite3.Connection, district: str, state: str) -> int:
    row = conn.execute(
        """SELECT COUNT(DISTINCT ac_name) AS n FROM ac_district
           WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?)""",
        (district, state),
    ).fetchone()
    return int(row["n"]) if row else 0


_LEVEL_ORDER_SQL = (
    "CASE level WHEN 'local' THEN 0 WHEN 'district' THEN 1 "
    "WHEN 'state' THEN 2 WHEN 'national' THEN 3 ELSE 4 END"
)


def _build_complaint_kits(
    conn: sqlite3.Connection, district: str, state: str, flagged_schemes: list[str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """WHY/WHO/HOW to complain, per scheme present in this district.

    Not gated on a flagged shortfall — a personal grievance (delayed wages,
    refused rations) exists regardless of the district aggregate. Flagged
    schemes sort first. Twin of buildComplaintKits in web/src/lib/action-brief.ts.
    """
    present = {
        r["scheme"]
        for r in conn.execute(
            """SELECT DISTINCT scheme FROM scheme_delivery
                WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?)
               UNION
               SELECT DISTINCT scheme FROM money_flow
                WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?)""",
            (district, state, district, state),
        ).fetchall()
    }
    channels = [
        dict(r)
        for r in conn.execute(
            f"""SELECT scheme, level, authority, portal_name, portal_url, phone,
                       COALESCE(description,'') AS description
                  FROM grievance_channels
                 ORDER BY scheme, {_LEVEL_ORDER_SQL}"""
        ).fetchall()
    ]
    entitlements = {
        r["scheme"]: dict(r)
        for r in conn.execute(
            """SELECT scheme, entitlement, legal_basis, complain_when, source_url
                 FROM scheme_entitlements"""
        ).fetchall()
    }

    universal = [c for c in channels if c["scheme"] == "ALL"]
    by_scheme: dict[str, list[dict[str, Any]]] = {}
    for c in channels:
        if c["scheme"] != "ALL":
            by_scheme.setdefault(c["scheme"], []).append(c)

    flagged = set(flagged_schemes)
    kits: list[dict[str, Any]] = []
    for scheme in dict.fromkeys([*flagged_schemes, *sorted(present)]):
        ent = entitlements.get(scheme)
        laddered = by_scheme.get(scheme, [])
        if not ent and not laddered:
            continue
        complain_when: list[str] = []
        if ent and ent.get("complain_when"):
            try:
                parsed = json.loads(ent["complain_when"])
                complain_when = [str(x) for x in parsed] if isinstance(parsed, list) else [str(parsed)]
            except (json.JSONDecodeError, TypeError):
                complain_when = [str(ent["complain_when"])]
        kits.append({
            "scheme": scheme,
            "flagged": scheme in flagged,
            "entitlement": ent["entitlement"] if ent else None,
            "legal_basis": ent["legal_basis"] if ent else None,
            "complain_when": complain_when,
            "entitlement_source_url": ent["source_url"] if ent else None,
            "channels": laddered,
        })
    kits.sort(key=lambda k: (not k["flagged"], k["scheme"]))
    return kits, universal


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


# Fallback for PINs whose district has no constituency_district row (all of
# Delhi, among others) but does have a spatial PIN→PC match in pin_constituency.
# Mirrors findMpByPin in web/src/lib/action-brief.ts.
def _get_mp_by_pin(conn: sqlite3.Connection, pin: str) -> dict[str, Any] | None:
    pc = conn.execute(
        "SELECT constituency, state FROM pin_constituency WHERE pin_code = ?",
        (pin,),
    ).fetchone()
    if not pc:
        return None

    states = candidate_states(pc["state"])
    slots = ", ".join("?" for _ in states)
    m_norm = PC_NAME_NORM_SQL.format(col="constituency")
    row = conn.execute(
        f"""SELECT constituency, mp_name, party, state, elected_year, source_url
           FROM mp_info
           WHERE {m_norm} = ?
             AND UPPER(state) IN ({slots})
           LIMIT 1""",
        (strip_reservation(pc["constituency"]), *states),
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
