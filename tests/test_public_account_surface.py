from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def source(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_root_is_one_area_first_surface() -> None:
    page = source("web/src/app/page.tsx")
    result = source("web/src/components/AccountabilityResult.tsx")
    records = source("web/src/components/SchemeDataSection.tsx")
    assert "GeneralResult" not in page
    assert "resolveState" not in page
    assert 'action="/#action"' in result
    assert 'href="#action"' in result
    assert "<SchemeDataSection" in result
    assert 'id="action"' in result
    assert '<details className="state-context">' in records


def test_every_complaint_family_reaches_the_picker() -> None:
    page = source("web/src/app/page.tsx")
    result = source("web/src/components/AccountabilityResult.tsx")
    guide = source("web/src/components/ComplaintGuide.tsx")
    assert "complaintSchemes={kits.map((item) => item.scheme)}" in page
    assert "schemes={complaintSchemes}" in result
    assert "kit.channels.map" in guide
    assert "kit.complain_when.map" in guide
    assert "universal.map" in guide
    assert "Complete registration and any CAPTCHA on" in guide


def test_evidence_keeps_native_semantics_and_provenance() -> None:
    account = source("web/src/lib/area-account.ts")
    record = source("web/src/components/SchemeRow.tsx")
    assert "money_flow" not in account
    assert "installment = '22'" in account
    assert 'scheme: "NSAP"' in account
    assert "source_month" in account
    assert "nsapRecordDate" in account
    assert 'id: "pmgsy-money"' in account
    assert 'id: "pmgsy-delivery"' in account
    assert "date_of_data" in account
    assert "Record date:" in record
    assert "Retrieved" in record
    assert "record.claimId" in record


def test_representative_copy_never_claims_exactness() -> None:
    page = source("web/src/app/page.tsx")
    result = source("web/src/components/AccountabilityResult.tsx")
    action = source("web/src/lib/action-brief.ts")
    assert "districtBrief.mps" in page
    assert "does not claim an exact MLA" in page
    assert "Representative dataset" in result
    assert "mla: null" in action
    assert "estimated_parliamentary_constituency" in action
    assert "official record" not in result.lower()


def test_pin_api_labels_mapping_as_estimate() -> None:
    route = source("web/src/app/api/v1/pin/[pin_code]/route.ts")
    assert "precise: false" in route
    assert '"estimated_parliamentary_constituency"' in route
    assert 'assembly_match: "candidate_list"' in route
    assert 'mapping_claim_id: "DERIVED-2026-0002"' in route
