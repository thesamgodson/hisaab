"""PMGSY queries (Pradhan Mantri Gram Sadak Yojana — rural roads)."""

from __future__ import annotations

from typing import Any

import queries.common as _common

_fmt_rs = _common._fmt_rs


def pmgsy_district_summary(
    district: str,
    state: str = "TAMIL NADU",
) -> dict[str, Any]:
    conn = _common._conn()
    rows = conn.execute(
        """SELECT * FROM pmgsy_district
        WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?)
        ORDER BY fin_year DESC""",
        (district, state),
    ).fetchall()
    conn.close()

    if not rows:
        return {"answer": f"No PMGSY data found for {district}, {state}.", "data": None}

    data = [dict(r) for r in rows]
    total_sanctioned = sum(r.get("roads_sanctioned", 0) for r in data)
    total_completed = sum(r.get("roads_completed", 0) for r in data)
    total_length_s = sum(r.get("length_sanctioned_km", 0) for r in data)
    total_length_c = sum(r.get("length_completed_km", 0) for r in data)
    total_expenditure = sum(r.get("expenditure_cr", 0) for r in data)
    completion_rate = (total_completed / total_sanctioned * 100) if total_sanctioned > 0 else 0
    cost_per_km = (total_expenditure / total_length_c) if total_length_c > 0 else 0

    return {
        "answer": (
            f"{district}, {state} — PMGSY Rural Roads:\n"
            f"  Roads sanctioned: {total_sanctioned:,} | completed: {total_completed:,} ({completion_rate:.0f}%)\n"
            f"  Length sanctioned: {total_length_s:,.1f} km | completed: {total_length_c:,.1f} km\n"
            f"  Total expenditure: {_fmt_rs(total_expenditure * 10000000)}\n"
            f"  Cost per km: {_fmt_rs(cost_per_km * 10000000)}"
        ),
        "data": data,
        "source_url": data[0].get("source_url"),
    }


def pmgsy_state_summary(
    state: str = "TAMIL NADU",
) -> dict[str, Any]:
    conn = _common._conn()
    row = conn.execute(
        """SELECT COUNT(DISTINCT district) as districts,
                  SUM(roads_sanctioned) as total_sanctioned,
                  SUM(roads_completed) as total_completed,
                  SUM(length_sanctioned_km) as total_length_s,
                  SUM(length_completed_km) as total_length_c,
                  SUM(expenditure_cr) as total_expenditure
           FROM pmgsy_district
           WHERE UPPER(state) = UPPER(?)""",
        (state,),
    ).fetchone()
    conn.close()

    if not row or row["districts"] == 0:
        return {"answer": f"No PMGSY data for {state}.", "data": None}

    r = dict(row)
    completion_rate = (r["total_completed"] / r["total_sanctioned"] * 100) if r["total_sanctioned"] > 0 else 0

    return {
        "answer": (
            f"{state} PMGSY summary:\n"
            f"  Districts: {r['districts']}\n"
            f"  Roads sanctioned: {r['total_sanctioned']:,} | completed: {r['total_completed']:,} ({completion_rate:.0f}%)\n"
            f"  Length: {r['total_length_s']:,.1f} km sanctioned | {r['total_length_c']:,.1f} km completed\n"
            f"  Total expenditure: {_fmt_rs(r['total_expenditure'] * 10000000)}"
        ),
        "data": r,
    }


def pmgsy_worst_completion(
    state: str = "TAMIL NADU",
    limit: int = 5,
) -> dict[str, Any]:
    conn = _common._conn()
    rows = conn.execute(
        """SELECT district,
                  SUM(roads_sanctioned) as sanctioned,
                  SUM(roads_completed) as completed,
                  SUM(length_sanctioned_km) as len_s,
                  SUM(length_completed_km) as len_c,
                  SUM(expenditure_cr) as exp,
                  CASE WHEN SUM(roads_sanctioned) > 0
                       THEN (SUM(roads_completed) * 100.0 / SUM(roads_sanctioned))
                       ELSE 0 END as completion_pct
           FROM pmgsy_district
           WHERE UPPER(state) = UPPER(?) AND roads_sanctioned > 0
           GROUP BY district
           ORDER BY completion_pct ASC LIMIT ?""",
        (state, limit),
    ).fetchall()
    conn.close()

    if not rows:
        return {"answer": f"No PMGSY data for {state}.", "data": None}

    lines = [f"Worst {limit} districts by road completion rate ({state}, PMGSY):"]
    data = []
    for i, row in enumerate(rows, 1):
        r = dict(row)
        lines.append(
            f"  {i}. {r['district']}: {r['completion_pct']:.0f}% "
            f"({r['completed']:,}/{r['sanctioned']:,} roads, "
            f"{r['len_c']:,.1f}/{r['len_s']:,.1f} km)"
        )
        data.append(r)

    return {"answer": "\n".join(lines), "data": data}
