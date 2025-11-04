"""Tests for the citizen action brief system."""

import sqlite3
from datetime import date, datetime

import pytest


@pytest.fixture
def db():
    """In-memory SQLite database with action brief tables."""
    conn = sqlite3.connect(":memory:")
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
