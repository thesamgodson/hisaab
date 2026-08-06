"""Tests for the citizen action brief system."""

import sqlite3
from datetime import date, datetime

import pytest


@pytest.fixture
def db():
    """In-memory SQLite database with action brief tables."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    from db.schema import SCHEMA
    conn.executescript(SCHEMA)
    return conn


def test_district_officials_table_exists(db):
    row = db.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='district_officials'"
    ).fetchone()
    assert row is not None
    sql = row[0].lower()
    assert "state" in sql
    assert "district" in sql
    assert "role" in sql
    assert "name" in sql
    assert "source_url" in sql
    assert "scraped_at" in sql


def test_grievance_channels_table_exists(db):
    row = db.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='grievance_channels'"
    ).fetchone()
    assert row is not None
    sql = row[0].lower()
    assert "scheme" in sql
    assert "level" in sql
    assert "portal_name" in sql
    assert "portal_url" in sql


def test_district_officials_insert_and_pk(db):
    db.execute(
        """INSERT INTO district_officials
           (state, district, role, name, phone, email, office_address, source_url, scraped_at)
           VALUES ('UTTAR PRADESH', 'VARANASI', 'District Collector', 'Test Name',
                   '1234567890', 'test@nic.in', 'DC Office', 'https://varanasi.nic.in', '2026-03-30T00:00:00')"""
    )
    row = db.execute(
        "SELECT * FROM district_officials WHERE district='VARANASI' AND role='District Collector'"
    ).fetchone()
    assert row["name"] == "Test Name"

    db.execute(
        """INSERT OR REPLACE INTO district_officials
           (state, district, role, name, phone, email, office_address, source_url, scraped_at)
           VALUES ('UTTAR PRADESH', 'VARANASI', 'District Collector', 'New Name',
                   NULL, NULL, NULL, 'https://varanasi.nic.in', '2026-03-31T00:00:00')"""
    )
    row = db.execute(
        "SELECT * FROM district_officials WHERE district='VARANASI' AND role='District Collector'"
    ).fetchone()
    assert row["name"] == "New Name"


def test_grievance_channels_insert_and_pk(db):
    db.execute(
        """INSERT INTO grievance_channels
           (scheme, level, portal_name, portal_url, phone, description,
            escalation_scheme, source_url, scraped_at)
           VALUES ('MGNREGA', 'national', 'CPGRAMS', 'https://pgportal.gov.in/',
                   '1800-111-555', 'Central grievance portal', NULL,
                   'https://pgportal.gov.in/', '2026-03-30T00:00:00')"""
    )
    row = db.execute(
        "SELECT * FROM grievance_channels WHERE scheme='MGNREGA' AND level='national'"
    ).fetchone()
    assert row["portal_name"] == "CPGRAMS"


def test_diagnosis_item_frozen():
    from action_brief.models import DiagnosisItem
    item = DiagnosisItem(
        severity="high", scheme="MGNREGA",
        summary="Only 8% of misappropriated funds recovered.",
        detail="Rs 4.2 crore flagged, Rs 3.9 crore unrecovered.",
        amount="Rs 3.9 crore", source_url="https://nrega.nic.in/",
    )
    assert item.severity == "high"
    with pytest.raises(AttributeError):
        item.severity = "low"


def test_contact_card_frozen():
    from action_brief.models import ContactCard
    card = ContactCard(
        role="District Collector", name="Test DC", phone="9876543210",
        email="dc@nic.in", office_address="DC Office",
        relevance="Oversees all district-level schemes",
        source_url="https://varanasi.nic.in",
        last_verified=date(2026, 3, 15), freshness="fresh",
    )
    assert card.role == "District Collector"


def test_action_item_frozen():
    from action_brief.models import ActionItem
    item = ActionItem(
        scheme="MGNREGA", action="File a complaint about delayed wages",
        portal_name="MGNREGA Public Grievance",
        portal_url="https://nrega.nic.in/Nregahome/EComplaint.aspx",
        escalation="If no response in 30 days, escalate to CPGRAMS",
        escalation_url="https://pgportal.gov.in/",
    )
    assert item.scheme == "MGNREGA"


def test_action_brief_frozen():
    from action_brief.models import ActionBrief
    brief = ActionBrief(
        pin="221001", district="VARANASI", state="UTTAR PRADESH",
        mp=None, mla=None, diagnosis=[], contacts=[], actions=[],
        scheme_data={}, generated_at=datetime.now(),
    )
    assert brief.pin == "221001"
    assert brief.diagnosis == []


def test_action_items_for_flagged_schemes(db):
    from directory.seed_data import seed_grievance_channels
    seed_grievance_channels(db)
    from action_brief.actions import build_actions
    actions = build_actions(db, ["MGNREGA", "PMAY-G"])
    schemes = {a.scheme for a in actions}
    assert "MGNREGA" in schemes
    assert "PMAY-G" in schemes
    for a in actions:
        assert a.portal_url.startswith("http")
        assert a.escalation_url.startswith("http")


def test_action_items_empty_when_no_flags(db):
    from directory.seed_data import seed_grievance_channels
    seed_grievance_channels(db)
    from action_brief.actions import build_actions
    actions = build_actions(db, [])
    assert actions == []


def test_action_items_always_include_cpgrams_escalation(db):
    from directory.seed_data import seed_grievance_channels
    seed_grievance_channels(db)
    from action_brief.actions import build_actions
    actions = build_actions(db, ["MGNREGA"])
    for a in actions:
        assert "CPGRAMS" in a.escalation or "pgportal" in a.escalation_url


# ---------------------------------------------------------------------------
# Diagnosis engine tests
# ---------------------------------------------------------------------------

def test_diagnosis_mgnrega_low_recovery(db):
    db.execute(
        """INSERT INTO misappropriation
           (district, state, state_code, fin_year, cases_reported, amount_reported, amount_recovered,
            recovery_rate_pct, source_url, scraped_at)
           VALUES ('VARANASI', 'UTTAR PRADESH', 'UP', '2024-2025', 50, 420, 34,
                   8.1, 'https://nrega.nic.in/', '2026-03-30T00:00:00')"""
    )
    db.commit()
    from action_brief.diagnosis import build_diagnosis
    items = build_diagnosis(db, "VARANASI", "UTTAR PRADESH")
    assert len(items) >= 1
    mgnrega = [i for i in items if i.scheme == "MGNREGA"]
    assert len(mgnrega) >= 1
    assert mgnrega[0].severity == "high"
    assert "recover" in mgnrega[0].summary.lower()
    assert mgnrega[0].source_url


def test_diagnosis_pmayg_low_completion(db):
    db.execute(
        """INSERT INTO pmayg_district
           (district, state, fin_year, houses_sanctioned, houses_completed,
            houses_occupied, completion_pct, source_url, scraped_at)
           VALUES ('VARANASI', 'UTTAR PRADESH', '2024-2025', 1000, 300,
                   200, 30.0, 'https://pmayg.nic.in/', '2026-03-30T00:00:00')"""
    )
    db.commit()
    from action_brief.diagnosis import build_diagnosis
    items = build_diagnosis(db, "VARANASI", "UTTAR PRADESH")
    pmayg = [i for i in items if i.scheme == "PMAY-G"]
    assert len(pmayg) >= 1
    assert "house" in pmayg[0].summary.lower() or "built" in pmayg[0].summary.lower()


def test_diagnosis_no_flags(db):
    from action_brief.diagnosis import build_diagnosis
    items = build_diagnosis(db, "NONEXISTENT", "NOWHERE")
    assert items == []


def test_diagnosis_max_5_items(db):
    db.execute("""INSERT INTO misappropriation (district, state, state_code, fin_year, cases_reported, amount_reported, amount_recovered, recovery_rate_pct, source_url, scraped_at) VALUES ('BADPLACE', 'BADSTATE', 'BS', '2024-2025', 200, 1000, 0, 0.0, 'https://nrega.nic.in/', '2026-03-30T00:00:00')""")
    db.execute("""INSERT INTO financial_statement (district, state, state_code, fin_year, total_availability, cumulative_expenditure, utilization_pct, source_url, scraped_at) VALUES ('BADPLACE', 'BADSTATE', 'BS', '2024-2025', 5000, 1000, 20.0, 'https://nrega.nic.in/', '2026-03-30T00:00:00')""")
    db.execute("""INSERT INTO pmayg_district (district, state, fin_year, houses_sanctioned, houses_completed, houses_occupied, completion_pct, source_url, scraped_at) VALUES ('BADPLACE', 'BADSTATE', '2024-2025', 1000, 100, 30, 10.0, 'https://pmayg.nic.in/', '2026-03-30T00:00:00')""")
    db.execute("""INSERT INTO jjm_district (district, state, total_households, households_with_tap, coverage_pct, funds_released_lakhs, funds_utilized_lakhs, source_url, scraped_at) VALUES ('BADPLACE', 'BADSTATE', 10000, 1000, 10.0, 500, 50, 'https://ejalshakti.gov.in/', '2026-03-30T00:00:00')""")
    db.execute("""INSERT INTO pmposhan_district (district, state, fin_year, children_enrolled, children_fed, source_url, scraped_at) VALUES ('BADPLACE', 'BADSTATE', '2024-2025', 10000, 1000, 'https://pmposhan.education.gov.in/', '2026-03-30T00:00:00')""")
    db.execute("""INSERT INTO nfsa_district (district, state, fin_year, ration_cards_total, ration_cards_active, allocation_mt, offtake_mt, offtake_pct, source_url, scraped_at) VALUES ('BADPLACE', 'BADSTATE', '2024-2025', 10000, 3000, 100.0, 20.0, 20.0, 'https://nfsa.gov.in/', '2026-03-30T00:00:00')""")
    db.commit()
    from action_brief.diagnosis import build_diagnosis
    items = build_diagnosis(db, "BADPLACE", "BADSTATE")
    assert len(items) <= 5


def test_diagnosis_sorted_by_severity(db):
    db.execute("""INSERT INTO misappropriation (district, state, state_code, fin_year, cases_reported, amount_reported, amount_recovered, recovery_rate_pct, source_url, scraped_at) VALUES ('SORTTEST', 'SORTSTATE', 'SS', '2024-2025', 50, 420, 0, 0.0, 'https://nrega.nic.in/', '2026-03-30T00:00:00')""")
    db.execute("""INSERT INTO jjm_district (district, state, total_households, households_with_tap, coverage_pct, funds_released_lakhs, funds_utilized_lakhs, source_url, scraped_at) VALUES ('SORTTEST', 'SORTSTATE', 10000, 4000, 40.0, 500, 400, 'https://ejalshakti.gov.in/', '2026-03-30T00:00:00')""")
    db.commit()
    from action_brief.diagnosis import build_diagnosis
    items = build_diagnosis(db, "SORTTEST", "SORTSTATE")
    if len(items) >= 2:
        severity_order = {"high": 0, "medium": 1, "low": 2}
        for i in range(len(items) - 1):
            assert severity_order[items[i].severity] <= severity_order[items[i + 1].severity]


# ---------------------------------------------------------------------------
# Contacts builder tests
# ---------------------------------------------------------------------------

def test_contacts_ordering(db):
    from datetime import datetime as dt
    now = dt.now().isoformat()
    db.execute(
        """INSERT INTO district_officials VALUES
           ('UTTAR PRADESH', 'VARANASI', 'District Collector', 'Test DC',
            '9876543210', NULL, NULL, 'https://varanasi.nic.in', ?)""", (now,))
    db.execute(
        """INSERT INTO district_officials VALUES
           ('UTTAR PRADESH', 'VARANASI', 'MGNREGA Programme Officer', 'Test PO',
            NULL, NULL, NULL, 'https://varanasi.nic.in', ?)""", (now,))
    db.commit()

    from action_brief.contacts import build_contacts
    mp_info = {"mp_name": "Test MP", "party": "INC", "constituency": "VARANASI",
               "state": "UTTAR PRADESH", "source_url": "https://eci.gov.in"}
    mla_info = {"mla_name": "Test MLA", "party": "BJP", "ac_name": "VARANASI CANTT",
                "state": "UTTAR PRADESH", "source_url": "https://myneta.info"}
    contacts = build_contacts(
        db, "VARANASI", "UTTAR PRADESH",
        mp_info=mp_info, mla_info=mla_info, flagged_schemes=["MGNREGA"],
    )
    roles = [c.role for c in contacts]
    assert roles[0] == "Member of Parliament"
    assert roles[1] == "MLA"
    assert roles[2] == "District Collector"
    assert "MGNREGA Programme Officer" in roles


def test_contacts_mp_mla_dc_always_shown(db):
    from datetime import datetime as dt
    now = dt.now().isoformat()
    db.execute(
        """INSERT INTO district_officials VALUES
           ('UTTAR PRADESH', 'VARANASI', 'District Collector', 'Test DC',
            '9876543210', NULL, NULL, 'https://varanasi.nic.in', ?)""", (now,))
    db.commit()

    from action_brief.contacts import build_contacts
    mp_info = {"mp_name": "Test MP", "party": "INC", "constituency": "VARANASI",
               "state": "UTTAR PRADESH", "source_url": "https://eci.gov.in"}
    contacts = build_contacts(
        db, "VARANASI", "UTTAR PRADESH",
        mp_info=mp_info, mla_info=None, flagged_schemes=[],
    )
    roles = [c.role for c in contacts]
    assert "Member of Parliament" in roles
    assert "District Collector" in roles


# ---------------------------------------------------------------------------
# SVG card generation tests
# ---------------------------------------------------------------------------

def test_card_portrait_svg():
    from action_brief.card import generate_action_card
    from action_brief.models import ActionBrief, DiagnosisItem
    brief = ActionBrief(
        pin="221001", district="VARANASI", state="UTTAR PRADESH",
        mp={"mp_name": "Test MP", "party": "BJP"},
        mla={"mla_name": "Test MLA", "party": "INC"},
        diagnosis=[DiagnosisItem(
            severity="high", scheme="MGNREGA",
            summary="Rs 3.9 crore MGNREGA funds unrecovered",
            detail="", amount="Rs 3.9 crore", source_url="https://nrega.nic.in/",
        )],
        contacts=[], actions=[], scheme_data={},
        generated_at=datetime(2026, 3, 30, 14, 30),
    )
    svg_bytes = generate_action_card(brief, fmt="portrait")
    svg_str = svg_bytes.decode("utf-8")
    assert svg_str.startswith("<?xml")
    assert "VARANASI" in svg_str
    assert "UTTAR PRADESH" in svg_str
    assert "MGNREGA" in svg_str
    assert "Test MP" in svg_str
    assert "hisaab" in svg_str.lower()


def test_card_landscape_svg():
    from action_brief.card import generate_action_card
    from action_brief.models import ActionBrief
    brief = ActionBrief(
        pin="221001", district="VARANASI", state="UTTAR PRADESH",
        mp={"mp_name": "Test MP", "party": "BJP"}, mla=None,
        diagnosis=[], contacts=[], actions=[], scheme_data={},
        generated_at=datetime(2026, 3, 30, 14, 30),
    )
    svg_bytes = generate_action_card(brief, fmt="landscape")
    svg_str = svg_bytes.decode("utf-8")
    assert 'width="1200"' in svg_str
    assert 'height="630"' in svg_str


# ---------------------------------------------------------------------------
# Engine orchestrator tests
# ---------------------------------------------------------------------------

def test_engine_valid_pin(db):
    """Full pipeline: PIN → ActionBrief."""
    db.execute(
        """INSERT INTO pin_district_mapping (pin_code, district, state, office_name)
           VALUES ('221001', 'VARANASI', 'UTTAR PRADESH', 'Varanasi GPO')"""
    )
    db.execute(
        """INSERT INTO misappropriation
           (district, state, state_code, fin_year, cases_reported, amount_reported, amount_recovered,
            recovery_rate_pct, source_url, scraped_at)
           VALUES ('VARANASI', 'UTTAR PRADESH', 'UP', '2024-2025', 50, 420, 34,
                   8.1, 'https://nrega.nic.in/', '2026-03-30T00:00:00')"""
    )
    db.commit()
    from directory.seed_data import seed_grievance_channels
    seed_grievance_channels(db)

    from action_brief.engine import build_action_brief
    brief = build_action_brief("221001", conn=db)
    assert brief is not None
    assert brief.pin == "221001"
    assert brief.district == "VARANASI"
    assert brief.state == "UTTAR PRADESH"
    assert len(brief.diagnosis) >= 1
    assert brief.generated_at is not None


def test_engine_mp_falls_back_to_pin_constituency(db):
    """Delhi has no constituency_district rows — the spatial PIN→PC match must
    still resolve the MP rather than leaving the brief blank."""
    db.execute(
        """INSERT INTO pin_district_mapping (pin_code, district, state, office_name)
           VALUES ('110018', 'WEST', 'DELHI', 'Delhi Cantt')"""
    )
    db.execute(
        """INSERT INTO pin_constituency (pin_code, constituency, state, method)
           VALUES ('110018', 'WEST DELHI', 'DELHI', 'spatial_join')"""
    )
    db.execute(
        """INSERT INTO mp_info (constituency, mp_name, party, state, elected_year, source_url)
           VALUES ('WEST DELHI', 'KAMALJEET SEHRAWAT', 'BJP', 'DELHI', 2024, 'https://eci.gov.in')"""
    )
    db.commit()

    from action_brief.engine import build_action_brief
    brief = build_action_brief("110018", conn=db)
    assert brief is not None
    assert brief.mp is not None
    assert brief.mp["mp_name"] == "KAMALJEET SEHRAWAT"


def test_engine_schemes_checked_reports_what_was_looked_at(db):
    db.execute(
        """INSERT INTO pin_district_mapping (pin_code, district, state, office_name)
           VALUES ('110018', 'WEST', 'DELHI', 'Delhi Cantt')"""
    )
    db.commit()

    from action_brief.engine import build_action_brief
    thin = build_action_brief("110018", conn=db)
    assert thin is not None
    assert thin.diagnosis == []
    assert thin.schemes_checked == []

    db.execute(
        """INSERT INTO pmayg_district
           (district, state, fin_year, houses_sanctioned, houses_completed,
            houses_occupied, completion_pct, source_url, scraped_at)
           VALUES ('WEST', 'DELHI', '2024-2025', 1000, 900, 800, 90.0,
                   'https://pmayg.nic.in/', '2026-03-30T00:00:00')"""
    )
    db.commit()

    checked = build_action_brief("110018", conn=db)
    assert checked is not None
    assert checked.diagnosis == []
    assert checked.schemes_checked == ["PMAY-G"]


def _seed_complaint_data(db):
    db.execute(
        """INSERT INTO pin_district_mapping (pin_code, district, state, office_name)
           VALUES ('632001', 'VELLORE', 'TAMIL NADU', 'Vellore HO')"""
    )
    db.execute(
        """INSERT INTO grievance_channels
           (scheme, level, authority, portal_name, portal_url, phone,
            description, source_url, scraped_at)
           VALUES
           ('MGNREGA','local','Programme Officer','Block office','https://nrega.dord.gov.in',NULL,
            'Written complaint at the Block office','https://nrega.dord.gov.in','2026-08-06'),
           ('MGNREGA','national','Ministry of Rural Development','CPGRAMS','https://pgportal.gov.in',NULL,
            'Lodge on CPGRAMS','https://pgportal.gov.in','2026-08-06'),
           ('PDS/NFSA','local','State PDS helpline','PDS toll-free','https://nfsa.gov.in','1967',
            'Call 1967','https://nfsa.gov.in','2026-08-06'),
           ('ALL','national','DARPG','CPGRAMS','https://pgportal.gov.in',NULL,
            'Any scheme, any ministry','https://pgportal.gov.in','2026-08-06')"""
    )
    db.execute(
        """INSERT INTO scheme_entitlements
           (scheme, entitlement, legal_basis, complain_when, source_url, scraped_at)
           VALUES ('MGNREGA','Wages within 15 days plus delay compensation',
                   'MGNREGA Act 2005 s.3(3), Schedule II para 29(1)',
                   '["Wages pending beyond 15 days"]',
                   'https://www.indiacode.nic.in','2026-08-06')"""
    )
    # District presence: MGNREGA via financial_statement (money_flow branch).
    db.execute(
        """INSERT INTO financial_statement
           (district, state, state_code, fin_year, total_availability,
            cumulative_expenditure, utilization_pct, source_url, scraped_at)
           VALUES ('VELLORE', 'TAMIL NADU', 'TN', '2024-2025', 1000, 400, 40.0,
                   'https://x.gov.in', '2026-03-30T00:00:00')"""
    )
    # Flag trigger for the PYTHON twin: its MGNREGA checker reads
    # misappropriation at FIN_YEAR with recovery_rate_pct < 20.
    from briefs.formatting import FIN_YEAR
    db.execute(
        """INSERT INTO misappropriation
           (district, state, state_code, fin_year, cases_reported, amount_reported,
            cases_decided, amount_decided, cases_pending_recovery, amount_to_recover,
            cases_recovered, amount_recovered, amount_unrecovered, recovery_rate_pct,
            source_url, scraped_at)
           VALUES ('VELLORE', 'TAMIL NADU', 'TN', ?, 10, 50.0, 5, 25.0, 5, 45.0,
                   1, 5.0, 45.0, 10.0, 'https://x.gov.in', '2026-03-30T00:00:00')""",
        (FIN_YEAR,),
    )
    db.commit()


def test_engine_complaint_kits_presence_and_order(db):
    """Kits render for schemes PRESENT in the district (not just flagged),
    flagged schemes first, with entitlement + ladder + universal separated."""
    _seed_complaint_data(db)

    from action_brief.engine import build_action_brief
    brief = build_action_brief("632001", conn=db)
    assert brief is not None

    schemes = [k["scheme"] for k in brief.complaint_kits]
    assert "MGNREGA" in schemes  # present via financial_statement
    mgnrega = next(k for k in brief.complaint_kits if k["scheme"] == "MGNREGA")
    # 40% utilization < 60% threshold — flagged, so it must sort first.
    assert mgnrega["flagged"] is True
    assert schemes[0] == "MGNREGA"
    assert mgnrega["entitlement"].startswith("Wages within 15 days")
    assert mgnrega["complain_when"] == ["Wages pending beyond 15 days"]
    levels = [c["level"] for c in mgnrega["channels"]]
    assert levels == ["local", "national"]  # ladder ordering

    # Universal channels are separated out, never duplicated into kits.
    assert [c["scheme"] for c in brief.universal_channels] == ["ALL"]
    assert all(k["scheme"] != "ALL" for k in brief.complaint_kits)
    # PDS has a channel but no VELLORE presence in this fixture — no kit.
    assert "PDS/NFSA" not in schemes


def test_engine_invalid_pin():
    from action_brief.engine import build_action_brief
    result = build_action_brief("12345")
    assert result is None


def test_engine_unknown_pin(db):
    from action_brief.engine import build_action_brief
    result = build_action_brief("999999", conn=db)
    assert result is None


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------

def test_api_action_valid_pin(db):
    db.execute("""INSERT INTO pin_district_mapping (pin_code, district, state, office_name) VALUES ('221001', 'VARANASI', 'UTTAR PRADESH', 'Varanasi GPO')""")
    db.commit()
    from directory.seed_data import seed_grievance_channels
    seed_grievance_channels(db)

    from fastapi import FastAPI

    from api.routes.action import _set_test_conn, router
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    _set_test_conn(db)
    from fastapi.testclient import TestClient
    client = TestClient(app)
    resp = client.get("/api/v1/action/221001")
    assert resp.status_code == 200
    body = resp.json()
    assert body["pin"] == "221001"
    assert body["district"] == "VARANASI"
    assert "diagnosis" in body
    assert "contacts" in body
    assert "actions" in body
    _set_test_conn(None)


def test_api_action_invalid_pin():
    from fastapi import FastAPI

    from api.routes.action import _set_test_conn, router
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    _set_test_conn(None)
    from fastapi.testclient import TestClient
    client = TestClient(app)
    resp = client.get("/api/v1/action/123")
    assert resp.status_code == 400


def test_api_action_card_svg(db):
    db.execute("""INSERT INTO pin_district_mapping (pin_code, district, state, office_name) VALUES ('221001', 'VARANASI', 'UTTAR PRADESH', 'Varanasi GPO')""")
    db.commit()
    from directory.seed_data import seed_grievance_channels
    seed_grievance_channels(db)

    from fastapi import FastAPI

    from api.routes.action import _set_test_conn, router
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    _set_test_conn(db)
    from fastapi.testclient import TestClient
    client = TestClient(app)
    resp = client.get("/api/v1/action/221001/card?format=portrait")
    assert resp.status_code == 200
    assert "svg" in resp.headers["content-type"]
    assert b"<svg" in resp.content
    _set_test_conn(None)
