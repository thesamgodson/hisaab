# Citizen Action Brief — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform Hisaab from a data dashboard into a citizen action platform — PIN code in, plain-English diagnosis + verified contacts + complaint paths out.

**Architecture:** New `action_brief/` module assembles an ActionBrief dataclass by combining existing PIN→district mapping, existing red flag detection, new directory tables (officials + grievance channels), and new diagnosis templates. New FastAPI routes serve the brief as JSON and shareable SVG. New Next.js `/action/[pin]` page renders three progressive-disclosure layers.

**Tech Stack:** Python 3.14+ (dataclasses, sqlite3), FastAPI, Next.js 15 + React 19 + TypeScript, Tailwind CSS, SVG generation (following existing `report_card.py` pattern).

---

## File Structure

### New Files (Backend)

| File | Responsibility |
|------|---------------|
| `action_brief/__init__.py` | Package marker |
| `action_brief/models.py` | Frozen dataclasses: `DiagnosisItem`, `ContactCard`, `ActionItem`, `ActionBrief` |
| `action_brief/diagnosis.py` | Template-based diagnosis engine — maps red flag data to plain-English `DiagnosisItem` list |
| `action_brief/contacts.py` | Build `ContactCard` list from MP/MLA + `district_officials` table, with freshness rules |
| `action_brief/actions.py` | Build `ActionItem` list from `grievance_channels` table for flagged schemes |
| `action_brief/engine.py` | `build_action_brief(pin)` — orchestrator that calls mapper, queries, diagnosis, contacts, actions |
| `action_brief/card.py` | SVG generation for shareable cards (portrait + landscape) |
| `directory/__init__.py` | Package marker |
| `directory/officials.py` | Query `district_officials` table with freshness filtering |
| `directory/grievances.py` | Query `grievance_channels` table for scheme-specific portals |
| `directory/seed_data.py` | Seed `grievance_channels` with known portal URLs (static, verified data) |
| `api/routes/action.py` | FastAPI router: `GET /action/{pin}` and `GET /action/{pin}/card` |
| `tests/test_action_brief.py` | Unit tests for diagnosis, contacts, actions, engine, card |
| `tests/test_directory.py` | Unit tests for directory queries + seed data |

### New Files (Frontend)

| File | Responsibility |
|------|---------------|
| `web/src/app/action/[pin]/page.tsx` | Action brief page — three layers + share button |
| `web/src/app/action/[pin]/loading.tsx` | Loading skeleton |
| `web/src/components/DiagnosisCard.tsx` | Severity dot + summary + detail + source link |
| `web/src/components/ContactCard.tsx` | Role, name, phone/email, freshness badge |
| `web/src/components/ActionCard.tsx` | Scheme action + portal link + escalation |
| `web/src/components/ShareButton.tsx` | SVG→PNG conversion + Web Share API / download fallback |
| `web/src/lib/action-types.ts` | TypeScript interfaces for ActionBrief API response |

### Modified Files

| File | Change |
|------|--------|
| `db/schema.py` | Add `district_officials` and `grievance_channels` CREATE TABLE statements |
| `db/loaders.py` | Add `load_district_officials()` and `load_grievance_channels()` |
| `api/main.py` | Add `action.router` include |
| `web/src/app/page.tsx` | Reorder hero: PIN input primary, SearchBar secondary |
| `web/src/app/layout.tsx` | Add "Check Your Area" nav item |
| `web/src/lib/types.ts` | Re-export action types (optional, for consistency) |

---

## Task 1: Database Schema — New Tables

**Files:**
- Modify: `db/schema.py`
- Test: `tests/test_action_brief.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_action_brief.py
"""Tests for the citizen action brief system."""

import sqlite3
import pytest


@pytest.fixture
def db():
    """In-memory SQLite database with action brief tables."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    from db.schema import SCHEMA_SQL
    conn.executescript(SCHEMA_SQL)

    return conn


def test_district_officials_table_exists(db):
    """district_officials table should exist with correct columns."""
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
    """grievance_channels table should exist with correct columns."""
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
    """Insert an official and verify PK constraint."""
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

    # Duplicate PK should fail or replace
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
    """Insert a grievance channel and verify PK constraint."""
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_action_brief.py -v`
Expected: FAIL — `district_officials` table does not exist in SCHEMA_SQL

- [ ] **Step 3: Add CREATE TABLE statements to schema.py**

Add to `db/schema.py` after the existing `mla_info` table definition (around line 850):

```python
# ---------------------------------------------------------------------------
# Directory tables (citizen action briefs)
# ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS district_officials (
    state           TEXT NOT NULL,
    district        TEXT NOT NULL,
    role            TEXT NOT NULL,
    name            TEXT NOT NULL,
    phone           TEXT,
    email           TEXT,
    office_address  TEXT,
    source_url      TEXT NOT NULL,
    scraped_at      TEXT NOT NULL,
    PRIMARY KEY (state, district, role)
);

CREATE TABLE IF NOT EXISTS grievance_channels (
    scheme              TEXT NOT NULL,
    level               TEXT NOT NULL,
    portal_name         TEXT NOT NULL,
    portal_url          TEXT NOT NULL,
    phone               TEXT,
    description         TEXT,
    escalation_scheme   TEXT,
    source_url          TEXT NOT NULL,
    scraped_at          TEXT NOT NULL,
    PRIMARY KEY (scheme, level, portal_name)
);

CREATE INDEX IF NOT EXISTS idx_officials_district ON district_officials(district, state);
CREATE INDEX IF NOT EXISTS idx_grievance_scheme ON grievance_channels(scheme);
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_action_brief.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add db/schema.py tests/test_action_brief.py
git commit -m "feat: add district_officials and grievance_channels tables to schema"
```

---

## Task 2: Directory Module — Officials + Grievances Queries

**Files:**
- Create: `directory/__init__.py`
- Create: `directory/officials.py`
- Create: `directory/grievances.py`
- Test: `tests/test_directory.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_directory.py
"""Tests for the directory module — officials and grievance channel queries."""

import sqlite3
from datetime import datetime, timedelta

import pytest


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    from db.schema import SCHEMA_SQL
    conn.executescript(SCHEMA_SQL)
    return conn


@pytest.fixture
def db_with_officials(db):
    """DB with sample officials at various freshness levels."""
    now = datetime.now()
    fresh = now.isoformat()
    stale_91 = (now - timedelta(days=91)).isoformat()
    stale_181 = (now - timedelta(days=181)).isoformat()

    db.execute(
        """INSERT INTO district_officials VALUES
           ('UTTAR PRADESH', 'VARANASI', 'District Collector', 'Fresh DC',
            '9876543210', 'dc@varanasi.nic.in', 'DC Office Varanasi',
            'https://varanasi.nic.in', ?)""",
        (fresh,),
    )
    db.execute(
        """INSERT INTO district_officials VALUES
           ('UTTAR PRADESH', 'VARANASI', 'MGNREGA Programme Officer', 'Stale PO',
            '1111111111', NULL, NULL,
            'https://varanasi.nic.in', ?)""",
        (stale_91,),
    )
    db.execute(
        """INSERT INTO district_officials VALUES
           ('UTTAR PRADESH', 'VARANASI', 'BDO', 'Very Stale BDO',
            '2222222222', NULL, NULL,
            'https://varanasi.nic.in', ?)""",
        (stale_181,),
    )
    db.commit()
    return db


@pytest.fixture
def db_with_grievances(db):
    """DB with sample grievance channels."""
    db.execute(
        """INSERT INTO grievance_channels VALUES
           ('MGNREGA', 'district', 'MGNREGA Complaint Portal',
            'https://nrega.nic.in/netnrega/muster_complaint.aspx',
            NULL, 'File MGNREGA work complaints', NULL,
            'https://nrega.nic.in', '2026-03-30T00:00:00')"""
    )
    db.execute(
        """INSERT INTO grievance_channels VALUES
           ('MGNREGA', 'national', 'CPGRAMS',
            'https://pgportal.gov.in/',
            '1800-111-555', 'Central grievance portal', NULL,
            'https://pgportal.gov.in/', '2026-03-30T00:00:00')"""
    )
    db.execute(
        """INSERT INTO grievance_channels VALUES
           ('PMAY-G', 'national', 'PMAY-G Grievance Portal',
            'https://pmayg.nic.in/netiayHome/Aboreal_grievance.aspx',
            NULL, 'Housing scheme complaints', NULL,
            'https://pmayg.nic.in', '2026-03-30T00:00:00')"""
    )
    db.commit()
    return db


def test_get_officials_fresh(db_with_officials):
    from directory.officials import get_officials
    officials = get_officials(db_with_officials, "VARANASI", "UTTAR PRADESH")
    assert len(officials) == 3


def test_officials_freshness_warning(db_with_officials):
    from directory.officials import get_officials
    officials = get_officials(db_with_officials, "VARANASI", "UTTAR PRADESH")
    by_role = {o["role"]: o for o in officials}

    assert by_role["District Collector"]["freshness"] == "fresh"
    assert by_role["MGNREGA Programme Officer"]["freshness"] == "stale"
    assert by_role["BDO"]["freshness"] == "expired"


def test_expired_officials_name_hidden(db_with_officials):
    from directory.officials import get_officials
    officials = get_officials(db_with_officials, "VARANASI", "UTTAR PRADESH")
    by_role = {o["role"]: o for o in officials}

    # Fresh: name visible
    assert by_role["District Collector"]["name"] == "Fresh DC"
    # Expired (>180 days): name hidden
    assert by_role["BDO"]["name"] is None


def test_get_officials_empty(db):
    from directory.officials import get_officials
    officials = get_officials(db, "NOWHERE", "NOWHERE STATE")
    assert officials == []


def test_get_grievance_channels(db_with_grievances):
    from directory.grievances import get_grievance_channels
    channels = get_grievance_channels(db_with_grievances, ["MGNREGA"])
    assert len(channels) == 2
    assert any(c["portal_name"] == "CPGRAMS" for c in channels)


def test_get_grievance_channels_multiple_schemes(db_with_grievances):
    from directory.grievances import get_grievance_channels
    channels = get_grievance_channels(db_with_grievances, ["MGNREGA", "PMAY-G"])
    assert len(channels) == 3


def test_get_grievance_channels_empty(db_with_grievances):
    from directory.grievances import get_grievance_channels
    channels = get_grievance_channels(db_with_grievances, ["JJM"])
    assert channels == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_directory.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'directory'`

- [ ] **Step 3: Implement directory/__init__.py**

```python
# directory/__init__.py
```

- [ ] **Step 4: Implement directory/officials.py**

```python
# directory/officials.py
"""Query district_officials with freshness-aware filtering."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from typing import Any

_FRESH_DAYS = 90
_EXPIRED_DAYS = 180


def get_officials(
    conn: sqlite3.Connection,
    district: str,
    state: str,
) -> list[dict[str, Any]]:
    """Return officials for a district with freshness status.

    Freshness rules:
    - < 90 days: "fresh" — show all fields
    - 90-180 days: "stale" — show all fields + amber warning
    - > 180 days: "expired" — hide name/phone/email, show role + source_url only
    """
    rows = conn.execute(
        """SELECT * FROM district_officials
           WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?)
           ORDER BY role""",
        (district, state),
    ).fetchall()

    now = datetime.now()
    results: list[dict[str, Any]] = []

    for row in rows:
        r = dict(row)
        scraped = datetime.fromisoformat(r["scraped_at"])
        age_days = (now - scraped).days

        if age_days > _EXPIRED_DAYS:
            freshness = "expired"
            results.append({
                "role": r["role"],
                "name": None,
                "phone": None,
                "email": None,
                "office_address": None,
                "source_url": r["source_url"],
                "scraped_at": r["scraped_at"],
                "freshness": freshness,
            })
        else:
            freshness = "stale" if age_days > _FRESH_DAYS else "fresh"
            results.append({
                "role": r["role"],
                "name": r["name"],
                "phone": r["phone"],
                "email": r["email"],
                "office_address": r["office_address"],
                "source_url": r["source_url"],
                "scraped_at": r["scraped_at"],
                "freshness": freshness,
            })

    return results
```

- [ ] **Step 5: Implement directory/grievances.py**

```python
# directory/grievances.py
"""Query grievance_channels for scheme-specific complaint portals."""

from __future__ import annotations

import sqlite3
from typing import Any


def get_grievance_channels(
    conn: sqlite3.Connection,
    schemes: list[str],
) -> list[dict[str, Any]]:
    """Return grievance channels for a list of schemes.

    Returns channels at all levels (district, state, national) for each scheme,
    sorted by scheme then level (district first, national last).
    """
    if not schemes:
        return []

    placeholders = ",".join("?" * len(schemes))
    rows = conn.execute(
        f"""SELECT * FROM grievance_channels
            WHERE scheme IN ({placeholders})
            ORDER BY scheme,
                     CASE level
                         WHEN 'district' THEN 1
                         WHEN 'state' THEN 2
                         WHEN 'national' THEN 3
                         ELSE 4
                     END""",
        schemes,
    ).fetchall()

    return [dict(r) for r in rows]
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_directory.py -v`
Expected: PASS (7 tests)

- [ ] **Step 7: Commit**

```bash
git add directory/ tests/test_directory.py
git commit -m "feat: directory module — officials + grievance channel queries with freshness"
```

---

## Task 3: Grievance Channels Seed Data

**Files:**
- Create: `directory/seed_data.py`
- Test: `tests/test_directory.py` (extend)

- [ ] **Step 1: Write the failing test**

Add to `tests/test_directory.py`:

```python
def test_seed_grievance_channels(db):
    from directory.seed_data import seed_grievance_channels
    count = seed_grievance_channels(db)
    assert count > 0

    # Every row must have a portal_url and source_url
    rows = db.execute("SELECT * FROM grievance_channels").fetchall()
    for row in rows:
        assert row["portal_url"], f"Missing portal_url for {row['scheme']} {row['level']}"
        assert row["source_url"], f"Missing source_url for {row['scheme']} {row['level']}"

    # CPGRAMS should exist as national escalation for every scheme
    cpgrams = db.execute(
        "SELECT COUNT(*) as cnt FROM grievance_channels WHERE portal_name='CPGRAMS'"
    ).fetchone()
    assert cpgrams["cnt"] >= 1

    # RTI portal should exist
    rti = db.execute(
        "SELECT COUNT(*) as cnt FROM grievance_channels WHERE portal_name LIKE '%RTI%'"
    ).fetchone()
    assert rti["cnt"] >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_directory.py::test_seed_grievance_channels -v`
Expected: FAIL — `ModuleNotFoundError` or `ImportError`

- [ ] **Step 3: Implement directory/seed_data.py**

```python
# directory/seed_data.py
"""Seed grievance_channels with verified government portal URLs.

These are stable official portals — not scraped, manually verified.
Updated quarterly.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime

# Verified grievance portals per scheme
# source_url = the page where we confirmed this portal exists
_CHANNELS: list[dict[str, str | None]] = [
    # -- MGNREGA --
    {
        "scheme": "MGNREGA",
        "level": "district",
        "portal_name": "MGNREGA Public Grievance",
        "portal_url": "https://nrega.nic.in/Nregahome/EComplaint.aspx",
        "phone": None,
        "description": "File complaints about delayed wages, worksite issues, or job card problems",
        "escalation_scheme": None,
        "source_url": "https://nrega.nic.in",
    },
    {
        "scheme": "MGNREGA",
        "level": "national",
        "portal_name": "MGNREGA Helpline",
        "portal_url": "https://nrega.nic.in",
        "phone": "1800-111-555",
        "description": "Toll-free MGNREGA helpline",
        "escalation_scheme": None,
        "source_url": "https://nrega.nic.in",
    },
    # -- PMAY-G --
    {
        "scheme": "PMAY-G",
        "level": "national",
        "portal_name": "PMAY-G Grievance Portal",
        "portal_url": "https://pmayg.nic.in/netiayHome/Aboreal_grievance.aspx",
        "phone": None,
        "description": "File complaints about housing scheme delays or irregularities",
        "escalation_scheme": None,
        "source_url": "https://pmayg.nic.in",
    },
    # -- JJM --
    {
        "scheme": "JJM",
        "level": "national",
        "portal_name": "JJM Grievance Portal",
        "portal_url": "https://jalshakti-ddws.gov.in/grievance",
        "phone": None,
        "description": "File complaints about tap water connections",
        "escalation_scheme": None,
        "source_url": "https://ejalshakti.gov.in",
    },
    # -- PM Kisan --
    {
        "scheme": "PM Kisan",
        "level": "national",
        "portal_name": "PM Kisan Helpline",
        "portal_url": "https://pmkisan.gov.in/Aboreal_grievance.aspx",
        "phone": "155261",
        "description": "PM Kisan grievance and beneficiary status",
        "escalation_scheme": None,
        "source_url": "https://pmkisan.gov.in",
    },
    # -- PM POSHAN --
    {
        "scheme": "PM POSHAN",
        "level": "national",
        "portal_name": "PM POSHAN Portal",
        "portal_url": "https://pmposhan.education.gov.in/",
        "phone": None,
        "description": "Mid-day meal scheme monitoring and complaints",
        "escalation_scheme": None,
        "source_url": "https://pmposhan.education.gov.in",
    },
    # -- NSAP --
    {
        "scheme": "NSAP",
        "level": "national",
        "portal_name": "NSAP Portal",
        "portal_url": "https://nsap.nic.in/statedashboard.do",
        "phone": None,
        "description": "National pension scheme tracking and status",
        "escalation_scheme": None,
        "source_url": "https://nsap.nic.in",
    },
    # -- PDS/NFSA --
    {
        "scheme": "PDS/NFSA",
        "level": "national",
        "portal_name": "NFSA Grievance",
        "portal_url": "https://nfsa.gov.in/public/nfsadashboard/PGR.aspx",
        "phone": "1967",
        "description": "Ration distribution complaints and ration card issues",
        "escalation_scheme": None,
        "source_url": "https://nfsa.gov.in",
    },
    # -- PMGSY --
    {
        "scheme": "PMGSY",
        "level": "national",
        "portal_name": "PMGSY Feedback",
        "portal_url": "https://omms.nic.in/",
        "phone": None,
        "description": "Rural roads construction monitoring",
        "escalation_scheme": None,
        "source_url": "https://omms.nic.in",
    },
    # -- Universal escalation --
    {
        "scheme": "ALL",
        "level": "national",
        "portal_name": "CPGRAMS",
        "portal_url": "https://pgportal.gov.in/",
        "phone": "1800-111-555",
        "description": "Central grievance portal for all government departments — escalate here if no response in 30 days",
        "escalation_scheme": None,
        "source_url": "https://pgportal.gov.in/",
    },
    {
        "scheme": "ALL",
        "level": "national",
        "portal_name": "RTI Online",
        "portal_url": "https://rtionline.gov.in/",
        "phone": None,
        "description": "File a Right to Information request for any government department",
        "escalation_scheme": None,
        "source_url": "https://rtionline.gov.in/",
    },
]


def seed_grievance_channels(conn: sqlite3.Connection) -> int:
    """Insert verified grievance channels. Returns count of rows inserted."""
    now = datetime.now().isoformat()
    loaded = 0
    for ch in _CHANNELS:
        conn.execute(
            """INSERT OR REPLACE INTO grievance_channels
               (scheme, level, portal_name, portal_url, phone, description,
                escalation_scheme, source_url, scraped_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                ch["scheme"],
                ch["level"],
                ch["portal_name"],
                ch["portal_url"],
                ch["phone"],
                ch["description"],
                ch["escalation_scheme"],
                ch["source_url"],
                now,
            ),
        )
        loaded += 1
    conn.commit()
    return loaded
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_directory.py::test_seed_grievance_channels -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add directory/seed_data.py tests/test_directory.py
git commit -m "feat: seed grievance channels with verified government portal URLs"
```

---

## Task 4: Action Brief Models (Dataclasses)

**Files:**
- Create: `action_brief/__init__.py`
- Create: `action_brief/models.py`
- Test: `tests/test_action_brief.py` (extend)

- [ ] **Step 1: Write the failing test**

Add to `tests/test_action_brief.py`:

```python
from datetime import date, datetime


def test_diagnosis_item_frozen():
    from action_brief.models import DiagnosisItem
    item = DiagnosisItem(
        severity="high",
        scheme="MGNREGA",
        summary="Only 8% of misappropriated funds recovered.",
        detail="Rs 4.2 crore flagged, Rs 3.9 crore unrecovered.",
        amount="Rs 3.9 crore",
        source_url="https://nrega.nic.in/",
    )
    assert item.severity == "high"
    with pytest.raises(AttributeError):
        item.severity = "low"


def test_contact_card_frozen():
    from action_brief.models import ContactCard
    card = ContactCard(
        role="District Collector",
        name="Test DC",
        phone="9876543210",
        email="dc@nic.in",
        office_address="DC Office",
        relevance="Oversees all district-level schemes",
        source_url="https://varanasi.nic.in",
        last_verified=date(2026, 3, 15),
        freshness="fresh",
    )
    assert card.role == "District Collector"


def test_action_item_frozen():
    from action_brief.models import ActionItem
    item = ActionItem(
        scheme="MGNREGA",
        action="File a complaint about delayed wages",
        portal_name="MGNREGA Public Grievance",
        portal_url="https://nrega.nic.in/Nregahome/EComplaint.aspx",
        escalation="If no response in 30 days, escalate to CPGRAMS",
        escalation_url="https://pgportal.gov.in/",
    )
    assert item.scheme == "MGNREGA"


def test_action_brief_frozen():
    from action_brief.models import ActionBrief, DiagnosisItem
    brief = ActionBrief(
        pin="221001",
        district="VARANASI",
        state="UTTAR PRADESH",
        mp=None,
        mla=None,
        diagnosis=[],
        contacts=[],
        actions=[],
        scheme_data={},
        generated_at=datetime.now(),
    )
    assert brief.pin == "221001"
    assert brief.diagnosis == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_action_brief.py::test_diagnosis_item_frozen -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'action_brief'`

- [ ] **Step 3: Implement action_brief/__init__.py**

```python
# action_brief/__init__.py
```

- [ ] **Step 4: Implement action_brief/models.py**

```python
# action_brief/models.py
"""Frozen dataclasses for the citizen action brief."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any


@dataclass(frozen=True)
class DiagnosisItem:
    severity: str          # "high", "medium", "low"
    scheme: str            # "MGNREGA", "PMAY-G", etc.
    summary: str           # Plain English, one sentence
    detail: str            # Supporting context, one sentence
    amount: str | None     # "Rs 4.2 crore" — formatted for readability
    source_url: str        # Direct link to source data


@dataclass(frozen=True)
class ContactCard:
    role: str              # "Member of Parliament", "District Collector", etc.
    name: str | None       # None if data is expired
    phone: str | None
    email: str | None
    office_address: str | None
    relevance: str         # "Oversees all district-level schemes"
    source_url: str
    last_verified: date
    freshness: str         # "fresh", "stale", "expired"


@dataclass(frozen=True)
class ActionItem:
    scheme: str
    action: str            # "File a complaint about delayed MGNREGA wages"
    portal_name: str
    portal_url: str
    escalation: str        # "If no response in 30 days, escalate to CPGRAMS"
    escalation_url: str


@dataclass(frozen=True)
class ActionBrief:
    pin: str
    district: str
    state: str
    mp: dict[str, Any] | None
    mla: dict[str, Any] | None
    diagnosis: list[DiagnosisItem]
    contacts: list[ContactCard]
    actions: list[ActionItem]
    scheme_data: dict[str, Any]
    generated_at: datetime
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_action_brief.py -v`
Expected: PASS (all 8 tests — 4 schema + 4 model)

- [ ] **Step 6: Commit**

```bash
git add action_brief/ tests/test_action_brief.py
git commit -m "feat: action brief dataclasses — DiagnosisItem, ContactCard, ActionItem, ActionBrief"
```

---

## Task 5: Diagnosis Engine — Template-Based Red Flag → Plain English

**Files:**
- Create: `action_brief/diagnosis.py`
- Test: `tests/test_action_brief.py` (extend)

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_action_brief.py`:

```python
def test_diagnosis_mgnrega_low_recovery(db):
    """Low recovery rate produces a high-severity MGNREGA diagnosis."""
    db.execute(
        """INSERT INTO misappropriation
           (district, state, fin_year, cases_reported, amount_reported, amount_recovered,
            recovery_rate_pct, source_url, scraped_at)
           VALUES ('VARANASI', 'UTTAR PRADESH', '2024-2025', 50, 420, 34,
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
    """Low PMAY-G completion produces a medium-severity diagnosis."""
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
    """District with no data produces no diagnosis items."""
    from action_brief.diagnosis import build_diagnosis
    items = build_diagnosis(db, "NONEXISTENT", "NOWHERE")
    assert items == []


def test_diagnosis_max_5_items(db):
    """Diagnosis is capped at 5 items."""
    # Insert data that triggers many flags
    db.execute(
        """INSERT INTO misappropriation
           (district, state, fin_year, cases_reported, amount_reported, amount_recovered,
            recovery_rate_pct, source_url, scraped_at)
           VALUES ('BADPLACE', 'BADSTATE', '2024-2025', 200, 1000, 0,
                   0.0, 'https://nrega.nic.in/', '2026-03-30T00:00:00')"""
    )
    db.execute(
        """INSERT INTO financial_statement
           (district, state, fin_year, total_availability, cumulative_expenditure,
            utilization_pct, source_url, scraped_at)
           VALUES ('BADPLACE', 'BADSTATE', '2024-2025', 5000, 1000,
                   20.0, 'https://nrega.nic.in/', '2026-03-30T00:00:00')"""
    )
    db.execute(
        """INSERT INTO pmayg_district
           (district, state, fin_year, houses_sanctioned, houses_completed,
            houses_occupied, completion_pct, source_url, scraped_at)
           VALUES ('BADPLACE', 'BADSTATE', '2024-2025', 1000, 100,
                   30, 10.0, 'https://pmayg.nic.in/', '2026-03-30T00:00:00')"""
    )
    db.execute(
        """INSERT INTO jjm_district
           (district, state, total_households, households_with_tap, coverage_pct,
            funds_released_lakhs, funds_utilized_lakhs, source_url, scraped_at)
           VALUES ('BADPLACE', 'BADSTATE', 10000, 1000, 10.0,
                   500, 50, 'https://ejalshakti.gov.in/', '2026-03-30T00:00:00')"""
    )
    db.execute(
        """INSERT INTO pmposhan_district
           (district, state, fin_year, children_enrolled, children_fed,
            source_url, scraped_at)
           VALUES ('BADPLACE', 'BADSTATE', '2024-2025', 10000, 1000,
                   'https://pmposhan.education.gov.in/', '2026-03-30T00:00:00')"""
    )
    db.execute(
        """INSERT INTO nfsa_district
           (district, state, fin_year, ration_cards_total, ration_cards_active,
            allocation_mt, offtake_mt, offtake_pct, source_url, scraped_at)
           VALUES ('BADPLACE', 'BADSTATE', '2024-2025', 10000, 3000,
                   100.0, 20.0, 20.0, 'https://nfsa.gov.in/', '2026-03-30T00:00:00')"""
    )
    db.commit()

    from action_brief.diagnosis import build_diagnosis
    items = build_diagnosis(db, "BADPLACE", "BADSTATE")
    assert len(items) <= 5


def test_diagnosis_sorted_by_severity(db):
    """High severity items come before medium and low."""
    db.execute(
        """INSERT INTO misappropriation
           (district, state, fin_year, cases_reported, amount_reported, amount_recovered,
            recovery_rate_pct, source_url, scraped_at)
           VALUES ('SORTTEST', 'SORTSTATE', '2024-2025', 50, 420, 0,
                   0.0, 'https://nrega.nic.in/', '2026-03-30T00:00:00')"""
    )
    db.execute(
        """INSERT INTO jjm_district
           (district, state, total_households, households_with_tap, coverage_pct,
            funds_released_lakhs, funds_utilized_lakhs, source_url, scraped_at)
           VALUES ('SORTTEST', 'SORTSTATE', 10000, 4000, 40.0,
                   500, 400, 'https://ejalshakti.gov.in/', '2026-03-30T00:00:00')"""
    )
    db.commit()

    from action_brief.diagnosis import build_diagnosis
    items = build_diagnosis(db, "SORTTEST", "SORTSTATE")
    if len(items) >= 2:
        severity_order = {"high": 0, "medium": 1, "low": 2}
        for i in range(len(items) - 1):
            assert severity_order[items[i].severity] <= severity_order[items[i + 1].severity]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_action_brief.py::test_diagnosis_mgnrega_low_recovery -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement action_brief/diagnosis.py**

```python
# action_brief/diagnosis.py
"""Template-based diagnosis engine — maps red flag data to plain-English DiagnosisItem list.

No LLM. Every diagnosis is a deterministic template filled with real data.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from action_brief.models import DiagnosisItem
from briefs.formatting import FIN_YEAR, fmt_inr

_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}
_MAX_ITEMS = 5


def build_diagnosis(
    conn: sqlite3.Connection,
    district: str,
    state: str,
) -> list[DiagnosisItem]:
    """Build a list of DiagnosisItems for a district. Max 5, sorted by severity."""
    items: list[DiagnosisItem] = []

    items.extend(_mgnrega_diagnosis(conn, district, state))
    items.extend(_pmayg_diagnosis(conn, district, state))
    items.extend(_jjm_diagnosis(conn, district, state))
    items.extend(_pmgsy_diagnosis(conn, district, state))
    items.extend(_poshan_diagnosis(conn, district, state))
    items.extend(_nfsa_diagnosis(conn, district, state))
    items.extend(_nsap_diagnosis(conn, district, state))
    items.extend(_mgnrega_complaints_diagnosis(conn, district, state))

    items.sort(key=lambda x: _SEVERITY_ORDER.get(x.severity, 99))
    return items[:_MAX_ITEMS]


def _mgnrega_diagnosis(
    conn: sqlite3.Connection, district: str, state: str
) -> list[DiagnosisItem]:
    mis = conn.execute(
        "SELECT * FROM misappropriation WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchone()
    if not mis:
        return []

    m = dict(mis)
    if m["amount_reported"] <= 0:
        return []

    recovery_pct = m["recovery_rate_pct"]
    reported = m["amount_reported"]
    recovered = m["amount_recovered"]
    unrecovered = reported - recovered

    if recovery_pct < 20:
        return [DiagnosisItem(
            severity="high",
            scheme="MGNREGA",
            summary=f"Only {recovery_pct:.0f}% of misappropriated MGNREGA funds have been recovered in {district.title()}.",
            detail=f"{fmt_inr(reported, 'lakhs')} flagged, {fmt_inr(unrecovered, 'lakhs')} remains unrecovered.",
            amount=fmt_inr(unrecovered, "lakhs"),
            source_url=m["source_url"],
        )]
    return []


def _pmayg_diagnosis(
    conn: sqlite3.Connection, district: str, state: str
) -> list[DiagnosisItem]:
    row = conn.execute(
        "SELECT * FROM pmayg_district WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchone()
    if not row:
        return []

    h = dict(row)
    if h["houses_sanctioned"] > 0 and h["completion_pct"] < 50:
        unbuilt = h["houses_sanctioned"] - h["houses_completed"]
        return [DiagnosisItem(
            severity="medium",
            scheme="PMAY-G",
            summary=f"Less than half the sanctioned houses have been built in {district.title()}.",
            detail=f"{h['houses_completed']:,} out of {h['houses_sanctioned']:,} houses completed.",
            amount=None,
            source_url=h["source_url"],
        )]
    return []


def _jjm_diagnosis(
    conn: sqlite3.Connection, district: str, state: str
) -> list[DiagnosisItem]:
    row = conn.execute(
        "SELECT * FROM jjm_district WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?)",
        (district, state),
    ).fetchone()
    if not row:
        return []

    j = dict(row)
    if j["total_households"] > 0 and j["coverage_pct"] < 50:
        return [DiagnosisItem(
            severity="medium",
            scheme="JJM",
            summary=f"Less than half the households in {district.title()} have tap water connections.",
            detail=f"{j['households_with_tap']:,} out of {j['total_households']:,} households connected.",
            amount=None,
            source_url=j["source_url"],
        )]
    return []


def _pmgsy_diagnosis(
    conn: sqlite3.Connection, district: str, state: str
) -> list[DiagnosisItem]:
    rows = conn.execute(
        "SELECT * FROM pmgsy_district WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?)",
        (district, state),
    ).fetchall()
    if not rows:
        return []

    total_s = sum(dict(r).get("roads_sanctioned", 0) for r in rows)
    total_c = sum(dict(r).get("roads_completed", 0) for r in rows)
    if total_s > 0 and total_c / total_s < 0.5:
        pending = total_s - total_c
        source = dict(rows[0]).get("source_url", "https://omms.nic.in")
        return [DiagnosisItem(
            severity="medium",
            scheme="PMGSY",
            summary=f"{pending:,} sanctioned roads in {district.title()} are still incomplete.",
            detail=f"{total_c:,} out of {total_s:,} sanctioned roads completed.",
            amount=None,
            source_url=source,
        )]
    return []


def _poshan_diagnosis(
    conn: sqlite3.Connection, district: str, state: str
) -> list[DiagnosisItem]:
    row = conn.execute(
        "SELECT * FROM pmposhan_district WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchone()
    if not row:
        return []

    p = dict(row)
    if p["children_enrolled"] > 0:
        feeding_pct = p["children_fed"] / p["children_enrolled"] * 100
        if feeding_pct < 60:
            return [DiagnosisItem(
                severity="medium",
                scheme="PM POSHAN",
                summary=f"Only {feeding_pct:.0f}% of enrolled children in {district.title()} are being fed under the mid-day meal scheme.",
                detail=f"{p['children_fed']:,} out of {p['children_enrolled']:,} children fed.",
                amount=None,
                source_url=p["source_url"],
            )]
    return []


def _nfsa_diagnosis(
    conn: sqlite3.Connection, district: str, state: str
) -> list[DiagnosisItem]:
    row = conn.execute(
        "SELECT * FROM nfsa_district WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchone()
    if not row:
        return []

    nf = dict(row)
    if nf["ration_cards_active"] > 0 and nf["offtake_pct"] < 50:
        return [DiagnosisItem(
            severity="medium",
            scheme="PDS/NFSA",
            summary=f"Only {nf['offtake_pct']:.0f}% of allocated grain has been distributed in {district.title()}.",
            detail=f"{nf['offtake_mt']:,.1f} MT distributed out of {nf['allocation_mt']:,.1f} MT allocated.",
            amount=None,
            source_url=nf["source_url"],
        )]
    return []


def _nsap_diagnosis(
    conn: sqlite3.Connection, district: str, state: str
) -> list[DiagnosisItem]:
    rows = conn.execute(
        "SELECT * FROM nsap_district WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchall()
    if not rows:
        return []

    total_paid = sum(dict(r)["beneficiaries_paid"] for r in rows)
    total_eligible = sum(dict(r)["beneficiaries_eligible"] for r in rows)
    if total_eligible > 0 and total_paid / total_eligible < 0.5:
        source = dict(rows[0]).get("source_url", "https://nsap.nic.in")
        return [DiagnosisItem(
            severity="medium",
            scheme="NSAP",
            summary=f"Only {total_paid:,} out of {total_eligible:,} eligible pensioners received payments in {district.title()}.",
            detail="Pension coverage is below 50%.",
            amount=None,
            source_url=source,
        )]
    return []


def _mgnrega_complaints_diagnosis(
    conn: sqlite3.Connection, district: str, state: str
) -> list[DiagnosisItem]:
    row = conn.execute(
        "SELECT * FROM issues_reported WHERE UPPER(district)=UPPER(?) AND UPPER(state)=UPPER(?) AND fin_year=?",
        (district, state, FIN_YEAR),
    ).fetchone()
    if not row:
        return []

    a = dict(row)
    total = a.get("total_issues", 0)
    if total > 100:
        return [DiagnosisItem(
            severity="low",
            scheme="MGNREGA",
            summary=f"{total:,} complaints have been filed against MGNREGA implementation in {district.title()}.",
            detail="High complaint volume indicates systemic issues.",
            amount=None,
            source_url=a.get("source_url", "https://nrega.nic.in"),
        )]
    return []
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_action_brief.py -v -k diagnosis`
Expected: PASS (5 diagnosis tests)

- [ ] **Step 5: Commit**

```bash
git add action_brief/diagnosis.py tests/test_action_brief.py
git commit -m "feat: template-based diagnosis engine — red flags to plain English"
```

---

## Task 6: Contacts Builder

**Files:**
- Create: `action_brief/contacts.py`
- Test: `tests/test_action_brief.py` (extend)

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_action_brief.py`:

```python
def test_contacts_ordering(db):
    """Contacts should be ordered: MP → MLA → DC → scheme officers."""
    from datetime import timedelta
    now = datetime.now()
    fresh = now.isoformat()

    db.execute(
        """INSERT INTO district_officials VALUES
           ('UTTAR PRADESH', 'VARANASI', 'District Collector', 'Test DC',
            '9876543210', NULL, NULL, 'https://varanasi.nic.in', ?)""",
        (fresh,),
    )
    db.execute(
        """INSERT INTO district_officials VALUES
           ('UTTAR PRADESH', 'VARANASI', 'MGNREGA Programme Officer', 'Test PO',
            NULL, NULL, NULL, 'https://varanasi.nic.in', ?)""",
        (fresh,),
    )
    db.commit()

    from action_brief.contacts import build_contacts

    mp_info = {"mp_name": "Test MP", "party": "INC", "constituency": "VARANASI",
               "state": "UTTAR PRADESH", "source_url": "https://eci.gov.in"}
    mla_info = {"mla_name": "Test MLA", "party": "BJP", "ac_name": "VARANASI CANTT",
                "state": "UTTAR PRADESH", "source_url": "https://myneta.info"}
    flagged_schemes = ["MGNREGA"]

    contacts = build_contacts(
        db, "VARANASI", "UTTAR PRADESH",
        mp_info=mp_info, mla_info=mla_info,
        flagged_schemes=flagged_schemes,
    )

    roles = [c.role for c in contacts]
    assert roles[0] == "Member of Parliament"
    assert roles[1] == "MLA"
    assert roles[2] == "District Collector"
    # Scheme-specific officers only if flagged
    assert "MGNREGA Programme Officer" in roles


def test_contacts_mp_mla_dc_always_shown(db):
    """MP, MLA, DC should always be shown even with no flagged schemes."""
    now = datetime.now().isoformat()
    db.execute(
        """INSERT INTO district_officials VALUES
           ('UTTAR PRADESH', 'VARANASI', 'District Collector', 'Test DC',
            '9876543210', NULL, NULL, 'https://varanasi.nic.in', ?)""",
        (now,),
    )
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_action_brief.py -v -k contacts`
Expected: FAIL

- [ ] **Step 3: Implement action_brief/contacts.py**

```python
# action_brief/contacts.py
"""Build ContactCard list from MP/MLA info + district_officials table."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from typing import Any

from action_brief.models import ContactCard
from directory.officials import get_officials

# Roles that are always shown (in order)
_ALWAYS_ROLES = {"District Collector"}

# Roles that are only shown when their scheme is flagged
_SCHEME_ROLES: dict[str, list[str]] = {
    "MGNREGA": ["MGNREGA Programme Officer", "BDO"],
    "PMAY-G": ["PMAY-G Programme Officer"],
    "JJM": ["JJM Programme Officer"],
    "PMGSY": ["PMGSY Programme Officer"],
    "PM POSHAN": ["PM POSHAN Nodal Officer"],
    "NSAP": ["NSAP Nodal Officer"],
    "PDS/NFSA": ["Food & Civil Supplies Officer"],
    "PM Kisan": ["PM Kisan Nodal Officer"],
}


def build_contacts(
    conn: sqlite3.Connection,
    district: str,
    state: str,
    *,
    mp_info: dict[str, Any] | None = None,
    mla_info: dict[str, Any] | None = None,
    flagged_schemes: list[str] | None = None,
) -> list[ContactCard]:
    """Build ordered list of ContactCards.

    Order: MP → MLA → District Collector → scheme-specific officers (flagged only).
    """
    contacts: list[ContactCard] = []
    today = date.today()

    # 1. MP (always shown)
    if mp_info:
        contacts.append(ContactCard(
            role="Member of Parliament",
            name=mp_info.get("mp_name", "Unknown"),
            phone=mp_info.get("phone"),
            email=mp_info.get("email"),
            office_address=mp_info.get("office_address"),
            relevance=f"Elected representative for {mp_info.get('constituency', district)} constituency",
            source_url=mp_info.get("source_url", "https://eci.gov.in"),
            last_verified=today,
            freshness="fresh",
        ))

    # 2. MLA (always shown if available)
    if mla_info:
        contacts.append(ContactCard(
            role="MLA",
            name=mla_info.get("mla_name", "Unknown"),
            phone=mla_info.get("phone"),
            email=mla_info.get("email"),
            office_address=mla_info.get("office_address"),
            relevance=f"MLA for {mla_info.get('ac_name', '')} assembly constituency",
            source_url=mla_info.get("source_url", "https://myneta.info"),
            last_verified=today,
            freshness="fresh",
        ))

    # 3. Officials from directory
    officials = get_officials(conn, district, state)

    # Build set of roles to include
    allowed_roles = set(_ALWAYS_ROLES)
    for scheme in (flagged_schemes or []):
        for role in _SCHEME_ROLES.get(scheme, []):
            allowed_roles.add(role)

    for off in officials:
        if off["role"] not in allowed_roles:
            continue

        scraped_date = datetime.fromisoformat(off["scraped_at"]).date()
        contacts.append(ContactCard(
            role=off["role"],
            name=off["name"],
            phone=off["phone"],
            email=off["email"],
            office_address=off["office_address"],
            relevance=_role_relevance(off["role"]),
            source_url=off["source_url"],
            last_verified=scraped_date,
            freshness=off["freshness"],
        ))

    return contacts


def _role_relevance(role: str) -> str:
    """Return a one-line relevance note for a role."""
    relevance_map = {
        "District Collector": "Oversees all district-level government schemes",
        "BDO": "Block Development Officer — local scheme implementation",
        "MGNREGA Programme Officer": "Manages MGNREGA implementation in the district",
        "PMAY-G Programme Officer": "Manages housing scheme implementation",
        "JJM Programme Officer": "Manages tap water connection rollout",
        "PMGSY Programme Officer": "Manages rural roads construction",
        "PM POSHAN Nodal Officer": "Oversees mid-day meal scheme",
        "NSAP Nodal Officer": "Manages pension scheme distribution",
        "Food & Civil Supplies Officer": "Manages ration distribution",
        "PM Kisan Nodal Officer": "Manages farmer income support scheme",
    }
    return relevance_map.get(role, f"Responsible for {role} duties")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_action_brief.py -v -k contacts`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add action_brief/contacts.py tests/test_action_brief.py
git commit -m "feat: contacts builder — MP/MLA/DC + scheme officers with ordering"
```

---

## Task 7: Action Items Builder

**Files:**
- Create: `action_brief/actions.py`
- Test: `tests/test_action_brief.py` (extend)

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_action_brief.py`:

```python
def test_action_items_for_flagged_schemes(db):
    """Action items are generated only for flagged schemes."""
    from directory.seed_data import seed_grievance_channels
    seed_grievance_channels(db)

    from action_brief.actions import build_actions
    actions = build_actions(db, ["MGNREGA", "PMAY-G"])

    schemes = {a.scheme for a in actions}
    assert "MGNREGA" in schemes
    assert "PMAY-G" in schemes
    # Each action must have a portal_url and escalation_url
    for a in actions:
        assert a.portal_url.startswith("http")
        assert a.escalation_url.startswith("http")


def test_action_items_empty_when_no_flags(db):
    """No action items when no schemes are flagged."""
    from directory.seed_data import seed_grievance_channels
    seed_grievance_channels(db)

    from action_brief.actions import build_actions
    actions = build_actions(db, [])
    assert actions == []


def test_action_items_always_include_cpgrams_escalation(db):
    """Every action item should escalate to CPGRAMS."""
    from directory.seed_data import seed_grievance_channels
    seed_grievance_channels(db)

    from action_brief.actions import build_actions
    actions = build_actions(db, ["MGNREGA"])
    for a in actions:
        assert "CPGRAMS" in a.escalation or "pgportal" in a.escalation_url
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_action_brief.py -v -k "action_items"`
Expected: FAIL

- [ ] **Step 3: Implement action_brief/actions.py**

```python
# action_brief/actions.py
"""Build ActionItem list from grievance_channels for flagged schemes."""

from __future__ import annotations

import sqlite3

from action_brief.models import ActionItem
from directory.grievances import get_grievance_channels

_CPGRAMS_URL = "https://pgportal.gov.in/"
_RTI_URL = "https://rtionline.gov.in/"

# Human-readable action verbs per scheme
_SCHEME_ACTIONS: dict[str, str] = {
    "MGNREGA": "File a complaint about MGNREGA fund misuse or delayed wages",
    "PMAY-G": "File a complaint about housing scheme delays or irregularities",
    "JJM": "File a complaint about missing or non-functional tap water connections",
    "PM Kisan": "File a complaint about missing PM Kisan payments",
    "PM POSHAN": "File a complaint about mid-day meal scheme issues",
    "NSAP": "File a complaint about missing pension payments",
    "PDS/NFSA": "File a complaint about ration distribution problems",
    "PMGSY": "File a complaint about incomplete or poor-quality rural roads",
}


def build_actions(
    conn: sqlite3.Connection,
    flagged_schemes: list[str],
) -> list[ActionItem]:
    """Build action items for flagged schemes.

    Each flagged scheme gets one action item pointing to its primary grievance portal.
    CPGRAMS is always the escalation path.
    """
    if not flagged_schemes:
        return []

    channels = get_grievance_channels(conn, flagged_schemes)

    # Group by scheme, pick the first (most specific level) per scheme
    best_per_scheme: dict[str, dict] = {}
    for ch in channels:
        scheme = ch["scheme"]
        if scheme not in best_per_scheme:
            best_per_scheme[scheme] = ch

    # Also grab universal channels (scheme='ALL') for escalation reference
    universal = get_grievance_channels(conn, ["ALL"])
    cpgrams_url = _CPGRAMS_URL
    for ch in universal:
        if ch["portal_name"] == "CPGRAMS":
            cpgrams_url = ch["portal_url"]
            break

    actions: list[ActionItem] = []
    for scheme in flagged_schemes:
        ch = best_per_scheme.get(scheme)
        if not ch:
            continue
        actions.append(ActionItem(
            scheme=scheme,
            action=_SCHEME_ACTIONS.get(scheme, f"File a complaint about {scheme}"),
            portal_name=ch["portal_name"],
            portal_url=ch["portal_url"],
            escalation="If no response in 30 days, escalate to CPGRAMS",
            escalation_url=cpgrams_url,
        ))

    return actions
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_action_brief.py -v -k "action_items"`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add action_brief/actions.py tests/test_action_brief.py
git commit -m "feat: action items builder — grievance portals + CPGRAMS escalation"
```

---

## Task 8: Action Brief Engine (Orchestrator)

**Files:**
- Create: `action_brief/engine.py`
- Test: `tests/test_action_brief.py` (extend)

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_action_brief.py`:

```python
def test_engine_valid_pin(db):
    """Full pipeline: PIN → ActionBrief with real DB data."""
    # Seed PIN mapping
    db.execute(
        """INSERT INTO pin_district_mapping (pin_code, district, state, office_name)
           VALUES ('221001', 'VARANASI', 'UTTAR PRADESH', 'Varanasi GPO')"""
    )
    # Seed some scheme data
    db.execute(
        """INSERT INTO misappropriation
           (district, state, fin_year, cases_reported, amount_reported, amount_recovered,
            recovery_rate_pct, source_url, scraped_at)
           VALUES ('VARANASI', 'UTTAR PRADESH', '2024-2025', 50, 420, 34,
                   8.1, 'https://nrega.nic.in/', '2026-03-30T00:00:00')"""
    )
    db.commit()

    # Seed grievance channels
    from directory.seed_data import seed_grievance_channels
    seed_grievance_channels(db)

    from action_brief.engine import build_action_brief
    brief = build_action_brief("221001", conn=db)

    assert brief.pin == "221001"
    assert brief.district == "VARANASI"
    assert brief.state == "UTTAR PRADESH"
    assert len(brief.diagnosis) >= 1
    assert brief.generated_at is not None


def test_engine_invalid_pin():
    """Invalid PIN (not 6 digits) returns None."""
    from action_brief.engine import build_action_brief
    result = build_action_brief("12345")
    assert result is None


def test_engine_unknown_pin(db):
    """Unknown PIN (valid format but not in DB) returns None."""
    from action_brief.engine import build_action_brief
    result = build_action_brief("999999", conn=db)
    assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_action_brief.py -v -k engine`
Expected: FAIL

- [ ] **Step 3: Implement action_brief/engine.py**

```python
# action_brief/engine.py
"""Orchestrator: PIN → ActionBrief.

Calls mapper, queries, diagnosis, contacts, actions to assemble the full brief.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime
from typing import Any

from action_brief.actions import build_actions
from action_brief.contacts import build_contacts
from action_brief.diagnosis import build_diagnosis
from action_brief.models import ActionBrief
from briefs.formatting import get_conn


def build_action_brief(
    pin: str,
    *,
    conn: sqlite3.Connection | None = None,
) -> ActionBrief | None:
    """Build a full ActionBrief for a 6-digit PIN code.

    Returns None if:
    - PIN is not 6 digits
    - PIN is not found in the database
    """
    # Validate PIN format
    clean = pin.strip()
    if not re.match(r"^\d{6}$", clean):
        return None

    own_conn = conn is None
    if own_conn:
        conn = get_conn()

    try:
        # Resolve PIN → district
        row = conn.execute(
            "SELECT * FROM pin_district_mapping WHERE pin_code = ?",
            (clean,),
        ).fetchone()

        if not row:
            return None

        district = row["district"]
        state = row["state"]

        # Resolve MP + MLA
        mp_info = _get_first_mp(conn, district, state)
        mla_info = _get_first_mla(conn, district, state)

        # Build diagnosis
        diagnosis = build_diagnosis(conn, district, state)
        flagged_schemes = list({d.scheme for d in diagnosis})

        # Build contacts
        contacts = build_contacts(
            conn, district, state,
            mp_info=mp_info,
            mla_info=mla_info,
            flagged_schemes=flagged_schemes,
        )

        # Build actions
        actions = build_actions(conn, flagged_schemes)

        return ActionBrief(
            pin=clean,
            district=district,
            state=state,
            mp=mp_info,
            mla=mla_info,
            diagnosis=diagnosis,
            contacts=contacts,
            actions=actions,
            scheme_data={},
            generated_at=datetime.now(),
        )
    finally:
        if own_conn:
            conn.close()


def _get_first_mp(
    conn: sqlite3.Connection, district: str, state: str
) -> dict[str, Any] | None:
    """Get the first MP for a district (via constituency mapping)."""
    row = conn.execute(
        """SELECT cd.constituency, m.mp_name, m.party, m.state,
                  m.elected_year, m.source_url
           FROM constituency_district cd
           JOIN mp_info m ON UPPER(cd.constituency) = UPPER(m.constituency)
           WHERE UPPER(cd.district) = UPPER(?)
             AND UPPER(cd.state) = UPPER(?)
           LIMIT 1""",
        (district, state),
    ).fetchone()
    if row:
        return dict(row)
    return None


def _get_first_mla(
    conn: sqlite3.Connection, district: str, state: str
) -> dict[str, Any] | None:
    """Get the first MLA for a district (via AC mapping)."""
    row = conn.execute(
        """SELECT a.ac_name, m.mla_name, m.party, m.state, m.source_url
           FROM ac_district a
           JOIN mla_info m ON UPPER(a.ac_name) = UPPER(m.ac_name)
             AND UPPER(a.state) = UPPER(m.state)
           WHERE UPPER(a.district) = UPPER(?)
             AND UPPER(a.state) = UPPER(?)
           LIMIT 1""",
        (district, state),
    ).fetchone()
    if row:
        return dict(row)
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_action_brief.py -v -k engine`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add action_brief/engine.py tests/test_action_brief.py
git commit -m "feat: action brief engine — PIN to full ActionBrief orchestrator"
```

---

## Task 9: Shareable Card SVG Generation

**Files:**
- Create: `action_brief/card.py`
- Test: `tests/test_action_brief.py` (extend)

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_action_brief.py`:

```python
def test_card_portrait_svg():
    """Portrait card generates valid SVG."""
    from action_brief.card import generate_action_card
    from action_brief.models import ActionBrief, DiagnosisItem

    brief = ActionBrief(
        pin="221001",
        district="VARANASI",
        state="UTTAR PRADESH",
        mp={"mp_name": "Test MP", "party": "BJP"},
        mla={"mla_name": "Test MLA", "party": "INC"},
        diagnosis=[
            DiagnosisItem(
                severity="high",
                scheme="MGNREGA",
                summary="Rs 3.9 crore MGNREGA funds unrecovered",
                detail="",
                amount="Rs 3.9 crore",
                source_url="https://nrega.nic.in/",
            ),
        ],
        contacts=[],
        actions=[],
        scheme_data={},
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
    """Landscape card generates valid SVG with correct dimensions."""
    from action_brief.card import generate_action_card
    from action_brief.models import ActionBrief

    brief = ActionBrief(
        pin="221001",
        district="VARANASI",
        state="UTTAR PRADESH",
        mp={"mp_name": "Test MP", "party": "BJP"},
        mla=None,
        diagnosis=[],
        contacts=[],
        actions=[],
        scheme_data={},
        generated_at=datetime(2026, 3, 30, 14, 30),
    )

    svg_bytes = generate_action_card(brief, fmt="landscape")
    svg_str = svg_bytes.decode("utf-8")
    assert 'width="1200"' in svg_str
    assert 'height="630"' in svg_str
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_action_brief.py -v -k card`
Expected: FAIL

- [ ] **Step 3: Implement action_brief/card.py**

```python
# action_brief/card.py
"""SVG generation for shareable action brief cards.

Portrait (1080x1920) — WhatsApp / stories
Landscape (1200x630) — Twitter / Telegram / OG
"""

from __future__ import annotations

import textwrap

from action_brief.models import ActionBrief

_SEVERITY_COLORS = {
    "high": "#dc2626",
    "medium": "#d97706",
    "low": "#6b7280",
}


def generate_action_card(brief: ActionBrief, fmt: str = "portrait") -> bytes:
    """Generate SVG bytes for the action brief card."""
    if fmt == "landscape":
        return _render_landscape(brief)
    return _render_portrait(brief)


def _render_portrait(brief: ActionBrief) -> bytes:
    w, h = 1080, 1920

    # Diagnosis items (max 4 for portrait)
    diag_svg = ""
    for i, d in enumerate(brief.diagnosis[:4]):
        y = 520 + i * 200
        color = _SEVERITY_COLORS.get(d.severity, "#6b7280")
        summary = textwrap.shorten(d.summary, width=50, placeholder="...")
        detail = textwrap.shorten(d.detail, width=55, placeholder="...") if d.detail else ""
        diag_svg += f"""
    <circle cx="80" cy="{y + 6}" r="14" fill="{color}"/>
    <text x="110" y="{y + 12}" font-size="30" fill="#1f2937" font-family="Inter,sans-serif" font-weight="600">{_escape(summary)}</text>
    <text x="110" y="{y + 52}" font-size="24" fill="#6b7280" font-family="Inter,sans-serif">{_escape(detail)}</text>"""

    # Contacts section
    contacts_y = 520 + min(len(brief.diagnosis), 4) * 200 + 60
    contacts_svg = f'<line x1="60" y1="{contacts_y - 30}" x2="{w - 60}" y2="{contacts_y - 30}" stroke="#e5e7eb" stroke-width="2"/>'

    mp_name = brief.mp.get("mp_name", "—") if brief.mp else "—"
    mp_party = brief.mp.get("party", "") if brief.mp else ""
    mla_name = brief.mla.get("mla_name", "—") if brief.mla else "—"
    mla_party = brief.mla.get("party", "") if brief.mla else ""

    contacts_svg += f"""
    <text x="60" y="{contacts_y + 10}" font-size="28" fill="#374151" font-family="Inter,sans-serif">MP: {_escape(mp_name)} ({_escape(mp_party)})</text>
    <text x="60" y="{contacts_y + 56}" font-size="28" fill="#374151" font-family="Inter,sans-serif">MLA: {_escape(mla_name)} ({_escape(mla_party)})</text>"""

    date_str = brief.generated_at.strftime("%d %b %Y")

    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <rect width="{w}" height="{h}" fill="#f9fafb"/>
  <rect x="0" y="0" width="{w}" height="420" fill="#1e3a5f"/>

  <!-- Header -->
  <text x="60" y="80" font-size="36" fill="#93c5fd" font-family="Inter,sans-serif" font-weight="400">HISAAB</text>
  <line x1="60" y1="100" x2="{w - 60}" y2="100" stroke="#93c5fd" stroke-width="3"/>

  <!-- District -->
  <text x="60" y="190" font-size="60" fill="#ffffff" font-family="Inter,sans-serif" font-weight="700">{_escape(brief.district)}</text>
  <text x="60" y="250" font-size="34" fill="#93c5fd" font-family="Inter,sans-serif">{_escape(brief.state)}</text>

  <!-- Diagnosis -->
  {diag_svg}

  <!-- Contacts -->
  {contacts_svg}

  <!-- Footer -->
  <rect x="0" y="{h - 120}" width="{w}" height="120" fill="#1e3a5f"/>
  <text x="{w // 2}" y="{h - 70}" font-size="28" fill="#93c5fd" text-anchor="middle"
        font-family="Inter,sans-serif">Enter your PIN at hisaab.info</text>
  <text x="{w // 2}" y="{h - 30}" font-size="22" fill="#64748b" text-anchor="middle"
        font-family="Inter,sans-serif">Data as of {date_str}</text>
</svg>"""
    return svg.encode("utf-8")


def _render_landscape(brief: ActionBrief) -> bytes:
    w, h = 1200, 630

    # Diagnosis items (max 3 for landscape)
    diag_svg = ""
    for i, d in enumerate(brief.diagnosis[:3]):
        y = 260 + i * 80
        color = _SEVERITY_COLORS.get(d.severity, "#6b7280")
        summary = textwrap.shorten(d.summary, width=45, placeholder="...")
        diag_svg += f"""
    <circle cx="52" cy="{y}" r="10" fill="{color}"/>
    <text x="72" y="{y + 6}" font-size="22" fill="#1f2937" font-family="Inter,sans-serif">{_escape(summary)}</text>"""

    mp_name = brief.mp.get("mp_name", "—") if brief.mp else "—"
    mla_name = brief.mla.get("mla_name", "—") if brief.mla else "—"
    date_str = brief.generated_at.strftime("%d %b %Y")

    # Abbreviate state for landscape
    state_short = brief.state[:2] if len(brief.state) > 12 else brief.state

    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <rect width="{w}" height="{h}" fill="#f9fafb"/>

  <!-- Header bar -->
  <rect x="0" y="0" width="{w}" height="160" fill="#1e3a5f"/>
  <text x="40" y="60" font-size="28" fill="#93c5fd" font-family="Inter,sans-serif" font-weight="600">HISAAB</text>
  <text x="180" y="60" font-size="28" fill="#ffffff" font-family="Inter,sans-serif" font-weight="700">{_escape(brief.district)}, {_escape(state_short)}</text>
  <text x="{w - 40}" y="50" font-size="20" fill="#bfdbfe" text-anchor="end" font-family="Inter,sans-serif">MP: {_escape(mp_name)}</text>
  <text x="{w - 40}" y="80" font-size="20" fill="#bfdbfe" text-anchor="end" font-family="Inter,sans-serif">MLA: {_escape(mla_name)}</text>

  <!-- Diagnosis -->
  <text x="40" y="220" font-size="22" fill="#374151" font-family="Inter,sans-serif" font-weight="600">Key Issues</text>
  {diag_svg}

  <!-- Footer -->
  <line x1="40" y1="{h - 60}" x2="{w - 40}" y2="{h - 60}" stroke="#e5e7eb" stroke-width="1"/>
  <text x="40" y="{h - 25}" font-size="18" fill="#9ca3af" font-family="Inter,sans-serif">Enter your PIN at hisaab.info</text>
  <text x="{w - 40}" y="{h - 25}" font-size="18" fill="#9ca3af" text-anchor="end" font-family="Inter,sans-serif">Data: {date_str}</text>
</svg>"""
    return svg.encode("utf-8")


def _escape(text: str) -> str:
    """Escape XML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_action_brief.py -v -k card`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add action_brief/card.py tests/test_action_brief.py
git commit -m "feat: shareable action brief SVG cards — portrait + landscape"
```

---

## Task 10: API Routes

**Files:**
- Create: `api/routes/action.py`
- Modify: `api/main.py`
- Test: `tests/test_action_brief.py` (extend)

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_action_brief.py`:

```python
from fastapi.testclient import TestClient


def test_api_action_valid_pin(db):
    """GET /api/v1/action/{pin} returns 200 with correct shape."""
    # Seed data
    db.execute(
        """INSERT INTO pin_district_mapping (pin_code, district, state, office_name)
           VALUES ('221001', 'VARANASI', 'UTTAR PRADESH', 'Varanasi GPO')"""
    )
    db.commit()
    from directory.seed_data import seed_grievance_channels
    seed_grievance_channels(db)

    from api.routes.action import router, _set_test_conn
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    _set_test_conn(db)
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
    from api.routes.action import router, _set_test_conn
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    _set_test_conn(None)
    client = TestClient(app)
    resp = client.get("/api/v1/action/123")
    assert resp.status_code == 400


def test_api_action_card_svg(db):
    """GET /api/v1/action/{pin}/card returns SVG."""
    db.execute(
        """INSERT INTO pin_district_mapping (pin_code, district, state, office_name)
           VALUES ('221001', 'VARANASI', 'UTTAR PRADESH', 'Varanasi GPO')"""
    )
    db.commit()
    from directory.seed_data import seed_grievance_channels
    seed_grievance_channels(db)

    from api.routes.action import router, _set_test_conn
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")

    _set_test_conn(db)
    client = TestClient(app)
    resp = client.get("/api/v1/action/221001/card?format=portrait")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/svg+xml; charset=utf-8"
    assert b"<svg" in resp.content
    _set_test_conn(None)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_action_brief.py -v -k api`
Expected: FAIL

- [ ] **Step 3: Implement api/routes/action.py**

```python
# api/routes/action.py
"""Citizen Action Brief endpoints."""

from __future__ import annotations

import re
import sqlite3
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from action_brief.card import generate_action_card
from action_brief.engine import build_action_brief

router = APIRouter()

# Test injection point — None in production
_test_conn: sqlite3.Connection | None = None


def _set_test_conn(conn: sqlite3.Connection | None) -> None:
    global _test_conn
    _test_conn = conn


@router.get("/action/{pin_code}")
def action_brief(pin_code: str) -> dict[str, Any]:
    """Full citizen action brief for a PIN code.

    Returns diagnosis, contacts, and action items.
    """
    if not re.match(r"^\d{6}$", pin_code.strip()):
        raise HTTPException(status_code=400, detail="PIN code must be exactly 6 digits.")

    brief = build_action_brief(pin_code, conn=_test_conn)
    if not brief:
        raise HTTPException(
            status_code=404,
            detail="PIN code not found. Try a nearby PIN.",
        )

    result = asdict(brief)
    # Convert datetime to ISO string
    result["generated_at"] = brief.generated_at.isoformat()
    # Convert date objects in contacts
    for c in result["contacts"]:
        if c.get("last_verified"):
            c["last_verified"] = str(c["last_verified"])
    return result


@router.get("/action/{pin_code}/card")
def action_card(
    pin_code: str,
    format: str = Query(default="portrait", alias="format"),
) -> Response:
    """Shareable SVG card for a PIN code.

    format: 'portrait' (1080x1920) or 'landscape' (1200x630).
    """
    if not re.match(r"^\d{6}$", pin_code.strip()):
        raise HTTPException(status_code=400, detail="PIN code must be exactly 6 digits.")

    if format not in ("portrait", "landscape"):
        raise HTTPException(status_code=400, detail="format must be 'portrait' or 'landscape'")

    brief = build_action_brief(pin_code, conn=_test_conn)
    if not brief:
        raise HTTPException(
            status_code=404,
            detail="PIN code not found. Try a nearby PIN.",
        )

    svg_bytes = generate_action_card(brief, fmt=format)
    return Response(
        content=svg_bytes,
        media_type="image/svg+xml",
        headers={
            "Content-Disposition": f'inline; filename="hisaab-{pin_code}-{format}.svg"',
            "Cache-Control": "public, max-age=3600",
        },
    )
```

- [ ] **Step 4: Register the router in api/main.py**

Add to `api/main.py` imports:

```python
from api.routes import action
```

Add after the last `app.include_router(...)`:

```python
app.include_router(action.router, prefix="/api/v1", tags=["action"])
```

Add `/api/v1/action/{pin_code}` and `/api/v1/action/{pin_code}/card` to the root endpoint list.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_action_brief.py -v -k api`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add api/routes/action.py api/main.py tests/test_action_brief.py
git commit -m "feat: API endpoints — GET /action/{pin} and /action/{pin}/card"
```

---

## Task 11: Frontend TypeScript Types

**Files:**
- Create: `web/src/lib/action-types.ts`

- [ ] **Step 1: Create action-types.ts**

```typescript
// web/src/lib/action-types.ts
/** TypeScript interfaces for the /api/v1/action/{pin} response. */

export interface DiagnosisItem {
  severity: "high" | "medium" | "low";
  scheme: string;
  summary: string;
  detail: string;
  amount: string | null;
  source_url: string;
}

export interface ContactCard {
  role: string;
  name: string | null;
  phone: string | null;
  email: string | null;
  office_address: string | null;
  relevance: string;
  source_url: string;
  last_verified: string;
  freshness: "fresh" | "stale" | "expired";
}

export interface ActionItem {
  scheme: string;
  action: string;
  portal_name: string;
  portal_url: string;
  escalation: string;
  escalation_url: string;
}

export interface MPInfo {
  mp_name: string;
  party: string;
  constituency: string;
  state: string;
}

export interface MLAInfo {
  mla_name: string;
  party: string;
  ac_name: string;
  state: string;
}

export interface ActionBriefResponse {
  pin: string;
  district: string;
  state: string;
  mp: MPInfo | null;
  mla: MLAInfo | null;
  diagnosis: DiagnosisItem[];
  contacts: ContactCard[];
  actions: ActionItem[];
  scheme_data: Record<string, unknown>;
  generated_at: string;
}
```

- [ ] **Step 2: Commit**

```bash
git add web/src/lib/action-types.ts
git commit -m "feat: TypeScript types for ActionBrief API response"
```

---

## Task 12: Frontend — Action Brief Page

**Files:**
- Create: `web/src/app/action/[pin]/page.tsx`
- Create: `web/src/app/action/[pin]/loading.tsx`
- Create: `web/src/components/DiagnosisCard.tsx`
- Create: `web/src/components/ContactCard.tsx`
- Create: `web/src/components/ActionCard.tsx`

**Important:** Before implementing, read `node_modules/next/dist/docs/` for Next.js 15 API conventions per the project's `web/AGENTS.md`.

- [ ] **Step 1: Create the loading skeleton**

```tsx
// web/src/app/action/[pin]/loading.tsx
export default function ActionLoading() {
  return (
    <div className="flex-1 px-4 sm:px-6 py-8">
      <div className="max-w-3xl mx-auto space-y-6">
        {/* Header skeleton */}
        <div className="rounded-2xl p-6" style={{ background: "var(--surface)", boxShadow: "var(--shadow-md)" }}>
          <div className="h-8 w-48 rounded-lg animate-pulse" style={{ background: "var(--border)" }} />
          <div className="h-5 w-32 mt-2 rounded-lg animate-pulse" style={{ background: "var(--border-subtle)" }} />
          <div className="flex gap-4 mt-4">
            <div className="h-5 w-40 rounded-lg animate-pulse" style={{ background: "var(--border-subtle)" }} />
            <div className="h-5 w-40 rounded-lg animate-pulse" style={{ background: "var(--border-subtle)" }} />
          </div>
        </div>
        {/* Diagnosis skeletons */}
        {[1, 2, 3].map((i) => (
          <div key={i} className="rounded-xl p-5" style={{ background: "var(--surface)", boxShadow: "var(--shadow-sm)" }}>
            <div className="h-5 w-3/4 rounded-lg animate-pulse" style={{ background: "var(--border)" }} />
            <div className="h-4 w-1/2 mt-2 rounded-lg animate-pulse" style={{ background: "var(--border-subtle)" }} />
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create DiagnosisCard component**

```tsx
// web/src/components/DiagnosisCard.tsx
import type { DiagnosisItem } from "@/lib/action-types";

const SEVERITY_COLORS = {
  high: "oklch(0.55 0.22 25)",    // red
  medium: "oklch(0.65 0.18 65)",  // amber
  low: "oklch(0.55 0.10 250)",    // blue-gray
} as const;

export default function DiagnosisCard({ item }: { item: DiagnosisItem }) {
  const dotColor = SEVERITY_COLORS[item.severity] || SEVERITY_COLORS.low;

  return (
    <div
      className="rounded-xl px-5 py-4 flex gap-4 items-start"
      style={{ background: "var(--surface)", boxShadow: "var(--shadow-sm)" }}
    >
      <span
        className="mt-1 w-3 h-3 rounded-full shrink-0"
        style={{ background: dotColor }}
        aria-label={`${item.severity} severity`}
      />
      <div className="min-w-0">
        <p className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
          {item.summary}
        </p>
        {item.detail && (
          <p className="text-xs mt-1" style={{ color: "var(--text-secondary)" }}>
            {item.detail}
          </p>
        )}
        <a
          href={item.source_url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs mt-2 inline-block hover:underline"
          style={{ color: "var(--accent)" }}
        >
          Source
        </a>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Create ContactCard component**

```tsx
// web/src/components/ContactCard.tsx
import type { ContactCard as ContactCardType } from "@/lib/action-types";

export default function ContactCard({ contact }: { contact: ContactCardType }) {
  const isStale = contact.freshness === "stale";
  const isExpired = contact.freshness === "expired";

  return (
    <div
      className="rounded-xl px-5 py-4"
      style={{ background: "var(--surface)", boxShadow: "var(--shadow-sm)" }}
    >
      <p className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
        {contact.role}
      </p>

      {contact.name ? (
        <p className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>
          {contact.name}
        </p>
      ) : (
        <p className="text-xs mt-1 italic" style={{ color: "var(--text-muted)" }}>
          Contact the {contact.role} office —{" "}
          <a href={contact.source_url} target="_blank" rel="noopener noreferrer" className="hover:underline" style={{ color: "var(--accent)" }}>
            verify at source
          </a>
        </p>
      )}

      {contact.phone && (
        <a
          href={`tel:${contact.phone}`}
          className="text-xs mt-1 inline-block hover:underline"
          style={{ color: "var(--accent)" }}
        >
          {contact.phone}
        </a>
      )}

      {contact.email && (
        <a
          href={`mailto:${contact.email}`}
          className="text-xs mt-1 ml-3 inline-block hover:underline"
          style={{ color: "var(--accent)" }}
        >
          {contact.email}
        </a>
      )}

      {contact.office_address && (
        <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
          {contact.office_address}
        </p>
      )}

      <p className="text-xs mt-1" style={{ color: "var(--text-muted)" }}>
        {contact.relevance}
      </p>

      <div className="flex items-center gap-2 mt-2">
        <span
          className="text-xs"
          style={{ color: isStale ? "oklch(0.65 0.18 65)" : isExpired ? "oklch(0.55 0.22 25)" : "var(--text-muted)" }}
        >
          {isStale && "May be outdated — "}
          {isExpired && "Data expired — "}
          Verified {contact.last_verified}
        </span>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Create ActionCard component**

```tsx
// web/src/components/ActionCard.tsx
import type { ActionItem } from "@/lib/action-types";

export default function ActionCard({ action }: { action: ActionItem }) {
  return (
    <div
      className="rounded-xl px-5 py-4"
      style={{ background: "var(--surface)", boxShadow: "var(--shadow-sm)" }}
    >
      <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>
        {action.scheme}
      </p>
      <p className="text-sm font-semibold mt-1" style={{ color: "var(--text-primary)" }}>
        {action.action}
      </p>
      <a
        href={action.portal_url}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-block mt-3 px-4 py-2 rounded-lg text-xs font-semibold transition-opacity hover:opacity-80"
        style={{
          background: "var(--accent-gradient, var(--accent))",
          color: "white",
        }}
      >
        Go to {action.portal_name}
      </a>
      <p className="text-xs mt-2" style={{ color: "var(--text-muted)" }}>
        {action.escalation}{" "}
        <a
          href={action.escalation_url}
          target="_blank"
          rel="noopener noreferrer"
          className="hover:underline"
          style={{ color: "var(--accent)" }}
        >
          CPGRAMS
        </a>
      </p>
    </div>
  );
}
```

- [ ] **Step 5: Create the main action page**

```tsx
// web/src/app/action/[pin]/page.tsx
import { Suspense } from "react";
import { notFound } from "next/navigation";
import type { ActionBriefResponse } from "@/lib/action-types";
import DiagnosisCard from "@/components/DiagnosisCard";
import ContactCard from "@/components/ContactCard";
import ActionCard from "@/components/ActionCard";
import ActionLoading from "./loading";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function fetchActionBrief(pin: string): Promise<ActionBriefResponse | null> {
  try {
    const res = await fetch(`${API}/api/v1/action/${pin}`, { cache: "no-store" });
    if (res.status === 404) return null;
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

async function ActionContent({ pin }: { pin: string }) {
  const brief = await fetchActionBrief(pin);
  if (!brief) notFound();

  const hasDiagnosis = brief.diagnosis.length > 0;

  return (
    <div className="max-w-3xl mx-auto space-y-8">
      {/* Header */}
      <div
        className="rounded-2xl p-6 animate-fade-in-up"
        style={{ background: "var(--surface)", boxShadow: "var(--shadow-md)" }}
      >
        <h1 className="text-2xl sm:text-3xl font-bold" style={{ color: "var(--text-primary)" }}>
          {brief.district}
        </h1>
        <p className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>
          {brief.state}
        </p>
        <div className="flex flex-wrap gap-4 mt-4">
          {brief.mp && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>MP</p>
              <p className="text-sm" style={{ color: "var(--text-primary)" }}>
                {brief.mp.mp_name} <span style={{ color: "var(--text-muted)" }}>({brief.mp.party})</span>
              </p>
            </div>
          )}
          {brief.mla && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: "var(--text-muted)" }}>MLA</p>
              <p className="text-sm" style={{ color: "var(--text-primary)" }}>
                {brief.mla.mla_name} <span style={{ color: "var(--text-muted)" }}>({brief.mla.party})</span>
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Layer 1: What's Wrong */}
      <section className="space-y-3 animate-fade-in-up stagger-1">
        <h2 className="text-xs font-semibold uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>
          What&apos;s Wrong
        </h2>
        {hasDiagnosis ? (
          brief.diagnosis.map((d, i) => <DiagnosisCard key={i} item={d} />)
        ) : (
          <div
            className="rounded-xl px-5 py-6 text-center"
            style={{ background: "oklch(0.95 0.05 145)", boxShadow: "var(--shadow-sm)" }}
          >
            <p className="text-sm font-semibold" style={{ color: "oklch(0.35 0.15 145)" }}>
              No major red flags detected in {brief.district}.
            </p>
            <p className="text-xs mt-1" style={{ color: "oklch(0.45 0.10 145)" }}>
              Your area is performing at or above state average across tracked schemes.
            </p>
          </div>
        )}
      </section>

      {/* Layer 2: Who's Responsible */}
      {brief.contacts.length > 0 && (
        <section className="space-y-3 animate-fade-in-up stagger-2">
          <h2 className="text-xs font-semibold uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>
            Who&apos;s Responsible
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {brief.contacts.map((c, i) => (
              <ContactCard key={i} contact={c} />
            ))}
          </div>
        </section>
      )}

      {/* Layer 3: What You Can Do */}
      {brief.actions.length > 0 && (
        <section className="space-y-3 animate-fade-in-up stagger-3">
          <h2 className="text-xs font-semibold uppercase tracking-widest" style={{ color: "var(--text-muted)" }}>
            What You Can Do
          </h2>
          {brief.actions.map((a, i) => (
            <ActionCard key={i} action={a} />
          ))}
        </section>
      )}

      {/* Universal fallback */}
      <div
        className="rounded-xl px-5 py-4 text-center animate-fade-in-up stagger-4"
        style={{ background: "var(--surface-tinted)", boxShadow: "var(--shadow-sm)" }}
      >
        <p className="text-xs" style={{ color: "var(--text-secondary)" }}>
          For any government service complaint, file at{" "}
          <a href="https://pgportal.gov.in/" target="_blank" rel="noopener noreferrer" className="font-semibold hover:underline" style={{ color: "var(--accent)" }}>
            CPGRAMS
          </a>
          {" "}or file an RTI request at{" "}
          <a href="https://rtionline.gov.in/" target="_blank" rel="noopener noreferrer" className="font-semibold hover:underline" style={{ color: "var(--accent)" }}>
            rtionline.gov.in
          </a>
        </p>
      </div>
    </div>
  );
}

export default async function ActionPage({ params }: { params: Promise<{ pin: string }> }) {
  const { pin } = await params;

  return (
    <main className="flex-1 px-4 sm:px-6 py-8">
      <Suspense fallback={<ActionLoading />}>
        <ActionContent pin={pin} />
      </Suspense>
    </main>
  );
}
```

- [ ] **Step 6: Commit**

```bash
git add web/src/app/action/ web/src/components/DiagnosisCard.tsx web/src/components/ContactCard.tsx web/src/components/ActionCard.tsx
git commit -m "feat: /action/[pin] page — three-layer citizen action brief"
```

---

## Task 13: Share Button Component

**Files:**
- Create: `web/src/components/ShareButton.tsx`
- Modify: `web/src/app/action/[pin]/page.tsx`

- [ ] **Step 1: Create ShareButton.tsx**

```tsx
// web/src/components/ShareButton.tsx
"use client";

import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ShareButton({ pin, district }: { pin: string; district: string }) {
  const [sharing, setSharing] = useState(false);

  async function handleShare() {
    setSharing(true);
    try {
      const res = await fetch(`${API}/api/v1/action/${pin}/card?format=portrait`);
      if (!res.ok) throw new Error("Failed to fetch card");
      const svgText = await res.text();

      // Convert SVG to PNG via canvas
      const img = new Image();
      const blob = new Blob([svgText], { type: "image/svg+xml" });
      const url = URL.createObjectURL(blob);

      img.onload = async () => {
        const canvas = document.createElement("canvas");
        canvas.width = 1080;
        canvas.height = 1920;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;
        ctx.drawImage(img, 0, 0, 1080, 1920);
        URL.revokeObjectURL(url);

        canvas.toBlob(async (pngBlob) => {
          if (!pngBlob) return;

          const file = new File([pngBlob], `hisaab-${district.toLowerCase()}.png`, {
            type: "image/png",
          });

          // Try Web Share API first (mobile)
          if (navigator.share && navigator.canShare?.({ files: [file] })) {
            await navigator.share({
              title: `Hisaab — ${district}`,
              text: `Check the government scheme performance in ${district}`,
              files: [file],
            });
          } else {
            // Desktop fallback: download
            const a = document.createElement("a");
            a.href = URL.createObjectURL(pngBlob);
            a.download = `hisaab-${district.toLowerCase()}.png`;
            a.click();
            URL.revokeObjectURL(a.href);
          }
          setSharing(false);
        }, "image/png");
      };
      img.src = url;
    } catch {
      setSharing(false);
    }
  }

  return (
    <button
      onClick={handleShare}
      disabled={sharing}
      className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-opacity hover:opacity-80 disabled:opacity-50"
      style={{
        background: "var(--surface)",
        color: "var(--text-primary)",
        boxShadow: "var(--shadow-sm)",
        border: "1px solid var(--border)",
      }}
    >
      <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M4 12v1a2 2 0 002 2h4a2 2 0 002-2v-1M12 5l-4-4-4 4M8 1v10" />
      </svg>
      {sharing ? "Sharing..." : "Share"}
    </button>
  );
}
```

- [ ] **Step 2: Add ShareButton to the action page**

In `web/src/app/action/[pin]/page.tsx`, add to the header card (after the state line, before the MP/MLA section):

```tsx
import ShareButton from "@/components/ShareButton";
```

Inside the header `<div>`, add after the state `<p>`:

```tsx
<div className="mt-3">
  <ShareButton pin={pin} district={brief.district} />
</div>
```

Note: `pin` must be passed to `ActionContent` as a prop. Update the component signature:

```tsx
async function ActionContent({ pin }: { pin: string }) {
```

And pass `pin` in the `ShareButton`:

```tsx
<ShareButton pin={pin} district={brief.district} />
```

- [ ] **Step 3: Commit**

```bash
git add web/src/components/ShareButton.tsx web/src/app/action/\[pin\]/page.tsx
git commit -m "feat: share button — SVG to PNG with Web Share API + download fallback"
```

---

## Task 14: Home Page — PIN Input as Hero

**Files:**
- Modify: `web/src/app/page.tsx`
- Modify: `web/src/app/layout.tsx`

- [ ] **Step 1: Update home page hero**

In `web/src/app/page.tsx`, replace the CTA section (lines 122-160, the "Your MP's Report Card" block) with a PIN-first action CTA:

```tsx
{/* CTA: Check Your Area */}
<section className="px-4 sm:px-6 py-12">
  <div className="max-w-xl mx-auto animate-fade-in-up">
    <div
      className="rounded-2xl p-6 sm:p-8 text-center"
      style={{
        background: "var(--surface-tinted)",
        boxShadow: "var(--shadow-md)",
      }}
    >
      <p
        className="text-sm font-semibold uppercase tracking-widest mb-2"
        style={{ color: "var(--accent)" }}
      >
        New
      </p>
      <h3
        className="text-xl sm:text-2xl font-bold mb-2"
        style={{ color: "var(--text-primary)" }}
      >
        Check Your Area
      </h3>
      <p className="text-sm mb-4" style={{ color: "var(--text-secondary)" }}>
        Enter your 6-digit PIN code to see what&apos;s wrong, who&apos;s responsible,
        and what you can do about it.
      </p>
      <PinInput />
    </div>
  </div>
</section>
```

Create a small client component for the PIN input (inline or separate — inline is simpler). Add at top of `page.tsx`:

```tsx
"use client" // only if needed — or extract PinInput to a separate client component
```

Since this is a server component page, extract `PinInput` to a client component file:

Create `web/src/components/PinInput.tsx`:

```tsx
// web/src/components/PinInput.tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function PinInput() {
  const [pin, setPin] = useState("");
  const router = useRouter();

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const clean = pin.trim();
    if (/^\d{6}$/.test(clean)) {
      router.push(`/action/${clean}`);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex items-center justify-center gap-2">
      <input
        type="text"
        inputMode="numeric"
        pattern="[0-9]{6}"
        maxLength={6}
        placeholder="Enter PIN code"
        value={pin}
        onChange={(e) => setPin(e.target.value.replace(/\D/g, "").slice(0, 6))}
        className="w-36 px-4 py-2 rounded-lg text-center text-sm font-mono tabular-nums"
        style={{
          background: "var(--surface)",
          color: "var(--text-primary)",
          border: "1px solid var(--border)",
        }}
      />
      <button
        type="submit"
        disabled={pin.length !== 6}
        className="px-4 py-2 rounded-lg text-sm font-semibold transition-opacity hover:opacity-80 disabled:opacity-40"
        style={{
          background: "var(--accent-gradient, var(--accent))",
          color: "white",
        }}
      >
        Go
      </button>
    </form>
  );
}
```

Import in `page.tsx`:

```tsx
import PinInput from "@/components/PinInput";
```

- [ ] **Step 2: Add "Check Your Area" to nav**

In `web/src/app/layout.tsx`, add a nav link in the NavBar. Find the existing nav links (Home, MP Cards) and add:

```tsx
<Link href="/action" className="..." style={{...}}>
  Check Your Area
</Link>
```

Note: Since `/action` without a PIN doesn't exist as a page, link to the home page's PIN section or create a redirect. Simplest approach: link to `/#check` and add `id="check"` to the CTA section.

Alternative: Keep linking to home page and rely on the hero CTA.

- [ ] **Step 3: Commit**

```bash
git add web/src/components/PinInput.tsx web/src/app/page.tsx web/src/app/layout.tsx
git commit -m "feat: home page PIN input CTA + Check Your Area nav link"
```

---

## Task 15: DB Loaders for Officials + Grievance Channels

**Files:**
- Modify: `db/loaders.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_directory.py`:

```python
def test_load_district_officials(db):
    from db.loaders import load_district_officials
    records = [
        {
            "state": "UTTAR PRADESH",
            "district": "VARANASI",
            "role": "District Collector",
            "name": "Test DC",
            "phone": "9876543210",
            "email": "dc@varanasi.nic.in",
            "office_address": "DC Office",
            "source_url": "https://varanasi.nic.in",
            "scraped_at": "2026-03-30T00:00:00",
        }
    ]
    count = load_district_officials(db, records)
    assert count == 1

    row = db.execute("SELECT * FROM district_officials WHERE district='VARANASI'").fetchone()
    assert row["name"] == "Test DC"


def test_load_grievance_channels(db):
    from db.loaders import load_grievance_channels
    records = [
        {
            "scheme": "MGNREGA",
            "level": "national",
            "portal_name": "Test Portal",
            "portal_url": "https://example.gov.in",
            "phone": None,
            "description": "Test",
            "escalation_scheme": None,
            "source_url": "https://example.gov.in",
            "scraped_at": "2026-03-30T00:00:00",
        }
    ]
    count = load_grievance_channels(db, records)
    assert count == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_directory.py -v -k load`
Expected: FAIL — `ImportError`

- [ ] **Step 3: Add loaders to db/loaders.py**

Add at the end of `db/loaders.py`:

```python
def load_district_officials(
    conn: sqlite3.Connection,
    records: list[dict[str, Any]],
) -> int:
    """Load district official records."""
    loaded = 0
    for r in records:
        try:
            conn.execute(
                """INSERT OR REPLACE INTO district_officials
                   (state, district, role, name, phone, email, office_address,
                    source_url, scraped_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    r.get("state", ""),
                    r.get("district", ""),
                    r.get("role", ""),
                    r.get("name", ""),
                    r.get("phone"),
                    r.get("email"),
                    r.get("office_address"),
                    r.get("source_url", ""),
                    r.get("scraped_at", ""),
                ),
            )
            loaded += 1
        except sqlite3.IntegrityError:
            pass
    return loaded


def load_grievance_channels(
    conn: sqlite3.Connection,
    records: list[dict[str, Any]],
) -> int:
    """Load grievance channel records."""
    loaded = 0
    for r in records:
        try:
            conn.execute(
                """INSERT OR REPLACE INTO grievance_channels
                   (scheme, level, portal_name, portal_url, phone, description,
                    escalation_scheme, source_url, scraped_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    r.get("scheme", ""),
                    r.get("level", ""),
                    r.get("portal_name", ""),
                    r.get("portal_url", ""),
                    r.get("phone"),
                    r.get("description"),
                    r.get("escalation_scheme"),
                    r.get("source_url", ""),
                    r.get("scraped_at", ""),
                ),
            )
            loaded += 1
        except sqlite3.IntegrityError:
            pass
    return loaded
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_directory.py -v -k load`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add db/loaders.py tests/test_directory.py
git commit -m "feat: DB loaders for district_officials and grievance_channels"
```

---

## Task 16: Run Full Test Suite

- [ ] **Step 1: Run all new tests**

Run: `python3 -m pytest tests/test_action_brief.py tests/test_directory.py -v`
Expected: All tests PASS

- [ ] **Step 2: Run existing test suite to check for regressions**

Run: `python3 -m pytest tests/ -v`
Expected: No regressions — all existing tests still pass

- [ ] **Step 3: Build frontend**

Run: `cd web && npm run build`
Expected: Build succeeds with no TypeScript errors

- [ ] **Step 4: Commit any fixes needed**

If any tests fail, fix and commit:
```bash
git add -A
git commit -m "fix: address test failures from action brief integration"
```

---

## Summary

| Task | What it delivers | Tests |
|------|-----------------|-------|
| 1 | `district_officials` + `grievance_channels` tables | 4 |
| 2 | `directory/` module — query officials + grievances | 7 |
| 3 | Seed data for grievance channels | 1 |
| 4 | ActionBrief dataclasses | 4 |
| 5 | Diagnosis engine (red flags → English) | 5 |
| 6 | Contacts builder (MP/MLA/DC ordering) | 2 |
| 7 | Action items builder (portals + escalation) | 3 |
| 8 | Engine orchestrator (PIN → ActionBrief) | 3 |
| 9 | SVG card generation | 2 |
| 10 | API routes (`/action/{pin}`, `/action/{pin}/card`) | 3 |
| 11 | TypeScript types | 0 |
| 12 | Frontend page + components | 0 (manual) |
| 13 | Share button | 0 (manual) |
| 14 | Home page hero + nav | 0 (manual) |
| 15 | DB loaders | 2 |
| 16 | Full suite validation | regression check |
| **Total** | | **~36 tests** |
