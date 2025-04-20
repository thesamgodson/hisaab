"""Data integrity tests against the real database at data/hisaab.db.

All tests are skipped if the database file does not exist. Tests validate
invariants that the loaders and VIEWs must uphold: no NULLs in key columns,
correct scheme presence/absence, no duplicate rows, and cross-table state
name consistency.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "hisaab.db"
pytestmark = pytest.mark.skipif(
    not DB_PATH.exists(), reason=f"Database not found at {DB_PATH}"
)


@pytest.fixture(scope="module")
def db():
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# TestMoneyFlow
# ---------------------------------------------------------------------------


class TestMoneyFlow:
    def test_no_null_schemes(self, db):
        (count,) = db.execute(
            "SELECT COUNT(*) FROM money_flow WHERE scheme IS NULL"
        ).fetchone()
        assert count == 0


# ---------------------------------------------------------------------------
# TestSchemeDelivery
# ---------------------------------------------------------------------------

_EXPECTED_DELIVERY_SCHEMES = {
    "DAY-NRLM",
    "JJM",
    "NSAP",
    "PDS/NFSA",
    "PM Kisan",
    "PM POSHAN",
    "PMAY-G",
    "PMGSY",
    "SBM-G",
    "UDISE+",
}


class TestSchemeDelivery:
    def test_schemes_present(self, db):
        rows = db.execute("SELECT DISTINCT scheme FROM scheme_delivery").fetchall()
        present = {r["scheme"] for r in rows}
        missing = _EXPECTED_DELIVERY_SCHEMES - present
        assert not missing, f"Missing schemes from scheme_delivery: {missing}"


# ---------------------------------------------------------------------------
# TestSchemeFinance
# ---------------------------------------------------------------------------


class TestSchemeFinance:
    def test_no_nfsa(self, db):
        """NFSA uses metric tonnes, not lakhs — must not appear in scheme_finance."""
        (count,) = db.execute(
            "SELECT COUNT(*) FROM scheme_finance WHERE scheme = 'PDS/NFSA'"
        ).fetchone()
        assert count == 0

    def test_mgnrega_no_allocation(self, db):
        """MGNREGA and PMGSY have no allocated_lakhs column in scheme_finance."""
        (count,) = db.execute(
            """
            SELECT COUNT(*) FROM scheme_finance
            WHERE scheme IN ('MGNREGA', 'PMGSY')
              AND allocated_lakhs IS NOT NULL
            """
        ).fetchone()
        assert count == 0

    def test_jjm_has_release_and_expenditure(self, db):
        """JJM allocation table must have at least one row with released_lakhs > 0."""
        (count,) = db.execute(
            "SELECT COUNT(*) FROM scheme_finance WHERE scheme = 'JJM' AND released_lakhs > 0"
        ).fetchone()
        assert count > 0


# ---------------------------------------------------------------------------
# TestMGNREGA
# ---------------------------------------------------------------------------


class TestMGNREGA:
    def test_not_in_scheme_delivery(self, db):
        """MGNREGA has no delivery units in the schema — must not appear in scheme_delivery."""
        (count,) = db.execute(
            "SELECT COUNT(*) FROM scheme_delivery WHERE scheme = 'MGNREGA'"
        ).fetchone()
        assert count == 0


# ---------------------------------------------------------------------------
# TestNoDuplicates
# ---------------------------------------------------------------------------

_DUPLICATE_CASES = [
    ("sbm_district", "district, state, fin_year"),
    ("nrlm_district", "district, state, fin_year"),
    ("udise_state", "state, fin_year"),
    ("jjm_allocation", "state, fin_year"),
    ("pmayg_finance", "state, fin_year"),
    ("pmposhan_finance", "state, fin_year"),
    ("nsap_finance", "state, fin_year"),
    ("nfsa_allocation", "state, fin_year, grain_type"),
]


class TestNoDuplicates:
    @pytest.mark.parametrize("table,keys", _DUPLICATE_CASES)
    def test_no_duplicate_rows(self, db, table: str, keys: str):
        rows = db.execute(
            f"SELECT {keys}, COUNT(*) AS cnt FROM {table} GROUP BY {keys} HAVING cnt > 1"
        ).fetchall()
        assert len(rows) == 0, (
            f"Duplicate rows in {table} on ({keys}): "
            + ", ".join(str(dict(r)) for r in rows[:5])
        )


# ---------------------------------------------------------------------------
# TestStateNameConsistency
# ---------------------------------------------------------------------------


class TestStateNameConsistency:
    def test_sbm_states_exist_elsewhere(self, db):
        """Every state in sbm_district should appear in at least one other scheme table.

        Uses EXCEPT to find states present in sbm_district but absent from all
        four reference tables: financial_statement, jjm_district, pmayg_district,
        nrlm_district.
        """
        orphan_rows = db.execute(
            """
            SELECT DISTINCT state FROM sbm_district
            EXCEPT
            SELECT DISTINCT state FROM financial_statement
            EXCEPT
            SELECT DISTINCT state FROM jjm_district
            EXCEPT
            SELECT DISTINCT state FROM pmayg_district
            EXCEPT
            SELECT DISTINCT state FROM nrlm_district
            """
        ).fetchall()
        orphan_states = [r["state"] for r in orphan_rows]
        assert not orphan_states, (
            f"States in sbm_district not found in any reference table: {orphan_states}"
        )
