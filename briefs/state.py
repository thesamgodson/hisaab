"""State-level journalist brief generation."""

from __future__ import annotations

import difflib
import sqlite3
from datetime import datetime

from briefs.formatting import FIN_YEAR, fmt_inr, get_conn, pct


def state_brief(state_name: str) -> str:
    """Generate a journalist briefing for an entire state."""
    conn = get_conn()

    check = conn.execute(
        "SELECT COUNT(*) as n FROM misappropriation WHERE UPPER(state)=UPPER(?) AND fin_year=?",
        (state_name, FIN_YEAR),
    ).fetchone()
    if not check or check["n"] == 0:
        all_states = [r[0] for r in conn.execute("SELECT DISTINCT state FROM misappropriation").fetchall()]
        conn.close()
        matches = difflib.get_close_matches(state_name.upper(), [s.upper() for s in all_states], n=1, cutoff=0.5)
        if matches:
            return f"ERROR: State '{state_name}' not found. Did you mean '{matches[0]}'?"
        return f"ERROR: State '{state_name}' not found in database."

    state_row = conn.execute(
        "SELECT DISTINCT state FROM misappropriation WHERE UPPER(state)=UPPER(?)", (state_name,)
    ).fetchone()
    state = state_row["state"]

    generated = datetime.now().strftime("%d %b %Y")
    lines = [
        "HISAAB STATE BRIEF",
        state,
        f"Generated: {generated} | Source: Government of India, MoRD MGNREGA MIS",
        f"Financial Year: {FIN_YEAR}",
        "",
    ]

    sections = [
        _section_misappropriation,
        _section_fund_utilization,
        _section_fto,
        _section_social_audit,
        _section_pmgsy,
        _section_pmayg,
        _section_pmkisan,
        _section_jjm,
        _section_poshan,
        _section_nsap,
        _section_nfsa,
        _section_worst_districts,
    ]
    for section_fn in sections:
        lines.extend(section_fn(conn, state))

    conn.close()
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# State-level section generators
# ---------------------------------------------------------------------------
def _section_misappropriation(conn: sqlite3.Connection, state: str) -> list[str]:
    mis = conn.execute(
        """SELECT COUNT(*) as districts, SUM(cases_reported) as cases,
                  SUM(amount_reported) as reported, SUM(amount_recovered) as recovered,
                  SUM(amount_to_recover) as to_recover
           FROM misappropriation WHERE UPPER(state)=UPPER(?) AND fin_year=?""",
        (state, FIN_YEAR),
    ).fetchone()
    m = dict(mis)
    total_unrecovered = m["reported"] - m["recovered"]
    recovery_pct = (m["recovered"] / m["reported"] * 100) if m["reported"] > 0 else 0

    lines = ["FINANCIAL MISAPPROPRIATION"]
    lines.append(f"  {m['districts']} districts | {m['cases']:,} cases reported")
    lines.append(f"  {fmt_inr(m['reported'])} misappropriated")
    lines.append(f"  {fmt_inr(m['recovered'])} recovered ({pct(recovery_pct)})")
    lines.append(f"  {fmt_inr(total_unrecovered)} still unrecovered")

    state_ranks = conn.execute(
        """SELECT state, SUM(amount_reported - amount_recovered) as unrecovered
           FROM misappropriation WHERE fin_year=? GROUP BY state ORDER BY unrecovered DESC""",
        (FIN_YEAR,),
    ).fetchall()
    total_states = len(state_ranks)
    state_national_rank = 0
    for i, r in enumerate(state_ranks, 1):
        if r["state"].upper() == state.upper():
            state_national_rank = i
            break
    if state_national_rank > 0:
        lines.append(
            f"  State ranks #{state_national_rank} out of {total_states} states nationally for unrecovered amount"
        )
    lines.append("")
    return lines


def _section_fund_utilization(conn: sqlite3.Connection, state: str) -> list[str]:
    fin = conn.execute(
        """SELECT SUM(total_availability) as funds, SUM(cumulative_expenditure) as exp,
                  AVG(utilization_pct) as util, SUM(exp_unskilled_wage) as wage
           FROM financial_statement WHERE UPPER(state)=UPPER(?) AND fin_year=?""",
        (state, FIN_YEAR),
    ).fetchone()

    lines = ["FUND UTILIZATION"]
    if fin and fin["funds"]:
        f = dict(fin)
        lines.append(f"  Total allocated: {fmt_inr(f['funds'], 'lakhs')}")
        lines.append(f"  Total expended: {fmt_inr(f['exp'], 'lakhs')}")
        lines.append(f"  Average utilization: {pct(f['util'])}")
        lines.append(f"  Wage payments: {fmt_inr(f['wage'], 'lakhs')}")
    else:
        lines.append("  No data available.")
    lines.append("")
    return lines


def _section_fto(conn: sqlite3.Connection, state: str) -> list[str]:
    fto = conn.execute(
        """SELECT SUM(total_fto_generated) as gen, SUM(first_signatory_pending) as p1,
                  SUM(second_signatory_pending) as p2, SUM(fto_sent_to_bank) as bank
           FROM fto_status WHERE UPPER(state)=UPPER(?) AND fin_year=?""",
        (state, FIN_YEAR),
    ).fetchone()

    lines = ["PAYMENT STATUS (FTO)"]
    if fto and fto["gen"]:
        ft = dict(fto)
        total_pending = ft["p1"] + ft["p2"]
        lines.append(f"  {ft['gen']:,} FTOs generated | {ft['bank']:,} sent to bank")
        if total_pending == 0:
            lines.append("  No pending FTOs — all payments processed")
        else:
            lines.append(f"  {total_pending:,} FTOs still pending approval")
            lines.append(f"    1st signatory: {ft['p1']:,} | 2nd signatory: {ft['p2']:,}")
    else:
        lines.append("  No data available.")
    lines.append("")
    return lines


def _section_social_audit(conn: sqlite3.Connection, state: str) -> list[str]:
    aud = conn.execute(
        """SELECT SUM(total_issues) as issues, SUM(total_gps) as gps, SUM(gps_audited) as audited,
                  SUM(misappropriation_issues) as mis, SUM(financial_deviation_issues) as dev,
                  SUM(process_violation_issues) as pv, SUM(grievances_issues) as gr
           FROM issues_reported WHERE UPPER(state)=UPPER(?) AND fin_year=?""",
        (state, FIN_YEAR),
    ).fetchone()

    lines = ["SOCIAL AUDIT"]
    if aud and aud["issues"]:
        a = dict(aud)
        coverage = (a["audited"] / a["gps"] * 100) if a["gps"] > 0 else 0
        lines.append(f"  {a['issues']:,} issues across {a['audited']:,}/{a['gps']:,} GPs ({pct(coverage)} coverage)")
        lines.append(
            f"  Misappropriation: {a['mis']:,} | Deviation: {a['dev']:,} | Process violations: {a['pv']:,} | Grievances: {a['gr']:,}"
        )
    else:
        lines.append("  No data available.")
    lines.append("")
    return lines


def _section_pmgsy(conn: sqlite3.Connection, state: str) -> list[str]:
    pmgsy = conn.execute(
        """SELECT COUNT(DISTINCT district) as districts,
                  SUM(roads_sanctioned) as sanctioned, SUM(roads_completed) as completed,
                  SUM(length_sanctioned_km) as len_s, SUM(length_completed_km) as len_c,
                  SUM(expenditure_cr) as exp
           FROM pmgsy_district WHERE UPPER(state)=UPPER(?)""",
        (state,),
    ).fetchone()

    lines = ["RURAL ROADS (PMGSY)"]
    if pmgsy and pmgsy["districts"] and pmgsy["districts"] > 0:
        pm = dict(pmgsy)
        completion_pct = (pm["completed"] / pm["sanctioned"] * 100) if pm["sanctioned"] > 0 else 0
        lines.append(
            f"  {pm['districts']} districts | {pm['sanctioned']:,} roads sanctioned | {pm['completed']:,} completed ({pct(completion_pct)})"
        )
        lines.append(f"  Length: {pm['len_s']:,.1f} km sanctioned | {pm['len_c']:,.1f} km completed")
        lines.append(f"  Total expenditure: {fmt_inr(pm['exp'] * 10000000)}")
    else:
        lines.append("  No data available.")
    lines.append("")
    return lines


def _section_pmayg(conn: sqlite3.Connection, state: str) -> list[str]:
    pmayg = conn.execute(
        """SELECT COUNT(DISTINCT district) as districts,
                  SUM(houses_sanctioned) as sanctioned, SUM(houses_completed) as completed,
                  SUM(houses_occupied) as occupied,
                  SUM(funds_released_lakhs) as released, SUM(funds_utilized_lakhs) as utilized
           FROM pmayg_district WHERE UPPER(state)=UPPER(?) AND fin_year=?""",
        (state, FIN_YEAR),
    ).fetchone()

    lines = ["RURAL HOUSING (PMAY-G)"]
    if pmayg and pmayg["districts"] and pmayg["districts"] > 0:
        h = dict(pmayg)
        comp_pct = (h["completed"] / h["sanctioned"] * 100) if h["sanctioned"] > 0 else 0
        lines.append(
            f"  {h['districts']} districts | {h['sanctioned']:,} houses sanctioned | {h['completed']:,} completed ({pct(comp_pct)})"
        )
        lines.append(f"  Occupied: {h['occupied']:,}")
        lines.append(
            f"  Funds released: {fmt_inr(h['released'], 'lakhs')} | utilized: {fmt_inr(h['utilized'], 'lakhs')}"
        )
    else:
        lines.append("  No data available.")
    lines.append("")
    return lines


def _section_pmkisan(conn: sqlite3.Connection, state: str) -> list[str]:
    pmkisan = conn.execute(
        """SELECT COUNT(DISTINCT district) as districts,
                  SUM(beneficiaries_paid) as paid, SUM(amount_paid_lakhs) as amount
           FROM pmkisan_district WHERE UPPER(state)=UPPER(?) AND fin_year=?""",
        (state, FIN_YEAR),
    ).fetchone()

    lines = ["FARMER PAYMENTS (PM KISAN)"]
    if pmkisan and pmkisan["districts"] and pmkisan["districts"] > 0:
        pk = dict(pmkisan)
        lines.append(f"  {pk['districts']} districts | {pk['paid']:,} beneficiaries paid")
        lines.append(f"  Amount disbursed: {fmt_inr(pk['amount'], 'lakhs')}")
    else:
        lines.append("  No data available.")
    lines.append("")
    return lines


def _section_jjm(conn: sqlite3.Connection, state: str) -> list[str]:
    jjm = conn.execute(
        """SELECT COUNT(DISTINCT district) as districts,
                  SUM(total_households) as total_hh, SUM(households_with_tap) as tapped,
                  SUM(funds_released_lakhs) as released, SUM(funds_utilized_lakhs) as utilized
           FROM jjm_district WHERE UPPER(state)=UPPER(?)""",
        (state,),
    ).fetchone()

    lines = ["RURAL WATER (JJM)"]
    if jjm and jjm["districts"] and jjm["districts"] > 0:
        j = dict(jjm)
        cov_pct = (j["tapped"] / j["total_hh"] * 100) if j["total_hh"] > 0 else 0
        lines.append(
            f"  {j['districts']} districts | {j['total_hh']:,} households | {j['tapped']:,} with tap ({pct(cov_pct)})"
        )
        lines.append(
            f"  Funds released: {fmt_inr(j['released'], 'lakhs')} | utilized: {fmt_inr(j['utilized'], 'lakhs')}"
        )
    else:
        lines.append("  No data available.")
    lines.append("")
    return lines


def _section_poshan(conn: sqlite3.Connection, state: str) -> list[str]:
    poshan = conn.execute(
        """SELECT COUNT(DISTINCT district) as districts,
                  SUM(schools_covered) as schools, SUM(children_enrolled) as enrolled,
                  SUM(children_fed) as fed
           FROM pmposhan_district WHERE UPPER(state)=UPPER(?) AND fin_year=?""",
        (state, FIN_YEAR),
    ).fetchone()

    lines = ["SCHOOL NUTRITION (PM POSHAN)"]
    if poshan and poshan["districts"] and poshan["districts"] > 0:
        p = dict(poshan)
        feeding_pct = (p["fed"] / p["enrolled"] * 100) if p["enrolled"] > 0 else 0
        lines.append(f"  {p['districts']} districts | {p['schools']:,} schools")
        lines.append(f"  Children enrolled: {p['enrolled']:,} | fed: {p['fed']:,} ({pct(feeding_pct)})")
    else:
        lines.append("  No data available.")
    lines.append("")
    return lines


def _section_nsap(conn: sqlite3.Connection, state: str) -> list[str]:
    nsap = conn.execute(
        """SELECT COUNT(DISTINCT district) as districts,
                  SUM(beneficiaries_paid) as paid, SUM(beneficiaries_eligible) as eligible,
                  SUM(amount_paid_lakhs) as amount
           FROM nsap_district WHERE UPPER(state)=UPPER(?) AND fin_year=?""",
        (state, FIN_YEAR),
    ).fetchone()

    lines = ["PENSIONS (NSAP)"]
    if nsap and nsap["districts"] and nsap["districts"] > 0:
        n = dict(nsap)
        lines.append(f"  {n['districts']} districts | {n['paid']:,} beneficiaries paid")
        if n["eligible"] > 0:
            lines.append(f"  Eligible: {n['eligible']:,} ({n['paid'] / n['eligible'] * 100:.0f}% coverage)")
        lines.append(f"  Amount paid: {fmt_inr(n['amount'], 'lakhs')}")
    else:
        lines.append("  No data available.")
    lines.append("")
    return lines


def _section_nfsa(conn: sqlite3.Connection, state: str) -> list[str]:
    nfsa = conn.execute(
        """SELECT COUNT(DISTINCT district) as districts,
                  SUM(ration_cards_total) as total_cards, SUM(ration_cards_active) as active_cards,
                  SUM(allocation_mt) as allocation, SUM(offtake_mt) as offtake,
                  SUM(beneficiaries_total) as beneficiaries
           FROM nfsa_district WHERE UPPER(state)=UPPER(?) AND fin_year=?""",
        (state, FIN_YEAR),
    ).fetchone()

    lines = ["RATION SYSTEM (PDS/NFSA)"]
    if nfsa and nfsa["districts"] and nfsa["districts"] > 0:
        nf = dict(nfsa)
        offtake_pct = (nf["offtake"] / nf["allocation"] * 100) if nf["allocation"] > 0 else 0
        lines.append(
            f"  {nf['districts']} districts | {nf['active_cards']:,} active / {nf['total_cards']:,} total ration cards"
        )
        lines.append(
            f"  Allocation: {nf['allocation']:,.1f} MT | Offtake: {nf['offtake']:,.1f} MT ({pct(offtake_pct)})"
        )
        lines.append(f"  Beneficiaries: {nf['beneficiaries']:,}")
    else:
        lines.append("  No data available.")
    lines.append("")
    return lines


def _section_worst_districts(conn: sqlite3.Connection, state: str) -> list[str]:
    worst = conn.execute(
        """SELECT district, cases_reported, amount_reported,
                  (amount_reported - amount_recovered) as unrecovered,
                  CASE WHEN amount_reported > 0
                       THEN (amount_recovered * 100.0 / amount_reported)
                       ELSE 0 END as recovery_pct
           FROM misappropriation
           WHERE UPPER(state)=UPPER(?) AND fin_year=?
           ORDER BY unrecovered DESC LIMIT 5""",
        (state, FIN_YEAR),
    ).fetchall()

    lines = ["TOP 5 DISTRICTS BY UNRECOVERED AMOUNT"]
    for i, row in enumerate(worst, 1):
        w = dict(row)
        lines.append(
            f"  {i}. {w['district']}: {fmt_inr(w['unrecovered'])} unrecovered "
            f"({w['cases_reported']:,} cases, {pct(w['recovery_pct'])} recovered)"
        )
    return lines
