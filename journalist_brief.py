"""
Journalist briefing generator for MGNREGA and PMGSY data.

Produces clean, citable plain-text briefings from hisaab.db.

Usage:
    python journalist_brief.py "Tiruvanna"
    python journalist_brief.py "CUDDALORE"
    python journalist_brief.py --state "TAMIL NADU"
    python journalist_brief.py --state "BIHAR" --save
"""

from __future__ import annotations

import argparse
import difflib
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parent / "data" / "hisaab.db"
BRIEFS_DIR = Path(__file__).resolve().parent / "data" / "briefs"
FIN_YEAR = "2024-2025"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Formatting
# ---------------------------------------------------------------------------
def _fmt_inr(amount: float, unit: str = "rupees") -> str:
    """Format as ₹X crore / ₹X lakh."""
    if unit == "lakhs":
        if abs(amount) >= 100:
            return f"₹{amount / 100:.2f} crore"
        return f"₹{amount:.2f} lakh"
    if abs(amount) >= 10000000:
        return f"₹{amount / 10000000:.2f} crore"
    if abs(amount) >= 100000:
        return f"₹{amount / 100000:.2f} lakh"
    return f"₹{amount:,.0f}"


def _pct(value: float) -> str:
    return f"{value:.1f}%"


# ---------------------------------------------------------------------------
# Fuzzy district matching
# ---------------------------------------------------------------------------
def _all_districts(conn: sqlite3.Connection) -> list[dict[str, str]]:
    """Return all (district, state) pairs from all scheme tables."""
    seen: set[tuple[str, str]] = set()
    result: list[dict[str, str]] = []
    tables = (
        "misappropriation", "financial_statement", "pmgsy_district",
        "pmayg_district", "pmkisan_district", "jjm_district",
        "pmposhan_district", "nsap_district", "nfsa_district",
    )
    for table in tables:
        try:
            rows = conn.execute(
                f"SELECT DISTINCT district, state FROM {table} ORDER BY state, district"
            ).fetchall()
            for r in rows:
                key = (r["district"].upper(), r["state"].upper())
                if key not in seen:
                    seen.add(key)
                    result.append({"district": r["district"], "state": r["state"]})
        except Exception:
            pass
    return sorted(result, key=lambda d: (d["state"], d["district"]))


def resolve_district(query: str) -> dict[str, str] | None:
    """Fuzzy-match a district name. Returns {district, state} or None."""
    conn = _conn()
    all_d = _all_districts(conn)
    conn.close()

    query_upper = query.strip().upper()

    # Exact match
    for d in all_d:
        if d["district"].upper() == query_upper:
            return d

    # Prefix match
    for d in all_d:
        if d["district"].upper().startswith(query_upper):
            return d

    # Fuzzy match via difflib
    names = [d["district"] for d in all_d]
    matches = difflib.get_close_matches(query_upper, [n.upper() for n in names], n=1, cutoff=0.5)
    if matches:
        idx = [n.upper() for n in names].index(matches[0])
        return all_d[idx]

    return None


# ---------------------------------------------------------------------------
# Ranking queries
# ---------------------------------------------------------------------------
def _state_rank_unrecovered(conn: sqlite3.Connection, district: str, state: str) -> tuple[int, int]:
    """Rank within state by unrecovered amount (amount_reported - amount_recovered). Returns (rank, total)."""
    rows = conn.execute(
        """SELECT district, (amount_reported - amount_recovered) as unrecovered
           FROM misappropriation WHERE UPPER(state) = UPPER(?)
           ORDER BY unrecovered DESC""",
        (state,),
    ).fetchall()
    total = len(rows)
    for i, r in enumerate(rows, 1):
        if r["district"].upper() == district.upper():
            return i, total
    return 0, total


def _national_rank_unrecovered(conn: sqlite3.Connection, district: str, state: str) -> tuple[int, int]:
    """Rank nationally by unrecovered amount. Returns (rank, total)."""
    rows = conn.execute(
        """SELECT district, state, (amount_reported - amount_recovered) as unrecovered
           FROM misappropriation ORDER BY unrecovered DESC"""
    ).fetchall()
    total = len(rows)
    for i, r in enumerate(rows, 1):
        if r["district"].upper() == district.upper() and r["state"].upper() == state.upper():
            return i, total
    return 0, total


# ---------------------------------------------------------------------------
# District brief
# ---------------------------------------------------------------------------
def brief(district_query: str) -> str:
    """Generate a journalist briefing for a district. Accepts fuzzy names."""
    match = resolve_district(district_query)
    if not match:
        return f"ERROR: Could not find district matching '{district_query}'.\nTry an exact name or longer prefix."

    district = match["district"]
    state = match["state"]
    conn = _conn()

    generated = datetime.now().strftime("%d %b %Y")
    lines = [
        "HISAAB DISTRICT BRIEF",
        f"{district}, {state}",
        f"Generated: {generated} | Source: Government of India, MoRD MGNREGA MIS",
        f"Financial Year: {FIN_YEAR}",
        "",
    ]

    # --- MISAPPROPRIATION ---
    mis = conn.execute(
        "SELECT * FROM misappropriation WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchone()

    lines.append("FINANCIAL MISAPPROPRIATION")
    if mis:
        m = dict(mis)
        unrecovered = m["amount_reported"] - m["amount_recovered"]
        recovery_pct = (m["amount_recovered"] / m["amount_reported"] * 100) if m["amount_reported"] > 0 else 0
        lines.append(f"  {m['cases_reported']:,} cases reported")
        lines.append(f"  {_fmt_inr(m['amount_reported'])} misappropriated")
        lines.append(f"  {_fmt_inr(unrecovered)} still unrecovered (recovery rate: {_pct(recovery_pct)})")
        lines.append(f"  Source: {m['source_url']}")
    else:
        lines.append("  No data available.")
    lines.append("")

    # --- FUND UTILIZATION ---
    fin = conn.execute(
        "SELECT * FROM financial_statement WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchone()

    lines.append("FUND UTILIZATION")
    if fin:
        f = dict(fin)
        lines.append(f"  Allocated: {_fmt_inr(f['total_availability'], 'lakhs')}")
        lines.append(f"  Expended: {_fmt_inr(f['cumulative_expenditure'], 'lakhs')}")
        lines.append(f"  Utilization: {_pct(f['utilization_pct'])}")
        lines.append(f"  Wage payments: {_fmt_inr(f['exp_unskilled_wage'], 'lakhs')} (unskilled)")
        lines.append(f"  Source: {f['source_url']}")
    else:
        lines.append("  No data available.")
    lines.append("")

    # --- PENDING PAYMENTS (FTO) ---
    fto = conn.execute(
        "SELECT * FROM fto_status WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchone()

    lines.append("PENDING PAYMENTS (FTO)")
    if fto:
        ft = dict(fto)
        total_pending = ft["first_signatory_pending"] + ft["second_signatory_pending"]
        lines.append(f"  {ft['total_fto_generated']:,} Fund Transfer Orders generated")
        if total_pending == 0:
            lines.append("  No pending FTOs — all payments processed")
        else:
            lines.append(f"  {ft['first_signatory_pending']:,} pending 1st signatory approval")
            lines.append(f"  {ft['second_signatory_pending']:,} pending 2nd signatory approval")
            lines.append(f"  {total_pending:,} total FTOs pending")
        lines.append(f"  {ft['fto_sent_to_bank']:,} sent to bank, {ft['fto_processed_by_bank']:,} transactions processed")
        lines.append(f"  Source: {ft['source_url']}")
    else:
        lines.append("  No data available.")
    lines.append("")

    # --- SOCIAL AUDIT ---
    aud = conn.execute(
        "SELECT * FROM issues_reported WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchone()

    lines.append("SOCIAL AUDIT FINDINGS")
    if aud:
        a = dict(aud)
        coverage = (a["gps_audited"] / a["total_gps"] * 100) if a["total_gps"] > 0 else 0
        # Find top issue category
        categories = {
            "Financial Misappropriation": a["misappropriation_issues"],
            "Financial Deviation": a["financial_deviation_issues"],
            "Process Violation": a["process_violation_issues"],
            "Grievances": a["grievances_issues"],
        }
        top_category = max(categories, key=lambda k: categories[k])
        lines.append(f"  {a['total_issues']:,} issues reported across {a['gps_audited']}/{a['total_gps']} GPs audited ({_pct(coverage)})")
        lines.append(f"  Misappropriation: {a['misappropriation_issues']:,} | Deviation: {a['financial_deviation_issues']:,} | Process violations: {a['process_violation_issues']:,} | Grievances: {a['grievances_issues']:,}")
        lines.append(f"  Top issue category: {top_category} ({categories[top_category]:,} cases)")
        lines.append(f"  Source: {a['source_url']}")
    else:
        lines.append("  No data available.")
    lines.append("")

    # --- PMGSY (Rural Roads) ---
    pmgsy = conn.execute(
        "SELECT * FROM pmgsy_district WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?)",
        (district, state),
    ).fetchall()

    lines.append("RURAL ROADS (PMGSY)")
    if pmgsy:
        rows = [dict(r) for r in pmgsy]
        total_sanctioned = sum(r.get("roads_sanctioned", 0) for r in rows)
        total_completed = sum(r.get("roads_completed", 0) for r in rows)
        total_len_s = sum(r.get("length_sanctioned_km", 0) for r in rows)
        total_len_c = sum(r.get("length_completed_km", 0) for r in rows)
        total_exp = sum(r.get("expenditure_cr", 0) for r in rows)
        completion_rate = (total_completed / total_sanctioned * 100) if total_sanctioned > 0 else 0
        cost_per_km = (total_exp / total_len_c) if total_len_c > 0 else 0

        lines.append(f"  Roads sanctioned: {total_sanctioned:,} | completed: {total_completed:,} ({_pct(completion_rate)})")
        lines.append(f"  Length sanctioned: {total_len_s:,.1f} km | completed: {total_len_c:,.1f} km")
        lines.append(f"  Total expenditure: {_fmt_inr(total_exp * 10000000)}")
        if total_len_c > 0:
            lines.append(f"  Cost per km: {_fmt_inr(cost_per_km * 10000000)}")
        lines.append(f"  Source: {rows[0].get('source_url', 'N/A')}")
    else:
        lines.append("  No data available.")
    lines.append("")

    # --- PMAY-G (Rural Housing) ---
    pmayg = conn.execute(
        "SELECT * FROM pmayg_district WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchone()

    lines.append("RURAL HOUSING (PMAY-G)")
    if pmayg:
        h = dict(pmayg)
        occupied_pct = (h["houses_occupied"] / h["houses_completed"] * 100) if h["houses_completed"] > 0 else 0
        lines.append(f"  Houses sanctioned: {h['houses_sanctioned']:,} | completed: {h['houses_completed']:,} ({h['completion_pct']:.0f}%)")
        lines.append(f"  Houses occupied: {h['houses_occupied']:,} ({occupied_pct:.0f}% of completed)")
        lines.append(f"  Funds released: {_fmt_inr(h['funds_released_lakhs'], 'lakhs')} | utilized: {_fmt_inr(h['funds_utilized_lakhs'], 'lakhs')}")
        if h.get("source_url"):
            lines.append(f"  Source: {h['source_url']}")
    else:
        lines.append("  No data available.")
    lines.append("")

    # --- PM Kisan ---
    pmkisan = conn.execute(
        "SELECT * FROM pmkisan_district WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchall()

    lines.append("FARMER PAYMENTS (PM KISAN)")
    if pmkisan:
        pk = [dict(r) for r in pmkisan]
        total_paid = sum(r["beneficiaries_paid"] for r in pk)
        total_amount = sum(r["amount_paid_lakhs"] for r in pk)
        max_reg = max(r["beneficiaries_registered"] for r in pk)
        cov_pct = (total_paid / max_reg * 100) if max_reg > 0 else 0
        is_all = any(r["district"].upper() == "ALL" for r in pk)
        lines.append(f"  Beneficiaries registered: {max_reg:,} | paid: {total_paid:,} ({cov_pct:.0f}% coverage)")
        lines.append(f"  Amount disbursed: {_fmt_inr(total_amount, 'lakhs')}")
        if is_all:
            lines.append("  NOTE: This is state-level aggregate data (district='ALL'), not district-specific.")
        if pk[0].get("source_url"):
            lines.append(f"  Source: {pk[0]['source_url']}")
    else:
        lines.append("  No data available.")
    lines.append("")

    # --- JJM (Water) ---
    jjm = conn.execute(
        "SELECT * FROM jjm_district WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?)",
        (district, state),
    ).fetchone()

    lines.append("RURAL WATER (JJM)")
    if jjm:
        j = dict(jjm)
        util_pct = (j["funds_utilized_lakhs"] / j["funds_released_lakhs"] * 100) if j["funds_released_lakhs"] > 0 else 0
        lines.append(f"  Households: {j['total_households']:,} total | {j['households_with_tap']:,} with tap ({j['coverage_pct']:.0f}%)")
        lines.append(f"  Funds released: {_fmt_inr(j['funds_released_lakhs'], 'lakhs')} | utilized: {_fmt_inr(j['funds_utilized_lakhs'], 'lakhs')} ({util_pct:.0f}%)")
        if j.get("source_url"):
            lines.append(f"  Source: {j['source_url']}")
    else:
        lines.append("  No data available.")
    lines.append("")

    # --- PM POSHAN (School Nutrition) ---
    poshan = conn.execute(
        "SELECT * FROM pmposhan_district WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchone()

    lines.append("SCHOOL NUTRITION (PM POSHAN)")
    if poshan:
        p = dict(poshan)
        feeding_pct = (p["children_fed"] / p["children_enrolled"] * 100) if p["children_enrolled"] > 0 else 0
        lines.append(f"  Schools covered: {p['schools_covered']:,}")
        lines.append(f"  Children enrolled: {p['children_enrolled']:,} | fed: {p['children_fed']:,} ({feeding_pct:.0f}%)")
        lines.append(f"  Funds released: {_fmt_inr(p['funds_released_lakhs'], 'lakhs')} | utilized: {_fmt_inr(p['funds_utilized_lakhs'], 'lakhs')}")
        if p.get("source_url"):
            lines.append(f"  Source: {p['source_url']}")
    else:
        lines.append("  No data available.")
    lines.append("")

    # --- NSAP (Pensions) ---
    nsap = conn.execute(
        "SELECT * FROM nsap_district WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchall()

    lines.append("PENSIONS (NSAP)")
    if nsap:
        ns = [dict(r) for r in nsap]
        total_paid = sum(r["beneficiaries_paid"] for r in ns)
        total_eligible = sum(r["beneficiaries_eligible"] for r in ns)
        total_amount = sum(r["amount_paid_lakhs"] for r in ns)
        lines.append(f"  Beneficiaries paid: {total_paid:,}")
        if total_eligible > 0:
            lines.append(f"  Eligible: {total_eligible:,} ({total_paid / total_eligible * 100:.0f}% coverage)")
        lines.append(f"  Amount paid: {_fmt_inr(total_amount, 'lakhs')}")
        for r in ns:
            if r["scheme_type"]:
                lines.append(f"    {r['scheme_type']}: {r['beneficiaries_paid']:,} paid")
        if ns[0].get("source_url"):
            lines.append(f"  Source: {ns[0]['source_url']}")
    else:
        lines.append("  No data available.")
    lines.append("")

    # --- NFSA (Ration System) ---
    nfsa = conn.execute(
        "SELECT * FROM nfsa_district WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchone()

    lines.append("RATION SYSTEM (PDS/NFSA)")
    if nfsa:
        nf = dict(nfsa)
        active_pct = (nf["ration_cards_active"] / nf["ration_cards_total"] * 100) if nf["ration_cards_total"] > 0 else 0
        lines.append(f"  Ration cards: {nf['ration_cards_active']:,} active / {nf['ration_cards_total']:,} total ({active_pct:.0f}%)")
        lines.append(f"  Allocation: {nf['allocation_mt']:,.1f} MT | Offtake: {nf['offtake_mt']:,.1f} MT ({nf['offtake_pct']:.0f}%)")
        lines.append(f"  Beneficiaries: {nf['beneficiaries_total']:,}")
        if nf.get("source_url"):
            lines.append(f"  Source: {nf['source_url']}")
    else:
        lines.append("  No data available.")
    lines.append("")

    # --- RED FLAGS (automated anomaly detection) ---
    flags = _detect_flags(conn, district, state, verbose=True)

    if flags:
        lines.append("RED FLAGS")
        for flag in flags:
            lines.append(f"  ⚠ {flag}")
        lines.append("")

    # --- CONTEXT (rankings) ---
    lines.append("CONTEXT")
    state_rank, state_total = _state_rank_unrecovered(conn, district, state)
    national_rank, national_total = _national_rank_unrecovered(conn, district, state)
    if state_rank > 0:
        lines.append(f"  {district} ranks #{state_rank} out of {state_total} {state} districts for unrecovered misappropriation.")
    if national_rank > 0:
        lines.append(f"  Nationally, it ranks #{national_rank} out of {national_total} districts.")

    conn.close()
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# State brief
# ---------------------------------------------------------------------------
def state_brief(state_name: str) -> str:
    """Generate a journalist briefing for an entire state."""
    conn = _conn()

    # Verify state exists
    check = conn.execute(
        "SELECT COUNT(*) as n FROM misappropriation WHERE UPPER(state)=UPPER(?) AND fin_year=?",
        (state_name, FIN_YEAR),
    ).fetchone()
    if not check or check["n"] == 0:
        # Fuzzy match state name before closing
        all_states = [r[0] for r in conn.execute("SELECT DISTINCT state FROM misappropriation").fetchall()]
        conn.close()
        matches = difflib.get_close_matches(state_name.upper(), [s.upper() for s in all_states], n=1, cutoff=0.5)
        if matches:
            return f"ERROR: State '{state_name}' not found. Did you mean '{matches[0]}'?"
        return f"ERROR: State '{state_name}' not found in database."

    # Normalize state name from DB
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

    # --- MISAPPROPRIATION SUMMARY ---
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

    lines.append("FINANCIAL MISAPPROPRIATION")
    lines.append(f"  {m['districts']} districts | {m['cases']:,} cases reported")
    lines.append(f"  {_fmt_inr(m['reported'])} misappropriated")
    lines.append(f"  {_fmt_inr(m['recovered'])} recovered ({_pct(recovery_pct)})")
    lines.append(f"  {_fmt_inr(total_unrecovered)} still unrecovered")

    # National state ranking
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
        lines.append(f"  State ranks #{state_national_rank} out of {total_states} states nationally for unrecovered amount")
    lines.append("")

    # --- FUND UTILIZATION ---
    fin = conn.execute(
        """SELECT SUM(total_availability) as funds, SUM(cumulative_expenditure) as exp,
                  AVG(utilization_pct) as util, SUM(exp_unskilled_wage) as wage
           FROM financial_statement WHERE UPPER(state)=UPPER(?) AND fin_year=?""",
        (state, FIN_YEAR),
    ).fetchone()

    lines.append("FUND UTILIZATION")
    if fin and fin["funds"]:
        f = dict(fin)
        lines.append(f"  Total allocated: {_fmt_inr(f['funds'], 'lakhs')}")
        lines.append(f"  Total expended: {_fmt_inr(f['exp'], 'lakhs')}")
        lines.append(f"  Average utilization: {_pct(f['util'])}")
        lines.append(f"  Wage payments: {_fmt_inr(f['wage'], 'lakhs')}")
    else:
        lines.append("  No data available.")
    lines.append("")

    # --- FTO SUMMARY ---
    fto = conn.execute(
        """SELECT SUM(total_fto_generated) as gen, SUM(first_signatory_pending) as p1,
                  SUM(second_signatory_pending) as p2, SUM(fto_sent_to_bank) as bank
           FROM fto_status WHERE UPPER(state)=UPPER(?) AND fin_year=?""",
        (state, FIN_YEAR),
    ).fetchone()

    lines.append("PAYMENT STATUS (FTO)")
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

    # --- SOCIAL AUDIT ---
    aud = conn.execute(
        """SELECT SUM(total_issues) as issues, SUM(total_gps) as gps, SUM(gps_audited) as audited,
                  SUM(misappropriation_issues) as mis, SUM(financial_deviation_issues) as dev,
                  SUM(process_violation_issues) as pv, SUM(grievances_issues) as gr
           FROM issues_reported WHERE UPPER(state)=UPPER(?) AND fin_year=?""",
        (state, FIN_YEAR),
    ).fetchone()

    lines.append("SOCIAL AUDIT")
    if aud and aud["issues"]:
        a = dict(aud)
        coverage = (a["audited"] / a["gps"] * 100) if a["gps"] > 0 else 0
        lines.append(f"  {a['issues']:,} issues across {a['audited']:,}/{a['gps']:,} GPs ({_pct(coverage)} coverage)")
        lines.append(f"  Misappropriation: {a['mis']:,} | Deviation: {a['dev']:,} | Process violations: {a['pv']:,} | Grievances: {a['gr']:,}")
    else:
        lines.append("  No data available.")
    lines.append("")

    # --- PMGSY (Rural Roads) ---
    pmgsy = conn.execute(
        """SELECT COUNT(DISTINCT district) as districts,
                  SUM(roads_sanctioned) as sanctioned, SUM(roads_completed) as completed,
                  SUM(length_sanctioned_km) as len_s, SUM(length_completed_km) as len_c,
                  SUM(expenditure_cr) as exp
           FROM pmgsy_district WHERE UPPER(state)=UPPER(?)""",
        (state,),
    ).fetchone()

    lines.append("RURAL ROADS (PMGSY)")
    if pmgsy and pmgsy["districts"] and pmgsy["districts"] > 0:
        pm = dict(pmgsy)
        completion_pct = (pm["completed"] / pm["sanctioned"] * 100) if pm["sanctioned"] > 0 else 0
        lines.append(f"  {pm['districts']} districts | {pm['sanctioned']:,} roads sanctioned | {pm['completed']:,} completed ({_pct(completion_pct)})")
        lines.append(f"  Length: {pm['len_s']:,.1f} km sanctioned | {pm['len_c']:,.1f} km completed")
        lines.append(f"  Total expenditure: {_fmt_inr(pm['exp'] * 10000000)}")
    else:
        lines.append("  No data available.")
    lines.append("")

    # --- PMAY-G ---
    pmayg = conn.execute(
        """SELECT COUNT(DISTINCT district) as districts,
                  SUM(houses_sanctioned) as sanctioned, SUM(houses_completed) as completed,
                  SUM(houses_occupied) as occupied,
                  SUM(funds_released_lakhs) as released, SUM(funds_utilized_lakhs) as utilized
           FROM pmayg_district WHERE UPPER(state)=UPPER(?) AND fin_year=?""",
        (state, FIN_YEAR),
    ).fetchone()

    lines.append("RURAL HOUSING (PMAY-G)")
    if pmayg and pmayg["districts"] and pmayg["districts"] > 0:
        h = dict(pmayg)
        comp_pct = (h["completed"] / h["sanctioned"] * 100) if h["sanctioned"] > 0 else 0
        lines.append(f"  {h['districts']} districts | {h['sanctioned']:,} houses sanctioned | {h['completed']:,} completed ({_pct(comp_pct)})")
        lines.append(f"  Occupied: {h['occupied']:,}")
        lines.append(f"  Funds released: {_fmt_inr(h['released'], 'lakhs')} | utilized: {_fmt_inr(h['utilized'], 'lakhs')}")
    else:
        lines.append("  No data available.")
    lines.append("")

    # --- PM Kisan ---
    pmkisan = conn.execute(
        """SELECT COUNT(DISTINCT district) as districts,
                  SUM(beneficiaries_paid) as paid, SUM(amount_paid_lakhs) as amount
           FROM pmkisan_district WHERE UPPER(state)=UPPER(?) AND fin_year=?""",
        (state, FIN_YEAR),
    ).fetchone()

    lines.append("FARMER PAYMENTS (PM KISAN)")
    if pmkisan and pmkisan["districts"] and pmkisan["districts"] > 0:
        pk = dict(pmkisan)
        lines.append(f"  {pk['districts']} districts | {pk['paid']:,} beneficiaries paid")
        lines.append(f"  Amount disbursed: {_fmt_inr(pk['amount'], 'lakhs')}")
    else:
        lines.append("  No data available.")
    lines.append("")

    # --- JJM ---
    jjm = conn.execute(
        """SELECT COUNT(DISTINCT district) as districts,
                  SUM(total_households) as total_hh, SUM(households_with_tap) as tapped,
                  SUM(funds_released_lakhs) as released, SUM(funds_utilized_lakhs) as utilized
           FROM jjm_district WHERE UPPER(state)=UPPER(?)""",
        (state,),
    ).fetchone()

    lines.append("RURAL WATER (JJM)")
    if jjm and jjm["districts"] and jjm["districts"] > 0:
        j = dict(jjm)
        cov_pct = (j["tapped"] / j["total_hh"] * 100) if j["total_hh"] > 0 else 0
        lines.append(f"  {j['districts']} districts | {j['total_hh']:,} households | {j['tapped']:,} with tap ({_pct(cov_pct)})")
        lines.append(f"  Funds released: {_fmt_inr(j['released'], 'lakhs')} | utilized: {_fmt_inr(j['utilized'], 'lakhs')}")
    else:
        lines.append("  No data available.")
    lines.append("")

    # --- PM POSHAN ---
    poshan = conn.execute(
        """SELECT COUNT(DISTINCT district) as districts,
                  SUM(schools_covered) as schools, SUM(children_enrolled) as enrolled,
                  SUM(children_fed) as fed
           FROM pmposhan_district WHERE UPPER(state)=UPPER(?) AND fin_year=?""",
        (state, FIN_YEAR),
    ).fetchone()

    lines.append("SCHOOL NUTRITION (PM POSHAN)")
    if poshan and poshan["districts"] and poshan["districts"] > 0:
        p = dict(poshan)
        feeding_pct = (p["fed"] / p["enrolled"] * 100) if p["enrolled"] > 0 else 0
        lines.append(f"  {p['districts']} districts | {p['schools']:,} schools")
        lines.append(f"  Children enrolled: {p['enrolled']:,} | fed: {p['fed']:,} ({_pct(feeding_pct)})")
    else:
        lines.append("  No data available.")
    lines.append("")

    # --- NSAP ---
    nsap = conn.execute(
        """SELECT COUNT(DISTINCT district) as districts,
                  SUM(beneficiaries_paid) as paid, SUM(beneficiaries_eligible) as eligible,
                  SUM(amount_paid_lakhs) as amount
           FROM nsap_district WHERE UPPER(state)=UPPER(?) AND fin_year=?""",
        (state, FIN_YEAR),
    ).fetchone()

    lines.append("PENSIONS (NSAP)")
    if nsap and nsap["districts"] and nsap["districts"] > 0:
        n = dict(nsap)
        lines.append(f"  {n['districts']} districts | {n['paid']:,} beneficiaries paid")
        if n["eligible"] > 0:
            lines.append(f"  Eligible: {n['eligible']:,} ({n['paid'] / n['eligible'] * 100:.0f}% coverage)")
        lines.append(f"  Amount paid: {_fmt_inr(n['amount'], 'lakhs')}")
    else:
        lines.append("  No data available.")
    lines.append("")

    # --- NFSA ---
    nfsa = conn.execute(
        """SELECT COUNT(DISTINCT district) as districts,
                  SUM(ration_cards_total) as total_cards, SUM(ration_cards_active) as active_cards,
                  SUM(allocation_mt) as allocation, SUM(offtake_mt) as offtake,
                  SUM(beneficiaries_total) as beneficiaries
           FROM nfsa_district WHERE UPPER(state)=UPPER(?) AND fin_year=?""",
        (state, FIN_YEAR),
    ).fetchone()

    lines.append("RATION SYSTEM (PDS/NFSA)")
    if nfsa and nfsa["districts"] and nfsa["districts"] > 0:
        nf = dict(nfsa)
        offtake_pct = (nf["offtake"] / nf["allocation"] * 100) if nf["allocation"] > 0 else 0
        lines.append(f"  {nf['districts']} districts | {nf['active_cards']:,} active / {nf['total_cards']:,} total ration cards")
        lines.append(f"  Allocation: {nf['allocation']:,.1f} MT | Offtake: {nf['offtake']:,.1f} MT ({_pct(offtake_pct)})")
        lines.append(f"  Beneficiaries: {nf['beneficiaries']:,}")
    else:
        lines.append("  No data available.")
    lines.append("")

    # --- TOP 5 WORST DISTRICTS ---
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

    lines.append("TOP 5 DISTRICTS BY UNRECOVERED AMOUNT")
    for i, row in enumerate(worst, 1):
        w = dict(row)
        lines.append(
            f"  {i}. {w['district']}: {_fmt_inr(w['unrecovered'])} unrecovered "
            f"({w['cases_reported']:,} cases, {_pct(w['recovery_pct'])} recovered)"
        )

    conn.close()
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Story finder — scan all districts for red flags
# ---------------------------------------------------------------------------
def _detect_flags(conn: sqlite3.Connection, district: str, state: str, verbose: bool = False) -> list[str]:
    """Return list of red flag strings for a district.

    verbose=True gives detailed explanations (for briefs).
    verbose=False gives compact labels (for scan tables).
    """
    flags: list[str] = []

    mis = conn.execute(
        "SELECT * FROM misappropriation WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchone()

    fin = conn.execute(
        "SELECT * FROM financial_statement WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchone()

    aud = conn.execute(
        "SELECT * FROM issues_reported WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchone()

    fto = conn.execute(
        "SELECT * FROM fto_status WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchone()

    if mis:
        m = dict(mis)
        if m["amount_reported"] > 0 and m["amount_recovered"] == 0:
            if verbose:
                flags.append(f"Zero recovery: {_fmt_inr(m['amount_reported'])} misappropriated with ₹0 recovered")
            else:
                flags.append(f"Zero recovery on {_fmt_inr(m['amount_reported'])}")
        elif m["amount_reported"] > 0:
            rr = m["amount_recovered"] / m["amount_reported"] * 100
            if rr < 10:
                if verbose:
                    flags.append(f"Very low recovery rate: only {_pct(rr)} of misappropriated funds recovered")
                else:
                    flags.append(f"Recovery rate only {_pct(rr)}")

    if fin:
        f = dict(fin)
        if f["utilization_pct"] > 105:
            if verbose:
                flags.append(f"Over-expenditure: {_pct(f['utilization_pct'])} utilization — spending exceeds allocation by {_fmt_inr(f['cumulative_expenditure'] - f['total_availability'], 'lakhs')}")
            else:
                flags.append(f"Over-expenditure: {_pct(f['utilization_pct'])}")
        if f["total_availability"] > 0 and f["utilization_pct"] < 50:
            if verbose:
                flags.append(f"Severe under-utilization: only {_pct(f['utilization_pct'])} of {_fmt_inr(f['total_availability'], 'lakhs')} allocated funds spent")
            else:
                flags.append(f"Under-utilized: {_pct(f['utilization_pct'])}")

    if aud:
        a = dict(aud)
        if a["total_gps"] > 0 and a["gps_audited"] / a["total_gps"] < 0.5:
            coverage = a["gps_audited"] / a["total_gps"] * 100
            if verbose:
                flags.append(f"Low audit coverage: only {_pct(coverage)} of Gram Panchayats audited")
            else:
                flags.append(f"Low audit: {a['gps_audited']}/{a['total_gps']} GPs")
        if a["process_violation_issues"] > 0 and a["total_issues"] > 0:
            pv_share = a["process_violation_issues"] / a["total_issues"] * 100
            if pv_share > 80:
                if verbose:
                    flags.append(f"Process violations dominate: {_pct(pv_share)} of all audit issues ({a['process_violation_issues']:,} cases)")
                else:
                    flags.append("Process violations >80%")

    if fto:
        ft = dict(fto)
        pending = ft["first_signatory_pending"] + ft["second_signatory_pending"]
        if pending > 100:
            if verbose:
                flags.append(f"Significant FTO backlog: {pending:,} payment orders pending approval")
            else:
                flags.append(f"{pending:,} FTOs pending")

    # --- PMGSY red flags ---
    pmgsy_rows = conn.execute(
        "SELECT * FROM pmgsy_district WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?)",
        (district, state),
    ).fetchall()

    if pmgsy_rows:
        pm = [dict(r) for r in pmgsy_rows]
        total_sanctioned = sum(r.get("roads_sanctioned", 0) for r in pm)
        total_completed = sum(r.get("roads_completed", 0) for r in pm)
        total_exp = sum(r.get("expenditure_cr", 0) for r in pm)
        total_value = sum(r.get("value_of_projects_cr", 0) for r in pm)
        total_len_c = sum(r.get("length_completed_km", 0) for r in pm)

        # Low completion rate
        if total_sanctioned > 0:
            completion_pct = total_completed / total_sanctioned * 100
            if completion_pct < 50:
                if verbose:
                    flags.append(
                        f"PMGSY low completion: only {_pct(completion_pct)} of sanctioned roads completed "
                        f"({total_completed:,}/{total_sanctioned:,})"
                    )
                else:
                    flags.append(f"PMGSY roads {_pct(completion_pct)} complete")

        # High cost per km (compare to state average)
        if total_len_c > 0:
            cost_per_km = total_exp / total_len_c
            state_avg = conn.execute(
                """SELECT SUM(expenditure_cr) / NULLIF(SUM(length_completed_km), 0) as avg_cpk
                   FROM pmgsy_district WHERE UPPER(state)=UPPER(?)""",
                (state,),
            ).fetchone()
            if state_avg and state_avg["avg_cpk"] and cost_per_km > 2 * state_avg["avg_cpk"]:
                if verbose:
                    flags.append(
                        f"PMGSY high cost: {_fmt_inr(cost_per_km * 10000000)}/km vs state average "
                        f"{_fmt_inr(state_avg['avg_cpk'] * 10000000)}/km (>2x)"
                    )
                else:
                    flags.append("PMGSY cost >2x state avg/km")

        # Expenditure exceeds sanctioned cost
        if total_value > 0 and total_exp > total_value:
            if verbose:
                flags.append(
                    f"PMGSY over-expenditure: {_fmt_inr(total_exp * 10000000)} spent vs "
                    f"{_fmt_inr(total_value * 10000000)} sanctioned"
                )
            else:
                flags.append("PMGSY expenditure > sanctioned")

    # --- Cross-reference: MGNREGA earthwork vs PMGSY road completion ---
    if fin and pmgsy_rows:
        f_dict = dict(fin)
        # High MGNREGA expenditure + low PMGSY completion = possible red flag
        if (f_dict.get("cumulative_expenditure", 0) > 0
                and total_sanctioned > 0
                and total_completed / total_sanctioned < 0.5
                and f_dict["utilization_pct"] > 80):
            if verbose:
                flags.append(
                    f"Cross-scheme anomaly: MGNREGA utilization is high ({_pct(f_dict['utilization_pct'])}) "
                    f"but PMGSY road completion is low ({total_completed}/{total_sanctioned} roads)"
                )
            else:
                flags.append("High MGNREGA spend, low PMGSY roads")

    # --- PMAY-G red flags ---
    pmayg = conn.execute(
        "SELECT * FROM pmayg_district WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchone()

    if pmayg:
        h = dict(pmayg)
        if h["houses_sanctioned"] > 0 and h["completion_pct"] < 40:
            if verbose:
                flags.append(
                    f"PMAY-G low completion: only {_pct(h['completion_pct'])} of sanctioned houses completed "
                    f"({h['houses_completed']:,}/{h['houses_sanctioned']:,})"
                )
            else:
                flags.append(f"PMAY-G housing {_pct(h['completion_pct'])} complete")
        if h["houses_completed"] > 0:
            occ_pct = h["houses_occupied"] / h["houses_completed"] * 100
            if occ_pct < 50:
                if verbose:
                    flags.append(
                        f"PMAY-G low occupancy: only {_pct(occ_pct)} of completed houses occupied "
                        f"({h['houses_occupied']:,}/{h['houses_completed']:,})"
                    )
                else:
                    flags.append(f"PMAY-G occupancy {_pct(occ_pct)}")

    # --- PM Kisan red flags ---
    pmkisan_rows = conn.execute(
        "SELECT * FROM pmkisan_district WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchall()

    if pmkisan_rows:
        pk = [dict(r) for r in pmkisan_rows]
        max_reg = max(r["beneficiaries_registered"] for r in pk)
        total_paid = sum(r["beneficiaries_paid"] for r in pk)
        is_all = any(r["district"].upper() == "ALL" for r in pk)
        if is_all:
            if verbose:
                flags.append("PM Kisan: only state-level aggregate data (district='ALL'), not district-specific")
            else:
                flags.append("PM Kisan: state-level only")
        elif max_reg > 0 and (total_paid / max_reg * 100) < 50:
            cov = total_paid / max_reg * 100
            if verbose:
                flags.append(f"PM Kisan low coverage: only {_pct(cov)} of registered beneficiaries paid")
            else:
                flags.append(f"PM Kisan coverage {_pct(cov)}")

    # --- JJM red flags ---
    jjm = conn.execute(
        "SELECT * FROM jjm_district WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?)",
        (district, state),
    ).fetchone()

    if jjm:
        j = dict(jjm)
        if j["total_households"] > 0 and j["coverage_pct"] < 30:
            if verbose:
                flags.append(
                    f"JJM low coverage: only {_pct(j['coverage_pct'])} of households have tap water "
                    f"({j['households_with_tap']:,}/{j['total_households']:,})"
                )
            else:
                flags.append(f"JJM tap coverage {_pct(j['coverage_pct'])}")
        if j["funds_released_lakhs"] > 0:
            util = j["funds_utilized_lakhs"] / j["funds_released_lakhs"] * 100
            if util < 40:
                if verbose:
                    flags.append(f"JJM low fund utilization: only {_pct(util)} of released funds utilized")
                else:
                    flags.append(f"JJM utilization {_pct(util)}")

    # --- PM POSHAN red flags ---
    poshan = conn.execute(
        "SELECT * FROM pmposhan_district WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchone()

    if poshan:
        p = dict(poshan)
        if p["children_enrolled"] > 0:
            feeding_pct = p["children_fed"] / p["children_enrolled"] * 100
            if feeding_pct < 30:
                if verbose:
                    flags.append(
                        f"PM POSHAN low feeding: only {_pct(feeding_pct)} of enrolled children fed "
                        f"({p['children_fed']:,}/{p['children_enrolled']:,})"
                    )
                else:
                    flags.append(f"PM POSHAN feeding {_pct(feeding_pct)}")

    # --- NSAP red flags ---
    nsap_rows = conn.execute(
        "SELECT * FROM nsap_district WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchall()

    if nsap_rows:
        ns = [dict(r) for r in nsap_rows]
        total_paid = sum(r["beneficiaries_paid"] for r in ns)
        total_eligible = sum(r["beneficiaries_eligible"] for r in ns)
        if total_paid == 0 and total_eligible == 0:
            if verbose:
                flags.append("NSAP: both beneficiaries_paid and beneficiaries_eligible are zero (data quality issue)")
            else:
                flags.append("NSAP: no beneficiary data")

    # --- NFSA red flags ---
    nfsa = conn.execute(
        "SELECT * FROM nfsa_district WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchone()

    if nfsa:
        nf = dict(nfsa)
        if nf["allocation_mt"] > 0 and nf["offtake_pct"] < 50:
            if verbose:
                flags.append(
                    f"NFSA low offtake: only {_pct(nf['offtake_pct'])} of allocated grain distributed "
                    f"({nf['offtake_mt']:,.1f}/{nf['allocation_mt']:,.1f} MT)"
                )
            else:
                flags.append(f"NFSA offtake {_pct(nf['offtake_pct'])}")
        if nf["ration_cards_total"] > 0:
            active_pct = nf["ration_cards_active"] / nf["ration_cards_total"] * 100
            if active_pct < 60:
                if verbose:
                    flags.append(
                        f"NFSA low active cards: only {_pct(active_pct)} of ration cards active "
                        f"({nf['ration_cards_active']:,}/{nf['ration_cards_total']:,})"
                    )
                else:
                    flags.append(f"NFSA active cards {_pct(active_pct)}")

    # --- Cross-scheme: MGNREGA + PMAY-G ---
    if fin and pmayg:
        f_dict = dict(fin)
        h_dict = dict(pmayg)
        if (f_dict["utilization_pct"] > 80
                and h_dict["houses_sanctioned"] > 0
                and h_dict["completion_pct"] < 40):
            if verbose:
                flags.append(
                    f"Cross-scheme: high MGNREGA spend ({_pct(f_dict['utilization_pct'])}) "
                    f"but low housing completion ({_pct(h_dict['completion_pct'])})"
                )
            else:
                flags.append("High MGNREGA, low PMAY-G")

    # --- Cross-scheme: JJM + PM POSHAN (infrastructure gap) ---
    if jjm and poshan:
        j_dict = dict(jjm)
        p_dict = dict(poshan)
        low_water = j_dict["total_households"] > 0 and j_dict["coverage_pct"] < 40
        low_meals = p_dict["children_enrolled"] > 0 and (p_dict["children_fed"] / p_dict["children_enrolled"] * 100) < 40
        if low_water and low_meals:
            if verbose:
                flags.append(
                    f"Infrastructure gap: both water ({_pct(j_dict['coverage_pct'])}) and "
                    f"school meals (<40% coverage) are low — possible systemic delivery failure"
                )
            else:
                flags.append("Low water + low meals")

    # --- Cross-scheme: 3+ schemes showing low delivery ---
    low_delivery_count = 0
    if pmgsy_rows and total_sanctioned > 0 and total_completed / total_sanctioned < 0.5:
        low_delivery_count += 1
    if pmayg and dict(pmayg)["houses_sanctioned"] > 0 and dict(pmayg)["completion_pct"] < 50:
        low_delivery_count += 1
    if jjm and dict(jjm)["total_households"] > 0 and dict(jjm)["coverage_pct"] < 50:
        low_delivery_count += 1
    if poshan and dict(poshan)["children_enrolled"] > 0 and dict(poshan)["children_fed"] / dict(poshan)["children_enrolled"] < 0.5:
        low_delivery_count += 1
    if nfsa and dict(nfsa)["offtake_pct"] < 50:
        low_delivery_count += 1
    if fin and dict(fin)["utilization_pct"] < 50:
        low_delivery_count += 1

    if low_delivery_count >= 3:
        if verbose:
            flags.append(
                f"Multi-scheme underperformance: {low_delivery_count} schemes showing <50% delivery in this district"
            )
        else:
            flags.append(f"{low_delivery_count} schemes <50% delivery")

    return flags


def scan_red_flags(limit: int = 25, state_filter: str | None = None) -> str:
    """Scan all districts and rank by number of red flags. Story finder for journalists."""
    conn = _conn()

    # Gather districts from all scheme tables for comprehensive scanning
    all_districts: set[tuple[str, str]] = set()
    tables_with_fy = [
        "misappropriation", "financial_statement", "fto_status",
        "pmayg_district", "pmkisan_district", "pmposhan_district",
        "nsap_district", "nfsa_district",
    ]
    tables_without_fy = ["pmgsy_district", "jjm_district"]
    for table in tables_with_fy:
        try:
            where = "WHERE fin_year=?"
            params: list[Any] = [FIN_YEAR]
            if state_filter:
                where += " AND UPPER(state)=UPPER(?)"
                params.append(state_filter)
            for r in conn.execute(
                f"SELECT DISTINCT district, state FROM {table} {where}", params
            ).fetchall():
                all_districts.add((r["district"], r["state"]))
        except Exception:
            pass
    for table in tables_without_fy:
        try:
            where = "WHERE 1=1"
            params_nfy: list[Any] = []
            if state_filter:
                where += " AND UPPER(state)=UPPER(?)"
                params_nfy.append(state_filter)
            for r in conn.execute(
                f"SELECT DISTINCT district, state FROM {table} {where}", params_nfy
            ).fetchall():
                all_districts.add((r["district"], r["state"]))
        except Exception:
            pass

    rows = sorted(all_districts, key=lambda x: (x[1], x[0]))

    flagged: list[tuple[str, str, list[str], float]] = []
    for row in rows:
        d, s = row[0], row[1]
        flags = _detect_flags(conn, d, s)
        if flags:
            # Weight by unrecovered amount for sorting
            mis = conn.execute(
                "SELECT amount_reported, amount_recovered FROM misappropriation WHERE district=? AND state=? AND fin_year=?",
                (d, s, FIN_YEAR),
            ).fetchone()
            unrecovered = (mis["amount_reported"] - mis["amount_recovered"]) if mis else 0
            flagged.append((d, s, flags, unrecovered))

    # Sort by flag count descending, then unrecovered amount descending
    flagged.sort(key=lambda x: (-len(x[2]), -x[3]))

    scope = state_filter if state_filter else "INDIA"
    generated = datetime.now().strftime("%d %b %Y")
    lines = [
        "HISAAB RED FLAG SCAN",
        f"Scope: {scope} | Generated: {generated}",
        f"Financial Year: {FIN_YEAR}",
        f"Scanned {len(rows)} districts, {len(flagged)} have red flags",
        "",
    ]

    for i, (d, s, flags, unrec) in enumerate(flagged[:limit], 1):
        lines.append(f"{i}. {d}, {s} — {len(flags)} flags | {_fmt_inr(unrec)} unrecovered")
        for flag in flags:
            lines.append(f"     {flag}")
        lines.append("")

    if len(flagged) > limit:
        lines.append(f"... and {len(flagged) - limit} more districts with red flags.")

    conn.close()
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def save_brief(text: str, filename: str) -> Path:
    BRIEFS_DIR.mkdir(parents=True, exist_ok=True)
    path = BRIEFS_DIR / filename
    path.write_text(text, encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Hisaab journalist briefing generator")
    parser.add_argument("district", nargs="*", help="District name (fuzzy match supported)")
    parser.add_argument("--state", type=str, help="Generate state-level brief instead")
    parser.add_argument("--scan", action="store_true", help="Scan all districts for red flags (story finder)")
    parser.add_argument("--limit", type=int, default=25, help="Number of results for --scan (default: 25)")
    parser.add_argument("--save", action="store_true", help="Save briefing to data/briefs/")
    args = parser.parse_args()

    if args.scan:
        text = scan_red_flags(limit=args.limit, state_filter=args.state)
        print(text)
        if args.save:
            scope = args.state.strip().lower().replace(" ", "-") if args.state else "india"
            path = save_brief(text, f"scan_{scope}_{FIN_YEAR}.txt")
            print(f"\nSaved to: {path}")
        return 0

    if args.state:
        text = state_brief(args.state)
        print(text)
        if args.save:
            slug = args.state.strip().lower().replace(" ", "-")
            path = save_brief(text, f"state_{slug}_{FIN_YEAR}.txt")
            print(f"\nSaved to: {path}")
        return 0

    if not args.district:
        parser.print_help()
        return 1

    query = " ".join(args.district)
    text = brief(query)
    print(text)

    if args.save:
        match = resolve_district(query)
        if match:
            slug = match["district"].lower().replace(" ", "-")
            path = save_brief(text, f"district_{slug}_{FIN_YEAR}.txt")
            print(f"\nSaved to: {path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
