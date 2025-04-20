"""Integration tests for the Hisaab FastAPI application.

Uses starlette TestClient against the real DB at data/hisaab.db so all
endpoints exercise the same data path as production.  Each test is
deliberately narrow: status code + required top-level keys + basic type
assertions.  No mutation of DB state.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from api.main import app

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Shared TestClient for the whole module (DB is read-only)."""
    return TestClient(app)


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------


def test_root_ok(client: TestClient) -> None:
    resp = client.get("/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "Hisaab API"
    assert isinstance(body["endpoints"], list)
    assert len(body["endpoints"]) > 0


# ---------------------------------------------------------------------------
# GET /api/v1/schemes
# ---------------------------------------------------------------------------


def test_schemes_status(client: TestClient) -> None:
    resp = client.get("/api/v1/schemes")
    assert resp.status_code == 200


def test_schemes_structure(client: TestClient) -> None:
    body = client.get("/api/v1/schemes").json()
    assert "schemes" in body
    assert "count" in body
    assert isinstance(body["count"], int)
    assert body["count"] == 8


def test_schemes_each_has_name_and_warnings(client: TestClient) -> None:
    body = client.get("/api/v1/schemes").json()
    for scheme in body["schemes"]:
        assert "name" in scheme
        assert isinstance(scheme["name"], str)
        assert "warnings" in scheme
        assert isinstance(scheme["warnings"], list)


# ---------------------------------------------------------------------------
# GET /api/v1/scheme/{name}
# ---------------------------------------------------------------------------


def test_scheme_mgnrega_ok(client: TestClient) -> None:
    resp = client.get("/api/v1/scheme/MGNREGA")
    assert resp.status_code == 200


def test_scheme_mgnrega_structure(client: TestClient) -> None:
    body = client.get("/api/v1/scheme/MGNREGA").json()
    assert "answer" in body
    assert isinstance(body["answer"], str)
    assert "data" in body


def test_scheme_pmgsy_ok(client: TestClient) -> None:
    resp = client.get("/api/v1/scheme/PMGSY")
    assert resp.status_code == 200


def test_scheme_pmgsy_structure(client: TestClient) -> None:
    body = client.get("/api/v1/scheme/PMGSY").json()
    assert "answer" in body
    assert "data" in body


def test_scheme_pmkisan_ok(client: TestClient) -> None:
    resp = client.get("/api/v1/scheme/PM Kisan")
    assert resp.status_code == 200


def test_scheme_invalid_returns_404(client: TestClient) -> None:
    resp = client.get("/api/v1/scheme/FAKESCHEME")
    assert resp.status_code == 404


def test_scheme_invalid_detail_mentions_valid(client: TestClient) -> None:
    body = client.get("/api/v1/scheme/FAKESCHEME").json()
    assert "detail" in body
    assert "MGNREGA" in body["detail"]


# ---------------------------------------------------------------------------
# GET /api/v1/scheme/{name}/worst
# ---------------------------------------------------------------------------


def test_scheme_worst_mgnrega_ok(client: TestClient) -> None:
    resp = client.get("/api/v1/scheme/MGNREGA/worst")
    assert resp.status_code == 200


def test_scheme_worst_mgnrega_structure(client: TestClient) -> None:
    body = client.get("/api/v1/scheme/MGNREGA/worst").json()
    assert "answer" in body
    assert "data" in body
    assert "source_url" in body


def test_scheme_worst_mgnrega_data_is_list(client: TestClient) -> None:
    body = client.get("/api/v1/scheme/MGNREGA/worst?limit=3").json()
    assert isinstance(body["data"], list)
    assert len(body["data"]) <= 3


def test_scheme_worst_pmgsy_ok(client: TestClient) -> None:
    resp = client.get("/api/v1/scheme/PMGSY/worst")
    assert resp.status_code == 200


def test_scheme_worst_invalid_returns_404(client: TestClient) -> None:
    resp = client.get("/api/v1/scheme/NOTASCHEME/worst")
    assert resp.status_code == 404


def test_scheme_worst_limit_query_param(client: TestClient) -> None:
    body = client.get("/api/v1/scheme/MGNREGA/worst?limit=5").json()
    assert isinstance(body["data"], list)
    assert len(body["data"]) <= 5


# ---------------------------------------------------------------------------
# GET /api/v1/district/{name}
# ---------------------------------------------------------------------------


def test_district_known_ok(client: TestClient) -> None:
    resp = client.get("/api/v1/district/VILLUPURAM")
    assert resp.status_code == 200


def test_district_known_structure(client: TestClient) -> None:
    body = client.get("/api/v1/district/VILLUPURAM").json()
    assert "answer" in body
    assert isinstance(body["answer"], str)


def test_district_unknown_returns_200_with_no_data(client: TestClient) -> None:
    # District endpoint does NOT raise 404 — returns empty answer instead.
    resp = client.get("/api/v1/district/DEFINITELYNOTADISTRICT99")
    assert resp.status_code == 200
    body = resp.json()
    assert "answer" in body


def test_district_with_explicit_state(client: TestClient) -> None:
    resp = client.get("/api/v1/district/VILLUPURAM?state=TAMIL+NADU")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# GET /api/v1/brief/{district}
# ---------------------------------------------------------------------------


def test_brief_known_district_ok(client: TestClient) -> None:
    resp = client.get("/api/v1/brief/VILLUPURAM")
    assert resp.status_code == 200


def test_brief_known_district_structure(client: TestClient) -> None:
    body = client.get("/api/v1/brief/VILLUPURAM").json()
    assert "district" in body
    assert "state" in body
    assert "brief" in body
    assert "format" in body


def test_brief_district_uppercase(client: TestClient) -> None:
    body = client.get("/api/v1/brief/villupuram").json()
    assert body["district"] == "VILLUPURAM"


def test_brief_format_is_plain_text(client: TestClient) -> None:
    body = client.get("/api/v1/brief/VILLUPURAM").json()
    assert body["format"] == "plain_text"


def test_brief_brief_is_string(client: TestClient) -> None:
    body = client.get("/api/v1/brief/VILLUPURAM").json()
    assert isinstance(body["brief"], str)


def test_brief_unknown_district_ok(client: TestClient) -> None:
    # brief endpoint returns 200 even for unknown districts (brief text may be empty/minimal)
    resp = client.get("/api/v1/brief/ZONETHATISNOWHERE")
    assert resp.status_code == 200
    body = resp.json()
    assert "district" in body
    assert "brief" in body


# ---------------------------------------------------------------------------
# GET /api/v1/freshness
# ---------------------------------------------------------------------------


def test_freshness_status(client: TestClient) -> None:
    resp = client.get("/api/v1/freshness")
    assert resp.status_code == 200


def test_freshness_structure(client: TestClient) -> None:
    body = client.get("/api/v1/freshness").json()
    assert "freshness" in body
    assert "total_records" in body
    assert isinstance(body["total_records"], int)
    assert isinstance(body["freshness"], list)


def test_freshness_eight_schemes(client: TestClient) -> None:
    body = client.get("/api/v1/freshness").json()
    assert len(body["freshness"]) == 8


def test_freshness_entry_keys(client: TestClient) -> None:
    body = client.get("/api/v1/freshness").json()
    required = {"scheme", "source", "latest_scraped", "records", "states"}
    for entry in body["freshness"]:
        assert required.issubset(entry.keys()), f"Missing keys in {entry}"


def test_freshness_records_are_non_negative(client: TestClient) -> None:
    body = client.get("/api/v1/freshness").json()
    for entry in body["freshness"]:
        assert entry["records"] >= 0


def test_freshness_total_records_positive(client: TestClient) -> None:
    body = client.get("/api/v1/freshness").json()
    assert body["total_records"] > 0


# ---------------------------------------------------------------------------
# GET /api/v1/data-quality
# ---------------------------------------------------------------------------


def test_data_quality_status(client: TestClient) -> None:
    resp = client.get("/api/v1/data-quality")
    assert resp.status_code == 200


def test_data_quality_is_dict(client: TestClient) -> None:
    body = client.get("/api/v1/data-quality").json()
    assert isinstance(body, dict)


def test_data_quality_values_are_lists(client: TestClient) -> None:
    body = client.get("/api/v1/data-quality").json()
    for scheme, warnings in body.items():
        assert isinstance(warnings, list), f"{scheme} warnings must be a list"


def test_data_quality_known_schemes_present(client: TestClient) -> None:
    body = client.get("/api/v1/data-quality").json()
    expected = {"MGNREGA", "PMGSY", "PM Kisan", "NSAP"}
    for scheme in expected:
        assert scheme in body, f"{scheme} missing from data-quality"


# ---------------------------------------------------------------------------
# GET /api/v1/red-flags
# ---------------------------------------------------------------------------


def test_red_flags_status(client: TestClient) -> None:
    resp = client.get("/api/v1/red-flags")
    assert resp.status_code == 200


def test_red_flags_structure(client: TestClient) -> None:
    body = client.get("/api/v1/red-flags").json()
    assert "misappropriation" in body
    assert "pmgsy_completion" in body
    assert "jjm_coverage" in body


def test_red_flags_misappropriation_has_answer(client: TestClient) -> None:
    body = client.get("/api/v1/red-flags").json()
    misap = body["misappropriation"]
    assert isinstance(misap, dict)
    assert "answer" in misap


def test_red_flags_limit_param(client: TestClient) -> None:
    body_5 = client.get("/api/v1/red-flags?limit=5").json()
    data = body_5["misappropriation"].get("data", [])
    assert isinstance(data, list)
    assert len(data) <= 5


# ---------------------------------------------------------------------------
# POST /api/v1/query
# ---------------------------------------------------------------------------


def test_query_valid_ok(client: TestClient) -> None:
    resp = client.post("/api/v1/query", json={"text": "misappropriation in villupuram"})
    assert resp.status_code == 200


def test_query_valid_structure(client: TestClient) -> None:
    body = client.post("/api/v1/query", json={"text": "misappropriation in villupuram"}).json()
    required = {"query", "intent", "district", "answer", "lang"}
    assert required.issubset(body.keys())


def test_query_echoes_input_text(client: TestClient) -> None:
    text = "misappropriation in villupuram"
    body = client.post("/api/v1/query", json={"text": text}).json()
    assert body["query"] == text


def test_query_answer_is_string(client: TestClient) -> None:
    body = client.post("/api/v1/query", json={"text": "worst roads bihar"}).json()
    assert isinstance(body["answer"], str)


def test_query_lang_default_is_en(client: TestClient) -> None:
    body = client.post("/api/v1/query", json={"text": "funds cuddalore"}).json()
    assert body["lang"] == "en"


def test_query_lang_override(client: TestClient) -> None:
    body = client.post("/api/v1/query", json={"text": "funds cuddalore", "lang": "hi"}).json()
    assert body["lang"] == "hi"


def test_query_empty_text_returns_422(client: TestClient) -> None:
    resp = client.post("/api/v1/query", json={"text": ""})
    assert resp.status_code == 422


def test_query_missing_text_returns_422(client: TestClient) -> None:
    resp = client.post("/api/v1/query", json={})
    assert resp.status_code == 422


def test_query_invalid_lang_returns_422(client: TestClient) -> None:
    resp = client.post("/api/v1/query", json={"text": "some query", "lang": "xx"})
    assert resp.status_code == 422


def test_query_text_too_long_returns_422(client: TestClient) -> None:
    resp = client.post("/api/v1/query", json={"text": "a" * 501})
    assert resp.status_code == 422
