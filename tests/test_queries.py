"""Tests for new scheme query functions (PMAY-G, PM Kisan, JJM, PM POSHAN, NSAP, NFSA).

Each test: seed in-memory DB, monkeypatch _conn, call function, assert response structure + values.
"""

from __future__ import annotations

import sqlite3

import pytest

from db import init_db


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
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


@pytest.fixture
def patch_conn(db, monkeypatch):
    import query

    monkeypatch.setattr(query, "_conn", lambda: NoCloseConn(db))
    return db


# ---------------------------------------------------------------------------
# PMAY-G
# ---------------------------------------------------------------------------


class TestPMAYGQueries:
    @staticmethod
    def _seed(db):
        db.execute(
            """INSERT INTO pmayg_district
            (district, state, state_code, fin_year, houses_sanctioned, houses_completed,
             houses_occupied, funds_released_lakhs, funds_utilized_lakhs, completion_pct,
             source_url, scraped_at)
            VALUES ('PATNA', 'BIHAR', '05', '2024-2025', 2000, 1500, 1200, 5000, 3500, 75.0, 'src', '2026-01-01')"""
        )
        db.execute(
            """INSERT INTO pmayg_district
            (district, state, state_code, fin_year, houses_sanctioned, houses_completed,
             houses_occupied, funds_released_lakhs, funds_utilized_lakhs, completion_pct,
             source_url, scraped_at)
            VALUES ('GAYA', 'BIHAR', '05', '2024-2025', 1000, 200, 100, 2000, 800, 20.0, 'src', '2026-01-01')"""
        )
        db.commit()

    def test_by_district(self, patch_conn):
        self._seed(patch_conn)
        import query

        result = query.pmayg_by_district("PATNA", "BIHAR")
        assert result["data"] is not None
        assert result["data"]["houses_sanctioned"] == 2000
        assert "75%" in result["answer"]

    def test_by_district_no_data(self, patch_conn):
        import query

        result = query.pmayg_by_district("NONEXISTENT", "BIHAR")
        assert result["data"] is None

    def test_state_summary(self, patch_conn):
        self._seed(patch_conn)
        import query

        result = query.pmayg_state_summary("BIHAR")
        assert result["data"]["districts"] == 2
        assert result["data"]["sanctioned"] == 3000

    def test_worst_completion(self, patch_conn):
        self._seed(patch_conn)
        import query

        result = query.pmayg_worst_completion("BIHAR", limit=2)
        assert len(result["data"]) == 2
        assert result["data"][0]["district"] == "GAYA"  # lowest completion


# ---------------------------------------------------------------------------
# PM Kisan
# ---------------------------------------------------------------------------


class TestPMKisanQueries:
    @staticmethod
    def _seed(db):
        db.execute(
            """INSERT INTO pmkisan_district
            (district, state, state_code, fin_year, beneficiaries_registered,
             beneficiaries_paid, amount_paid_lakhs, beneficiaries_rejected,
             installment, source_url, scraped_at)
            VALUES ('PATNA', 'BIHAR', '05', '2024-2025', 50000, 45000, 900, 1000,
                    '17th', 'src', '2026-01-01')"""
        )
        db.execute(
            """INSERT INTO pmkisan_district
            (district, state, state_code, fin_year, beneficiaries_registered,
             beneficiaries_paid, amount_paid_lakhs, beneficiaries_rejected,
             installment, source_url, scraped_at)
            VALUES ('ALL', 'BIHAR', '05', '2024-2025', 100000, 20000, 400, 500,
                    '17th', 'src', '2026-01-01')"""
        )
        db.commit()

    def test_by_district(self, patch_conn):
        self._seed(patch_conn)
        import query

        result = query.pmkisan_by_district("PATNA", "BIHAR")
        assert result["data"] is not None
        assert "45,000" in result["answer"] or "45000" in result["answer"].replace(",", "")

    def test_state_summary(self, patch_conn):
        self._seed(patch_conn)
        import query

        result = query.pmkisan_state_summary("BIHAR")
        assert result["data"]["districts"] == 2

    def test_worst_coverage_excludes_all(self, patch_conn):
        self._seed(patch_conn)
        import query

        result = query.pmkisan_worst_coverage("BIHAR", limit=5)
        # "ALL" district should be excluded
        districts = [r["district"] for r in result["data"]]
        assert "ALL" not in districts


# ---------------------------------------------------------------------------
# JJM
# ---------------------------------------------------------------------------


class TestJJMQueries:
    @staticmethod
    def _seed(db):
        db.execute(
            """INSERT INTO jjm_district
            (district, state, state_code, fin_year, total_households, households_with_tap,
             tap_connections_provided, coverage_pct, funds_released_lakhs, funds_utilized_lakhs,
             source_url, scraped_at)
            VALUES ('PATNA', 'BIHAR', '05', 'cumulative', 10000, 7000, 7000, 70.0,
                    3000, 2100, 'src', '2026-01-01')"""
        )
        db.commit()

    def test_by_district(self, patch_conn):
        self._seed(patch_conn)
        import query

        result = query.jjm_by_district("PATNA", "BIHAR")
        assert result["data"]["coverage_pct"] == 70.0
        assert "70%" in result["answer"]

    def test_state_summary(self, patch_conn):
        self._seed(patch_conn)
        import query

        result = query.jjm_state_summary("BIHAR")
        assert result["data"]["districts"] == 1
        assert result["data"]["tapped"] == 7000

    def test_worst_coverage(self, patch_conn):
        self._seed(patch_conn)
        import query

        result = query.jjm_worst_coverage("BIHAR")
        assert len(result["data"]) == 1


# ---------------------------------------------------------------------------
# PM POSHAN
# ---------------------------------------------------------------------------


class TestPMPOSHANQueries:
    @staticmethod
    def _seed(db):
        db.execute(
            """INSERT INTO pmposhan_district
            (district, state, state_code, fin_year, schools_covered, children_enrolled,
             children_fed, funds_released_lakhs, funds_utilized_lakhs, utilization_pct,
             source_url, scraped_at)
            VALUES ('PATNA', 'BIHAR', '05', '2024-2025', 500, 25000, 22000,
                    1200, 1000, 83.3, 'src', '2026-01-01')"""
        )
        db.commit()

    def test_by_district(self, patch_conn):
        self._seed(patch_conn)
        import query

        result = query.pmposhan_by_district("PATNA", "BIHAR")
        assert result["data"]["children_fed"] == 22000
        assert "88%" in result["answer"]  # 22000/25000

    def test_state_summary(self, patch_conn):
        self._seed(patch_conn)
        import query

        result = query.pmposhan_state_summary("BIHAR")
        assert result["data"]["fed"] == 22000

    def test_worst_feeding(self, patch_conn):
        self._seed(patch_conn)
        import query

        result = query.pmposhan_worst_feeding("BIHAR")
        assert len(result["data"]) == 1


# ---------------------------------------------------------------------------
# NSAP
# ---------------------------------------------------------------------------


class TestNSAPQueries:
    @staticmethod
    def _seed(db):
        db.execute(
            """INSERT INTO nsap_district
            (district, state, state_code, fin_year, scheme_type, beneficiaries_eligible,
             beneficiaries_paid, amount_paid_lakhs, pension_per_month, source_url, scraped_at)
            VALUES ('PATNA', 'BIHAR', '05', '2024-2025', 'IGNOAPS', 8000, 7500,
                    450, 500, 'src', '2026-01-01')"""
        )
        db.execute(
            """INSERT INTO nsap_district
            (district, state, state_code, fin_year, scheme_type, beneficiaries_eligible,
             beneficiaries_paid, amount_paid_lakhs, pension_per_month, source_url, scraped_at)
            VALUES ('PATNA', 'BIHAR', '05', '2024-2025', 'IGNWPS', 2000, 1800,
                    100, 300, 'src', '2026-01-01')"""
        )
        db.commit()

    def test_by_district(self, patch_conn):
        self._seed(patch_conn)
        import query

        result = query.nsap_by_district("PATNA", "BIHAR")
        assert len(result["data"]) == 2
        assert "9,300" in result["answer"] or "9300" in result["answer"].replace(",", "")

    def test_state_summary(self, patch_conn):
        self._seed(patch_conn)
        import query

        result = query.nsap_state_summary("BIHAR")
        assert result["data"]["total_paid"] == 9300

    def test_worst_coverage(self, patch_conn):
        self._seed(patch_conn)
        import query

        result = query.nsap_worst_coverage("BIHAR")
        assert len(result["data"]) == 1


# ---------------------------------------------------------------------------
# NFSA
# ---------------------------------------------------------------------------


class TestNFSAQueries:
    @staticmethod
    def _seed(db):
        db.execute(
            """INSERT INTO nfsa_district
            (district, state, state_code, fin_year, ration_cards_total, ration_cards_active,
             allocation_mt, offtake_mt, offtake_pct, beneficiaries_total,
             source_url, scraped_at)
            VALUES ('PATNA', 'BIHAR', '05', '2024-2025', 100000, 85000,
                    5000, 4200, 84.0, 300000, 'src', '2026-01-01')"""
        )
        db.commit()

    def test_by_district(self, patch_conn):
        self._seed(patch_conn)
        import query

        result = query.nfsa_by_district("PATNA", "BIHAR")
        assert result["data"]["offtake_pct"] == 84.0
        assert "84%" in result["answer"]

    def test_state_summary(self, patch_conn):
        self._seed(patch_conn)
        import query

        result = query.nfsa_state_summary("BIHAR")
        assert result["data"]["total_cards"] == 100000

    def test_worst_coverage(self, patch_conn):
        self._seed(patch_conn)
        import query

        result = query.nfsa_worst_coverage("BIHAR")
        assert len(result["data"]) == 1


# ---------------------------------------------------------------------------
# Data quality warnings
# ---------------------------------------------------------------------------


class TestDataQualityWarnings:
    def test_returns_all_schemes(self):
        import query

        warnings = query.data_quality_warnings()
        assert "PM Kisan" in warnings
        assert "NSAP" in warnings
        assert "PDS/NFSA" in warnings
        assert "PM POSHAN" in warnings

    def test_warnings_are_non_empty(self):
        import query

        warnings = query.data_quality_warnings()
        for scheme, issues in warnings.items():
            assert len(issues) > 0, f"{scheme} has no warnings"


# ---------------------------------------------------------------------------
# list_districts across all tables
# ---------------------------------------------------------------------------


class TestListDistricts:
    def test_includes_new_scheme_districts(self, patch_conn):
        patch_conn.execute(
            """INSERT INTO jjm_district
            (district, state, state_code, fin_year, total_households, households_with_tap,
             tap_connections_provided, coverage_pct, funds_released_lakhs, funds_utilized_lakhs,
             source_url, scraped_at)
            VALUES ('UNIQUE_JJM', 'TESTSTATE', 'TS', '2024-2025', 100, 50, 50, 50.0,
                    100, 80, 'src', '2026-01-01')"""
        )
        patch_conn.commit()
        import query

        districts = query.list_districts("TESTSTATE", "2024-2025")
        assert "UNIQUE_JJM" in districts


# ---------------------------------------------------------------------------
# New VIEWs
# ---------------------------------------------------------------------------


class TestNewViews:
    @staticmethod
    def _seed(db):
        db.execute(
            """INSERT INTO financial_statement
            (district, state, state_code, fin_year, total_availability, cumulative_expenditure,
             utilization_pct, balance, source_url, scraped_at)
            VALUES ('ALPHA', 'TESTSTATE', 'TS', '2024-2025', 5000, 4000, 80.0, 1000, 'src', '2026-01-01')"""
        )
        db.execute(
            """INSERT INTO pmayg_district
            (district, state, state_code, fin_year, houses_sanctioned, houses_completed,
             houses_occupied, funds_released_lakhs, funds_utilized_lakhs, completion_pct,
             source_url, scraped_at)
            VALUES ('ALPHA', 'TESTSTATE', 'TS', '2024-2025', 1000, 700, 600, 3000, 2100, 70.0, 'src', '2026-01-01')"""
        )
        db.execute(
            """INSERT INTO nfsa_district
            (district, state, state_code, fin_year, ration_cards_total, ration_cards_active,
             allocation_mt, offtake_mt, offtake_pct, beneficiaries_total,
             source_url, scraped_at)
            VALUES ('ALPHA', 'TESTSTATE', 'TS', '2024-2025', 50000, 40000, 2000, 1600, 80.0, 150000, 'src', '2026-01-01')"""
        )
        db.commit()

    def test_scheme_finance_view_exists(self, db):
        views = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='view'").fetchall()]
        assert "scheme_finance" in views

    def test_scheme_delivery_view_exists(self, db):
        views = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='view'").fetchall()]
        assert "scheme_delivery" in views

    def test_scheme_finance_only_real_financial_data(self, db):
        self._seed(db)
        schemes = [r["scheme"] for r in db.execute("SELECT DISTINCT scheme FROM scheme_finance").fetchall()]
        assert "MGNREGA" in schemes
        # Excluded: zero-data schemes and non-rupee schemes
        assert "PDS/NFSA" not in schemes
        assert "PMAY-G" not in schemes  # financial data behind login/Power BI
        assert "JJM" not in schemes  # no financial API endpoint
        assert "PM POSHAN" not in schemes  # funds columns all zeros
        assert "NSAP" not in schemes  # all financial columns zeros

    def test_scheme_delivery_includes_all(self, db):
        self._seed(db)
        schemes = [r["scheme"] for r in db.execute("SELECT DISTINCT scheme FROM scheme_delivery").fetchall()]
        assert "MGNREGA" not in schemes  # removed: no delivery units in schema
        assert "PMAY-G" in schemes
        assert "PDS/NFSA" in schemes

    def test_scheme_finance_columns(self, db):
        info = db.execute("PRAGMA table_info(scheme_finance)").fetchall()
        cols = [r[1] for r in info]
        assert "allocated_lakhs" in cols
        assert "expended_lakhs" in cols
        assert "utilization_pct" in cols
        # Should NOT have units columns
        assert "units_target" not in cols
        assert "units_label" not in cols

    def test_scheme_delivery_columns(self, db):
        info = db.execute("PRAGMA table_info(scheme_delivery)").fetchall()
        cols = [r[1] for r in info]
        assert "units_target" in cols
        assert "units_completed" in cols
        assert "units_label" in cols
        assert "delivery_pct" in cols

    def test_money_flow_still_works(self, db):
        """Backward-compat: money_flow VIEW still exists and has expected columns."""
        self._seed(db)
        rows = db.execute("SELECT scheme, allocated_lakhs, units_label FROM money_flow").fetchall()
        assert len(rows) > 0
        schemes = [r["scheme"] for r in rows]
        assert "MGNREGA" in schemes
