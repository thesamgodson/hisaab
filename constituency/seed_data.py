"""Sample seed data for constituency mapping tables.

Contains ~10 Lok Sabha constituencies from Bihar and Uttar Pradesh.
Run this script directly to insert data into the database:

    python3 constituency/seed_data.py

Or import and call seed_all() in tests / scripts.

Data accuracy note: district→constituency mappings here are approximate and
for development/testing only.  For production, use the official ECI delimitation
order (2008) available at https://eci.gov.in/delimitation/
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running as a script from the project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from constituency.mapper import load_constituency_data, load_mp_data, load_pin_data
from db import init_db, get_connection

# ---------------------------------------------------------------------------
# PIN code samples (India Post — for dev/test only)
# ---------------------------------------------------------------------------

SAMPLE_PINS: list[dict] = [
    # Bihar
    {"pin_code": "800001", "district": "PATNA", "state": "BIHAR", "office_name": "Patna GPO"},
    {"pin_code": "800002", "district": "PATNA", "state": "BIHAR", "office_name": "Bankipore SO"},
    {"pin_code": "801503", "district": "NALANDA", "state": "BIHAR", "office_name": "Biharsharif HO"},
    {"pin_code": "823001", "district": "GAYA", "state": "BIHAR", "office_name": "Gaya HO"},
    {"pin_code": "842001", "district": "MUZAFFARPUR", "state": "BIHAR", "office_name": "Muzaffarpur HO"},
    {"pin_code": "844101", "district": "VAISHALI", "state": "BIHAR", "office_name": "Hajipur HO"},
    {"pin_code": "811101", "district": "MUNGER", "state": "BIHAR", "office_name": "Munger HO"},
    {"pin_code": "812001", "district": "BHAGALPUR", "state": "BIHAR", "office_name": "Bhagalpur HO"},
    # Uttar Pradesh
    {"pin_code": "226001", "district": "LUCKNOW", "state": "UTTAR PRADESH", "office_name": "Lucknow GPO"},
    {"pin_code": "221001", "district": "VARANASI", "state": "UTTAR PRADESH", "office_name": "Varanasi HO"},
    {"pin_code": "282001", "district": "AGRA", "state": "UTTAR PRADESH", "office_name": "Agra HO"},
    {"pin_code": "208001", "district": "KANPUR NAGAR", "state": "UTTAR PRADESH", "office_name": "Kanpur GPO"},
    {"pin_code": "201001", "district": "GHAZIABAD", "state": "UTTAR PRADESH", "office_name": "Ghaziabad HO"},
    {"pin_code": "273001", "district": "GORAKHPUR", "state": "UTTAR PRADESH", "office_name": "Gorakhpur HO"},
]


# ---------------------------------------------------------------------------
# Constituency → District mappings (approximate, for dev/test)
# ---------------------------------------------------------------------------

SAMPLE_CONSTITUENCIES: list[dict] = [
    # Bihar
    {"constituency": "PATNA SAHIB", "state": "BIHAR", "district": "PATNA", "constituency_type": "LOK_SABHA"},
    {"constituency": "PATNA SAHIB", "state": "BIHAR", "district": "NALANDA", "constituency_type": "LOK_SABHA"},
    {"constituency": "NALANDA", "state": "BIHAR", "district": "NALANDA", "constituency_type": "LOK_SABHA"},
    {"constituency": "GAYA", "state": "BIHAR", "district": "GAYA", "constituency_type": "LOK_SABHA"},
    {"constituency": "MUZAFFARPUR", "state": "BIHAR", "district": "MUZAFFARPUR", "constituency_type": "LOK_SABHA"},
    {"constituency": "MUZAFFARPUR", "state": "BIHAR", "district": "SITAMARHI", "constituency_type": "LOK_SABHA"},
    {"constituency": "VAISHALI", "state": "BIHAR", "district": "VAISHALI", "constituency_type": "LOK_SABHA"},
    {"constituency": "MUNGER", "state": "BIHAR", "district": "MUNGER", "constituency_type": "LOK_SABHA"},
    {"constituency": "MUNGER", "state": "BIHAR", "district": "LAKHISARAI", "constituency_type": "LOK_SABHA"},
    {"constituency": "BHAGALPUR", "state": "BIHAR", "district": "BHAGALPUR", "constituency_type": "LOK_SABHA"},
    # Uttar Pradesh
    {"constituency": "LUCKNOW", "state": "UTTAR PRADESH", "district": "LUCKNOW", "constituency_type": "LOK_SABHA"},
    {"constituency": "VARANASI", "state": "UTTAR PRADESH", "district": "VARANASI", "constituency_type": "LOK_SABHA"},
    {"constituency": "AGRA", "state": "UTTAR PRADESH", "district": "AGRA", "constituency_type": "LOK_SABHA"},
    {"constituency": "KANPUR", "state": "UTTAR PRADESH", "district": "KANPUR NAGAR", "constituency_type": "LOK_SABHA"},
    {"constituency": "GHAZIABAD", "state": "UTTAR PRADESH", "district": "GHAZIABAD", "constituency_type": "LOK_SABHA"},
    {"constituency": "GORAKHPUR", "state": "UTTAR PRADESH", "district": "GORAKHPUR", "constituency_type": "LOK_SABHA"},
]


# ---------------------------------------------------------------------------
# MP info — 18th Lok Sabha (June 2024)
# ---------------------------------------------------------------------------

SAMPLE_MP_INFO: list[dict] = [
    # Bihar
    {
        "constituency": "PATNA SAHIB",
        "mp_name": "Ravi Shankar Prasad",
        "party": "BJP",
        "state": "BIHAR",
        "elected_year": 2024,
        "source_url": "https://sansad.in/ls/members",
    },
    {
        "constituency": "NALANDA",
        "mp_name": "Kaushalendra Kumar",
        "party": "JDU",
        "state": "BIHAR",
        "elected_year": 2024,
        "source_url": "https://sansad.in/ls/members",
    },
    {
        "constituency": "GAYA",
        "mp_name": "Jitam Ram Manjhi",
        "party": "HAM",
        "state": "BIHAR",
        "elected_year": 2024,
        "source_url": "https://sansad.in/ls/members",
    },
    {
        "constituency": "MUZAFFARPUR",
        "mp_name": "Raj Bhushan Choudhary",
        "party": "BJP",
        "state": "BIHAR",
        "elected_year": 2024,
        "source_url": "https://sansad.in/ls/members",
    },
    {
        "constituency": "VAISHALI",
        "mp_name": "Veena Devi",
        "party": "LJP(RV)",
        "state": "BIHAR",
        "elected_year": 2024,
        "source_url": "https://sansad.in/ls/members",
    },
    {
        "constituency": "MUNGER",
        "mp_name": "Rajiv Ranjan Singh 'Lalan'",
        "party": "JDU",
        "state": "BIHAR",
        "elected_year": 2024,
        "source_url": "https://sansad.in/ls/members",
    },
    {
        "constituency": "BHAGALPUR",
        "mp_name": "Ajay Kumar Mandal",
        "party": "BJP",
        "state": "BIHAR",
        "elected_year": 2024,
        "source_url": "https://sansad.in/ls/members",
    },
    # Uttar Pradesh
    {
        "constituency": "LUCKNOW",
        "mp_name": "Rajnath Singh",
        "party": "BJP",
        "state": "UTTAR PRADESH",
        "elected_year": 2024,
        "source_url": "https://sansad.in/ls/members",
    },
    {
        "constituency": "VARANASI",
        "mp_name": "Narendra Modi",
        "party": "BJP",
        "state": "UTTAR PRADESH",
        "elected_year": 2024,
        "source_url": "https://sansad.in/ls/members",
    },
    {
        "constituency": "AGRA",
        "mp_name": "S.P. Singh Baghel",
        "party": "BJP",
        "state": "UTTAR PRADESH",
        "elected_year": 2024,
        "source_url": "https://sansad.in/ls/members",
    },
    {
        "constituency": "KANPUR",
        "mp_name": "Ramesh Awasthi",
        "party": "BJP",
        "state": "UTTAR PRADESH",
        "elected_year": 2024,
        "source_url": "https://sansad.in/ls/members",
    },
    {
        "constituency": "GHAZIABAD",
        "mp_name": "Atul Garg",
        "party": "BJP",
        "state": "UTTAR PRADESH",
        "elected_year": 2024,
        "source_url": "https://sansad.in/ls/members",
    },
    {
        "constituency": "GORAKHPUR",
        "mp_name": "Ravi Kishan",
        "party": "BJP",
        "state": "UTTAR PRADESH",
        "elected_year": 2024,
        "source_url": "https://sansad.in/ls/members",
    },
]


# ---------------------------------------------------------------------------
# Seed runner
# ---------------------------------------------------------------------------

def seed_all() -> dict[str, int]:
    """Insert all sample data. Returns counts per table."""
    conn = get_connection()
    init_db(conn)
    conn.close()

    pins = load_pin_data(SAMPLE_PINS)
    constituencies = load_constituency_data(SAMPLE_CONSTITUENCIES)
    mps = load_mp_data(SAMPLE_MP_INFO)

    return {"pins": pins, "constituencies": constituencies, "mps": mps}


if __name__ == "__main__":
    counts = seed_all()
    print(f"Seeded: {counts['pins']} PINs, {counts['constituencies']} constituency-district "
          f"mappings, {counts['mps']} MPs")
