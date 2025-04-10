"""Per-scheme red flag detection helpers.

Each function checks one scheme (or cross-scheme pattern) and returns
a list of flag strings. verbose=True for detailed briefs, False for scan tables.
"""

from __future__ import annotations

import sqlite3

from briefs.formatting import fmt_inr, pct


def mgnrega_flags(
    mis: sqlite3.Row | None,
    fin: sqlite3.Row | None,
    aud: sqlite3.Row | None,
    fto: sqlite3.Row | None,
    verbose: bool,
) -> list[str]:
    flags: list[str] = []

    if mis:
        m = dict(mis)
        if m["amount_reported"] > 0 and m["amount_recovered"] == 0:
            if verbose:
                flags.append(f"Zero recovery: {fmt_inr(m['amount_reported'])} misappropriated with \u20b90 recovered")
            else:
                flags.append(f"Zero recovery on {fmt_inr(m['amount_reported'])}")
        elif m["amount_reported"] > 0:
            rr = m["amount_recovered"] / m["amount_reported"] * 100
            if rr < 10:
                if verbose:
                    flags.append(f"Very low recovery rate: only {pct(rr)} of misappropriated funds recovered")
                else:
                    flags.append(f"Recovery rate only {pct(rr)}")

    if fin:
        f = dict(fin)
        if f["utilization_pct"] > 105:
            if verbose:
                flags.append(
                    f"Over-expenditure: {pct(f['utilization_pct'])} utilization \u2014 spending exceeds allocation by {fmt_inr(f['cumulative_expenditure'] - f['total_availability'], 'lakhs')}"
                )
            else:
                flags.append(f"Over-expenditure: {pct(f['utilization_pct'])}")
        if f["total_availability"] > 0 and f["utilization_pct"] < 50:
            if verbose:
                flags.append(
                    f"Severe under-utilization: only {pct(f['utilization_pct'])} of {fmt_inr(f['total_availability'], 'lakhs')} allocated funds spent"
                )
            else:
                flags.append(f"Under-utilized: {pct(f['utilization_pct'])}")

    if aud:
        a = dict(aud)
        if a["total_gps"] > 0 and a["gps_audited"] / a["total_gps"] < 0.5:
            coverage = a["gps_audited"] / a["total_gps"] * 100
            if verbose:
                flags.append(f"Low audit coverage: only {pct(coverage)} of Gram Panchayats audited")
            else:
                flags.append(f"Low audit: {a['gps_audited']}/{a['total_gps']} GPs")
        if a["process_violation_issues"] > 0 and a["total_issues"] > 0:
            pv_share = a["process_violation_issues"] / a["total_issues"] * 100
            if pv_share > 80:
                if verbose:
                    flags.append(
                        f"Process violations dominate: {pct(pv_share)} of all audit issues ({a['process_violation_issues']:,} cases)"
                    )
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

    return flags


def pmgsy_flags(
    conn: sqlite3.Connection,
    pmgsy_rows: list[sqlite3.Row],
    state: str,
    verbose: bool,
) -> list[str]:
    flags: list[str] = []
    if not pmgsy_rows:
        return flags

    pm = [dict(r) for r in pmgsy_rows]
    total_sanctioned = sum(r.get("roads_sanctioned", 0) for r in pm)
    total_completed = sum(r.get("roads_completed", 0) for r in pm)
    total_exp = sum(r.get("expenditure_cr", 0) for r in pm)
    total_value = sum(r.get("value_of_projects_cr", 0) for r in pm)
    total_len_c = sum(r.get("length_completed_km", 0) for r in pm)

    if total_sanctioned > 0:
        completion_pct = total_completed / total_sanctioned * 100
        if completion_pct < 50:
            if verbose:
                flags.append(
                    f"PMGSY low completion: only {pct(completion_pct)} of sanctioned roads completed "
                    f"({total_completed:,}/{total_sanctioned:,})"
                )
            else:
                flags.append(f"PMGSY roads {pct(completion_pct)} complete")

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
                    f"PMGSY high cost: {fmt_inr(cost_per_km * 10000000)}/km vs state average "
                    f"{fmt_inr(state_avg['avg_cpk'] * 10000000)}/km (>2x)"
                )
            else:
                flags.append("PMGSY cost >2x state avg/km")

    if total_value > 0 and total_exp > total_value:
        if verbose:
            flags.append(
                f"PMGSY over-expenditure: {fmt_inr(total_exp * 10000000)} spent vs "
                f"{fmt_inr(total_value * 10000000)} sanctioned"
            )
        else:
            flags.append("PMGSY expenditure > sanctioned")

    return flags


def pmayg_flags(pmayg: sqlite3.Row | None, verbose: bool) -> list[str]:
    flags: list[str] = []
    if not pmayg:
        return flags

    h = dict(pmayg)
    if h["houses_sanctioned"] > 0 and h["completion_pct"] < 40:
        if verbose:
            flags.append(
                f"PMAY-G low completion: only {pct(h['completion_pct'])} of sanctioned houses completed "
                f"({h['houses_completed']:,}/{h['houses_sanctioned']:,})"
            )
        else:
            flags.append(f"PMAY-G housing {pct(h['completion_pct'])} complete")
    if h["houses_completed"] > 0:
        occ_pct = h["houses_occupied"] / h["houses_completed"] * 100
        if occ_pct < 50:
            if verbose:
                flags.append(
                    f"PMAY-G low occupancy: only {pct(occ_pct)} of completed houses occupied "
                    f"({h['houses_occupied']:,}/{h['houses_completed']:,})"
                )
            else:
                flags.append(f"PMAY-G occupancy {pct(occ_pct)}")

    return flags


def pmkisan_flags(pmkisan_rows: list[sqlite3.Row], verbose: bool) -> list[str]:
    flags: list[str] = []
    if not pmkisan_rows:
        return flags

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
            flags.append(f"PM Kisan low coverage: only {pct(cov)} of registered beneficiaries paid")
        else:
            flags.append(f"PM Kisan coverage {pct(cov)}")

    return flags


def jjm_flags(jjm: sqlite3.Row | None, verbose: bool) -> list[str]:
    flags: list[str] = []
    if not jjm:
        return flags

    j = dict(jjm)
    if j["total_households"] > 0 and j["coverage_pct"] < 30:
        if verbose:
            flags.append(
                f"JJM low coverage: only {pct(j['coverage_pct'])} of households have tap water "
                f"({j['households_with_tap']:,}/{j['total_households']:,})"
            )
        else:
            flags.append(f"JJM tap coverage {pct(j['coverage_pct'])}")
    if j["funds_released_lakhs"] > 0:
        util = j["funds_utilized_lakhs"] / j["funds_released_lakhs"] * 100
        if util < 40:
            if verbose:
                flags.append(f"JJM low fund utilization: only {pct(util)} of released funds utilized")
            else:
                flags.append(f"JJM utilization {pct(util)}")

    return flags


def poshan_flags(poshan: sqlite3.Row | None, verbose: bool) -> list[str]:
    flags: list[str] = []
    if not poshan:
        return flags

    p = dict(poshan)
    if p["children_enrolled"] > 0:
        feeding_pct = p["children_fed"] / p["children_enrolled"] * 100
        if feeding_pct < 30:
            if verbose:
                flags.append(
                    f"PM POSHAN low feeding: only {pct(feeding_pct)} of enrolled children fed "
                    f"({p['children_fed']:,}/{p['children_enrolled']:,})"
                )
            else:
                flags.append(f"PM POSHAN feeding {pct(feeding_pct)}")

    return flags


def nsap_flags(nsap_rows: list[sqlite3.Row], verbose: bool) -> list[str]:
    flags: list[str] = []
    if not nsap_rows:
        return flags

    ns = [dict(r) for r in nsap_rows]
    total_paid = sum(r["beneficiaries_paid"] for r in ns)
    total_eligible = sum(r["beneficiaries_eligible"] for r in ns)
    if total_paid == 0 and total_eligible == 0:
        if verbose:
            flags.append("NSAP: both beneficiaries_paid and beneficiaries_eligible are zero (data quality issue)")
        else:
            flags.append("NSAP: no beneficiary data")

    return flags


def nfsa_flags(nfsa: sqlite3.Row | None, verbose: bool) -> list[str]:
    flags: list[str] = []
    if not nfsa:
        return flags

    nf = dict(nfsa)
    if nf["allocation_mt"] > 0 and nf["offtake_pct"] < 50:
        if verbose:
            flags.append(
                f"NFSA low offtake: only {pct(nf['offtake_pct'])} of allocated grain distributed "
                f"({nf['offtake_mt']:,.1f}/{nf['allocation_mt']:,.1f} MT)"
            )
        else:
            flags.append(f"NFSA offtake {pct(nf['offtake_pct'])}")
    if nf["ration_cards_total"] > 0:
        active_pct = nf["ration_cards_active"] / nf["ration_cards_total"] * 100
        if active_pct < 60:
            if verbose:
                flags.append(
                    f"NFSA low active cards: only {pct(active_pct)} of ration cards active "
                    f"({nf['ration_cards_active']:,}/{nf['ration_cards_total']:,})"
                )
            else:
                flags.append(f"NFSA active cards {pct(active_pct)}")

    return flags


def cross_scheme_flags(
    fin: sqlite3.Row | None,
    pmgsy_rows: list[sqlite3.Row],
    pmayg: sqlite3.Row | None,
    jjm: sqlite3.Row | None,
    poshan: sqlite3.Row | None,
    nfsa: sqlite3.Row | None,
    total_sanctioned: int,
    total_completed: int,
    verbose: bool,
) -> list[str]:
    flags: list[str] = []

    # MGNREGA + PMGSY cross-reference
    if fin and pmgsy_rows:
        f_dict = dict(fin)
        if (
            f_dict.get("cumulative_expenditure", 0) > 0
            and total_sanctioned > 0
            and total_completed / total_sanctioned < 0.5
            and f_dict["utilization_pct"] > 80
        ):
            if verbose:
                flags.append(
                    f"Cross-scheme anomaly: MGNREGA utilization is high ({pct(f_dict['utilization_pct'])}) "
                    f"but PMGSY road completion is low ({total_completed}/{total_sanctioned} roads)"
                )
            else:
                flags.append("High MGNREGA spend, low PMGSY roads")

    # MGNREGA + PMAY-G
    if fin and pmayg:
        f_dict = dict(fin)
        h_dict = dict(pmayg)
        if f_dict["utilization_pct"] > 80 and h_dict["houses_sanctioned"] > 0 and h_dict["completion_pct"] < 40:
            if verbose:
                flags.append(
                    f"Cross-scheme: high MGNREGA spend ({pct(f_dict['utilization_pct'])}) "
                    f"but low housing completion ({pct(h_dict['completion_pct'])})"
                )
            else:
                flags.append("High MGNREGA, low PMAY-G")

    # JJM + PM POSHAN infrastructure gap
    if jjm and poshan:
        j_dict = dict(jjm)
        p_dict = dict(poshan)
        low_water = j_dict["total_households"] > 0 and j_dict["coverage_pct"] < 40
        low_meals = (
            p_dict["children_enrolled"] > 0 and (p_dict["children_fed"] / p_dict["children_enrolled"] * 100) < 40
        )
        if low_water and low_meals:
            if verbose:
                flags.append(
                    f"Infrastructure gap: both water ({pct(j_dict['coverage_pct'])}) and "
                    f"school meals (<40% coverage) are low \u2014 possible systemic delivery failure"
                )
            else:
                flags.append("Low water + low meals")

    # Multi-scheme underperformance
    low_count = _count_low_delivery(fin, pmgsy_rows, pmayg, jjm, poshan, nfsa, total_sanctioned, total_completed)
    if low_count >= 3:
        if verbose:
            flags.append(f"Multi-scheme underperformance: {low_count} schemes showing <50% delivery in this district")
        else:
            flags.append(f"{low_count} schemes <50% delivery")

    return flags


def _count_low_delivery(
    fin: sqlite3.Row | None,
    pmgsy_rows: list[sqlite3.Row],
    pmayg: sqlite3.Row | None,
    jjm: sqlite3.Row | None,
    poshan: sqlite3.Row | None,
    nfsa: sqlite3.Row | None,
    total_sanctioned: int,
    total_completed: int,
) -> int:
    count = 0
    if pmgsy_rows and total_sanctioned > 0 and total_completed / total_sanctioned < 0.5:
        count += 1
    if pmayg and dict(pmayg)["houses_sanctioned"] > 0 and dict(pmayg)["completion_pct"] < 50:
        count += 1
    if jjm and dict(jjm)["total_households"] > 0 and dict(jjm)["coverage_pct"] < 50:
        count += 1
    if (
        poshan
        and dict(poshan)["children_enrolled"] > 0
        and dict(poshan)["children_fed"] / dict(poshan)["children_enrolled"] < 0.5
    ):
        count += 1
    if nfsa and dict(nfsa)["offtake_pct"] < 50:
        count += 1
    if fin and dict(fin)["utilization_pct"] < 50:
        count += 1
    return count
