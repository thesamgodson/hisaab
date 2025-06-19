"""Unit tests for pure/deterministic scraper helper functions.

No HTTP calls, no Playwright, no external I/O.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import scrapers.scrape_jjm_ejalshakti as jjm
import scrapers.scrape_sbm as sbm
import scrapers.scrape_udise as udise


# ---------------------------------------------------------------------------
# JJM — encode_txt
# ---------------------------------------------------------------------------

class TestJJMEncodeTxt:
    def test_zero_encodes_ends_with_enc_n(self):
        result = jjm.encode_txt("0")
        assert result.endswith("1"), f"Expected result to end with '1', got {result!r}"

    def test_deterministic(self):
        assert jjm.encode_txt("2024-2025") == jjm.encode_txt("2024-2025")

    def test_empty_string_does_not_crash(self):
        result = jjm.encode_txt("")
        assert isinstance(result, str)

    def test_result_ends_with_enc_n_for_nonempty(self):
        result = jjm.encode_txt("hello")
        assert result.endswith("1")

    def test_result_ends_with_enc_n_for_state_code(self):
        result = jjm.encode_txt("MH")
        assert result.endswith("1")


# ---------------------------------------------------------------------------
# JJM — _prev_year
# ---------------------------------------------------------------------------

class TestJJMPrevYear:
    def test_2024_2025_becomes_2023_2024(self):
        assert jjm._prev_year("2024-2025") == "2023-2024"

    def test_2020_2021_becomes_2019_2020(self):
        assert jjm._prev_year("2020-2021") == "2019-2020"

    def test_format_preserved(self):
        result = jjm._prev_year("2022-2023")
        assert result == "2021-2022"

    def test_decrements_both_parts(self):
        year = "2019-2020"
        result = jjm._prev_year(year)
        start, end = result.split("-")
        assert int(start) == 2018
        assert int(end) == 2019


# ---------------------------------------------------------------------------
# JJM — _parse_amount
# ---------------------------------------------------------------------------

class TestParseAmountJJM:
    def test_indian_comma_format(self):
        assert jjm._parse_amount("1,00,000") == 100000.0

    def test_dash_returns_zero(self):
        assert jjm._parse_amount("-") == 0.0

    def test_null_string_returns_zero(self):
        assert jjm._parse_amount("null") == 0.0

    def test_none_returns_zero(self):
        assert jjm._parse_amount(None) == 0.0

    def test_decimal_value(self):
        assert jjm._parse_amount("10.5") == 10.5

    def test_empty_string_returns_zero(self):
        assert jjm._parse_amount("") == 0.0

    def test_integer_string(self):
        assert jjm._parse_amount("42") == 42.0

    def test_numeric_passthrough(self):
        assert jjm._parse_amount(123) == 123.0


# ---------------------------------------------------------------------------
# SBM — extract_markers_district
# ---------------------------------------------------------------------------

class TestSBMExtractMarkers:
    def test_single_quoted_js_array(self):
        html = (
            "var markersDistrict = ["
            "{'STNAME': 'Bihar', 'dtname': 'PATNA', 'TotalVillages': '100'}"
            "];"
        )
        result = sbm.extract_markers_district(html)
        assert len(result) == 1
        assert result[0]["dtname"] == "PATNA"

    def test_empty_array_returns_empty_list(self):
        html = "var markersDistrict = [];"
        result = sbm.extract_markers_district(html)
        assert result == []

    def test_no_match_returns_empty_list(self):
        html = "<html><body>No markers here</body></html>"
        result = sbm.extract_markers_district(html)
        assert result == []

    def test_multiple_entries(self):
        html = (
            "var markersDistrict = ["
            "{'STNAME': 'Bihar', 'dtname': 'PATNA', 'TotalVillages': '100'},"
            "{'STNAME': 'Bihar', 'dtname': 'GAYA', 'TotalVillages': '80'}"
            "];"
        )
        result = sbm.extract_markers_district(html)
        assert len(result) == 2
        names = {r["dtname"] for r in result}
        assert names == {"PATNA", "GAYA"}

    def test_state_name_preserved(self):
        html = (
            "var markersDistrict = ["
            "{'STNAME': 'Rajasthan', 'dtname': 'JAIPUR', 'TotalVillages': '50'}"
            "];"
        )
        result = sbm.extract_markers_district(html)
        assert result[0]["STNAME"] == "Rajasthan"


# ---------------------------------------------------------------------------
# SBM — normalize_state
# ---------------------------------------------------------------------------

class TestSBMNormalizeState:
    def test_html_entity_a_and_n_islands(self):
        # "A &amp; N Islands" unescapes to "A & N Islands" then upper → _UPPER_FIXES
        assert sbm.normalize_state("A &amp; N Islands") == "ANDAMAN AND NICOBAR ISLANDS"

    def test_html_entity_jammu_kashmir(self):
        assert sbm.normalize_state("JAMMU &amp; KASHMIR") == "JAMMU AND KASHMIR"

    def test_plain_title_case(self):
        assert sbm.normalize_state("Bihar") == "BIHAR"

    def test_canonical_mapping_andaman(self):
        # Direct canonical lookup (no HTML entities)
        assert sbm.normalize_state("Andaman & Nicobar Islands") == "ANDAMAN AND NICOBAR ISLANDS"

    def test_canonical_mapping_jammu(self):
        assert sbm.normalize_state("Jammu & Kashmir") == "JAMMU AND KASHMIR"

    def test_already_upper(self):
        assert sbm.normalize_state("BIHAR") == "BIHAR"

    def test_strips_whitespace(self):
        assert sbm.normalize_state("  Bihar  ") == "BIHAR"


# ---------------------------------------------------------------------------
# UDISE — _convert_year
# ---------------------------------------------------------------------------

class TestUDISEConvertYear:
    def test_2024_25_to_full(self):
        assert udise._convert_year("2024-25") == "2024-2025"

    def test_2022_23_to_full(self):
        assert udise._convert_year("2022-23") == "2022-2023"

    def test_2019_20_to_full(self):
        assert udise._convert_year("2019-20") == "2019-2020"

    def test_format_matches_fin_year_convention(self):
        result = udise._convert_year("2023-24")
        start, end = result.split("-")
        assert int(end) == int(start) + 1

    def test_passthrough_on_bad_format(self):
        # No hyphen — returns as-is
        result = udise._convert_year("2024")
        assert result == "2024"


# ---------------------------------------------------------------------------
# UDISE — _safe_pct
# ---------------------------------------------------------------------------

class TestUDISESafePct:
    def test_half_is_fifty(self):
        assert udise._safe_pct(50, 100) == 50.0

    def test_zero_over_zero(self):
        assert udise._safe_pct(0, 0) == 0.0

    def test_over_one_hundred(self):
        assert udise._safe_pct(150, 100) == 150.0

    def test_zero_numerator(self):
        assert udise._safe_pct(0, 500) == 0.0

    def test_negative_denominator_returns_zero(self):
        assert udise._safe_pct(10, -1) == 0.0

    def test_rounding_to_two_decimals(self):
        result = udise._safe_pct(1, 3)
        assert result == round(1 / 3 * 100, 2)


# ---------------------------------------------------------------------------
# SBM — _parse_float
# ---------------------------------------------------------------------------

class TestParseFloatSBM:
    def test_integer_input(self):
        assert sbm._parse_float(42) == 42.0

    def test_float_passthrough(self):
        assert sbm._parse_float(3.14) == 3.14

    def test_dash_returns_zero(self):
        assert sbm._parse_float("-") == 0.0

    def test_none_string_returns_zero(self):
        assert sbm._parse_float("None") == 0.0

    def test_comma_formatted_number(self):
        assert sbm._parse_float("1,234") == 1234.0

    def test_none_value_returns_zero(self):
        # _parse_float checks isinstance(val, (int, float)) first;
        # None is neither, str(None)="None" → 0.0
        assert sbm._parse_float(None) == 0.0

    def test_empty_string_returns_zero(self):
        assert sbm._parse_float("") == 0.0

    def test_decimal_string(self):
        assert sbm._parse_float("2.718") == 2.718
