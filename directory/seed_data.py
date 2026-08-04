"""Seed grievance_channels with verified government portal URLs."""
from __future__ import annotations

import sqlite3
from datetime import datetime

_CHANNELS = [
    {"scheme": "MGNREGA", "level": "district", "portal_name": "MGNREGA Public Grievance",
     "portal_url": "https://nrega.nic.in/Nregahome/EComplaint.aspx", "phone": None,
     "description": "File complaints about delayed wages, worksite issues, or job card problems",
     "escalation_scheme": None, "source_url": "https://nrega.nic.in"},
    {"scheme": "MGNREGA", "level": "national", "portal_name": "MGNREGA Helpline",
     "portal_url": "https://nrega.nic.in", "phone": "1800-111-555",
     "description": "Toll-free MGNREGA helpline",
     "escalation_scheme": None, "source_url": "https://nrega.nic.in"},
    {"scheme": "PMAY-G", "level": "national", "portal_name": "PMAY-G Grievance Portal",
     "portal_url": "https://pmayg.nic.in/netiayHome/Aboreal_grievance.aspx", "phone": None,
     "description": "File complaints about housing scheme delays or irregularities",
     "escalation_scheme": None, "source_url": "https://pmayg.nic.in"},
    {"scheme": "JJM", "level": "national", "portal_name": "JJM Grievance Portal",
     "portal_url": "https://jalshakti-ddws.gov.in/grievance", "phone": None,
     "description": "File complaints about tap water connections",
     "escalation_scheme": None, "source_url": "https://ejalshakti.gov.in"},
    {"scheme": "PM Kisan", "level": "national", "portal_name": "PM Kisan Helpline",
     "portal_url": "https://pmkisan.gov.in/Aboreal_grievance.aspx", "phone": "155261",
     "description": "PM Kisan grievance and beneficiary status",
     "escalation_scheme": None, "source_url": "https://pmkisan.gov.in"},
    {"scheme": "PM POSHAN", "level": "national", "portal_name": "PM POSHAN Portal",
     "portal_url": "https://pmposhan.education.gov.in/", "phone": None,
     "description": "Mid-day meal scheme monitoring and complaints",
     "escalation_scheme": None, "source_url": "https://pmposhan.education.gov.in"},
    {"scheme": "NSAP", "level": "national", "portal_name": "NSAP Portal",
     "portal_url": "https://nsap.nic.in/statedashboard.do", "phone": None,
     "description": "National pension scheme tracking and status",
     "escalation_scheme": None, "source_url": "https://nsap.nic.in"},
    {"scheme": "PDS/NFSA", "level": "national", "portal_name": "NFSA Grievance",
     "portal_url": "https://nfsa.gov.in/public/nfsadashboard/PGR.aspx", "phone": "1967",
     "description": "Ration distribution complaints and ration card issues",
     "escalation_scheme": None, "source_url": "https://nfsa.gov.in"},
    {"scheme": "PMGSY", "level": "national", "portal_name": "PMGSY Feedback",
     "portal_url": "https://omms.nic.in/", "phone": None,
     "description": "Rural roads construction monitoring",
     "escalation_scheme": None, "source_url": "https://omms.nic.in"},
    {"scheme": "ALL", "level": "national", "portal_name": "CPGRAMS",
     "portal_url": "https://pgportal.gov.in/", "phone": "1800-111-555",
     "description": "Central grievance portal for all government departments — escalate here if no response in 30 days",
     "escalation_scheme": None, "source_url": "https://pgportal.gov.in/"},
    {"scheme": "ALL", "level": "national", "portal_name": "RTI Online",
     "portal_url": "https://rtionline.gov.in/", "phone": None,
     "description": "File a Right to Information request for any government department",
     "escalation_scheme": None, "source_url": "https://rtionline.gov.in/"},
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
            (ch["scheme"], ch["level"], ch["portal_name"], ch["portal_url"],
             ch["phone"], ch["description"], ch["escalation_scheme"],
             ch["source_url"], now),
        )
        loaded += 1
    conn.commit()
    return loaded
