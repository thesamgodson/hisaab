"""Tests for queries/composite.py — district scoring, grading, and ranking.

Uses in-memory SQLite with full schema to avoid hitting the live database.
"""

from __future__ import annotations

import sqlite3

import pytest

from db import init_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class NoCloseConn:
    """Wraps a connection but ignores close() calls so tests retain control."""

    def __init__(self, real_conn: sqlite3.Connection) -> None:
        self._conn = real_conn

    def execute(self, *a, **kw):
        return self._conn.execute(*a, **kw)

    def close(self) -> None:
        pass

    @property
    def row_factory(self):
        return self._conn.row_factory

    @row_factory.setter
    def row_factory(self, val) -> None:
        self._conn.row_factory = val


@pytest.fixture
def db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


def _seed_delivery_data(db: sqlite3.Connection) -> None:
    """Insert pmayg + jjm rows to create measurable delivery scores."""
    db.execute(
        """INSERT INTO pmayg_district
        (district, state, state_code, fin_year, houses_sanctioned, houses_completed,
         houses_occupied, funds_released_lakhs, funds_utilized_lakhs, completion_pct,
         source_url, scraped_at)
        VALUES ('PATNA', 'BIHAR', '05', '2024-2025', 1000, 800, 700, 3000, 2400, 80.0,
                'src', '2026-01-01')"""
    )
    db.execute(
        """INSERT INTO jjm_district
        (district, state, state_code, fin_year, total_households, households_with_tap,
         tap_connections_provided, coverage_pct, funds_released_lakhs, funds_utilized_lakhs,
         source_url, scraped_at)
        VALUES ('PATNA', 'BIHAR', '05', '2024-2025', 5000, 4000, 4000, 80.0, 2000, 1500,
                'src', '2026-01-01')"""
    )
    db.execute(
        """INSERT INTO pmayg_district
        (district, state, state_code, fin_year, houses_sanctioned, houses_completed,
         houses_occupied, funds_released_lakhs, funds_utilized_lakhs, completion_pct,
         source_url, scraped_at)
        VALUES ('GAYA', 'BIHAR', '05', '2024-2025', 1000, 100, 80, 2000, 300, 10.0,
                'src', '2026-01-01')"""
    )
    db.execute(
        """INSERT INTO jjm_district
        (district, state, state_code, fin_year, total_households, households_with_tap,
         tap_connections_provided, coverage_pct, funds_released_lakhs, funds_utilized_lakhs,
         source_url, scraped_at)
        VALUES ('GAYA', 'BIHAR', '05', '2024-2025', 5000, 500, 500, 10.0, 2000, 200,
                'src', '2026-01-01')"""
    )
    db.commit()


def _seed_finance_data(db: sqlite3.Connection) -> None:
    """Insert financial_statement row for MGNREGA finance scoring."""
    db.execute(
        """INSERT INTO financial_statement
        (district, state, state_code, fin_year, total_availability, cumulative_expenditure,
         utilization_pct, balance, source_url, scraped_at)
        VALUES ('PATNA', 'BIHAR', '05', '2024-2025', 5000, 4500, 90.0, 500, 'src', '2026-01-01')"""
    )
    db.commit()


def _seed_misappropriation(db: sqlite3.Connection, district: str = "PATNA", recovery: float = 85.0) -> None:
    db.execute(
        """INSERT INTO misappropriation
        (district, state, state_code, fin_year, cases_reported, amount_reported,
         cases_decided, amount_decided, cases_pending_recovery, amount_to_recover,
         cases_recovered, amount_recovered, amount_unrecovered, recovery_rate_pct,
         source_url, scraped_at)
        VALUES (?, 'BIHAR', '05', '2024-2025', 5, 10.0, 3, 6.0, 2, 4.0, 2, 3.0, 1.0, ?,
                'src', '2026-01-01')""",
        (district, recovery),
    )
    db.commit()


# ---------------------------------------------------------------------------
# _grade helper
# ---------------------------------------------------------------------------

class TestGradeHelper:
    def test_grade_a_at_80(self) -> None:
        from queries.composite import _grade
        assert _grade(80.0) == "A"

    def test_grade_a_at_100(self) -> None:
        from queries.composite import _grade
        assert _grade(100.0) == "A"

    def test_grade_b_at_60(self) -> None:
        from queries.composite import _grade
        assert _grade(60.0) == "B"

    def test_grade_b_at_79(self) -> None:
        from queries.composite import _grade
        assert _grade(79.9) == "B"

    def test_grade_c_at_40(self) -> None:
        from queries.composite import _grade
        assert _grade(40.0) == "C"

    def test_grade_c_at_59(self) -> None:
        from queries.composite import _grade
        assert _grade(59.9) == "C"

    def test_grade_d_at_20(self) -> None:
        from queries.composite import _grade
        assert _grade(20.0) == "D"

    def test_grade_d_at_39(self) -> None:
        from queries.composite import _grade
        assert _grade(39.9) == "D"

    def test_grade_f_at_19(self) -> None:
        from queries.composite import _grade
        assert _grade(19.9) == "F"

    def test_grade_f_at_0(self) -> None:
        from queries.composite import _grade
        assert _grade(0.0) == "F"


# ---------------------------------------------------------------------------
# _build_score_record
# ---------------------------------------------------------------------------

class TestBuildScoreRecord:
    def test_score_between_0_and_100(self) -> None:
        from queries.composite import _build_score_record

        record = _build_score_record(
            "PATNA", "BIHAR",
            delivery={"PMAY-G": 80.0, "JJM": 70.0},
            finance={"MGNREGA": 90.0},
            recovery_rate=85.0,
        )
        assert record["score"] is not None
        assert 0.0 <= record["score"] <= 100.0

    def test_grade_matches_score(self) -> None:
        from queries.composite import _build_score_record, _grade

        record = _build_score_record(
            "PATNA", "BIHAR",
            delivery={"PMAY-G": 80.0},
            finance={"MGNREGA": 90.0},
            recovery_rate=None,
        )
        assert record["grade"] == _grade(record["score"])

    def test_empty_data_returns_null_score(self) -> None:
        from queries.composite import _build_score_record

        record = _build_score_record("UNKNOWN", "UNKNOWN", delivery={}, finance={}, recovery_rate=None)
        assert record["score"] is None
        assert record["grade"] is None
        assert record["schemes_count"] == 0

    def test_schemes_with_data_populated(self) -> None:
        from queries.composite import _build_score_record

        record = _build_score_record(
            "PATNA", "BIHAR",
            delivery={"PMAY-G": 80.0, "JJM": 70.0},
            finance={"MGNREGA": 90.0},
            recovery_rate=None,
        )
        assert "PMAY-G" in record["schemes_with_data"]
        assert "JJM" in record["schemes_with_data"]
        assert "MGNREGA" in record["schemes_with_data"]

    def test_red_flags_generated_for_low_delivery(self) -> None:
        from queries.composite import _build_score_record

        record = _build_score_record(
            "GAYA", "BIHAR",
            delivery={"PMAY-G": 10.0},
            finance={},
            recovery_rate=None,
        )
        assert len(record["red_flags"]) > 0
        assert any("PMAY-G" in f for f in record["red_flags"])

    def test_red_flags_generated_for_low_recovery(self) -> None:
        from queries.composite import _build_score_record

        record = _build_score_record(
            "GAYA", "BIHAR",
            delivery={"PMAY-G": 80.0},
            finance={},
            recovery_rate=5.0,
        )
        assert any("recovery" in f.lower() for f in record["red_flags"])

    def test_score_capped_at_100(self) -> None:
        from queries.composite import _build_score_record

        record = _build_score_record(
            "TEST", "STATE",
            delivery={"PMAY-G": 100.0},
            finance={"MGNREGA": 150.0},  # over 100 — should be capped
            recovery_rate=100.0,
        )
        assert record["score"] <= 100.0

    def test_breakdown_structure_present(self) -> None:
        from queries.composite import _build_score_record

        record = _build_score_record(
            "PATNA", "BIHAR",
            delivery={"PMAY-G": 80.0},
            finance={"MGNREGA": 90.0},
            recovery_rate=70.0,
        )
        bd = record["breakdown"]
        assert "delivery_avg" in bd
        assert "finance_avg" in bd
        assert "governance_score" in bd


# ---------------------------------------------------------------------------
# compute_district_scores (full pipeline, in-memory DB)
# ---------------------------------------------------------------------------

class TestComputeDistrictScores:
    def test_returns_list(self, db: sqlite3.Connection, monkeypatch) -> None:
        from queries import composite
        monkeypatch.setattr(composite, "_conn", lambda: NoCloseConn(db))

        scores = composite.compute_district_scores(fin_year="2024-2025")
        assert isinstance(scores, list)

    def test_scored_districts_come_first(self, db: sqlite3.Connection, monkeypatch) -> None:
        _seed_delivery_data(db)
        from queries import composite
        monkeypatch.setattr(composite, "_conn", lambda: NoCloseConn(db))

        scores = composite.compute_district_scores(fin_year="2024-2025")
        # Scored districts appear before unscored (score=None)
        seen_null = False
        for rec in scores:
            if rec["score"] is None:
                seen_null = True
            elif seen_null:
                pytest.fail("Scored district appeared after unscored district")

    def test_all_scores_between_0_and_100(self, db: sqlite3.Connection, monkeypatch) -> None:
        _seed_delivery_data(db)
        _seed_finance_data(db)
        from queries import composite
        monkeypatch.setattr(composite, "_conn", lambda: NoCloseConn(db))

        scores = composite.compute_district_scores(fin_year="2024-2025")
        for rec in scores:
            if rec["score"] is not None:
                assert 0.0 <= rec["score"] <= 100.0, f"Score {rec['score']} out of range"

    def test_empty_db_returns_empty_list(self, db: sqlite3.Connection, monkeypatch) -> None:
        from queries import composite
        monkeypatch.setattr(composite, "_conn", lambda: NoCloseConn(db))

        scores = composite.compute_district_scores(fin_year="2024-2025")
        assert scores == []


# ---------------------------------------------------------------------------
# get_worst_districts
# ---------------------------------------------------------------------------

class TestGetWorstDistricts:
    def test_sorted_ascending_by_score(self, db: sqlite3.Connection, monkeypatch) -> None:
        _seed_delivery_data(db)
        from queries import composite
        monkeypatch.setattr(composite, "_conn", lambda: NoCloseConn(db))

        worst = composite.get_worst_districts(n=10, fin_year="2024-2025")
        # Worst districts are sorted ascending (lowest score first)
        scores = [w["score"] for w in worst if w["score"] is not None]
        assert scores == sorted(scores)

    def test_respects_n_limit(self, db: sqlite3.Connection, monkeypatch) -> None:
        _seed_delivery_data(db)
        from queries import composite
        monkeypatch.setattr(composite, "_conn", lambda: NoCloseConn(db))

        worst = composite.get_worst_districts(n=1, fin_year="2024-2025")
        assert len(worst) <= 1

    def test_empty_db_returns_empty(self, db: sqlite3.Connection, monkeypatch) -> None:
        from queries import composite
        monkeypatch.setattr(composite, "_conn", lambda: NoCloseConn(db))

        worst = composite.get_worst_districts(n=10, fin_year="2024-2025")
        assert worst == []

    def test_worst_district_has_lower_score_than_best(self, db: sqlite3.Connection, monkeypatch) -> None:
        _seed_delivery_data(db)
        from queries import composite
        monkeypatch.setattr(composite, "_conn", lambda: NoCloseConn(db))

        all_scores = composite.compute_district_scores(fin_year="2024-2025")
        scored = [r for r in all_scores if r["score"] is not None]
        if len(scored) < 2:
            pytest.skip("Need at least 2 scored districts for this test")

        worst = composite.get_worst_districts(n=1, fin_year="2024-2025")
        best_score = max(r["score"] for r in scored)
        assert worst[0]["score"] <= best_score


# ---------------------------------------------------------------------------
# get_state_rankings
# ---------------------------------------------------------------------------

class TestGetStateRankings:
    def test_returns_list(self, db: sqlite3.Connection, monkeypatch) -> None:
        from queries import composite
        monkeypatch.setattr(composite, "_conn", lambda: NoCloseConn(db))

        rankings = composite.get_state_rankings(fin_year="2024-2025")
        assert isinstance(rankings, list)

    def test_sorted_descending_by_avg_score(self, db: sqlite3.Connection, monkeypatch) -> None:
        _seed_delivery_data(db)
        from queries import composite
        monkeypatch.setattr(composite, "_conn", lambda: NoCloseConn(db))

        rankings = composite.get_state_rankings(fin_year="2024-2025")
        scores = [r["avg_score"] for r in rankings]
        assert scores == sorted(scores, reverse=True)

    def test_ranking_entry_structure(self, db: sqlite3.Connection, monkeypatch) -> None:
        _seed_delivery_data(db)
        from queries import composite
        monkeypatch.setattr(composite, "_conn", lambda: NoCloseConn(db))

        rankings = composite.get_state_rankings(fin_year="2024-2025")
        if not rankings:
            pytest.skip("No scored districts in in-memory DB for this test")

        rec = rankings[0]
        assert "state" in rec
        assert "avg_score" in rec
        assert "grade" in rec
        assert "district_count" in rec
        assert "best_district_score" in rec
        assert "worst_district_score" in rec

    def test_avg_score_between_0_and_100(self, db: sqlite3.Connection, monkeypatch) -> None:
        _seed_delivery_data(db)
        from queries import composite
        monkeypatch.setattr(composite, "_conn", lambda: NoCloseConn(db))

        rankings = composite.get_state_rankings(fin_year="2024-2025")
        for rec in rankings:
            assert 0.0 <= rec["avg_score"] <= 100.0

    def test_empty_db_returns_empty(self, db: sqlite3.Connection, monkeypatch) -> None:
        from queries import composite
        monkeypatch.setattr(composite, "_conn", lambda: NoCloseConn(db))

        rankings = composite.get_state_rankings(fin_year="2024-2025")
        assert rankings == []


# ---------------------------------------------------------------------------
# get_district_score
# ---------------------------------------------------------------------------

class TestGetDistrictScore:
    def test_known_district_returns_score(self, db: sqlite3.Connection, monkeypatch) -> None:
        _seed_delivery_data(db)
        from queries import composite
        monkeypatch.setattr(composite, "_conn", lambda: NoCloseConn(db))

        result = composite.get_district_score("PATNA", "BIHAR", fin_year="2024-2025")
        assert result["score"] is not None
        assert 0.0 <= result["score"] <= 100.0

    def test_unknown_district_returns_null_score(self, db: sqlite3.Connection, monkeypatch) -> None:
        from queries import composite
        monkeypatch.setattr(composite, "_conn", lambda: NoCloseConn(db))

        result = composite.get_district_score("NONEXISTENT", "NOSTATE", fin_year="2024-2025")
        assert result["score"] is None

    def test_case_insensitive_lookup(self, db: sqlite3.Connection, monkeypatch) -> None:
        _seed_delivery_data(db)
        from queries import composite
        monkeypatch.setattr(composite, "_conn", lambda: NoCloseConn(db))

        r1 = composite.get_district_score("PATNA", "BIHAR", fin_year="2024-2025")
        r2 = composite.get_district_score("patna", "bihar", fin_year="2024-2025")
        assert r1["score"] == r2["score"]
