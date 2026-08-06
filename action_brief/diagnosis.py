"""Template-based diagnosis engine — queries scheme tables, returns DiagnosisItem list.

No LLM. Purely deterministic threshold checks. Each helper returns 0 or 1 DiagnosisItem.
"""

from __future__ import annotations

import sqlite3

from action_brief.models import DiagnosisItem
from briefs.formatting import FIN_YEAR

_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def _check_mgnrega_recovery(
    conn: sqlite3.Connection, district: str, state: str
) -> list[DiagnosisItem]:
    row = conn.execute(
        """SELECT * FROM misappropriation
           WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?
           ORDER BY scraped_at DESC LIMIT 1""",
        (district, state, FIN_YEAR),
    ).fetchone()
    if not row:
        return []

    r = dict(row)
    rate = r.get("recovery_rate_pct", 0.0)
    if rate < 20:
        display = district.title()
        return [
            DiagnosisItem(
                severity="high",
                scheme="MGNREGA",
                summary=f"Only {rate:.1f}% of misappropriated MGNREGA funds have been recovered in {display}.",
                detail=(
                    f"{r['cases_reported']} cases reported; "
                    f"₹{r['amount_reported']:.2f} lakh reported, "
                    f"₹{r['amount_recovered']:.2f} lakh recovered."
                ),
                amount=f"₹{r['amount_reported']:.2f} lakh",
                source_url=r.get("source_url") or "https://nrega.nic.in/",
            )
        ]
    return []


def _check_pmayg_completion(
    conn: sqlite3.Connection, district: str, state: str
) -> list[DiagnosisItem]:
    row = conn.execute(
        """SELECT * FROM pmayg_district
           WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?
           ORDER BY scraped_at DESC LIMIT 1""",
        (district, state, FIN_YEAR),
    ).fetchone()
    if not row:
        return []

    r = dict(row)
    pct = r.get("completion_pct", 0.0)
    if r.get("houses_sanctioned", 0) > 0 and pct < 50:
        display = district.title()
        return [
            DiagnosisItem(
                severity="medium",
                scheme="PMAY-G",
                summary=f"Less than half the sanctioned houses have been built in {display}.",
                detail=(
                    f"{r['houses_completed']:,} of {r['houses_sanctioned']:,} sanctioned houses completed "
                    f"({pct:.1f}%)."
                ),
                amount=None,
                source_url=r.get("source_url") or "https://pmayg.nic.in/",
            )
        ]
    return []


def _check_jjm_coverage(
    conn: sqlite3.Connection, district: str, state: str
) -> list[DiagnosisItem]:
    row = conn.execute(
        """SELECT * FROM jjm_district
           WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?)
           ORDER BY scraped_at DESC LIMIT 1""",
        (district, state),
    ).fetchone()
    if not row:
        return []

    r = dict(row)
    pct = r.get("coverage_pct", 0.0)
    if r.get("total_households", 0) > 0 and pct < 50:
        display = district.title()
        return [
            DiagnosisItem(
                severity="medium",
                scheme="JJM",
                summary=f"Less than half the households in {display} have tap water connections.",
                detail=(
                    f"{r['households_with_tap']:,} of {r['total_households']:,} households connected "
                    f"({pct:.1f}%)."
                ),
                amount=None,
                source_url=r.get("source_url") or "https://ejalshakti.gov.in/",
            )
        ]
    return []


def _check_pmgsy_completion(
    conn: sqlite3.Connection, district: str, state: str
) -> list[DiagnosisItem]:
    rows = conn.execute(
        """SELECT * FROM pmgsy_district
           WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?)""",
        (district, state),
    ).fetchall()
    if not rows:
        return []

    total_sanctioned = sum(dict(r).get("roads_sanctioned", 0) for r in rows)
    total_completed = sum(dict(r).get("roads_completed", 0) for r in rows)
    if total_sanctioned <= 0:
        return []

    completion_pct = total_completed / total_sanctioned * 100
    if completion_pct < 50:
        pending = total_sanctioned - total_completed
        display = district.title()
        source_url = dict(rows[0]).get("source_url") or "https://pmgsy.nic.in/"
        return [
            DiagnosisItem(
                severity="medium",
                scheme="PMGSY",
                summary=f"{pending} sanctioned roads in {display} are still incomplete.",
                detail=(
                    f"{total_completed} of {total_sanctioned} sanctioned roads completed "
                    f"({completion_pct:.1f}%)."
                ),
                amount=None,
                source_url=source_url,
            )
        ]
    return []


def _check_pmposhan_feeding(
    conn: sqlite3.Connection, district: str, state: str
) -> list[DiagnosisItem]:
    row = conn.execute(
        """SELECT * FROM pmposhan_district
           WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?
           ORDER BY scraped_at DESC LIMIT 1""",
        (district, state, FIN_YEAR),
    ).fetchone()
    if not row:
        return []

    r = dict(row)
    enrolled = r.get("children_enrolled", 0)
    fed = r.get("children_fed", 0)
    if enrolled <= 0:
        return []

    feeding_pct = fed / enrolled * 100
    if feeding_pct < 60:
        display = district.title()
        return [
            DiagnosisItem(
                severity="medium",
                scheme="PM POSHAN",
                summary=(
                    f"Only {feeding_pct:.1f}% of enrolled children in {display} "
                    f"are being fed under the mid-day meal scheme."
                ),
                detail=f"{fed:,} of {enrolled:,} enrolled children are receiving meals.",
                amount=None,
                source_url=r.get("source_url") or "https://pmposhan.education.gov.in/",
            )
        ]
    return []


def _check_nfsa_offtake(
    conn: sqlite3.Connection, district: str, state: str
) -> list[DiagnosisItem]:
    row = conn.execute(
        """SELECT * FROM nfsa_district
           WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?
           ORDER BY scraped_at DESC LIMIT 1""",
        (district, state, FIN_YEAR),
    ).fetchone()
    if not row:
        return []

    r = dict(row)
    offtake_pct = r.get("offtake_pct", 0.0)
    if r.get("allocation_mt", 0) > 0 and offtake_pct < 50:
        display = district.title()
        return [
            DiagnosisItem(
                severity="medium",
                scheme="PDS/NFSA",
                summary=f"Only {offtake_pct:.1f}% of allocated grain has been distributed in {display}.",
                detail=(
                    f"{r['offtake_mt']:.1f} of {r['allocation_mt']:.1f} MT allocated "
                    f"grain distributed."
                ),
                amount=None,
                source_url=r.get("source_url") or "https://nfsa.gov.in/",
            )
        ]
    return []


def _check_nsap_coverage(
    conn: sqlite3.Connection, district: str, state: str
) -> list[DiagnosisItem]:
    rows = conn.execute(
        """SELECT * FROM nsap_district
           WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?""",
        (district, state, FIN_YEAR),
    ).fetchall()
    if not rows:
        return []

    total_paid = sum(dict(r).get("beneficiaries_paid", 0) for r in rows)
    total_eligible = sum(dict(r).get("beneficiaries_eligible", 0) for r in rows)
    if total_eligible <= 0:
        return []

    coverage_pct = total_paid / total_eligible * 100
    if coverage_pct < 50:
        display = district.title()
        source_url = dict(rows[0]).get("source_url") or "https://nsap.nic.in/"
        return [
            DiagnosisItem(
                severity="medium",
                scheme="NSAP",
                summary=(
                    f"Only {total_paid:,} out of {total_eligible:,} eligible pensioners "
                    f"received payments in {display}."
                ),
                detail=f"Payment coverage: {coverage_pct:.1f}% of eligible beneficiaries.",
                amount=None,
                source_url=source_url,
            )
        ]
    return []


def _check_mgnrega_complaints(
    conn: sqlite3.Connection, district: str, state: str
) -> list[DiagnosisItem]:
    row = conn.execute(
        """SELECT * FROM issues_reported
           WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?
           ORDER BY scraped_at DESC LIMIT 1""",
        (district, state, FIN_YEAR),
    ).fetchone()
    if not row:
        return []

    r = dict(row)
    total_issues = r.get("total_issues", 0)
    if total_issues > 100:
        display = district.title()
        return [
            DiagnosisItem(
                severity="low",
                scheme="MGNREGA",
                summary=(
                    f"{total_issues:,} complaints have been filed against MGNREGA "
                    f"implementation in {display}."
                ),
                detail=(
                    f"Issues breakdown — misappropriation: {r['misappropriation_issues']}, "
                    f"process violations: {r['process_violation_issues']}, "
                    f"grievances: {r['grievances_issues']}."
                ),
                amount=None,
                source_url=r.get("source_url") or "https://nrega.nic.in/",
            )
        ]
    return []


# Each diagnosable scheme and the district tables its checkers read. An empty
# diagnosis means "nothing wrong" only if at least one of these had a row —
# urban districts report none of them. Twin of the schemesChecked set in
# web/src/lib/action-brief.ts.
_DIAGNOSABLE_TABLES: dict[str, tuple[str, ...]] = {
    "MGNREGA": ("misappropriation", "issues_reported"),
    "PMAY-G": ("pmayg_district",),
    "JJM": ("jjm_district",),
    "PMGSY": ("pmgsy_district",),
    "PM POSHAN": ("pmposhan_district",),
    "PDS/NFSA": ("nfsa_district",),
    "NSAP": ("nsap_district",),
}


def schemes_with_district_data(
    conn: sqlite3.Connection, district: str, state: str
) -> list[str]:
    """Return the diagnosable schemes that report any row for this district."""
    found: list[str] = []
    for scheme, tables in _DIAGNOSABLE_TABLES.items():
        for table in tables:
            row = conn.execute(
                f"""SELECT 1 FROM {table}
                   WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?)
                   LIMIT 1""",
                (district, state),
            ).fetchone()
            if row:
                found.append(scheme)
                break
    return found


def build_diagnosis(
    conn: sqlite3.Connection, district: str, state: str
) -> list[DiagnosisItem]:
    """Query each scheme table and return up to 5 DiagnosisItems sorted by severity."""
    all_items: list[DiagnosisItem] = []

    checkers = [
        _check_mgnrega_recovery,
        _check_pmayg_completion,
        _check_jjm_coverage,
        _check_pmgsy_completion,
        _check_pmposhan_feeding,
        _check_nfsa_offtake,
        _check_nsap_coverage,
        _check_mgnrega_complaints,
    ]

    for checker in checkers:
        all_items.extend(checker(conn, district, state))

    all_items.sort(key=lambda item: _SEVERITY_ORDER[item.severity])
    return all_items[:5]
