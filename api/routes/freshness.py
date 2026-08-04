"""Data freshness endpoint — per-scheme scrape timestamps and record counts."""

from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import APIRouter

from db import DB_PATH

router = APIRouter()

# Every dataset the product serves — the freshness surface must cover ALL of
# them, including finance/allocation tables (mirrors the web freshness route).
SCHEME_TABLES = {
    "MGNREGA": ["misappropriation", "financial_statement", "fto_status", "fto_pendency", "issues_reported"],
    "PMGSY": ["pmgsy_progress", "pmgsy_district"],
    "PMAY-G": ["pmayg_district", "pmayg_finance"],
    "PM Kisan": ["pmkisan_district"],
    "JJM": ["jjm_district", "jjm_allocation"],
    "PM POSHAN": ["pmposhan_district", "pmposhan_finance"],
    "NSAP": ["nsap_district", "nsap_finance"],
    "PDS/NFSA": ["nfsa_district", "nfsa_allocation"],
    "SBM-G": ["sbm_district"],
    "DAY-NRLM": ["nrlm_district"],
    "UDISE+": ["udise_state"],
}

SCHEME_SOURCES = {
    "MGNREGA": "mnregaweb2.dord.gov.in (citizen portal)",
    "PMGSY": "pmgsy.dord.gov.in",
    "PMAY-G": "report.pmayg.dord.gov.in / data.gov.in",
    "PM Kisan": "data.gov.in",
    "JJM": "ejalshakti.gov.in",
    "PM POSHAN": "pmposhan-ams.education.gov.in / data.gov.in",
    "NSAP": "nsap.nic.in / data.gov.in",
    "PDS/NFSA": "nfsa.gov.in / data.gov.in",
    "SBM-G": "sbm.gov.in",
    "DAY-NRLM": "cdn.lokos.in (LokOS)",
    "UDISE+": "api.udiseplus.gov.in",
}


@router.get("/freshness")
def data_freshness() -> dict[str, Any]:
    """Per-scheme data freshness: latest scrape date, record counts, state counts."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    results = []

    for scheme, tables in SCHEME_TABLES.items():
        total_records = 0
        all_states: set[str] = set()
        latest_scraped = ""

        for table in tables:
            try:
                row = conn.execute(f"SELECT COUNT(*) as cnt FROM {table}").fetchone()
                total_records += row["cnt"] if row else 0

                states_rows = conn.execute(f"SELECT DISTINCT state FROM {table}").fetchall()
                all_states.update(r["state"] for r in states_rows if r["state"])

                ts_row = conn.execute(f"SELECT MAX(scraped_at) as ts FROM {table}").fetchone()
                ts = ts_row["ts"] if ts_row and ts_row["ts"] else ""
                if ts > latest_scraped:
                    latest_scraped = ts
            except Exception:
                pass

        results.append(
            {
                "scheme": scheme,
                "source": SCHEME_SOURCES.get(scheme, ""),
                "latest_scraped": latest_scraped[:10] if latest_scraped else None,
                "records": total_records,
                "states": len(all_states),
            }
        )

    conn.close()
    return {"freshness": results, "total_records": sum(r["records"] for r in results)}
