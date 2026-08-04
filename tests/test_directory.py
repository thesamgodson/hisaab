"""Tests for directory module — officials and grievance channel queries."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

import pytest

from db.schema import SCHEMA
from directory.grievances import get_grievance_channels
from directory.officials import get_officials


@pytest.fixture
def db():
    """In-memory SQLite with full schema."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def _insert_official(
    conn: sqlite3.Connection,
    *,
    state: str,
    district: str,
    role: str,
    name: str,
    scraped_at: str,
    phone: str | None = None,
    email: str | None = None,
    office_address: str | None = None,
    source_url: str = "https://example.nic.in",
) -> None:
    conn.execute(
        """INSERT INTO district_officials
           (state, district, role, name, phone, email, office_address, source_url, scraped_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (state, district, role, name, phone, email, office_address, source_url, scraped_at),
    )
    conn.commit()


def _insert_channel(
    conn: sqlite3.Connection,
    *,
    scheme: str,
    level: str,
    portal_name: str,
    portal_url: str = "https://portal.example.gov.in",
    phone: str | None = None,
    description: str | None = None,
    escalation_scheme: str | None = None,
    source_url: str = "https://source.example.gov.in",
    scraped_at: str = "2026-03-31T00:00:00",
) -> None:
    conn.execute(
        """INSERT INTO grievance_channels
           (scheme, level, portal_name, portal_url, phone, description, escalation_scheme, source_url, scraped_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (scheme, level, portal_name, portal_url, phone, description, escalation_scheme, source_url, scraped_at),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Officials tests
# ---------------------------------------------------------------------------

def test_get_officials_fresh(db):
    """All 3 officials are returned regardless of freshness."""
    now = datetime.now()
    _insert_official(db, state="UP", district="VARANASI", role="District Collector",
                     name="Alice", scraped_at=(now - timedelta(days=10)).isoformat())
    _insert_official(db, state="UP", district="VARANASI", role="Chief Medical Officer",
                     name="Bob", scraped_at=(now - timedelta(days=100)).isoformat())
    _insert_official(db, state="UP", district="VARANASI", role="Executive Engineer",
                     name="Carol", scraped_at=(now - timedelta(days=200)).isoformat())

    results = get_officials(db, "VARANASI", "UP")
    assert len(results) == 3


def test_officials_freshness_warning(db):
    """Freshness labels are assigned correctly based on age."""
    now = datetime.now()
    _insert_official(db, state="UP", district="LUCKNOW", role="District Collector",
                     name="Fresh One", scraped_at=(now - timedelta(days=10)).isoformat())
    _insert_official(db, state="UP", district="LUCKNOW", role="CDO",
                     name="Stale One", scraped_at=(now - timedelta(days=120)).isoformat())
    _insert_official(db, state="UP", district="LUCKNOW", role="DM",
                     name="Expired One", scraped_at=(now - timedelta(days=200)).isoformat())

    results = get_officials(db, "LUCKNOW", "UP")
    by_role = {r["role"]: r for r in results}

    assert by_role["District Collector"]["freshness"] == "fresh"
    assert by_role["CDO"]["freshness"] == "stale"
    assert by_role["DM"]["freshness"] == "expired"


def test_expired_officials_name_hidden(db):
    """Officials scraped > 180 days ago have PII fields set to None."""
    now = datetime.now()
    _insert_official(
        db, state="UP", district="AGRA", role="District Collector",
        name="Sensitive Name", phone="9999999999", email="dc@nic.in",
        office_address="DC Office Agra",
        scraped_at=(now - timedelta(days=200)).isoformat(),
    )

    results = get_officials(db, "AGRA", "UP")
    assert len(results) == 1
    r = results[0]
    assert r["freshness"] == "expired"
    assert r["name"] is None
    assert r["phone"] is None
    assert r["email"] is None
    assert r["office_address"] is None
    assert r["role"] == "District Collector"
    assert r["source_url"] == "https://example.nic.in"


def test_get_officials_empty(db):
    """Nonexistent district returns an empty list."""
    results = get_officials(db, "NONEXISTENT_DISTRICT", "UP")
    assert results == []


# ---------------------------------------------------------------------------
# Grievance channel tests
# ---------------------------------------------------------------------------

def test_get_grievance_channels(db):
    """Returns channels for a single scheme."""
    _insert_channel(db, scheme="MGNREGA", level="national",
                    portal_name="MGNREGA Grievance Portal",
                    portal_url="https://nrega.nic.in/grievance")
    _insert_channel(db, scheme="MGNREGA", level="state",
                    portal_name="State MGNREGA Portal",
                    portal_url="https://state.mgnrega.nic.in")

    results = get_grievance_channels(db, ["MGNREGA"])
    assert len(results) == 2
    schemes = {r["scheme"] for r in results}
    assert schemes == {"MGNREGA"}


def test_get_grievance_channels_multiple_schemes(db):
    """Returns channels for multiple schemes, ordered by scheme then level."""
    _insert_channel(db, scheme="MGNREGA", level="national",
                    portal_name="MGNREGA National Portal")
    _insert_channel(db, scheme="PMAY-G", level="district",
                    portal_name="PMAY-G District Portal")
    _insert_channel(db, scheme="PMAY-G", level="state",
                    portal_name="PMAY-G State Portal")

    results = get_grievance_channels(db, ["MGNREGA", "PMAY-G"])
    assert len(results) == 3
    schemes = [r["scheme"] for r in results]
    assert "MGNREGA" in schemes
    assert "PMAY-G" in schemes

    # PMAY-G district should come before PMAY-G state
    pmayg = [r for r in results if r["scheme"] == "PMAY-G"]
    assert pmayg[0]["level"] == "district"
    assert pmayg[1]["level"] == "state"


def test_get_grievance_channels_empty(db):
    """Unknown scheme returns an empty list."""
    results = get_grievance_channels(db, ["NONEXISTENT_SCHEME"])
    assert results == []


# ---------------------------------------------------------------------------
# Seed data tests
# ---------------------------------------------------------------------------

def test_seed_grievance_channels(db):
    from directory.seed_data import seed_grievance_channels
    count = seed_grievance_channels(db)
    assert count > 0

    rows = db.execute("SELECT * FROM grievance_channels").fetchall()
    for row in rows:
        assert row["portal_url"], f"Missing portal_url for {row['scheme']} {row['level']}"
        assert row["source_url"], f"Missing source_url for {row['scheme']} {row['level']}"

    cpgrams = db.execute(
        "SELECT COUNT(*) as cnt FROM grievance_channels WHERE portal_name='CPGRAMS'"
    ).fetchone()
    assert cpgrams["cnt"] >= 1

    rti = db.execute(
        "SELECT COUNT(*) as cnt FROM grievance_channels WHERE portal_name LIKE '%RTI%'"
    ).fetchone()
    assert rti["cnt"] >= 1


def test_load_district_officials(db):
    from db.loaders import load_district_officials
    records = [{
        "state": "UTTAR PRADESH", "district": "VARANASI",
        "role": "District Collector", "name": "Test DC",
        "phone": "9876543210", "email": "dc@varanasi.nic.in",
        "office_address": "DC Office",
        "source_url": "https://varanasi.nic.in",
        "scraped_at": "2026-03-30T00:00:00",
    }]
    count = load_district_officials(db, records)
    assert count == 1
    row = db.execute("SELECT * FROM district_officials WHERE district='VARANASI'").fetchone()
    assert row["name"] == "Test DC"


def test_load_grievance_channels(db):
    from db.loaders import load_grievance_channels
    records = [{
        "scheme": "MGNREGA", "level": "national",
        "portal_name": "Test Portal", "portal_url": "https://example.gov.in",
        "phone": None, "description": "Test",
        "escalation_scheme": None,
        "source_url": "https://example.gov.in",
        "scraped_at": "2026-03-30T00:00:00",
    }]
    count = load_grievance_channels(db, records)
    assert count == 1
