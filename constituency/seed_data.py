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
from db import get_connection, init_db
from db.connection import DB_PATH

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
# District lineage — tracks splits/reorganizations so the UI can show
# "formerly part of <parent>" for newly carved-out districts.
# ---------------------------------------------------------------------------

DISTRICT_LINEAGE: list[dict] = [
    # ==========================================================================
    # TELANGANA — 2016 reorganization (10 → 33 districts)
    # ==========================================================================
    {"new_district": "MEDCHAL MALKAJGIRI", "parent_district": "RANGAREDDY", "state": "TELANGANA", "split_year": 2016},
    {"new_district": "VIKARABAD", "parent_district": "RANGAREDDY", "state": "TELANGANA", "split_year": 2016},
    {"new_district": "SHAMSHABAD", "parent_district": "RANGAREDDY", "state": "TELANGANA", "split_year": 2016},
    {"new_district": "WANAPARTHY", "parent_district": "MAHABUBNAGAR", "state": "TELANGANA", "split_year": 2016},
    {"new_district": "NAGARKURNOOL", "parent_district": "MAHABUBNAGAR", "state": "TELANGANA", "split_year": 2016},
    {"new_district": "JOGULAMBA GADWAL", "parent_district": "MAHABUBNAGAR", "state": "TELANGANA", "split_year": 2016},
    {"new_district": "NARAYANPET", "parent_district": "MAHABUBNAGAR", "state": "TELANGANA", "split_year": 2016},
    {"new_district": "YADADRI BHUVANGIRI", "parent_district": "NALGONDA", "state": "TELANGANA", "split_year": 2016},
    {"new_district": "SURYAPET", "parent_district": "NALGONDA", "state": "TELANGANA", "split_year": 2016},
    {"new_district": "SIDDIPET", "parent_district": "MEDAK", "state": "TELANGANA", "split_year": 2016},
    {"new_district": "SANGAREDDY", "parent_district": "MEDAK", "state": "TELANGANA", "split_year": 2016},
    {"new_district": "KAMAREDDY", "parent_district": "NIZAMABAD", "state": "TELANGANA", "split_year": 2016},
    {"new_district": "RAJANNA SIRCILLA", "parent_district": "KARIMNAGAR", "state": "TELANGANA", "split_year": 2016},
    {"new_district": "PEDDAPALLI", "parent_district": "KARIMNAGAR", "state": "TELANGANA", "split_year": 2016},
    {"new_district": "JAGTIAL", "parent_district": "KARIMNAGAR", "state": "TELANGANA", "split_year": 2016},
    {"new_district": "JAYASHANKAR BHUPALPALLY", "parent_district": "WARANGAL", "state": "TELANGANA", "split_year": 2016},
    {"new_district": "MAHABUBABAD", "parent_district": "WARANGAL", "state": "TELANGANA", "split_year": 2016},
    {"new_district": "JANGAON", "parent_district": "WARANGAL", "state": "TELANGANA", "split_year": 2016},
    {"new_district": "MANCHERIAL", "parent_district": "ADILABAD", "state": "TELANGANA", "split_year": 2016},
    {"new_district": "NIRMAL", "parent_district": "ADILABAD", "state": "TELANGANA", "split_year": 2016},
    {"new_district": "KUMURAM BHEEM ASIFABAD", "parent_district": "ADILABAD", "state": "TELANGANA", "split_year": 2016},
    {"new_district": "BHADRADRI KOTHAGUDEM", "parent_district": "KHAMMAM", "state": "TELANGANA", "split_year": 2016},
    # ==========================================================================
    # ANDHRA PRADESH — 2022 reorganization (13 → 26 districts)
    # ==========================================================================
    {"new_district": "ALLURI SITHARAMA RAJU", "parent_district": "EAST GODAVARI", "state": "ANDHRA PRADESH", "split_year": 2022},
    {"new_district": "ANAKAPALLI", "parent_district": "VISAKHAPATNAM", "state": "ANDHRA PRADESH", "split_year": 2022},
    {"new_district": "ANNAMAYYA", "parent_district": "CHITTOOR", "state": "ANDHRA PRADESH", "split_year": 2022},
    {"new_district": "BAPATLA", "parent_district": "GUNTUR", "state": "ANDHRA PRADESH", "split_year": 2022},
    {"new_district": "ELURU", "parent_district": "WEST GODAVARI", "state": "ANDHRA PRADESH", "split_year": 2022},
    {"new_district": "KAKINADA", "parent_district": "EAST GODAVARI", "state": "ANDHRA PRADESH", "split_year": 2022},
    {"new_district": "KONASEEMA", "parent_district": "EAST GODAVARI", "state": "ANDHRA PRADESH", "split_year": 2022},
    {"new_district": "NANDYAL", "parent_district": "KURNOOL", "state": "ANDHRA PRADESH", "split_year": 2022},
    {"new_district": "NTR", "parent_district": "KRISHNA", "state": "ANDHRA PRADESH", "split_year": 2022},
    {"new_district": "PALNADU", "parent_district": "GUNTUR", "state": "ANDHRA PRADESH", "split_year": 2022},
    {"new_district": "PARVATHIPURAM MANYAM", "parent_district": "VIZIANAGARAM", "state": "ANDHRA PRADESH", "split_year": 2022},
    {"new_district": "SRI SATHYA SAI", "parent_district": "ANANTAPUR", "state": "ANDHRA PRADESH", "split_year": 2022},
    {"new_district": "TIRUPATI", "parent_district": "CHITTOOR", "state": "ANDHRA PRADESH", "split_year": 2022},
    # ==========================================================================
    # TAMIL NADU — 2004, 2007, 2009, 2019, 2020
    # ==========================================================================
    {"new_district": "KRISHNAGIRI", "parent_district": "DHARMAPURI", "state": "TAMIL NADU", "split_year": 2004},
    {"new_district": "ARIYALUR", "parent_district": "PERAMBALUR", "state": "TAMIL NADU", "split_year": 2007},
    {"new_district": "TIRUPPUR", "parent_district": "COIMBATORE", "state": "TAMIL NADU", "split_year": 2009},
    {"new_district": "CHENGALPATTU", "parent_district": "KANCHIPURAM", "state": "TAMIL NADU", "split_year": 2019},
    {"new_district": "KALLAKURICHI", "parent_district": "VILLUPURAM", "state": "TAMIL NADU", "split_year": 2019},
    {"new_district": "RANIPET", "parent_district": "VELLORE", "state": "TAMIL NADU", "split_year": 2019},
    {"new_district": "TIRUPATTUR", "parent_district": "VELLORE", "state": "TAMIL NADU", "split_year": 2019},
    {"new_district": "TENKASI", "parent_district": "TIRUNELVELI", "state": "TAMIL NADU", "split_year": 2019},
    {"new_district": "MAYILADUTHURAI", "parent_district": "NAGAPATTINAM", "state": "TAMIL NADU", "split_year": 2020},
    # ==========================================================================
    # KARNATAKA — 2007, 2010, 2020
    # ==========================================================================
    {"new_district": "RAMANAGARA", "parent_district": "BANGALORE RURAL", "state": "KARNATAKA", "split_year": 2007},
    {"new_district": "CHIKBALLAPUR", "parent_district": "KOLAR", "state": "KARNATAKA", "split_year": 2007},
    {"new_district": "YADGIR", "parent_district": "KALABURAGI", "state": "KARNATAKA", "split_year": 2010},
    {"new_district": "VIJAYANAGARA", "parent_district": "BALLARI", "state": "KARNATAKA", "split_year": 2020},
    # ==========================================================================
    # MAHARASHTRA — 2014
    # ==========================================================================
    {"new_district": "PALGHAR", "parent_district": "THANE", "state": "MAHARASHTRA", "split_year": 2014},
    # ==========================================================================
    # RAJASTHAN — 2008, 2023 (33 → 50 districts)
    # ==========================================================================
    {"new_district": "PRATAPGARH", "parent_district": "CHITTORGARH", "state": "RAJASTHAN", "split_year": 2008},
    {"new_district": "ANUPGARH", "parent_district": "SRI GANGANAGAR", "state": "RAJASTHAN", "split_year": 2023},
    {"new_district": "BALOTRA", "parent_district": "BARMER", "state": "RAJASTHAN", "split_year": 2023},
    {"new_district": "BEAWAR", "parent_district": "AJMER", "state": "RAJASTHAN", "split_year": 2023},
    {"new_district": "DEEG", "parent_district": "BHARATPUR", "state": "RAJASTHAN", "split_year": 2023},
    {"new_district": "DIDWANA-KUCHAMAN", "parent_district": "NAGAUR", "state": "RAJASTHAN", "split_year": 2023},
    {"new_district": "DUDU", "parent_district": "JAIPUR", "state": "RAJASTHAN", "split_year": 2023},
    {"new_district": "GANGAPUR CITY", "parent_district": "SAWAI MADHOPUR", "state": "RAJASTHAN", "split_year": 2023},
    {"new_district": "JAIPUR RURAL", "parent_district": "JAIPUR", "state": "RAJASTHAN", "split_year": 2023},
    {"new_district": "JODHPUR RURAL", "parent_district": "JODHPUR", "state": "RAJASTHAN", "split_year": 2023},
    {"new_district": "KEKRI", "parent_district": "AJMER", "state": "RAJASTHAN", "split_year": 2023},
    {"new_district": "KOTPUTLI-BEHROR", "parent_district": "JAIPUR", "state": "RAJASTHAN", "split_year": 2023},
    {"new_district": "NEEM KA THANA", "parent_district": "SIKAR", "state": "RAJASTHAN", "split_year": 2023},
    {"new_district": "PHALODI", "parent_district": "JODHPUR", "state": "RAJASTHAN", "split_year": 2023},
    {"new_district": "SALUMBAR", "parent_district": "UDAIPUR", "state": "RAJASTHAN", "split_year": 2023},
    {"new_district": "SANCHORE", "parent_district": "JALORE", "state": "RAJASTHAN", "split_year": 2023},
    {"new_district": "SHAHPURA", "parent_district": "BHILWARA", "state": "RAJASTHAN", "split_year": 2023},
    # ==========================================================================
    # UTTAR PRADESH — 2008, 2010, 2011
    # ==========================================================================
    {"new_district": "KASGANJ", "parent_district": "ETAH", "state": "UTTAR PRADESH", "split_year": 2008},
    {"new_district": "AMETHI", "parent_district": "SULTANPUR", "state": "UTTAR PRADESH", "split_year": 2010},
    {"new_district": "SHAMLI", "parent_district": "MUZAFFARNAGAR", "state": "UTTAR PRADESH", "split_year": 2011},
    {"new_district": "HAPUR", "parent_district": "GHAZIABAD", "state": "UTTAR PRADESH", "split_year": 2011},
    {"new_district": "SAMBHAL", "parent_district": "MORADABAD", "state": "UTTAR PRADESH", "split_year": 2011},
    # ==========================================================================
    # MADHYA PRADESH — 2003, 2008, 2013, 2018, 2023
    # ==========================================================================
    {"new_district": "BURHANPUR", "parent_district": "EAST NIMAR", "state": "MADHYA PRADESH", "split_year": 2003},
    {"new_district": "ANUPPUR", "parent_district": "SHAHDOL", "state": "MADHYA PRADESH", "split_year": 2003},
    {"new_district": "ASHOKNAGAR", "parent_district": "GUNA", "state": "MADHYA PRADESH", "split_year": 2003},
    {"new_district": "ALIRAJPUR", "parent_district": "JHABUA", "state": "MADHYA PRADESH", "split_year": 2008},
    {"new_district": "SINGRAULI", "parent_district": "SIDHI", "state": "MADHYA PRADESH", "split_year": 2008},
    {"new_district": "AGAR MALWA", "parent_district": "SHAJAPUR", "state": "MADHYA PRADESH", "split_year": 2013},
    {"new_district": "NIWARI", "parent_district": "TIKAMGARH", "state": "MADHYA PRADESH", "split_year": 2018},
    {"new_district": "MAUGANJ", "parent_district": "REWA", "state": "MADHYA PRADESH", "split_year": 2023},
    {"new_district": "MAIHAR", "parent_district": "SATNA", "state": "MADHYA PRADESH", "split_year": 2023},
    {"new_district": "NAGDA", "parent_district": "UJJAIN", "state": "MADHYA PRADESH", "split_year": 2023},
    {"new_district": "PANDHURNA", "parent_district": "CHHINDWARA", "state": "MADHYA PRADESH", "split_year": 2023},
    # ==========================================================================
    # BIHAR — 2001
    # ==========================================================================
    {"new_district": "ARWAL", "parent_district": "JEHANABAD", "state": "BIHAR", "split_year": 2001},
    {"new_district": "SUPAUL", "parent_district": "SAHARSA", "state": "BIHAR", "split_year": 2001},
    {"new_district": "SHEOHAR", "parent_district": "SITAMARHI", "state": "BIHAR", "split_year": 2001},
    {"new_district": "SHEIKHPURA", "parent_district": "MUNGER", "state": "BIHAR", "split_year": 2001},
    {"new_district": "LAKHISARAI", "parent_district": "MUNGER", "state": "BIHAR", "split_year": 2001},
    {"new_district": "JAMUI", "parent_district": "MUNGER", "state": "BIHAR", "split_year": 2001},
    # ==========================================================================
    # JHARKHAND — 2001, 2007
    # ==========================================================================
    {"new_district": "LATEHAR", "parent_district": "PALAMU", "state": "JHARKHAND", "split_year": 2001},
    {"new_district": "SERAIKELA-KHARSAWAN", "parent_district": "WEST SINGHBHUM", "state": "JHARKHAND", "split_year": 2001},
    {"new_district": "SAHEBGANJ", "parent_district": "DUMKA", "state": "JHARKHAND", "split_year": 2001},
    {"new_district": "PAKUR", "parent_district": "DUMKA", "state": "JHARKHAND", "split_year": 2001},
    {"new_district": "JAMTARA", "parent_district": "DUMKA", "state": "JHARKHAND", "split_year": 2001},
    {"new_district": "KHUNTI", "parent_district": "RANCHI", "state": "JHARKHAND", "split_year": 2007},
    {"new_district": "RAMGARH", "parent_district": "HAZARIBAGH", "state": "JHARKHAND", "split_year": 2007},
    # ==========================================================================
    # CHHATTISGARH — 2007, 2012, 2020, 2022
    # ==========================================================================
    {"new_district": "NARAYANPUR", "parent_district": "BASTAR", "state": "CHHATTISGARH", "split_year": 2007},
    {"new_district": "BIJAPUR", "parent_district": "DANTEWADA", "state": "CHHATTISGARH", "split_year": 2007},
    {"new_district": "BALOD", "parent_district": "DURG", "state": "CHHATTISGARH", "split_year": 2012},
    {"new_district": "BALODA BAZAR", "parent_district": "RAIPUR", "state": "CHHATTISGARH", "split_year": 2012},
    {"new_district": "BEMETARA", "parent_district": "DURG", "state": "CHHATTISGARH", "split_year": 2012},
    {"new_district": "GARIABAND", "parent_district": "RAIPUR", "state": "CHHATTISGARH", "split_year": 2012},
    {"new_district": "KONDAGAON", "parent_district": "BASTAR", "state": "CHHATTISGARH", "split_year": 2012},
    {"new_district": "MUNGELI", "parent_district": "BILASPUR", "state": "CHHATTISGARH", "split_year": 2012},
    {"new_district": "SURAJPUR", "parent_district": "SURGUJA", "state": "CHHATTISGARH", "split_year": 2012},
    {"new_district": "SUKMA", "parent_district": "DANTEWADA", "state": "CHHATTISGARH", "split_year": 2012},
    {"new_district": "BALRAMPUR", "parent_district": "SURGUJA", "state": "CHHATTISGARH", "split_year": 2012},
    {"new_district": "GAURELA-PENDRA-MARWAHI", "parent_district": "BILASPUR", "state": "CHHATTISGARH", "split_year": 2020},
    {"new_district": "MOHLA-MANPUR-AMBAGARH CHOWKI", "parent_district": "RAJNANDGAON", "state": "CHHATTISGARH", "split_year": 2022},
    {"new_district": "SARANGARH-BILAIGARH", "parent_district": "RAIGARH", "state": "CHHATTISGARH", "split_year": 2022},
    {"new_district": "KHAIRAGARH-CHHUIKHADAN-GANDAI", "parent_district": "RAJNANDGAON", "state": "CHHATTISGARH", "split_year": 2022},
    {"new_district": "MANENDRAGARH-CHIRMIRI-BHARATPUR", "parent_district": "KOREA", "state": "CHHATTISGARH", "split_year": 2022},
    {"new_district": "SHAKTI", "parent_district": "JANJGIR-CHAMPA", "state": "CHHATTISGARH", "split_year": 2022},
    # ==========================================================================
    # GUJARAT — 2000, 2007, 2013
    # ==========================================================================
    {"new_district": "NARMADA", "parent_district": "BHARUCH", "state": "GUJARAT", "split_year": 2000},
    {"new_district": "TAPI", "parent_district": "SURAT", "state": "GUJARAT", "split_year": 2007},
    {"new_district": "ARAVALLI", "parent_district": "SABARKANTHA", "state": "GUJARAT", "split_year": 2013},
    {"new_district": "GIR SOMNATH", "parent_district": "JUNAGADH", "state": "GUJARAT", "split_year": 2013},
    {"new_district": "CHHOTA UDAIPUR", "parent_district": "VADODARA", "state": "GUJARAT", "split_year": 2013},
    {"new_district": "MAHISAGAR", "parent_district": "PANCHMAHAL", "state": "GUJARAT", "split_year": 2013},
    {"new_district": "MORBI", "parent_district": "RAJKOT", "state": "GUJARAT", "split_year": 2013},
    {"new_district": "DEVBHOOMI DWARKA", "parent_district": "JAMNAGAR", "state": "GUJARAT", "split_year": 2013},
    {"new_district": "BOTAD", "parent_district": "BHAVNAGAR", "state": "GUJARAT", "split_year": 2013},
    # ==========================================================================
    # WEST BENGAL — 2014, 2017
    # ==========================================================================
    {"new_district": "ALIPURDUAR", "parent_district": "JALPAIGURI", "state": "WEST BENGAL", "split_year": 2014},
    {"new_district": "KALIMPONG", "parent_district": "DARJEELING", "state": "WEST BENGAL", "split_year": 2017},
    {"new_district": "JHARGRAM", "parent_district": "PASCHIM MEDINIPUR", "state": "WEST BENGAL", "split_year": 2017},
    {"new_district": "PURBA BARDHAMAN", "parent_district": "BARDHAMAN", "state": "WEST BENGAL", "split_year": 2017},
    {"new_district": "PASCHIM BARDHAMAN", "parent_district": "BARDHAMAN", "state": "WEST BENGAL", "split_year": 2017},
    # ==========================================================================
    # ASSAM — 2003, 2004, 2016, 2022
    # ==========================================================================
    {"new_district": "KAMRUP METROPOLITAN", "parent_district": "KAMRUP", "state": "ASSAM", "split_year": 2003},
    {"new_district": "BAKSA", "parent_district": "NALBARI", "state": "ASSAM", "split_year": 2004},
    {"new_district": "CHIRANG", "parent_district": "BONGAIGAON", "state": "ASSAM", "split_year": 2004},
    {"new_district": "UDALGURI", "parent_district": "DARRANG", "state": "ASSAM", "split_year": 2004},
    {"new_district": "HOJAI", "parent_district": "NAGAON", "state": "ASSAM", "split_year": 2016},
    {"new_district": "SOUTH SALMARA-MANKACHAR", "parent_district": "DHUBRI", "state": "ASSAM", "split_year": 2016},
    {"new_district": "WEST KARBI ANGLONG", "parent_district": "KARBI ANGLONG", "state": "ASSAM", "split_year": 2016},
    {"new_district": "BISWANATH", "parent_district": "SONITPUR", "state": "ASSAM", "split_year": 2016},
    {"new_district": "CHARAIDEO", "parent_district": "SIVASAGAR", "state": "ASSAM", "split_year": 2016},
    {"new_district": "MAJULI", "parent_district": "JORHAT", "state": "ASSAM", "split_year": 2016},
    {"new_district": "BAJALI", "parent_district": "BARPETA", "state": "ASSAM", "split_year": 2022},
    {"new_district": "TAMULPUR", "parent_district": "BAKSA", "state": "ASSAM", "split_year": 2022},
    # ==========================================================================
    # HARYANA — 2005, 2008, 2016
    # ==========================================================================
    {"new_district": "MEWAT", "parent_district": "GURGAON", "state": "HARYANA", "split_year": 2005},
    {"new_district": "PALWAL", "parent_district": "FARIDABAD", "state": "HARYANA", "split_year": 2008},
    {"new_district": "CHARKHI DADRI", "parent_district": "BHIWANI", "state": "HARYANA", "split_year": 2016},
    # ==========================================================================
    # PUNJAB — 2006, 2011, 2012, 2021
    # ==========================================================================
    {"new_district": "MOHALI", "parent_district": "RUPNAGAR", "state": "PUNJAB", "split_year": 2006},
    {"new_district": "BARNALA", "parent_district": "SANGRUR", "state": "PUNJAB", "split_year": 2006},
    {"new_district": "PATHANKOT", "parent_district": "GURDASPUR", "state": "PUNJAB", "split_year": 2011},
    {"new_district": "FAZILKA", "parent_district": "FIROZPUR", "state": "PUNJAB", "split_year": 2012},
    {"new_district": "MALERKOTLA", "parent_district": "SANGRUR", "state": "PUNJAB", "split_year": 2021},
    # ==========================================================================
    # JAMMU AND KASHMIR — 2007
    # ==========================================================================
    {"new_district": "BANDIPORE", "parent_district": "BARAMULLA", "state": "JAMMU AND KASHMIR", "split_year": 2007},
    {"new_district": "GANDERBAL", "parent_district": "SRINAGAR", "state": "JAMMU AND KASHMIR", "split_year": 2007},
    {"new_district": "KULGAM", "parent_district": "ANANTNAG", "state": "JAMMU AND KASHMIR", "split_year": 2007},
    {"new_district": "SHOPIAN", "parent_district": "PULWAMA", "state": "JAMMU AND KASHMIR", "split_year": 2007},
    {"new_district": "SAMBA", "parent_district": "JAMMU", "state": "JAMMU AND KASHMIR", "split_year": 2007},
    {"new_district": "KISHTWAR", "parent_district": "DODA", "state": "JAMMU AND KASHMIR", "split_year": 2007},
    {"new_district": "RAMBAN", "parent_district": "DODA", "state": "JAMMU AND KASHMIR", "split_year": 2007},
    {"new_district": "REASI", "parent_district": "UDHAMPUR", "state": "JAMMU AND KASHMIR", "split_year": 2007},
    # ==========================================================================
    # MANIPUR — 2016
    # ==========================================================================
    {"new_district": "JIRIBAM", "parent_district": "IMPHAL EAST", "state": "MANIPUR", "split_year": 2016},
    {"new_district": "KANGPOKPI", "parent_district": "SENAPATI", "state": "MANIPUR", "split_year": 2016},
    {"new_district": "KAKCHING", "parent_district": "THOUBAL", "state": "MANIPUR", "split_year": 2016},
    {"new_district": "TENGNOUPAL", "parent_district": "CHANDEL", "state": "MANIPUR", "split_year": 2016},
    {"new_district": "KAMJONG", "parent_district": "UKHRUL", "state": "MANIPUR", "split_year": 2016},
    {"new_district": "NONEY", "parent_district": "TAMENGLONG", "state": "MANIPUR", "split_year": 2016},
    {"new_district": "PHERZAWL", "parent_district": "CHURACHANDPUR", "state": "MANIPUR", "split_year": 2016},
    # ==========================================================================
    # ARUNACHAL PRADESH — 2001, 2004, 2012, 2014, 2015, 2017, 2018
    # ==========================================================================
    {"new_district": "LOWER DIBANG VALLEY", "parent_district": "DIBANG VALLEY", "state": "ARUNACHAL PRADESH", "split_year": 2001},
    {"new_district": "KURUNG KUMEY", "parent_district": "LOWER SUBANSIRI", "state": "ARUNACHAL PRADESH", "split_year": 2001},
    {"new_district": "ANJAW", "parent_district": "LOHIT", "state": "ARUNACHAL PRADESH", "split_year": 2004},
    {"new_district": "LONGDING", "parent_district": "TIRAP", "state": "ARUNACHAL PRADESH", "split_year": 2012},
    {"new_district": "NAMSAI", "parent_district": "LOHIT", "state": "ARUNACHAL PRADESH", "split_year": 2012},
    {"new_district": "LOWER SIANG", "parent_district": "WEST SIANG", "state": "ARUNACHAL PRADESH", "split_year": 2014},
    {"new_district": "KRA DAADI", "parent_district": "KURUNG KUMEY", "state": "ARUNACHAL PRADESH", "split_year": 2015},
    {"new_district": "SIANG", "parent_district": "WEST SIANG", "state": "ARUNACHAL PRADESH", "split_year": 2015},
    {"new_district": "KAMLE", "parent_district": "UPPER SUBANSIRI", "state": "ARUNACHAL PRADESH", "split_year": 2017},
    {"new_district": "PAKKE KESSANG", "parent_district": "EAST KAMENG", "state": "ARUNACHAL PRADESH", "split_year": 2018},
    {"new_district": "LEPA RADA", "parent_district": "LOWER SUBANSIRI", "state": "ARUNACHAL PRADESH", "split_year": 2018},
    {"new_district": "SHI YOMI", "parent_district": "WEST SIANG", "state": "ARUNACHAL PRADESH", "split_year": 2018},
    # ==========================================================================
    # NAGALAND — 2003, 2004, 2017, 2021
    # ==========================================================================
    {"new_district": "PEREN", "parent_district": "KOHIMA", "state": "NAGALAND", "split_year": 2003},
    {"new_district": "LONGLENG", "parent_district": "TUENSANG", "state": "NAGALAND", "split_year": 2004},
    {"new_district": "KIPHIRE", "parent_district": "TUENSANG", "state": "NAGALAND", "split_year": 2004},
    {"new_district": "NOKLAK", "parent_district": "TUENSANG", "state": "NAGALAND", "split_year": 2017},
    {"new_district": "NIULAND", "parent_district": "DIMAPUR", "state": "NAGALAND", "split_year": 2021},
    {"new_district": "CHUMOUKEDIMA", "parent_district": "DIMAPUR", "state": "NAGALAND", "split_year": 2021},
    {"new_district": "SHAMATOR", "parent_district": "TUENSANG", "state": "NAGALAND", "split_year": 2021},
    {"new_district": "TSEMINYU", "parent_district": "KOHIMA", "state": "NAGALAND", "split_year": 2021},
    # ==========================================================================
    # MEGHALAYA — 2012, 2021
    # ==========================================================================
    {"new_district": "SOUTH WEST KHASI HILLS", "parent_district": "WEST KHASI HILLS", "state": "MEGHALAYA", "split_year": 2012},
    {"new_district": "SOUTH WEST GARO HILLS", "parent_district": "WEST GARO HILLS", "state": "MEGHALAYA", "split_year": 2012},
    {"new_district": "NORTH GARO HILLS", "parent_district": "EAST GARO HILLS", "state": "MEGHALAYA", "split_year": 2012},
    {"new_district": "EASTERN WEST KHASI HILLS", "parent_district": "WEST KHASI HILLS", "state": "MEGHALAYA", "split_year": 2021},
    # ==========================================================================
    # MIZORAM — 2001, 2019
    # ==========================================================================
    {"new_district": "MAMIT", "parent_district": "AIZAWL", "state": "MIZORAM", "split_year": 2001},
    {"new_district": "SERCHHIP", "parent_district": "AIZAWL", "state": "MIZORAM", "split_year": 2001},
    {"new_district": "KOLASIB", "parent_district": "AIZAWL", "state": "MIZORAM", "split_year": 2001},
    {"new_district": "KHAWZAWL", "parent_district": "CHAMPHAI", "state": "MIZORAM", "split_year": 2019},
    {"new_district": "HNAHTHIAL", "parent_district": "LUNGLEI", "state": "MIZORAM", "split_year": 2019},
    {"new_district": "SAITUAL", "parent_district": "AIZAWL", "state": "MIZORAM", "split_year": 2019},
    # ==========================================================================
    # TRIPURA — 2012
    # ==========================================================================
    {"new_district": "UNAKOTI", "parent_district": "NORTH TRIPURA", "state": "TRIPURA", "split_year": 2012},
    {"new_district": "KHOWAI", "parent_district": "WEST TRIPURA", "state": "TRIPURA", "split_year": 2012},
    {"new_district": "SIPAHIJALA", "parent_district": "WEST TRIPURA", "state": "TRIPURA", "split_year": 2012},
    {"new_district": "GOMATI", "parent_district": "SOUTH TRIPURA", "state": "TRIPURA", "split_year": 2012},
    # ==========================================================================
    # SIKKIM — 2021
    # ==========================================================================
    {"new_district": "PAKYONG", "parent_district": "EAST SIKKIM", "state": "SIKKIM", "split_year": 2021},
    {"new_district": "SORENG", "parent_district": "WEST SIKKIM", "state": "SIKKIM", "split_year": 2021},
    # ==========================================================================
    # UTTARAKHAND — 2001
    # ==========================================================================
    {"new_district": "RUDRAPRAYAG", "parent_district": "CHAMOLI", "state": "UTTARAKHAND", "split_year": 2001},
    {"new_district": "CHAMPAWAT", "parent_district": "PITHORAGARH", "state": "UTTARAKHAND", "split_year": 2001},
    {"new_district": "BAGESHWAR", "parent_district": "ALMORA", "state": "UTTARAKHAND", "split_year": 2001},
    # ==========================================================================
    # ODISHA — 2000
    # ==========================================================================
    {"new_district": "DEOGARH", "parent_district": "SAMBALPUR", "state": "ODISHA", "split_year": 2000},
]


def load_district_lineage(records: list[dict]) -> int:
    """Bulk-insert district lineage records. Returns rows inserted."""
    if not records:
        return 0

    import sqlite3
    conn = sqlite3.connect(str(DB_PATH))
    count = 0
    try:
        for rec in records:
            conn.execute(
                """
                INSERT OR REPLACE INTO district_lineage
                    (new_district, parent_district, state, split_year)
                VALUES (?, ?, ?, ?)
                """,
                (
                    rec["new_district"].strip().upper(),
                    rec["parent_district"].strip().upper(),
                    rec["state"].strip().upper(),
                    int(rec["split_year"]),
                ),
            )
            count += 1
        conn.commit()
    finally:
        conn.close()
    return count


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
    lineage = load_district_lineage(DISTRICT_LINEAGE)

    return {"pins": pins, "constituencies": constituencies, "mps": mps, "lineage": lineage}


if __name__ == "__main__":
    counts = seed_all()
    print(f"Seeded: {counts['pins']} PINs, {counts['constituencies']} constituency-district "
          f"mappings, {counts['mps']} MPs, {counts['lineage']} district lineage records")
