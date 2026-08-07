from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEME_ROUTE = ROOT / "web/src/app/api/v1/scheme/[scheme]/route.ts"
DISTRICT_ROUTE = ROOT / "web/src/app/api/v1/district/[name]/[scheme]/route.ts"
WORST_ROUTE = ROOT / "web/src/app/api/v1/scheme/[scheme]/worst/route.ts"
DISTRICT_OVERVIEW_ROUTE = ROOT / "web/src/app/api/v1/district/[name]/route.ts"
BRIEF_ROUTE = ROOT / "web/src/app/api/v1/brief/[district]/route.ts"
RED_FLAGS_ROUTE = ROOT / "web/src/app/api/v1/red-flags/route.ts"


def section(source: str, start: str, end: str) -> str:
    return source.split(start, 1)[1].split(end, 1)[0]


def test_state_scheme_route_omits_unreported_money_and_false_status() -> None:
    route = SCHEME_ROUTE.read_text(encoding="utf-8")
    pmkisan = section(route, 'case "PM Kisan":', 'case "JJM":')
    poshan = section(route, 'case "PM POSHAN":', 'case "NSAP":')
    nsap = section(route, 'case "NSAP":', 'case "PDS/NFSA":')
    nfsa = section(route, 'case "PDS/NFSA":', "default:")

    assert "NULL as total_amount" in pmkisan
    assert "SUM(amount_paid_lakhs)" not in pmkisan
    assert "does not publish money" in pmkisan
    assert "daily meal snapshot" in poshan
    assert "not a coverage denominator" in poshan
    assert "COUNT(DISTINCT UPPER(district)) as districts" in nsap
    assert "NULL as total_amount" in nsap
    assert "District spending is not published" in nsap
    assert "NULL as active_cards" in nfsa
    assert "Active-card status is not separately published" in nfsa


def test_district_scheme_route_nulls_placeholders_before_response() -> None:
    route = DISTRICT_ROUTE.read_text(encoding="utf-8")
    pmkisan = section(route, "pmkisan: {", "jjm: {")
    poshan = section(route, "pmposhan: {", "nsap: {")
    nsap = section(route, "nsap: {", "nfsa: {")
    nfsa = section(route, "nfsa: {", "};")

    assert "amount_paid_lakhs: null" in pmkisan
    assert "Amount paid:" not in pmkisan
    assert "daily meal-reporting snapshot" in poshan
    assert "Feeding coverage:" not in poshan
    assert "funds_released_lakhs: null" in poshan
    assert "utilization_pct: null" in poshan
    assert "amount_paid_lakhs: null" in nsap
    assert "pension_per_month: null" in nsap
    assert "no money amount is reported" in nsap
    assert "SUM(beneficiaries_paid) as beneficiaries_paid" in route
    assert "GROUP_CONCAT(scheme_type, ', ') as scheme_types" in route
    assert "Programme counts are summed" in nsap
    assert "ration_cards_active: null" in nfsa
    assert "Active ration cards:" not in nfsa
    assert "data: publicRow" in route


def test_worst_route_rejects_raw_count_rankings_without_denominators() -> None:
    route = WORST_ROUTE.read_text(encoding="utf-8")
    assert '"PM Kisan":' in route
    assert "smaller district count is not evidence of worse delivery" in route
    assert "worst PM Kisan districts" not in route
    assert "CLAIM-2026-0041" in route
    assert "CLAIM-2026-0029" in route


def test_mgnrega_social_audit_money_is_never_treated_as_lakhs() -> None:
    routes = [
        SCHEME_ROUTE.read_text(encoding="utf-8"),
        DISTRICT_ROUTE.read_text(encoding="utf-8"),
        DISTRICT_OVERVIEW_ROUTE.read_text(encoding="utf-8"),
        BRIEF_ROUTE.read_text(encoding="utf-8"),
        RED_FLAGS_ROUTE.read_text(encoding="utf-8"),
    ]
    for route in routes:
        assert 'amount_reported), "lakhs"' not in route
        assert "formatLakhs" not in route
    assert "formatRupees(r.total_reported)" in routes[0]
    assert 'fmtRs(Number(row.amount_reported))' in routes[1]
    assert 'fmtRs(Number(row.amount_reported))' in routes[2]
    assert "fmtRs(amtReported)" in routes[3]
    assert "formatRupees(top.amount_reported)" in routes[4]


def test_legacy_brief_does_not_invent_runtime_red_flags() -> None:
    route = BRIEF_ROUTE.read_text(encoding="utf-8")
    assert "RED FLAG:" not in route
    assert "recoveryPct" not in route
    assert "utilizationPct" not in route
    assert "completionPct" not in route
