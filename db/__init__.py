"""Hisaab database package — schema, connection, and loaders.

Re-exports everything that was previously available from the top-level db module
so that ``from db import X`` continues to work unchanged.
"""

from db.connection import CURATED_DIR, DB_PATH, get_connection, init_db
from db.loaders import (
    LOADERS,
    NSAP_PENSION_RATES,
    impute_nsap_financials,
    load_all_latest,
    load_financial_statement,
    load_fto_pendency,
    load_fto_status,
    load_issues_reported,
    load_jjm_district,
    load_misappropriation,
    load_nfsa_district,
    load_nsap_district,
    load_pmayg_district,
    load_pmgsy_district,
    load_pmgsy_progress,
    load_pmkisan_district,
    load_pmposhan_district,
)
from db.schema import SCHEMA

__all__ = [
    "CURATED_DIR",
    "DB_PATH",
    "LOADERS",
    "NSAP_PENSION_RATES",
    "SCHEMA",
    "get_connection",
    "impute_nsap_financials",
    "init_db",
    "load_all_latest",
    "load_financial_statement",
    "load_fto_pendency",
    "load_fto_status",
    "load_issues_reported",
    "load_jjm_district",
    "load_misappropriation",
    "load_nfsa_district",
    "load_nsap_district",
    "load_pmayg_district",
    "load_pmgsy_district",
    "load_pmgsy_progress",
    "load_pmkisan_district",
    "load_pmposhan_district",
]
