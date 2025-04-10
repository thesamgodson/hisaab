"""District-level section generators for journalist briefs.

Each function takes (conn, district, state) and returns a list of lines.
"""

from __future__ import annotations

import sqlite3

from briefs.formatting import FIN_YEAR, fmt_inr, pct


def misappropriation(conn: sqlite3.Connection, district: str, state: str) -> list[str]:
    mis = conn.execute(
        "SELECT * FROM misappropriation WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchone()

    lines = ["FINANCIAL MISAPPROPRIATION"]
    if mis:
        m = dict(mis)
        unrecovered = m["amount_reported"] - m["amount_recovered"]
        recovery_pct = (m["amount_recovered"] / m["amount_reported"] * 100) if m["amount_reported"] > 0 else 0
        lines.append(f"  {m['cases_reported']:,} cases reported")
        lines.append(f"  {fmt_inr(m['amount_reported'])} misappropriated")
        lines.append(f"  {fmt_inr(unrecovered)} still unrecovered (recovery rate: {pct(recovery_pct)})")
        lines.append(f"  Source: {m['source_url']}")
    else:
        lines.append("  No data available.")
    lines.append("")
    return lines


def fund_utilization(conn: sqlite3.Connection, district: str, state: str) -> list[str]:
    fin = conn.execute(
        "SELECT * FROM financial_statement WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchone()

    lines = ["FUND UTILIZATION"]
    if fin:
        f = dict(fin)
        lines.append(f"  Allocated: {fmt_inr(f['total_availability'], 'lakhs')}")
        lines.append(f"  Expended: {fmt_inr(f['cumulative_expenditure'], 'lakhs')}")
        lines.append(f"  Utilization: {pct(f['utilization_pct'])}")
        lines.append(f"  Wage payments: {fmt_inr(f['exp_unskilled_wage'], 'lakhs')} (unskilled)")
        lines.append(f"  Source: {f['source_url']}")
    else:
        lines.append("  No data available.")
    lines.append("")
    return lines


def fto(conn: sqlite3.Connection, district: str, state: str) -> list[str]:
    fto_row = conn.execute(
        "SELECT * FROM fto_status WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchone()

    lines = ["PENDING PAYMENTS (FTO)"]
    if fto_row:
        ft = dict(fto_row)
        total_pending = ft["first_signatory_pending"] + ft["second_signatory_pending"]
        lines.append(f"  {ft['total_fto_generated']:,} Fund Transfer Orders generated")
        if total_pending == 0:
            lines.append("  No pending FTOs \u2014 all payments processed")
        else:
            lines.append(f"  {ft['first_signatory_pending']:,} pending 1st signatory approval")
            lines.append(f"  {ft['second_signatory_pending']:,} pending 2nd signatory approval")
            lines.append(f"  {total_pending:,} total FTOs pending")
        lines.append(
            f"  {ft['fto_sent_to_bank']:,} sent to bank, {ft['fto_processed_by_bank']:,} transactions processed"
        )
        lines.append(f"  Source: {ft['source_url']}")
    else:
        lines.append("  No data available.")
    lines.append("")
    return lines


def social_audit(conn: sqlite3.Connection, district: str, state: str) -> list[str]:
    aud = conn.execute(
        "SELECT * FROM issues_reported WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchone()

    lines = ["SOCIAL AUDIT FINDINGS"]
    if aud:
        a = dict(aud)
        coverage = (a["gps_audited"] / a["total_gps"] * 100) if a["total_gps"] > 0 else 0
        categories = {
            "Financial Misappropriation": a["misappropriation_issues"],
            "Financial Deviation": a["financial_deviation_issues"],
            "Process Violation": a["process_violation_issues"],
            "Grievances": a["grievances_issues"],
        }
        top_category = max(categories, key=lambda k: categories[k])
        lines.append(
            f"  {a['total_issues']:,} issues reported across {a['gps_audited']}/{a['total_gps']} GPs audited ({pct(coverage)})"
        )
        lines.append(
            f"  Misappropriation: {a['misappropriation_issues']:,} | Deviation: {a['financial_deviation_issues']:,} | Process violations: {a['process_violation_issues']:,} | Grievances: {a['grievances_issues']:,}"
        )
        lines.append(f"  Top issue category: {top_category} ({categories[top_category]:,} cases)")
        lines.append(f"  Source: {a['source_url']}")
    else:
        lines.append("  No data available.")
    lines.append("")
    return lines


def pmgsy(conn: sqlite3.Connection, district: str, state: str) -> list[str]:
    pmgsy_rows = conn.execute(
        "SELECT * FROM pmgsy_district WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?)",
        (district, state),
    ).fetchall()

    lines = ["RURAL ROADS (PMGSY)"]
    if pmgsy_rows:
        rows = [dict(r) for r in pmgsy_rows]
        total_sanctioned = sum(r.get("roads_sanctioned", 0) for r in rows)
        total_completed = sum(r.get("roads_completed", 0) for r in rows)
        total_len_s = sum(r.get("length_sanctioned_km", 0) for r in rows)
        total_len_c = sum(r.get("length_completed_km", 0) for r in rows)
        total_exp = sum(r.get("expenditure_cr", 0) for r in rows)
        completion_rate = (total_completed / total_sanctioned * 100) if total_sanctioned > 0 else 0
        cost_per_km = (total_exp / total_len_c) if total_len_c > 0 else 0

        lines.append(
            f"  Roads sanctioned: {total_sanctioned:,} | completed: {total_completed:,} ({pct(completion_rate)})"
        )
        lines.append(f"  Length sanctioned: {total_len_s:,.1f} km | completed: {total_len_c:,.1f} km")
        lines.append(f"  Total expenditure: {fmt_inr(total_exp * 10000000)}")
        if total_len_c > 0:
            lines.append(f"  Cost per km: {fmt_inr(cost_per_km * 10000000)}")
        lines.append(f"  Source: {rows[0].get('source_url', 'N/A')}")
    else:
        lines.append("  No data available.")
    lines.append("")
    return lines


def pmayg(conn: sqlite3.Connection, district: str, state: str) -> list[str]:
    row = conn.execute(
        "SELECT * FROM pmayg_district WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchone()

    lines = ["RURAL HOUSING (PMAY-G)"]
    if row:
        h = dict(row)
        occupied_pct = (h["houses_occupied"] / h["houses_completed"] * 100) if h["houses_completed"] > 0 else 0
        lines.append(
            f"  Houses sanctioned: {h['houses_sanctioned']:,} | completed: {h['houses_completed']:,} ({h['completion_pct']:.0f}%)"
        )
        lines.append(f"  Houses occupied: {h['houses_occupied']:,} ({occupied_pct:.0f}% of completed)")
        lines.append(
            f"  Funds released: {fmt_inr(h['funds_released_lakhs'], 'lakhs')} | utilized: {fmt_inr(h['funds_utilized_lakhs'], 'lakhs')}"
        )
        if h.get("source_url"):
            lines.append(f"  Source: {h['source_url']}")
    else:
        lines.append("  No data available.")
    lines.append("")
    return lines


def pmkisan(conn: sqlite3.Connection, district: str, state: str) -> list[str]:
    pmkisan_rows = conn.execute(
        "SELECT * FROM pmkisan_district WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchall()

    lines = ["FARMER PAYMENTS (PM KISAN)"]
    if pmkisan_rows:
        pk = [dict(r) for r in pmkisan_rows]
        total_paid = sum(r["beneficiaries_paid"] for r in pk)
        total_amount = sum(r["amount_paid_lakhs"] for r in pk)
        max_reg = max(r["beneficiaries_registered"] for r in pk)
        cov_pct = (total_paid / max_reg * 100) if max_reg > 0 else 0
        is_all = any(r["district"].upper() == "ALL" for r in pk)
        lines.append(f"  Beneficiaries registered: {max_reg:,} | paid: {total_paid:,} ({cov_pct:.0f}% coverage)")
        lines.append(f"  Amount disbursed: {fmt_inr(total_amount, 'lakhs')}")
        if is_all:
            lines.append("  NOTE: This is state-level aggregate data (district='ALL'), not district-specific.")
        if pk[0].get("source_url"):
            lines.append(f"  Source: {pk[0]['source_url']}")
    else:
        lines.append("  No data available.")
    lines.append("")
    return lines


def jjm(conn: sqlite3.Connection, district: str, state: str) -> list[str]:
    row = conn.execute(
        "SELECT * FROM jjm_district WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?)",
        (district, state),
    ).fetchone()

    lines = ["RURAL WATER (JJM)"]
    if row:
        j = dict(row)
        util_pct = (j["funds_utilized_lakhs"] / j["funds_released_lakhs"] * 100) if j["funds_released_lakhs"] > 0 else 0
        lines.append(
            f"  Households: {j['total_households']:,} total | {j['households_with_tap']:,} with tap ({j['coverage_pct']:.0f}%)"
        )
        lines.append(
            f"  Funds released: {fmt_inr(j['funds_released_lakhs'], 'lakhs')} | utilized: {fmt_inr(j['funds_utilized_lakhs'], 'lakhs')} ({util_pct:.0f}%)"
        )
        if j.get("source_url"):
            lines.append(f"  Source: {j['source_url']}")
    else:
        lines.append("  No data available.")
    lines.append("")
    return lines


def poshan(conn: sqlite3.Connection, district: str, state: str) -> list[str]:
    row = conn.execute(
        "SELECT * FROM pmposhan_district WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchone()

    lines = ["SCHOOL NUTRITION (PM POSHAN)"]
    if row:
        p = dict(row)
        feeding_pct = (p["children_fed"] / p["children_enrolled"] * 100) if p["children_enrolled"] > 0 else 0
        lines.append(f"  Schools covered: {p['schools_covered']:,}")
        lines.append(
            f"  Children enrolled: {p['children_enrolled']:,} | fed: {p['children_fed']:,} ({feeding_pct:.0f}%)"
        )
        lines.append(
            f"  Funds released: {fmt_inr(p['funds_released_lakhs'], 'lakhs')} | utilized: {fmt_inr(p['funds_utilized_lakhs'], 'lakhs')}"
        )
        if p.get("source_url"):
            lines.append(f"  Source: {p['source_url']}")
    else:
        lines.append("  No data available.")
    lines.append("")
    return lines


def nsap(conn: sqlite3.Connection, district: str, state: str) -> list[str]:
    nsap_rows = conn.execute(
        "SELECT * FROM nsap_district WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchall()

    lines = ["PENSIONS (NSAP)"]
    if nsap_rows:
        ns = [dict(r) for r in nsap_rows]
        total_paid = sum(r["beneficiaries_paid"] for r in ns)
        total_eligible = sum(r["beneficiaries_eligible"] for r in ns)
        total_amount = sum(r["amount_paid_lakhs"] for r in ns)
        lines.append(f"  Beneficiaries paid: {total_paid:,}")
        if total_eligible > 0:
            lines.append(f"  Eligible: {total_eligible:,} ({total_paid / total_eligible * 100:.0f}% coverage)")
        lines.append(f"  Amount paid: {fmt_inr(total_amount, 'lakhs')}")
        for r in ns:
            if r["scheme_type"]:
                lines.append(f"    {r['scheme_type']}: {r['beneficiaries_paid']:,} paid")
        if ns[0].get("source_url"):
            lines.append(f"  Source: {ns[0]['source_url']}")
    else:
        lines.append("  No data available.")
    lines.append("")
    return lines


def nfsa(conn: sqlite3.Connection, district: str, state: str) -> list[str]:
    row = conn.execute(
        "SELECT * FROM nfsa_district WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchone()

    lines = ["RATION SYSTEM (PDS/NFSA)"]
    if row:
        nf = dict(row)
        active_pct = (nf["ration_cards_active"] / nf["ration_cards_total"] * 100) if nf["ration_cards_total"] > 0 else 0
        lines.append(
            f"  Ration cards: {nf['ration_cards_active']:,} active / {nf['ration_cards_total']:,} total ({active_pct:.0f}%)"
        )
        lines.append(
            f"  Allocation: {nf['allocation_mt']:,.1f} MT | Offtake: {nf['offtake_mt']:,.1f} MT ({nf['offtake_pct']:.0f}%)"
        )
        lines.append(f"  Beneficiaries: {nf['beneficiaries_total']:,}")
        if nf.get("source_url"):
            lines.append(f"  Source: {nf['source_url']}")
    else:
        lines.append("  No data available.")
    lines.append("")
    return lines
