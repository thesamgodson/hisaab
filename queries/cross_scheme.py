"""Cross-scheme queries using the unified money_flow VIEW."""

from __future__ import annotations

from typing import Any

import queries.common as _common

_fmt_rs = _common._fmt_rs


def money_flow_by_district(
    district: str,
    state: str | None = None,
) -> dict[str, Any]:
    """Total money flow across all schemes for a district."""
    conn = _common._conn()
    if state:
        rows = conn.execute(
            """SELECT scheme, fin_year,
                      COALESCE(allocated_lakhs, 0) as allocated,
                      COALESCE(released_lakhs, 0) as released,
                      COALESCE(expended_lakhs, 0) as expended,
                      utilization_pct,
                      units_target, units_completed, units_label
               FROM money_flow
               WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?)
               ORDER BY scheme, fin_year""",
            (district, state),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT scheme, fin_year,
                      COALESCE(allocated_lakhs, 0) as allocated,
                      COALESCE(released_lakhs, 0) as released,
                      COALESCE(expended_lakhs, 0) as expended,
                      utilization_pct,
                      units_target, units_completed, units_label
               FROM money_flow
               WHERE UPPER(district) = UPPER(?)
               ORDER BY scheme, fin_year""",
            (district,),
        ).fetchall()
    conn.close()

    if not rows:
        return {"answer": f"No data found for {district} across any scheme.", "data": None}

    data = [dict(r) for r in rows]
    total_expended = sum(r["expended"] for r in data)
    schemes_present = sorted(set(r["scheme"] for r in data))

    lines = [f"{district} — Money flow across {len(schemes_present)} schemes:"]
    for scheme in schemes_present:
        scheme_rows = [r for r in data if r["scheme"] == scheme]
        exp = sum(r["expended"] for r in scheme_rows)
        lines.append(f"  {scheme}: {_fmt_rs(exp, 'lakhs')}")
        if scheme_rows[0]["units_label"] and scheme_rows[0]["units_target"]:
            target = sum(r["units_target"] or 0 for r in scheme_rows)
            done = sum(r["units_completed"] or 0 for r in scheme_rows)
            lines.append(f"    {scheme_rows[0]['units_label']}: {done:,}/{target:,}")

    lines.append(f"  TOTAL: {_fmt_rs(total_expended, 'lakhs')}")

    return {"answer": "\n".join(lines), "data": data}


def money_flow_state_summary(
    state: str = "TAMIL NADU",
) -> dict[str, Any]:
    """Aggregated money flow across all schemes for a state."""
    conn = _common._conn()
    rows = conn.execute(
        """SELECT scheme,
                  COUNT(DISTINCT district) as districts,
                  SUM(COALESCE(expended_lakhs, 0)) as total_expended,
                  AVG(utilization_pct) as avg_util
           FROM money_flow
           WHERE UPPER(state) = UPPER(?)
           GROUP BY scheme
           ORDER BY total_expended DESC""",
        (state,),
    ).fetchall()
    conn.close()

    if not rows:
        return {"answer": f"No data found for {state} across any scheme.", "data": None}

    data = [dict(r) for r in rows]
    total = sum(r["total_expended"] for r in data)

    lines = [f"{state} — Money flow across all schemes:"]
    for r in data:
        util_str = f", {r['avg_util']:.0f}% util" if r["avg_util"] else ""
        lines.append(f"  {r['scheme']}: {_fmt_rs(r['total_expended'], 'lakhs')} ({r['districts']} districts{util_str})")
    lines.append(f"  TOTAL: {_fmt_rs(total, 'lakhs')}")

    return {"answer": "\n".join(lines), "data": data}


def schemes_in_district(district: str) -> dict[str, Any]:
    """List which schemes have data for a district."""
    conn = _common._conn()
    rows = conn.execute(
        """SELECT DISTINCT scheme FROM money_flow
           WHERE UPPER(district) = UPPER(?)
           ORDER BY scheme""",
        (district,),
    ).fetchall()
    conn.close()

    schemes = [r["scheme"] for r in rows]
    if not schemes:
        return {"answer": f"No scheme data found for {district}.", "data": []}
    return {
        "answer": f"{district} has data for: {', '.join(schemes)}",
        "data": schemes,
    }
