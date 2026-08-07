from __future__ import annotations

import json

import pytest

from scrapers import scrape_nsap_api as nsap


def _raw(
    district: str = "GANGTOK",
    code: str = "225",
    month: str = "02",
    beneficiaries: int = 100,
) -> dict:
    return {
        "state_name": "SIKKIM",
        "district_name": district,
        "scheme_code": "IGNOAPS",
        "lgd_state_code": "11",
        "lgd_district_code": code,
        "mnth": month,
        "total_beneficiaries": beneficiaries,
    }


def _curated(district: str, code: str | None = None) -> dict:
    record = {"state": "SIKKIM", "district": district}
    if code is not None:
        record["district_lgd_code"] = code
    return record


def test_latest_snapshot_uses_lgd_identity_and_fiscal_month_order() -> None:
    records = [
        _raw("EAST DISTRICT", month="06", beneficiaries=6436),
        _raw("GANGTOK", month="11", beneficiaries=703),
        _raw("GANGTOK", month="02", beneficiaries=3180),
    ]

    result = nsap.transform_records(records, "2025-2026", "now")

    assert len(result) == 1
    assert result[0]["district"] == "GANGTOK"
    assert result[0]["district_lgd_code"] == "225"
    assert result[0]["source_month"] == "02"
    assert result[0]["beneficiaries_paid"] == 3180


def test_newer_lgd_code_for_same_canonical_district_wins() -> None:
    records = [
        _raw("VAV-THARAD", code="400", month="01", beneficiaries=7313),
        _raw("VAV-THARAD", code="789", month="02", beneficiaries=12937),
    ]

    result = nsap.transform_records(records, "2025-2026", "now")

    assert len(result) == 1
    assert result[0]["district"] == "VAV THARAD"
    assert result[0]["district_lgd_code"] == "789"
    assert result[0]["beneficiaries_paid"] == 12937


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("lgd_district_code", "", "district identity"),
        ("lgd_district_code", "NA", "district identity"),
        ("mnth", "", "month"),
        ("mnth", "13", "month"),
    ],
)
def test_unusable_source_identity_or_month_fails(
    field: str, value: str, message: str
) -> None:
    record = _raw()
    record[field] = value

    with pytest.raises(ValueError, match=message):
        nsap.aggregate_latest_month([record])


def test_conflicting_same_month_snapshots_fail() -> None:
    with pytest.raises(ValueError, match="Conflicting NSAP snapshots"):
        nsap.aggregate_latest_month([_raw(beneficiaries=1), _raw(beneficiaries=2)])


def test_legacy_alias_maps_to_new_lgd_identity(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(nsap, "CURATED_DIR", tmp_path)
    old_path = tmp_path / "nsap_district_sikkim_latest.json"
    old_path.write_text(json.dumps([_curated("EAST DISTRICT")]))

    paths = nsap.save_curated_by_state([_curated("GANGTOK", "225")])

    assert paths["SIKKIM"] == old_path
    assert json.loads(old_path.read_text())[0]["district_lgd_code"] == "225"


def test_coverage_guard_rejects_lost_lgd_identity(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(nsap, "CURATED_DIR", tmp_path)
    path = tmp_path / "nsap_district_sikkim_latest.json"
    path.write_text(
        json.dumps([_curated("GANGTOK", "225"), _curated("MANGAN", "226")])
    )

    with pytest.raises(ValueError, match="lost 1 LGD district"):
        nsap.save_curated_by_state([_curated("GANGTOK", "225")])


def test_coverage_guard_fails_when_legacy_name_cannot_map(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(nsap, "CURATED_DIR", tmp_path)
    path = tmp_path / "nsap_district_sikkim_latest.json"
    path.write_text(json.dumps([_curated("UNKNOWN DISTRICT")]))

    with pytest.raises(ValueError, match="Cannot map existing NSAP identity"):
        nsap.save_curated_by_state([_curated("GANGTOK", "225")])
