"""Tests for cross-scheme DB architecture and money_flow queries.

Covers: unified schema, new scheme loaders, money_flow VIEW, cross-scheme queries.
"""

from __future__ import annotations

import sqlite3

import pytest

from db import init_db

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class NoCloseConn:
    """Wraps a connection but ignores close() calls."""

    def __init__(self, real_conn: sqlite3.Connection):
        self._conn = real_conn

    def execute(self, *a, **kw):
        return self._conn.execute(*a, **kw)

    def close(self):
        pass

    @property
    def row_factory(self):
        return self._conn.row_factory

    @row_factory.setter
    def row_factory(self, val):
        self._conn.row_factory = val


@pytest.fixture
def db():
    """In-memory DB with full schema including money_flow VIEW."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


def _seed_multi_scheme(conn: sqlite3.Connection) -> None:
    """Insert test data across multiple scheme tables."""
    conn.execute(
        """INSERT INTO financial_statement
        (district, state, state_code, fin_year, total_availability, cumulative_expenditure,
         utilization_pct, balance, source_url, scraped_at)
        VALUES ('ALPHA', 'TESTSTATE', 'TS', '2024-2025', 5000, 4000, 80.0, 1000, 'src', '2026-01-01')"""
    )
    conn.execute(
        """INSERT INTO pmgsy_district
        (district, state, state_code, fin_year, scheme, roads_sanctioned, roads_completed,
         length_sanctioned_km, length_completed_km, habitations_covered,
         value_of_projects_cr, expenditure_cr, source_url, scraped_at)
        VALUES ('ALPHA', 'TestState', '', '2024-2025', 'PMGSY-I', 50, 40, 100, 80, 20, 10, 8, 'src', '2026-01-01')"""
    )
    conn.execute(
        """INSERT INTO pmayg_district
        (district, state, state_code, fin_year, houses_sanctioned, houses_completed,
         houses_occupied, funds_released_lakhs, funds_utilized_lakhs, completion_pct,
         source_url, scraped_at)
        VALUES ('ALPHA', 'TESTSTATE', 'TS', '2024-2025', 1000, 700, 600, 3000, 2100, 70.0, 'src', '2026-01-01')"""
    )
    conn.execute(
        """INSERT INTO jjm_district
        (district, state, state_code, fin_year, total_households, households_with_tap,
         tap_connections_provided, coverage_pct, funds_released_lakhs, funds_utilized_lakhs,
         source_url, scraped_at)
        VALUES ('ALPHA', 'TESTSTATE', 'TS', '2024-2025', 5000, 3500, 3500, 70.0, 2000, 1500, 'src', '2026-01-01')"""
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestSchema:
    def test_all_tables_created(self, db):
        tables = {
            r[0]
            for r in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name != 'sqlite_sequence'"
            ).fetchall()
        }
        expected = {
            "scrape_runs",
            "misappropriation",
            "fto_status",
            "fto_pendency",
            "issues_reported",
            "financial_statement",
            "pmgsy_progress",
            "pmgsy_district",
            "pmayg_district",
            "pmkisan_district",
            "jjm_district",
            "pmposhan_district",
            "nsap_district",
            "nfsa_district",
            "sbm_district",
            "nrlm_district",
            "udise_state",
            "pmposhan_finance",
            "nsap_finance",
            "nfsa_allocation",
            "jjm_allocation",
            "pmayg_finance",
        }
        assert expected.issubset(tables)

    def test_money_flow_view_exists(self, db):
        views = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='view'").fetchall()]
        assert "money_flow" in views

    def test_money_flow_columns(self, db):
        info = db.execute("PRAGMA table_info(money_flow)").fetchall()
        cols = [r[1] for r in info]
        assert "scheme" in cols
        assert "allocated_lakhs" in cols
        assert "units_label" in cols

    def test_idempotent_init(self, db):
        """Calling init_db twice should not error."""
        init_db(db)
        tables = db.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
        assert tables > 0


# ---------------------------------------------------------------------------
# Loader tests for new scheme tables
# ---------------------------------------------------------------------------


class TestNewLoaders:
    def test_load_pmayg(self, db):
        from db import load_pmayg_district

        records = [
            {
                "district": "PATNA",
                "state": "Bihar",
                "state_code": "05",
                "houses_sanctioned": 2000,
                "houses_completed": 1500,
                "houses_occupied": 1200,
                "funds_released_lakhs": 5000,
                "funds_utilized_lakhs": 3500,
                "completion_pct": 75.0,
                "source_url": "test",
                "scraped_at": "2026-01-01",
            }
        ]
        count = load_pmayg_district(db, records, "2024-2025")
        db.commit()
        assert count == 1
        row = db.execute("SELECT * FROM pmayg_district").fetchone()
        assert row["houses_sanctioned"] == 2000
        assert row["funds_utilized_lakhs"] == 3500

    def test_load_pmkisan(self, db):
        from db import load_pmkisan_district

        records = [
            {
                "district": "PATNA",
                "state": "Bihar",
                "state_code": "05",
                "beneficiaries_registered": 50000,
                "beneficiaries_paid": 45000,
                "amount_paid_lakhs": 900,
                "beneficiaries_rejected": 1000,
                "installment": "17th",
                "source_url": "test",
                "scraped_at": "2026-01-01",
            }
        ]
        count = load_pmkisan_district(db, records, "2024-2025")
        db.commit()
        assert count == 1
        row = db.execute("SELECT * FROM pmkisan_district").fetchone()
        assert row["beneficiaries_paid"] == 45000

    def test_load_jjm(self, db):
        from db import load_jjm_district

        records = [
            {
                "district": "PATNA",
                "state": "Bihar",
                "state_code": "05",
                "total_households": 10000,
                "households_with_tap": 7000,
                "tap_connections_provided": 7000,
                "coverage_pct": 70.0,
                "funds_released_lakhs": 3000,
                "funds_utilized_lakhs": 2100,
                "source_url": "test",
                "scraped_at": "2026-01-01",
            }
        ]
        count = load_jjm_district(db, records, "2024-2025")
        db.commit()
        assert count == 1
        row = db.execute("SELECT * FROM jjm_district").fetchone()
        assert row["coverage_pct"] == 70.0

    def test_load_pmposhan(self, db):
        from db import load_pmposhan_district

        records = [
            {
                "district": "PATNA",
                "state": "Bihar",
                "state_code": "05",
                "schools_covered": 500,
                "children_enrolled": 25000,
                "children_fed": 22000,
                "funds_released_lakhs": 1200,
                "funds_utilized_lakhs": 1000,
                "utilization_pct": 83.3,
                "source_url": "test",
                "scraped_at": "2026-01-01",
            }
        ]
        count = load_pmposhan_district(db, records, "2024-2025")
        db.commit()
        assert count == 1
        row = db.execute("SELECT * FROM pmposhan_district").fetchone()
        assert row["children_fed"] == 22000

    def test_load_nsap(self, db):
        from db import load_nsap_district

        records = [
            {
                "district": "PATNA",
                "state": "Bihar",
                "state_code": "05",
                "scheme_type": "IGNOAPS",
                "beneficiaries_eligible": 8000,
                "beneficiaries_paid": 7500,
                "amount_paid_lakhs": 450,
                "pension_per_month": 500,
                "source_url": "test",
                "scraped_at": "2026-01-01",
            }
        ]
        count = load_nsap_district(db, records, "2024-2025")
        db.commit()
        assert count == 1
        row = db.execute("SELECT * FROM nsap_district").fetchone()
        assert row["pension_per_month"] == 500

    def test_load_nfsa(self, db):
        from db import load_nfsa_district

        records = [
            {
                "district": "PATNA",
                "state": "Bihar",
                "state_code": "05",
                "ration_cards_total": 100000,
                "ration_cards_active": 85000,
                "allocation_mt": 5000,
                "offtake_mt": 4200,
                "offtake_pct": 84.0,
                "beneficiaries_total": 300000,
                "source_url": "test",
                "scraped_at": "2026-01-01",
            }
        ]
        count = load_nfsa_district(db, records, "2024-2025")
        db.commit()
        assert count == 1
        row = db.execute("SELECT * FROM nfsa_district").fetchone()
        assert row["offtake_pct"] == 84.0

    def test_upsert_replaces_pmayg(self, db):
        from db import load_pmayg_district

        rec = [
            {
                "district": "X",
                "state": "S",
                "houses_sanctioned": 100,
                "houses_completed": 50,
                "houses_occupied": 40,
                "funds_released_lakhs": 500,
                "funds_utilized_lakhs": 300,
                "completion_pct": 50.0,
                "source_url": "",
                "scraped_at": "2026-01-01",
            }
        ]
        load_pmayg_district(db, rec, "2024-2025")
        db.commit()
        rec[0]["houses_completed"] = 99
        load_pmayg_district(db, rec, "2024-2025")
        db.commit()
        rows = db.execute("SELECT * FROM pmayg_district").fetchall()
        assert len(rows) == 1
        assert rows[0]["houses_completed"] == 99


# ---------------------------------------------------------------------------
# money_flow VIEW tests
# ---------------------------------------------------------------------------


class TestMoneyFlowView:
    def test_cross_scheme_data_appears(self, db):
        _seed_multi_scheme(db)
        rows = db.execute("SELECT scheme FROM money_flow ORDER BY scheme").fetchall()
        schemes = [r["scheme"] for r in rows]
        assert "MGNREGA" in schemes
        assert "PMGSY" in schemes
        assert "PMAY-G" in schemes
        assert "JJM" in schemes

    def test_amounts_normalized_to_lakhs(self, db):
        _seed_multi_scheme(db)
        # PMGSY: expenditure_cr=8, so expended_lakhs should be 800
        row = db.execute("SELECT expended_lakhs FROM money_flow WHERE scheme='PMGSY'").fetchone()
        assert row["expended_lakhs"] == 800.0

    def test_units_populated(self, db):
        _seed_multi_scheme(db)
        row = db.execute(
            "SELECT units_target, units_completed, units_label FROM money_flow WHERE scheme='PMAY-G'"
        ).fetchone()
        assert row["units_label"] == "houses"
        assert row["units_target"] == 1000
        assert row["units_completed"] == 700

    def test_mgnrega_no_units(self, db):
        _seed_multi_scheme(db)
        row = db.execute("SELECT units_label FROM money_flow WHERE scheme='MGNREGA'").fetchone()
        assert row["units_label"] is None


# ---------------------------------------------------------------------------
# Cross-scheme query tests
# ---------------------------------------------------------------------------


class TestCrossSchemeQueries:
    @staticmethod
    def _patch(db, monkeypatch):
        import query

        monkeypatch.setattr(query, "_conn", lambda: NoCloseConn(db))

    def test_money_flow_by_district(self, db, monkeypatch):
        _seed_multi_scheme(db)
        self._patch(db, monkeypatch)
        import query

        result = query.money_flow_by_district("ALPHA")
        assert "answer" in result
        assert result["data"] is not None
        assert "MGNREGA" in result["answer"]
        assert "PMAY-G" in result["answer"]
        assert "TOTAL" in result["answer"]

    def test_money_flow_by_district_with_state(self, db, monkeypatch):
        _seed_multi_scheme(db)
        self._patch(db, monkeypatch)
        import query

        result = query.money_flow_by_district("ALPHA", state="TESTSTATE")
        # Should find MGNREGA and PMAY-G (both use TESTSTATE)
        assert result["data"] is not None
        schemes = {r["scheme"] for r in result["data"]}
        assert "MGNREGA" in schemes

    def test_money_flow_state_summary(self, db, monkeypatch):
        _seed_multi_scheme(db)
        self._patch(db, monkeypatch)
        import query

        result = query.money_flow_state_summary("TESTSTATE")
        assert "answer" in result
        assert "TOTAL" in result["answer"]

    def test_schemes_in_district(self, db, monkeypatch):
        _seed_multi_scheme(db)
        self._patch(db, monkeypatch)
        import query

        result = query.schemes_in_district("ALPHA")
        assert "MGNREGA" in result["data"]
        assert "PMAY-G" in result["data"]

    def test_no_data_returns_message(self, db, monkeypatch):
        self._patch(db, monkeypatch)
        import query

        result = query.money_flow_by_district("NONEXISTENT")
        assert "No data" in result["answer"]
        assert result["data"] is None


# ---------------------------------------------------------------------------
# scheme_delivery VIEW tests for new schemes
# ---------------------------------------------------------------------------

_SBM_INSERT = """
    INSERT INTO sbm_district
        (district, state, state_code, fin_year, total_villages, odf_plus_villages,
         odf_plus_pct, one_star_villages, three_star_villages, five_star_villages,
         model_village_pct, source_url, scraped_at)
    VALUES ('ALPHA', 'TESTSTATE', 'TS', '2024-2025', 100, 60, 60.0,
            20, 10, 30, 30.0, 'src', '2026-01-01')
"""

_NRLM_INSERT = """
    INSERT INTO nrlm_district
        (district, state, state_code, fin_year, shgs_total, shgs_new, shgs_revived,
         shgs_pre_nrlm, members_total, rf_shgs_provided, rf_amount_lakhs,
         source_url, scraped_at)
    VALUES ('ALPHA', 'TESTSTATE', 'TS', '2024-2025', 5000, 2000, 1000,
            2000, 60000, 3000, 150.0, 'src', '2026-01-01')
"""

_UDISE_INSERT = """
    INSERT INTO udise_state
        (state, fin_year, total_schools, schools_govt, total_students, total_teachers,
         ptr_primary, ger_primary, dropout_primary, schools_electricity_pct,
         source_url, scraped_at)
    VALUES ('TESTSTATE', '2024-2025', 85000, 45000, 8500000, 450000,
            25.3, 98.5, 1.2, 85.3, 'src', '2026-01-01')
"""


class TestSchemeDeliveryNewSchemes:
    def test_sbm_in_delivery(self, db):
        db.execute(_SBM_INSERT)
        db.commit()
        row = db.execute(
            "SELECT * FROM scheme_delivery WHERE scheme='SBM-G' AND district='ALPHA'"
        ).fetchone()
        assert row is not None
        assert row["units_label"] == "ODF+ villages"
        assert row["units_target"] == 100
        assert row["units_completed"] == 60

    def test_nrlm_in_delivery(self, db):
        db.execute(_NRLM_INSERT)
        db.commit()
        row = db.execute(
            "SELECT * FROM scheme_delivery WHERE scheme='DAY-NRLM' AND district='ALPHA'"
        ).fetchone()
        assert row is not None
        assert row["units_label"] == "SHGs"
        assert row["units_completed"] == 5000

    def test_udise_in_delivery(self, db):
        db.execute(_UDISE_INSERT)
        db.commit()
        row = db.execute(
            "SELECT * FROM scheme_delivery WHERE scheme='UDISE+' AND state='TESTSTATE'"
        ).fetchone()
        assert row is not None
        assert row["units_label"] == "schools"
        assert row["units_completed"] == 85000


# ---------------------------------------------------------------------------
# money_flow VIEW tests for new schemes
# ---------------------------------------------------------------------------


class TestMoneyFlowNewSchemes:
    def test_nrlm_in_money_flow(self, db):
        db.execute(_NRLM_INSERT)
        db.commit()
        row = db.execute(
            "SELECT * FROM money_flow WHERE scheme='DAY-NRLM' AND district='ALPHA'"
        ).fetchone()
        assert row is not None
        assert row["released_lakhs"] == 150.0
        assert row["units_label"] == "SHGs"


# ---------------------------------------------------------------------------
# scheme_finance VIEW tests for JJM crore-to-lakh conversion
# ---------------------------------------------------------------------------


class TestJJMAllocationFinancialFlow:
    def test_jjm_crores_to_lakhs(self, db):
        db.execute(
            """
            INSERT INTO jjm_allocation
                (state, fin_year, allocated_crores, released_crores, expended_crores,
                 source_url, scraped_at)
            VALUES ('TESTSTATE', '2024-2025', 32.0, 28.0, 25.0, 'src', '2026-01-01')
            """
        )
        db.commit()
        row = db.execute(
            "SELECT * FROM scheme_finance WHERE scheme='JJM' AND state='TESTSTATE'"
        ).fetchone()
        assert row is not None
        assert row["allocated_lakhs"] == 3200.0
        assert row["released_lakhs"] == 2800.0
        assert row["expended_lakhs"] == 2500.0
