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
