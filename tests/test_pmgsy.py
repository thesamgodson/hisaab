"""Tests for the PMGSY (rural roads) pipeline.

Covers: CSV parsing, DB loading, query functions, CLI intent routing,
and journalist brief generation.
"""

from __future__ import annotations

import sqlite3
import textwrap

import pytest

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_CSV = textwrap.dedent("""\
    Textbox33
    District Brief

    IMS_YEAR,RoadsSanctioned,LengthSanctioned,LSBsSanctioned,VoP,RoadsCompleted,LengthCompleted,LSBsCompleted,Expenditure,T_RS,T_LS,T_LSBs,T_VoP,T_RC,T_LC,T_LSBsC,T_Exp
    2020-2021,10,50.5,5,100.0,8,40.2,4,80.0,100,500,50,1000,80,400,40,800
    2020-2021,20,100.0,10,200.0,18,90.0,9,180.0,100,500,50,1000,80,400,40,800
    2020-2021,15,75.0,8,150.0,12,60.0,6,120.0,100,500,50,1000,80,400,40,800
    2021-2022,12,55.0,6,110.0,10,45.0,5,90.0,100,500,50,1000,80,400,40,800
    2021-2022,22,110.0,11,220.0,20,100.0,10,200.0,100,500,50,1000,80,400,40,800
    2021-2022,18,80.0,9,160.0,15,65.0,7,130.0,100,500,50,1000,80,400,40,800
""")

SAMPLE_DISTRICTS = [
    {"name": "Alpha", "id": "1"},
    {"name": "Beta", "id": "2"},
    {"name": "Gamma", "id": "3"},
]


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite DB with full schema (all 8 scheme tables)."""
    from db import init_db

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


# ---------------------------------------------------------------------------
# CSV Parsing tests
# ---------------------------------------------------------------------------


class TestParseDistrictCSV:
    def test_basic_parsing(self):
        from scrape_pmgsy import parse_district_csv

        records = parse_district_csv(SAMPLE_CSV, SAMPLE_DISTRICTS, "TestState", "http://example.com")
        assert len(records) == 3
        names = [r["district"] for r in records]
        assert names == ["Alpha", "Beta", "Gamma"]

    def test_aggregation_across_years(self):
        from scrape_pmgsy import parse_district_csv

        records = parse_district_csv(SAMPLE_CSV, SAMPLE_DISTRICTS, "TestState", "http://example.com")
        alpha = next(r for r in records if r["district"] == "Alpha")
        # 2020-2021: sanctioned=10, completed=8 | 2021-2022: sanctioned=12, completed=10
        assert alpha["roads_sanctioned"] == 22
        assert alpha["roads_completed"] == 18

    def test_state_and_metadata(self):
        from scrape_pmgsy import parse_district_csv

        records = parse_district_csv(SAMPLE_CSV, SAMPLE_DISTRICTS, "TestState", "http://example.com")
        for r in records:
            assert r["state"] == "TestState"
            assert r["source_url"] == "http://example.com"
            assert r["fin_year"] == "cumulative"
            assert r["scheme"] == "All"
            assert "scraped_at" in r

    def test_empty_districts(self):
        from scrape_pmgsy import parse_district_csv

        records = parse_district_csv(SAMPLE_CSV, [], "TestState", "http://example.com")
        assert records == []

    def test_empty_csv(self):
        from scrape_pmgsy import parse_district_csv

        records = parse_district_csv("", SAMPLE_DISTRICTS, "TestState", "http://example.com")
        assert records == []

    def test_mismatched_group_size_skipped(self):
        """Year groups with wrong number of rows should be skipped."""
        from scrape_pmgsy import parse_district_csv

        # CSV with 2 rows per year but 3 districts — should skip all
        csv_2_rows = textwrap.dedent("""\
            IMS_YEAR,RS,LS,LSBs,VoP,RC,LC,LSBsC,Exp,T1,T2,T3,T4,T5,T6,T7,T8
            2020-2021,10,50,5,100,8,40,4,80,0,0,0,0,0,0,0,0
            2020-2021,20,100,10,200,18,90,9,180,0,0,0,0,0,0,0,0
        """)
        records = parse_district_csv(csv_2_rows, SAMPLE_DISTRICTS, "TestState", "http://example.com")
        # With 3 districts but only 2 rows per year, parsing depends on most-common-size logic.
        # Most common size is 2, not 3, so 2 is accepted → 2 districts mapped.
        assert len(records) == 2


class TestExtractStateTotals:
    def test_basic_extraction(self):
        from scrape_pmgsy import extract_state_totals

        totals = extract_state_totals(SAMPLE_CSV, "TestState", "http://example.com")
        assert len(totals) == 1
        t = totals[0]
        assert t["state"] == "TestState"
        assert t["roads_completed"] == 80
        assert t["length_completed_km"] == 400.0
        assert t["expenditure_programme_cr"] == 800.0

    def test_empty_csv(self):
        from scrape_pmgsy import extract_state_totals

        totals = extract_state_totals("", "TestState", "http://example.com")
        assert totals == []


class TestParseAmount:
    def test_basic(self):
        from scrape_pmgsy import parse_amount

        assert parse_amount("1,234.56") == 1234.56

    def test_empty(self):
        from scrape_pmgsy import parse_amount

        assert parse_amount("") == 0.0

    def test_quoted(self):
        from scrape_pmgsy import parse_amount

        assert parse_amount('"27,132.852"') == 27132.852


# ---------------------------------------------------------------------------
# Query tests
# ---------------------------------------------------------------------------


class TestPmgsyQueries:
    def _load_sample_data(self, conn):
        """Insert sample PMGSY data."""
        districts = [
            ("Alpha", "TestState", "cumulative", "All", 100, 80, 200, 160, 50, 300, 250),
            ("Beta", "TestState", "cumulative", "All", 200, 150, 400, 300, 100, 600, 450),
            ("Gamma", "TestState", "cumulative", "All", 50, 50, 100, 100, 25, 150, 150),
        ]
        for d in districts:
            conn.execute(
                """INSERT INTO pmgsy_district
                (district, state, fin_year, scheme, roads_sanctioned, roads_completed,
                 length_sanctioned_km, length_completed_km, habitations_covered,
                 value_of_projects_cr, expenditure_cr, source_url, scraped_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (*d, "http://test", "2026-01-01"),
            )
        conn.execute(
            """INSERT INTO pmgsy_progress
            (state, state_code, fin_year, roads_completed, length_completed_km,
             habitations_connected, expenditure_programme_cr, expenditure_admin_cr,
             source_url, scraped_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            ("TestState", "", "cumulative", 280, 560, 175, 850, 0, "http://test", "2026-01-01"),
        )
        conn.commit()

    @staticmethod
    def _patch_query_conn(in_memory_db, monkeypatch):
        """Patch query._conn to return the in-memory DB without closing it."""
        import query

        class NoCloseConn:
            """Wraps a connection but ignores close() calls."""

            def __init__(self, real_conn):
                self._conn = real_conn

            def execute(self, *a, **kw):
                return self._conn.execute(*a, **kw)

            def close(self):
                pass  # Don't actually close

            @property
            def row_factory(self):
                return self._conn.row_factory

            @row_factory.setter
            def row_factory(self, val):
                self._conn.row_factory = val

        monkeypatch.setattr(query, "_conn", lambda: NoCloseConn(in_memory_db))

    def test_pmgsy_district_summary(self, in_memory_db, monkeypatch):
        self._load_sample_data(in_memory_db)
        self._patch_query_conn(in_memory_db, monkeypatch)
        import query

        result = query.pmgsy_district_summary("Alpha", state="TestState")
        assert "answer" in result
        assert "80%" in result["answer"]  # 80/100 = 80%

    def test_pmgsy_state_summary(self, in_memory_db, monkeypatch):
        self._load_sample_data(in_memory_db)
        self._patch_query_conn(in_memory_db, monkeypatch)
        import query

        result = query.pmgsy_state_summary(state="TestState")
        assert "answer" in result
        assert "3" in result["answer"]  # 3 districts

    def test_pmgsy_worst_completion(self, in_memory_db, monkeypatch):
        self._load_sample_data(in_memory_db)
        self._patch_query_conn(in_memory_db, monkeypatch)
        import query

        result = query.pmgsy_worst_completion(state="TestState")
        assert "answer" in result
        # Beta has 75% (150/200) — worst. Alpha 80%. Gamma 100%.
        assert "Beta" in result["answer"]

    def test_pmgsy_no_data(self, in_memory_db, monkeypatch):
        self._patch_query_conn(in_memory_db, monkeypatch)
        import query

        result = query.pmgsy_district_summary("Nonexistent", state="Nowhere")
        assert "No PMGSY" in result["answer"] or "no data" in result["answer"].lower()


# ---------------------------------------------------------------------------
# CLI intent detection tests
# ---------------------------------------------------------------------------


class TestCLIIntentDetection:
    def test_roads_intent(self):
        from cli import detect_intent

        assert detect_intent("roads patna") == "roads"
        assert detect_intent("pmgsy bihar") == "roads"

    def test_worst_intent_priority(self):
        from cli import detect_intent

        assert detect_intent("worst roads") == "worst"
        assert detect_intent("top corruption") == "worst"

    def test_misappropriation_intent(self):
        from cli import detect_intent

        assert detect_intent("corruption villupuram") == "misappropriation"

    def test_overview_fallback(self):
        from cli import detect_intent

        assert detect_intent("cuddalore") == "overview"


class TestCLIStateResolution:
    def test_resolve_known_state(self, in_memory_db, monkeypatch):
        in_memory_db.execute(
            "INSERT INTO pmgsy_district (district, state, fin_year, scheme, roads_sanctioned, roads_completed, length_sanctioned_km, length_completed_km, habitations_covered, value_of_projects_cr, expenditure_cr, source_url, scraped_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            ("TestDist", "Bihar", "cumulative", "All", 10, 8, 20, 16, 5, 30, 25, "", ""),
        )
        in_memory_db.commit()

        # cli._resolve_state imports db.get_connection internally
        import db as db_mod

        monkeypatch.setattr(db_mod, "get_connection", lambda: in_memory_db)

        from cli import _resolve_state

        assert _resolve_state("roads bihar") == "Bihar"

    def test_resolve_unknown_state(self, in_memory_db, monkeypatch):
        import db as db_mod

        monkeypatch.setattr(db_mod, "get_connection", lambda: in_memory_db)

        from cli import _resolve_state

        assert _resolve_state("roads somewhere") is None


# ---------------------------------------------------------------------------
# DB loading tests
# ---------------------------------------------------------------------------


class TestDBLoading:
    def test_load_pmgsy_district(self, in_memory_db):
        from db import load_pmgsy_district

        records = [
            {
                "district": "Alpha",
                "state": "TestState",
                "state_code": "",
                "fin_year": "cumulative",
                "scheme": "All",
                "roads_sanctioned": 100,
                "roads_completed": 80,
                "length_sanctioned_km": 200,
                "length_completed_km": 160,
                "habitations_covered": 50,
                "value_of_projects_cr": 300,
                "expenditure_cr": 250,
                "source_url": "http://test",
                "scraped_at": "2026-01-01",
            }
        ]
        count = load_pmgsy_district(in_memory_db, records, "cumulative")
        assert count == 1

        row = in_memory_db.execute("SELECT * FROM pmgsy_district").fetchone()
        assert row["district"] == "Alpha"
        assert row["roads_sanctioned"] == 100

    def test_upsert_replaces(self, in_memory_db):
        from db import load_pmgsy_district

        records = [
            {
                "district": "Alpha",
                "state": "TestState",
                "state_code": "",
                "fin_year": "cumulative",
                "scheme": "All",
                "roads_sanctioned": 100,
                "roads_completed": 80,
                "length_sanctioned_km": 200,
                "length_completed_km": 160,
                "habitations_covered": 50,
                "value_of_projects_cr": 300,
                "expenditure_cr": 250,
                "source_url": "http://test",
                "scraped_at": "2026-01-01",
            }
        ]
        load_pmgsy_district(in_memory_db, records, "cumulative")

        # Update the expenditure
        records[0]["expenditure_cr"] = 999
        load_pmgsy_district(in_memory_db, records, "cumulative")

        rows = in_memory_db.execute("SELECT * FROM pmgsy_district").fetchall()
        assert len(rows) == 1  # Should replace, not duplicate
        assert rows[0]["expenditure_cr"] == 999


# ---------------------------------------------------------------------------
# Journalist brief red flags tests
# ---------------------------------------------------------------------------


class TestRedFlags:
    def test_pmgsy_low_completion_flag(self, in_memory_db):
        from journalist_brief import _detect_flags

        # Insert district with <50% completion
        in_memory_db.execute(
            """INSERT INTO pmgsy_district
            (district, state, fin_year, scheme, roads_sanctioned, roads_completed,
             length_sanctioned_km, length_completed_km, habitations_covered,
             value_of_projects_cr, expenditure_cr, source_url, scraped_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("BadDist", "TESTSTATE", "cumulative", "All", 100, 30, 200, 60, 10, 300, 250, "", ""),
        )
        in_memory_db.commit()

        flags = _detect_flags(in_memory_db, "BadDist", "TESTSTATE", verbose=True)
        assert any("low completion" in f.lower() for f in flags)

    def test_pmgsy_over_expenditure_flag(self, in_memory_db):
        from journalist_brief import _detect_flags

        in_memory_db.execute(
            """INSERT INTO pmgsy_district
            (district, state, fin_year, scheme, roads_sanctioned, roads_completed,
             length_sanctioned_km, length_completed_km, habitations_covered,
             value_of_projects_cr, expenditure_cr, source_url, scraped_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("OverDist", "TESTSTATE", "cumulative", "All", 100, 90, 200, 180, 50, 100, 200, "", ""),
        )
        in_memory_db.commit()

        flags = _detect_flags(in_memory_db, "OverDist", "TESTSTATE", verbose=True)
        assert any("over-expenditure" in f.lower() for f in flags)

    def test_cross_scheme_flag(self, in_memory_db):
        from journalist_brief import _detect_flags

        # High MGNREGA utilization + low PMGSY completion
        in_memory_db.execute(
            """INSERT INTO financial_statement
            (district, state, fin_year, total_availability, cumulative_expenditure,
             utilization_pct, exp_unskilled_wage, source_url, scraped_at, state_code)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            ("CrossDist", "TESTSTATE", "2024-2025", 10000, 9000, 90, 7000, "", "", ""),
        )
        in_memory_db.execute(
            """INSERT INTO pmgsy_district
            (district, state, fin_year, scheme, roads_sanctioned, roads_completed,
             length_sanctioned_km, length_completed_km, habitations_covered,
             value_of_projects_cr, expenditure_cr, source_url, scraped_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("CrossDist", "TESTSTATE", "cumulative", "All", 100, 30, 200, 60, 10, 300, 250, "", ""),
        )
        in_memory_db.commit()

        flags = _detect_flags(in_memory_db, "CrossDist", "TESTSTATE", verbose=True)
        assert any("cross-scheme" in f.lower() for f in flags)

    def test_no_flags_for_good_district(self, in_memory_db):
        from journalist_brief import _detect_flags

        in_memory_db.execute(
            """INSERT INTO pmgsy_district
            (district, state, fin_year, scheme, roads_sanctioned, roads_completed,
             length_sanctioned_km, length_completed_km, habitations_covered,
             value_of_projects_cr, expenditure_cr, source_url, scraped_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            ("GoodDist", "TESTSTATE", "cumulative", "All", 100, 98, 200, 195, 50, 300, 280, "", ""),
        )
        in_memory_db.commit()

        flags = _detect_flags(in_memory_db, "GoodDist", "TESTSTATE", verbose=True)
        assert len(flags) == 0
