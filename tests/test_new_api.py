"""Smoke tests for all NEW API endpoints (scores, embed, investigate, constituency).

Uses the same TestClient pattern as tests/test_api.py.
All tests are narrow: status code + required top-level keys + basic type assertions.
No DB mutation.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app


# ---------------------------------------------------------------------------
# Shared fixture — module-scoped, read-only
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client() -> TestClient:
    """Shared TestClient for the whole module (DB is read-only)."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /api/v1/scores
# ---------------------------------------------------------------------------

class TestScoresEndpoint:
    def test_scores_status_200(self, client: TestClient) -> None:
        resp = client.get("/api/v1/scores")
        assert resp.status_code == 200

    def test_scores_has_required_keys(self, client: TestClient) -> None:
        body = client.get("/api/v1/scores").json()
        assert "fin_year" in body
        assert "count" in body
        assert "scored_count" in body
        assert "scores" in body

    def test_scores_is_list(self, client: TestClient) -> None:
        body = client.get("/api/v1/scores").json()
        assert isinstance(body["scores"], list)

    def test_scores_count_matches_list_length(self, client: TestClient) -> None:
        body = client.get("/api/v1/scores").json()
        assert body["count"] == len(body["scores"])

    def test_scores_scored_count_lte_count(self, client: TestClient) -> None:
        body = client.get("/api/v1/scores").json()
        assert body["scored_count"] <= body["count"]

    def test_scores_fin_year_param(self, client: TestClient) -> None:
        resp = client.get("/api/v1/scores?fin_year=2023-2024")
        assert resp.status_code == 200
        body = resp.json()
        assert body["fin_year"] == "2023-2024"

    def test_scores_entries_have_district_and_state(self, client: TestClient) -> None:
        body = client.get("/api/v1/scores").json()
        for entry in body["scores"][:5]:  # spot-check first 5
            assert "district" in entry
            assert "state" in entry
            assert "score" in entry
            assert "grade" in entry


# ---------------------------------------------------------------------------
# GET /api/v1/scores/states
# ---------------------------------------------------------------------------

class TestStateRankingsEndpoint:
    def test_states_status_200(self, client: TestClient) -> None:
        resp = client.get("/api/v1/scores/states")
        assert resp.status_code == 200

    def test_states_has_required_keys(self, client: TestClient) -> None:
        body = client.get("/api/v1/scores/states").json()
        assert "fin_year" in body
        assert "count" in body
        assert "rankings" in body

    def test_rankings_is_list(self, client: TestClient) -> None:
        body = client.get("/api/v1/scores/states").json()
        assert isinstance(body["rankings"], list)

    def test_rankings_entries_structure(self, client: TestClient) -> None:
        body = client.get("/api/v1/scores/states").json()
        for entry in body["rankings"][:3]:
            assert "state" in entry
            assert "avg_score" in entry
            assert "grade" in entry
            assert "district_count" in entry


# ---------------------------------------------------------------------------
# GET /api/v1/scores/worst
# ---------------------------------------------------------------------------

class TestWorstDistrictsEndpoint:
    def test_worst_status_200(self, client: TestClient) -> None:
        resp = client.get("/api/v1/scores/worst")
        assert resp.status_code == 200

    def test_worst_has_required_keys(self, client: TestClient) -> None:
        body = client.get("/api/v1/scores/worst").json()
        assert "fin_year" in body
        assert "count" in body
        assert "districts" in body

    def test_worst_districts_is_list(self, client: TestClient) -> None:
        body = client.get("/api/v1/scores/worst").json()
        assert isinstance(body["districts"], list)

    def test_worst_respects_n_param(self, client: TestClient) -> None:
        body = client.get("/api/v1/scores/worst?n=5").json()
        assert len(body["districts"]) <= 5

    def test_worst_n_too_large_rejected(self, client: TestClient) -> None:
        resp = client.get("/api/v1/scores/worst?n=999")
        assert resp.status_code == 422

    def test_worst_n_zero_rejected(self, client: TestClient) -> None:
        resp = client.get("/api/v1/scores/worst?n=0")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/scores/{district}
# ---------------------------------------------------------------------------

class TestDistrictScoreEndpoint:
    def test_nonexistent_district_returns_404(self, client: TestClient) -> None:
        resp = client.get("/api/v1/scores/DEFINITELYNOTADISTRICT99")
        assert resp.status_code == 404

    def test_404_has_detail_key(self, client: TestClient) -> None:
        body = client.get("/api/v1/scores/ZONETHATISNOWHERE").json()
        assert "detail" in body

    def test_known_district_with_state_returns_200_or_404(self, client: TestClient) -> None:
        # VILLUPURAM is a real district in the DB — either 200 or 404 (if no score)
        resp = client.get("/api/v1/scores/VILLUPURAM?state=TAMIL+NADU")
        assert resp.status_code in (200, 404)

    def test_district_score_structure_when_found(self, client: TestClient) -> None:
        # Try with a district that has data; skip if not in live DB
        resp = client.get("/api/v1/scores/VILLUPURAM?state=TAMIL+NADU")
        if resp.status_code == 200:
            body = resp.json()
            assert "score" in body
            assert "grade" in body
            assert "breakdown" in body


# ---------------------------------------------------------------------------
# GET /api/v1/embed/{district}  — HTML
# ---------------------------------------------------------------------------

class TestEmbedHtmlEndpoint:
    def test_known_district_returns_200_html(self, client: TestClient) -> None:
        resp = client.get("/api/v1/embed/VILLUPURAM")
        # 200 if district found, 404 if not in DB
        assert resp.status_code in (200, 404)

    def test_known_district_html_content_type(self, client: TestClient) -> None:
        resp = client.get("/api/v1/embed/VILLUPURAM")
        if resp.status_code == 200:
            assert "text/html" in resp.headers["content-type"]

    def test_known_district_html_contains_doctype(self, client: TestClient) -> None:
        resp = client.get("/api/v1/embed/VILLUPURAM")
        if resp.status_code == 200:
            assert "<!DOCTYPE html>" in resp.text or "<!doctype html>" in resp.text.lower()

    def test_nonexistent_district_returns_404(self, client: TestClient) -> None:
        resp = client.get("/api/v1/embed/DEFINITELYNOTAREALDISTRICT99")
        assert resp.status_code == 404

    def test_theme_param_accepted(self, client: TestClient) -> None:
        resp = client.get("/api/v1/embed/VILLUPURAM?theme=dark")
        assert resp.status_code in (200, 404)

    def test_width_too_small_rejected(self, client: TestClient) -> None:
        resp = client.get("/api/v1/embed/VILLUPURAM?width=50")
        assert resp.status_code == 422

    def test_width_too_large_rejected(self, client: TestClient) -> None:
        resp = client.get("/api/v1/embed/VILLUPURAM?width=1000")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/embed/{district}/svg
# ---------------------------------------------------------------------------

class TestEmbedSvgEndpoint:
    def test_known_district_svg_status(self, client: TestClient) -> None:
        resp = client.get("/api/v1/embed/VILLUPURAM/svg")
        assert resp.status_code in (200, 404)

    def test_known_district_svg_content_type(self, client: TestClient) -> None:
        resp = client.get("/api/v1/embed/VILLUPURAM/svg")
        if resp.status_code == 200:
            assert "svg" in resp.headers["content-type"]

    def test_known_district_svg_starts_with_svg_tag(self, client: TestClient) -> None:
        resp = client.get("/api/v1/embed/VILLUPURAM/svg")
        if resp.status_code == 200:
            assert "<svg" in resp.text

    def test_nonexistent_district_svg_returns_404(self, client: TestClient) -> None:
        resp = client.get("/api/v1/embed/ZONETHATISNOWHERE/svg")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/v1/embed/{district}/json
# ---------------------------------------------------------------------------

class TestEmbedJsonEndpoint:
    def test_known_district_json_status(self, client: TestClient) -> None:
        resp = client.get("/api/v1/embed/VILLUPURAM/json")
        assert resp.status_code in (200, 404)

    def test_known_district_json_structure(self, client: TestClient) -> None:
        resp = client.get("/api/v1/embed/VILLUPURAM/json")
        if resp.status_code == 200:
            body = resp.json()
            assert "district" in body
            assert "state" in body
            assert "fin_year" in body
            assert "metrics" in body
            assert isinstance(body["metrics"], list)

    def test_nonexistent_district_json_returns_404(self, client: TestClient) -> None:
        resp = client.get("/api/v1/embed/DEFINITELYNOTAREALDISTRICT99/json")
        assert resp.status_code == 404

    def test_json_district_uppercased(self, client: TestClient) -> None:
        resp = client.get("/api/v1/embed/villupuram/json")
        if resp.status_code == 200:
            body = resp.json()
            assert body["district"] == body["district"].upper()


# ---------------------------------------------------------------------------
# GET /api/v1/pin/{code}
# ---------------------------------------------------------------------------

def _has_constituency_tables() -> bool:
    """Return True if the live DB has the constituency tables (populated via init_db or migration)."""
    import sqlite3
    from db.connection import DB_PATH

    try:
        conn = sqlite3.connect(str(DB_PATH))
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        conn.close()
        return "pin_district_mapping" in tables and "mp_info" in tables
    except Exception:
        return False


_NEEDS_CONSTITUENCY_TABLES = pytest.mark.skipif(
    not _has_constituency_tables(),
    reason="Constituency tables (pin_district_mapping, mp_info) not yet in live DB — run init_db or migration first",
)


class TestPinEndpoint:
    @_NEEDS_CONSTITUENCY_TABLES
    def test_valid_pin_code_does_not_crash(self, client: TestClient) -> None:
        resp = client.get("/api/v1/pin/800001")
        # 200 if in DB, 404 if not
        assert resp.status_code in (200, 404)

    def test_invalid_pin_format_returns_404(self, client: TestClient) -> None:
        # Non-numeric PIN or wrong length → mapper returns None → 404
        # This does NOT require the table to exist (mapper rejects before querying)
        resp = client.get("/api/v1/pin/ABCDEF")
        assert resp.status_code == 404

    @_NEEDS_CONSTITUENCY_TABLES
    def test_pin_with_data_returns_structure(self, client: TestClient) -> None:
        resp = client.get("/api/v1/pin/800001")
        if resp.status_code == 200:
            body = resp.json()
            assert "pin_code" in body
            assert "district" in body
            assert "state" in body
            assert "constituencies" in body

    @_NEEDS_CONSTITUENCY_TABLES
    def test_unknown_pin_returns_404(self, client: TestClient) -> None:
        resp = client.get("/api/v1/pin/000000")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/v1/constituency/search?q=X
# ---------------------------------------------------------------------------

class TestConstituencySearchEndpoint:
    @_NEEDS_CONSTITUENCY_TABLES
    def test_search_returns_200(self, client: TestClient) -> None:
        resp = client.get("/api/v1/constituency/search?q=PATNA")
        assert resp.status_code == 200

    @_NEEDS_CONSTITUENCY_TABLES
    def test_search_result_structure(self, client: TestClient) -> None:
        body = client.get("/api/v1/constituency/search?q=PATNA").json()
        assert "query" in body
        assert "results" in body
        assert "count" in body
        assert isinstance(body["results"], list)

    @_NEEDS_CONSTITUENCY_TABLES
    def test_search_count_matches_results_length(self, client: TestClient) -> None:
        body = client.get("/api/v1/constituency/search?q=A").json()
        assert body["count"] == len(body["results"])

    def test_search_missing_q_returns_422(self, client: TestClient) -> None:
        resp = client.get("/api/v1/constituency/search")
        assert resp.status_code == 422

    @_NEEDS_CONSTITUENCY_TABLES
    def test_search_empty_q_returns_200(self, client: TestClient) -> None:
        resp = client.get("/api/v1/constituency/search?q=")
        assert resp.status_code == 200

    @_NEEDS_CONSTITUENCY_TABLES
    def test_search_case_insensitive(self, client: TestClient) -> None:
        lower = client.get("/api/v1/constituency/search?q=patna").json()
        upper = client.get("/api/v1/constituency/search?q=PATNA").json()
        assert lower["count"] == upper["count"]


# ---------------------------------------------------------------------------
# POST /api/v1/investigate — validation errors only (no LLM call)
# ---------------------------------------------------------------------------

class TestInvestigateEndpoint:
    def test_missing_question_returns_422(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/investigate",
            json={"api_key": "dummy_key_1234567890"},
        )
        assert resp.status_code == 422

    def test_missing_api_key_returns_422(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/investigate",
            json={"question": "Which districts have the most misappropriation?"},
        )
        assert resp.status_code == 422

    def test_question_too_short_returns_422(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/investigate",
            json={"question": "Hi", "api_key": "dummy_key_1234567890"},
        )
        assert resp.status_code == 422

    def test_api_key_too_short_returns_422(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/investigate",
            json={"question": "Which districts?", "api_key": "short"},
        )
        assert resp.status_code == 422

    def test_invalid_provider_returns_422(self, client: TestClient) -> None:
        resp = client.post(
            "/api/v1/investigate",
            json={
                "question": "Which districts have the most misappropriation cases?",
                "api_key": "dummy_key_1234567890",
                "provider": "fakeprovider",
            },
        )
        assert resp.status_code == 422

    def test_valid_request_body_schema_accepted(self, client: TestClient) -> None:
        # A valid body reaches the LLM which will fail with a real API error (501/502)
        # since we don't have a real key — but validation should pass (not 422)
        resp = client.post(
            "/api/v1/investigate",
            json={
                "question": "Which districts in Bihar have the most MGNREGA misappropriation?",
                "api_key": "dummy_key_1234567890_long_enough",
                "provider": "gemini",
            },
        )
        # Should not be 422 (schema valid) — will be 501 (package missing) or 502 (LLM error)
        assert resp.status_code != 422


# ---------------------------------------------------------------------------
# GET /api/v1/trends/{district} — via district route
# ---------------------------------------------------------------------------

class TestTrendsViaDistrictRoute:
    """The district route includes trends data. This smoke-tests the trends path."""

    def test_district_route_with_trends_does_not_crash(self, client: TestClient) -> None:
        resp = client.get("/api/v1/district/VILLUPURAM")
        assert resp.status_code == 200

    def test_district_schemes_route_does_not_crash(self, client: TestClient) -> None:
        resp = client.get("/api/v1/district/VILLUPURAM/schemes")
        assert resp.status_code == 200

    def test_district_money_flow_route_does_not_crash(self, client: TestClient) -> None:
        resp = client.get("/api/v1/district/VILLUPURAM/money-flow")
        assert resp.status_code == 200
