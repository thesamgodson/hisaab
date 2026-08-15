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
    # The service picker is link-driven now (chips), not a GET <form>: every
    # choice is an anchor built by the shared actionHref() helper, so it still
    # carries ?issue= plus the area params into #action, and still works
    # without JavaScript.
    assert "actionHref(" in result
    assert "#action" in records
    assert 'href="#action"' in result
    assert "<SchemeDataSection" in result
    assert 'id="action"' in result
    assert '<details className="state-context">' in records
    assert "persona" not in page.lower()


def test_account_uses_lossless_progressive_disclosure() -> None:
    records = source("web/src/components/SchemeDataSection.tsx")
    scheme = source("web/src/components/SchemeRow.tsx")
    assert '<details className="ledger-scheme"' in scheme
    assert '<details className="coverage-limits text-disclosure">' in records
    assert "records.map" in scheme
    assert "record.metrics.map" in scheme
    assert "record.sourceUrl" in scheme
    assert "record.asOf" in scheme
    assert "record.retrievedAt" in scheme
    assert "record.claimId" in scheme
    assert "defaultOpen" not in scheme
    assert ".slice(" not in scheme


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
    # Numbered step chips were dropped in the 2026-08-15 restyle; the routes
    # render inline under plain headings. The counted labels — proof that every
    # route is served, none sliced away — are unchanged.
    assert "Complaint routes ({kit.channels.length})" in guide
    assert "Official routes ({universal.length})" in guide
    assert ".slice(" not in guide


def test_surface_has_visual_task_orientation_without_persona_modes() -> None:
    start = source("web/src/components/ServiceStart.tsx")
    result = source("web/src/components/AccountabilityResult.tsx")
    records = source("web/src/components/SchemeDataSection.tsx")
    scheme = source("web/src/components/SchemeRow.tsx")
    # The three numbered "01 / 02 / 03" rows are gone from the entry screen
    # (2026-08-15 restyle). The same task order is still stated in words: the
    # entry names step one, and the result surface names the evidence step and
    # the official-route step where the visitor actually reaches them.
    assert "Find your area" in start
    assert "What the district records say" in records
    assert "official routes" in result
    assert "districtSchemeCount" in result
    assert "DIMENSION_LABEL" in scheme
    assert "persona mode" not in start.lower()


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
