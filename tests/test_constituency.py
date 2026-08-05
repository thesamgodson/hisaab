"""Tests for constituency/mapper.py and constituency/report_card.py.

Uses a temporary SQLite database (write tests) and the live DB (read-only tests).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest

from db import init_db

# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    """Temporary DB seeded with constituency + PIN + MP data."""
    db_path = tmp_path / "constituency_test.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    init_db(conn)
    conn.close()
    return db_path


def _insert_seed(db_path: Path) -> None:
    """Insert sample constituency/PIN/MP data directly into the temp DB."""
    conn = sqlite3.connect(str(db_path))
    conn.execute(
        """INSERT OR REPLACE INTO pin_district_mapping
        (pin_code, district, state, office_name)
        VALUES ('800001', 'PATNA', 'BIHAR', 'Patna GPO')"""
    )
    conn.execute(
        """INSERT OR REPLACE INTO pin_district_mapping
        (pin_code, district, state, office_name)
        VALUES ('226001', 'LUCKNOW', 'UTTAR PRADESH', 'Lucknow GPO')"""
    )
    conn.execute(
        """INSERT OR REPLACE INTO constituency_district
        (constituency, state, district, constituency_type)
        VALUES ('PATNA SAHIB', 'BIHAR', 'PATNA', 'LOK_SABHA')"""
    )
    conn.execute(
        """INSERT OR REPLACE INTO constituency_district
        (constituency, state, district, constituency_type)
        VALUES ('LUCKNOW', 'UTTAR PRADESH', 'LUCKNOW', 'LOK_SABHA')"""
    )
    conn.execute(
        """INSERT OR REPLACE INTO mp_info
        (constituency, mp_name, party, state, elected_year, source_url)
        VALUES ('PATNA SAHIB', 'Ravi Shankar Prasad', 'BJP', 'BIHAR', 2024, 'src')"""
    )
    conn.execute(
        """INSERT OR REPLACE INTO mp_info
        (constituency, mp_name, party, state, elected_year, source_url)
        VALUES ('LUCKNOW', 'Rajnath Singh', 'BJP', 'UTTAR PRADESH', 2024, 'src')"""
    )
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# seed_data.seed_all()
# ---------------------------------------------------------------------------

class TestSeedAll:
    def test_seed_all_populates_tables(self, tmp_db: Path) -> None:
        from constituency.mapper import load_constituency_data, load_mp_data, load_pin_data
        from constituency.seed_data import (
            SAMPLE_CONSTITUENCIES,
            SAMPLE_MP_INFO,
            SAMPLE_PINS,
        )

        with patch("constituency.mapper.DB_PATH", tmp_db):
            pins = load_pin_data(SAMPLE_PINS)
            constituencies = load_constituency_data(SAMPLE_CONSTITUENCIES)
            mps = load_mp_data(SAMPLE_MP_INFO)

        assert pins > 0
        assert constituencies > 0
        assert mps > 0

    def test_seed_populates_pin_table(self, tmp_db: Path) -> None:
        from constituency.mapper import load_pin_data
        from constituency.seed_data import SAMPLE_PINS

        with patch("constituency.mapper.DB_PATH", tmp_db):
            load_pin_data(SAMPLE_PINS)

        conn = sqlite3.connect(str(tmp_db))
        count = conn.execute("SELECT COUNT(*) FROM pin_district_mapping").fetchone()[0]
        conn.close()
        assert count == len(SAMPLE_PINS)

    def test_seed_populates_constituency_district(self, tmp_db: Path) -> None:
        from constituency.mapper import load_constituency_data
        from constituency.seed_data import SAMPLE_CONSTITUENCIES

        with patch("constituency.mapper.DB_PATH", tmp_db):
            load_constituency_data(SAMPLE_CONSTITUENCIES)

        conn = sqlite3.connect(str(tmp_db))
        count = conn.execute("SELECT COUNT(*) FROM constituency_district").fetchone()[0]
        conn.close()
        assert count == len(SAMPLE_CONSTITUENCIES)

    def test_seed_populates_mp_info(self, tmp_db: Path) -> None:
        from constituency.mapper import load_mp_data
        from constituency.seed_data import SAMPLE_MP_INFO

        with patch("constituency.mapper.DB_PATH", tmp_db):
            load_mp_data(SAMPLE_MP_INFO)

        conn = sqlite3.connect(str(tmp_db))
        count = conn.execute("SELECT COUNT(*) FROM mp_info").fetchone()[0]
        conn.close()
        assert count == len(SAMPLE_MP_INFO)


# ---------------------------------------------------------------------------
# pin_to_district
# ---------------------------------------------------------------------------

class TestPinToDistrict:
    def test_known_pin_returns_correct_district(self, tmp_db: Path) -> None:
        _insert_seed(tmp_db)
        with patch("constituency.mapper.DB_PATH", tmp_db):
            from constituency.mapper import pin_to_district
            result = pin_to_district("800001")

        assert result is not None
        assert result["district"] == "PATNA"
        assert result["state"] == "BIHAR"

    def test_unknown_pin_returns_none(self, tmp_db: Path) -> None:
        with patch("constituency.mapper.DB_PATH", tmp_db):
            from constituency.mapper import pin_to_district
            result = pin_to_district("999999")

        assert result is None

    def test_non_numeric_pin_returns_none(self, tmp_db: Path) -> None:
        with patch("constituency.mapper.DB_PATH", tmp_db):
            from constituency.mapper import pin_to_district
            result = pin_to_district("ABCDEF")

        assert result is None

    def test_wrong_length_pin_returns_none(self, tmp_db: Path) -> None:
        with patch("constituency.mapper.DB_PATH", tmp_db):
            from constituency.mapper import pin_to_district
            result = pin_to_district("12345")  # 5 digits, not 6

        assert result is None

    def test_pin_with_whitespace_is_cleaned(self, tmp_db: Path) -> None:
        _insert_seed(tmp_db)
        with patch("constituency.mapper.DB_PATH", tmp_db):
            from constituency.mapper import pin_to_district
            result = pin_to_district("  800001  ")

        assert result is not None
        assert result["district"] == "PATNA"

    def test_result_has_expected_keys(self, tmp_db: Path) -> None:
        _insert_seed(tmp_db)
        with patch("constituency.mapper.DB_PATH", tmp_db):
            from constituency.mapper import pin_to_district
            result = pin_to_district("800001")

        assert result is not None
        assert "pin_code" in result
        assert "district" in result
        assert "state" in result


# ---------------------------------------------------------------------------
# district_to_constituency
# ---------------------------------------------------------------------------

class TestDistrictToConstituency:
    def test_known_district_returns_constituencies(self, tmp_db: Path) -> None:
        _insert_seed(tmp_db)
        with patch("constituency.mapper.DB_PATH", tmp_db):
            from constituency.mapper import district_to_constituency
            results = district_to_constituency("PATNA", "BIHAR")

        assert isinstance(results, list)
        assert len(results) >= 1
        assert any(r["constituency"] == "PATNA SAHIB" for r in results)

    def test_unknown_district_returns_empty(self, tmp_db: Path) -> None:
        with patch("constituency.mapper.DB_PATH", tmp_db):
            from constituency.mapper import district_to_constituency
            results = district_to_constituency("NONEXISTENT", "NOSTATE")

        assert results == []

    def test_result_entries_have_required_keys(self, tmp_db: Path) -> None:
        _insert_seed(tmp_db)
        with patch("constituency.mapper.DB_PATH", tmp_db):
            from constituency.mapper import district_to_constituency
            results = district_to_constituency("PATNA", "BIHAR")

        for r in results:
            assert "constituency" in r
            assert "state" in r
            assert "district" in r

    def test_case_insensitive_lookup(self, tmp_db: Path) -> None:
        _insert_seed(tmp_db)
        with patch("constituency.mapper.DB_PATH", tmp_db):
            from constituency.mapper import district_to_constituency
            r1 = district_to_constituency("PATNA", "BIHAR")
            r2 = district_to_constituency("patna", "bihar")

        assert len(r1) == len(r2)


# ---------------------------------------------------------------------------
# get_mp_info
# ---------------------------------------------------------------------------

class TestGetMpInfo:
    def test_known_constituency_returns_mp(self, tmp_db: Path) -> None:
        _insert_seed(tmp_db)
        with patch("constituency.mapper.DB_PATH", tmp_db):
            from constituency.mapper import get_mp_info
            result = get_mp_info("PATNA SAHIB")

        assert result is not None
        assert result["mp_name"] == "Ravi Shankar Prasad"
        assert result["party"] == "BJP"

    def test_unknown_constituency_returns_none(self, tmp_db: Path) -> None:
        with patch("constituency.mapper.DB_PATH", tmp_db):
            from constituency.mapper import get_mp_info
            result = get_mp_info("NONEXISTENT CONSTITUENCY")

        assert result is None

    def test_case_insensitive_lookup(self, tmp_db: Path) -> None:
        _insert_seed(tmp_db)
        with patch("constituency.mapper.DB_PATH", tmp_db):
            from constituency.mapper import get_mp_info
            r1 = get_mp_info("PATNA SAHIB")
            r2 = get_mp_info("patna sahib")

        assert r1 is not None
        assert r2 is not None
        assert r1["mp_name"] == r2["mp_name"]


# ---------------------------------------------------------------------------
# Duplicate PC names across states — mp_info UNIQUE(constituency, state)
# ---------------------------------------------------------------------------

def _seed_duplicate_pc_names(db_path: Path) -> None:
    """Two states sharing one PC name, plus cd rows for district scoping."""
    from constituency.mapper import load_constituency_data, load_mp_data

    with patch("constituency.mapper.DB_PATH", db_path):
        load_mp_data(
            [
                {"constituency": "AURANGABAD", "mp_name": "Bihar Test MP",
                 "party": "P1", "state": "BIHAR", "elected_year": 2024},
                {"constituency": "AURANGABAD", "mp_name": "Maharashtra Test MP",
                 "party": "P2", "state": "MAHARASHTRA", "elected_year": 2024},
            ]
        )
        load_constituency_data(
            [
                {"constituency": "AURANGABAD", "state": "BIHAR",
                 "district": "AURANGABAD"},
                {"constituency": "AURANGABAD", "state": "MAHARASHTRA",
                 "district": "AURANGABAD"},
            ]
        )


class TestDuplicatePcNames:
    def test_both_states_rows_survive_ingest(self, tmp_db: Path) -> None:
        _seed_duplicate_pc_names(tmp_db)

        conn = sqlite3.connect(str(tmp_db))
        count = conn.execute(
            "SELECT COUNT(*) FROM mp_info WHERE constituency = 'AURANGABAD'"
        ).fetchone()[0]
        conn.close()
        assert count == 2  # UNIQUE(constituency) would have kept only one

    def test_reingest_is_idempotent(self, tmp_db: Path) -> None:
        _seed_duplicate_pc_names(tmp_db)
        _seed_duplicate_pc_names(tmp_db)

        conn = sqlite3.connect(str(tmp_db))
        count = conn.execute("SELECT COUNT(*) FROM mp_info").fetchone()[0]
        conn.close()
        assert count == 2

    def test_state_scoped_lookup_returns_right_mp(self, tmp_db: Path) -> None:
        _seed_duplicate_pc_names(tmp_db)
        with patch("constituency.mapper.DB_PATH", tmp_db):
            from constituency.mapper import get_mp_info
            bihar = get_mp_info("AURANGABAD", state="BIHAR")
            maha = get_mp_info("AURANGABAD", state="MAHARASHTRA")

        assert bihar is not None and bihar["mp_name"] == "Bihar Test MP"
        assert maha is not None and maha["mp_name"] == "Maharashtra Test MP"

    def test_ambiguous_name_without_state_returns_none(self, tmp_db: Path) -> None:
        _seed_duplicate_pc_names(tmp_db)
        with patch("constituency.mapper.DB_PATH", tmp_db):
            from constituency.mapper import get_mp_info
            result = get_mp_info("AURANGABAD")

        assert result is None  # honest null beats another state's MP

    def test_unambiguous_name_without_state_still_resolves(self, tmp_db: Path) -> None:
        _insert_seed(tmp_db)
        with patch("constituency.mapper.DB_PATH", tmp_db):
            from constituency.mapper import get_mp_info
            result = get_mp_info("PATNA SAHIB")

        assert result is not None
        assert result["mp_name"] == "Ravi Shankar Prasad"

    def test_get_mp_candidates_lists_all_states(self, tmp_db: Path) -> None:
        _seed_duplicate_pc_names(tmp_db)
        with patch("constituency.mapper.DB_PATH", tmp_db):
            from constituency.mapper import get_mp_candidates
            candidates = get_mp_candidates("AURANGABAD")

        assert [c["state"] for c in candidates] == ["BIHAR", "MAHARASHTRA"]

    def test_vintage_state_label_resolves(self, tmp_db: Path) -> None:
        from constituency.mapper import load_mp_data

        with patch("constituency.mapper.DB_PATH", tmp_db):
            load_mp_data(
                [{"constituency": "SECUNDERABAD", "mp_name": "Telangana Test MP",
                  "party": "P1", "state": "TELANGANA", "elected_year": 2024}]
            )
            from constituency.mapper import get_mp_info
            # datameet's vintage label for a Telangana seat
            result = get_mp_info("SECUNDERABAD", state="ANDHRA PRADESH")

        assert result is not None
        assert result["mp_name"] == "Telangana Test MP"

    def test_wrong_state_returns_none(self, tmp_db: Path) -> None:
        _seed_duplicate_pc_names(tmp_db)
        with patch("constituency.mapper.DB_PATH", tmp_db):
            from constituency.mapper import get_mp_info
            result = get_mp_info("AURANGABAD", state="UTTAR PRADESH")

        assert result is None

    def test_suffix_without_space_matches(self, tmp_db: Path) -> None:
        from constituency.mapper import load_mp_data

        with patch("constituency.mapper.DB_PATH", tmp_db):
            load_mp_data(
                [{"constituency": "WARANGAL", "mp_name": "Warangal Test MP",
                  "party": "P1", "state": "TELANGANA", "elected_year": 2024}]
            )
            from constituency.mapper import get_mp_info
            # datameet writes the reserved seat as "WARANGAL(SC)" — no space
            result = get_mp_info("WARANGAL(SC)", state="TELANGANA")

        assert result is not None
        assert result["mp_name"] == "Warangal Test MP"

    def test_districts_scoped_by_state(self, tmp_db: Path) -> None:
        _seed_duplicate_pc_names(tmp_db)
        with patch("constituency.mapper.DB_PATH", tmp_db):
            from constituency.mapper import get_districts_for_constituency
            merged = get_districts_for_constituency("AURANGABAD")
            bihar_only = get_districts_for_constituency("AURANGABAD", state="BIHAR")

        assert len(merged) == 2  # unscoped keeps both rows (same district name here)
        assert len(bihar_only) == 1

    def test_ambiguous_report_card_is_honest_stub(self, tmp_db: Path) -> None:
        _seed_duplicate_pc_names(tmp_db)
        with patch("constituency.mapper.DB_PATH", tmp_db), \
             patch("constituency.report_card.DB_PATH", tmp_db):
            from constituency.report_card import generate_mp_report_card
            rc = generate_mp_report_card("AURANGABAD")
            rc_scoped = generate_mp_report_card("AURANGABAD", scope_state="BIHAR")

        assert rc.mp_name == "Unknown"
        assert rc.districts == []
        assert rc.extra.get("ambiguous_states") == ["BIHAR", "MAHARASHTRA"]
        assert rc_scoped.mp_name == "Bihar Test MP"
        assert rc_scoped.state == "BIHAR"


# ---------------------------------------------------------------------------
# search_constituency
# ---------------------------------------------------------------------------

class TestSearchConstituency:
    def test_search_by_constituency_name(self, tmp_db: Path) -> None:
        _insert_seed(tmp_db)
        with patch("constituency.mapper.DB_PATH", tmp_db):
            from constituency.mapper import search_constituency
            results = search_constituency("PATNA")

        assert isinstance(results, list)
        names = [r["constituency"] for r in results]
        assert "PATNA SAHIB" in names

    def test_search_by_mp_name(self, tmp_db: Path) -> None:
        _insert_seed(tmp_db)
        with patch("constituency.mapper.DB_PATH", tmp_db):
            from constituency.mapper import search_constituency
            results = search_constituency("Rajnath")

        assert isinstance(results, list)
        # Case-insensitive: the pattern is uppercased internally
        constituencies = [r["constituency"] for r in results]
        assert "LUCKNOW" in constituencies

    def test_empty_query_returns_no_more_than_10(self, tmp_db: Path) -> None:
        _insert_seed(tmp_db)
        with patch("constituency.mapper.DB_PATH", tmp_db):
            from constituency.mapper import search_constituency
            results = search_constituency("")

        assert len(results) <= 10

    def test_no_match_returns_empty_list(self, tmp_db: Path) -> None:
        with patch("constituency.mapper.DB_PATH", tmp_db):
            from constituency.mapper import search_constituency
            results = search_constituency("XYZNONEXISTENTXYZ")

        assert results == []

    def test_sql_injection_safe(self, tmp_db: Path) -> None:
        with patch("constituency.mapper.DB_PATH", tmp_db):
            from constituency.mapper import search_constituency
            # Must not raise
            results = search_constituency("' OR '1'='1")
            assert isinstance(results, list)


# ---------------------------------------------------------------------------
# generate_mp_report_card
# ---------------------------------------------------------------------------

class TestGenerateMpReportCard:
    def test_unknown_constituency_returns_stub(self, tmp_db: Path) -> None:
        with patch("constituency.mapper.DB_PATH", tmp_db), \
             patch("constituency.report_card.DB_PATH", tmp_db):
            from constituency.report_card import generate_mp_report_card
            rc = generate_mp_report_card("NONEXISTENT CONSTITUENCY XYZ")

        assert rc.mp_name == "Unknown"
        assert rc.constituency == "NONEXISTENT CONSTITUENCY XYZ"

    def test_unknown_constituency_returns_mp_report_card_type(self, tmp_db: Path) -> None:
        with patch("constituency.mapper.DB_PATH", tmp_db), \
             patch("constituency.report_card.DB_PATH", tmp_db):
            from constituency.report_card import MPReportCard, generate_mp_report_card
            rc = generate_mp_report_card("NONEXISTENT CONSTITUENCY XYZ")

        assert isinstance(rc, MPReportCard)

    def test_unknown_constituency_has_all_schemes(self, tmp_db: Path) -> None:
        with patch("constituency.mapper.DB_PATH", tmp_db), \
             patch("constituency.report_card.DB_PATH", tmp_db):
            from constituency.report_card import ALL_SCHEMES, generate_mp_report_card
            rc = generate_mp_report_card("NONEXISTENT CONSTITUENCY XYZ")

        assert len(rc.schemes) == len(ALL_SCHEMES)

    def test_unknown_constituency_schemes_have_no_data(self, tmp_db: Path) -> None:
        with patch("constituency.mapper.DB_PATH", tmp_db), \
             patch("constituency.report_card.DB_PATH", tmp_db):
            from constituency.report_card import generate_mp_report_card
            rc = generate_mp_report_card("NONEXISTENT CONSTITUENCY XYZ")

        for sp in rc.schemes:
            assert sp.status == "no_data"
            assert sp.score is None

    def test_known_constituency_returns_mp_name(self, tmp_db: Path) -> None:
        _insert_seed(tmp_db)
        with patch("constituency.mapper.DB_PATH", tmp_db), \
             patch("constituency.report_card.DB_PATH", tmp_db):
            from constituency.report_card import generate_mp_report_card
            rc = generate_mp_report_card("PATNA SAHIB")

        assert rc.mp_name == "Ravi Shankar Prasad"
        assert rc.party == "BJP"
        assert rc.state == "BIHAR"

    def test_report_card_composite_score_is_none_with_no_scheme_data(self, tmp_db: Path) -> None:
        _insert_seed(tmp_db)
        with patch("constituency.mapper.DB_PATH", tmp_db), \
             patch("constituency.report_card.DB_PATH", tmp_db):
            from constituency.report_card import generate_mp_report_card
            rc = generate_mp_report_card("PATNA SAHIB")

        # No scheme data in empty DB → composite_score is None
        assert rc.composite_score is None

    def test_report_card_districts_list(self, tmp_db: Path) -> None:
        _insert_seed(tmp_db)
        with patch("constituency.mapper.DB_PATH", tmp_db), \
             patch("constituency.report_card.DB_PATH", tmp_db):
            from constituency.report_card import generate_mp_report_card
            rc = generate_mp_report_card("PATNA SAHIB")

        assert isinstance(rc.districts, list)
        assert "PATNA" in rc.districts

    def test_report_card_fin_year_stored(self, tmp_db: Path) -> None:
        with patch("constituency.mapper.DB_PATH", tmp_db), \
             patch("constituency.report_card.DB_PATH", tmp_db):
            from constituency.report_card import generate_mp_report_card
            rc = generate_mp_report_card("NONEXISTENT", fin_year="2023-2024")

        assert rc.fin_year == "2023-2024"


# ---------------------------------------------------------------------------
# generate_report_card_image
# ---------------------------------------------------------------------------

class TestGenerateReportCardImage:
    def _make_report_card(self, tmp_db: Path):
        with patch("constituency.mapper.DB_PATH", tmp_db), \
             patch("constituency.report_card.DB_PATH", tmp_db):
            from constituency.report_card import generate_mp_report_card
            return generate_mp_report_card("NONEXISTENT CONSTITUENCY XYZ")

    def test_portrait_returns_bytes(self, tmp_db: Path) -> None:
        from constituency.report_card import generate_report_card_image

        rc = self._make_report_card(tmp_db)
        result = generate_report_card_image(rc, fmt="portrait")
        assert isinstance(result, bytes)

    def test_portrait_is_valid_svg(self, tmp_db: Path) -> None:
        from constituency.report_card import generate_report_card_image

        rc = self._make_report_card(tmp_db)
        result = generate_report_card_image(rc, fmt="portrait")
        text = result.decode("utf-8")
        assert "<svg" in text
        assert "</svg>" in text

    def test_landscape_returns_bytes(self, tmp_db: Path) -> None:
        from constituency.report_card import generate_report_card_image

        rc = self._make_report_card(tmp_db)
        result = generate_report_card_image(rc, fmt="landscape")
        assert isinstance(result, bytes)

    def test_landscape_is_valid_svg(self, tmp_db: Path) -> None:
        from constituency.report_card import generate_report_card_image

        rc = self._make_report_card(tmp_db)
        result = generate_report_card_image(rc, fmt="landscape")
        text = result.decode("utf-8")
        assert "<svg" in text

    def test_portrait_svg_has_1080_width(self, tmp_db: Path) -> None:
        from constituency.report_card import generate_report_card_image

        rc = self._make_report_card(tmp_db)
        result = generate_report_card_image(rc, fmt="portrait")
        text = result.decode("utf-8")
        assert 'width="1080"' in text

    def test_landscape_svg_has_1200_width(self, tmp_db: Path) -> None:
        from constituency.report_card import generate_report_card_image

        rc = self._make_report_card(tmp_db)
        result = generate_report_card_image(rc, fmt="landscape")
        text = result.decode("utf-8")
        assert 'width="1200"' in text

    def test_default_format_is_portrait(self, tmp_db: Path) -> None:
        from constituency.report_card import generate_report_card_image

        rc = self._make_report_card(tmp_db)
        result = generate_report_card_image(rc)  # default fmt
        text = result.decode("utf-8")
        assert 'width="1080"' in text  # portrait
