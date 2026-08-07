"""Round-trip loader tests for all 8 schemes.

For each scheme: create a minimal valid curated JSON record with known values,
load via the scheme's loader function, query the DB row back, and assert all
fields match. Catches field name mismatches, unit conversions, and schema drift.
"""

from __future__ import annotations

import sqlite3

import pytest

from db import (
    init_db,
    load_financial_statement,
    load_fto_pendency,
    load_fto_status,
    load_issues_reported,
    load_jjm_allocation,
    load_jjm_district,
    load_misappropriation,
    load_nfsa_district,
    load_nrlm_district,
    load_nsap_district,
    load_pin_constituency,
    load_pmayg_district,
    load_pmgsy_district,
    load_pmgsy_progress,
    load_pmkisan_district,
    load_pmposhan_district,
    load_sbm_district,
    load_udise_state,
)

FIN_YEAR = "2024-2025"


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


def _load_and_query(db, loader, table, records):
    """Load records and return all rows from the table."""
    count = loader(db, records, FIN_YEAR)
    db.commit()
    rows = db.execute(f"SELECT * FROM {table}").fetchall()
    return count, rows


class TestMGNREGAMisappropriation:
    def test_round_trip(self, db):
        records = [
            {
                "district": "PATNA",
                "state": "BIHAR",
                "state_code": "05",
                "cases_reported": 12,
                "amount_reported": 45.5,
                "cases_decided": 8,
                "amount_decided": 30.0,
                "cases_pending_recovery": 4,
                "amount_to_recover": 15.5,
                "cases_recovered": 3,
                "amount_recovered": 10.0,
                "amount_unrecovered": 5.5,
                "recovery_rate_pct": 64.5,
                "source_url": "nrega.nic.in",
                "scraped_at": "2026-01-01T00:00:00",
            }
        ]
        count, rows = _load_and_query(db, load_misappropriation, "misappropriation", records)
        assert count == 1
        r = rows[0]
        assert r["district"] == "PATNA"
        assert r["cases_reported"] == 12
        assert r["amount_reported"] == 45.5
        assert r["recovery_rate_pct"] == 64.5


class TestMGNREGAFTOStatus:
    def test_round_trip(self, db):
        records = [
            {
                "district": "PATNA",
                "state": "BIHAR",
                "state_code": "05",
                "total_fto_generated": 500,
                "first_signatory_signed": 450,
                "first_signatory_pending": 50,
                "second_signatory_signed": 400,
                "second_signatory_pending": 100,
                "fto_sent_to_bank": 380,
                "fto_processed_by_bank": 350,
                "transactions_processed": 9000,
                "source_url": "nrega.nic.in",
                "scraped_at": "2026-01-01T00:00:00",
            }
        ]
        count, rows = _load_and_query(db, load_fto_status, "fto_status", records)
        assert count == 1
        r = rows[0]
        assert r["total_fto_generated"] == 500
        assert r["fto_processed_by_bank"] == 350


class TestMGNREGAFTOPendency:
    def test_round_trip(self, db):
        records = [
            {
                "bank_name": "SBI",
                "is_total": False,
                "state": "BIHAR",
                "state_code": "05",
                "pending_1_7_days": 10,
                "pending_8_15_days": 20,
                "pending_16_30_days": 5,
                "pending_over_30_days": 3,
                "total_pending": 38,
                "source_url": "nrega.nic.in",
                "scraped_at": "2026-01-01T00:00:00",
            }
        ]
        count, rows = _load_and_query(db, load_fto_pendency, "fto_pendency", records)
        assert count == 1
        r = rows[0]
        assert r["bank_name"] == "SBI"
        assert r["total_pending"] == 38


class TestMGNREGAIssuesReported:
    def test_round_trip(self, db):
        records = [
            {
                "district": "PATNA",
                "state": "BIHAR",
                "state_code": "05",
                "total_gps": 200,
                "gps_audited": 150,
                "misappropriation_issues": 10,
                "misappropriation_amount": 5.0,
                "financial_deviation_issues": 8,
                "financial_deviation_amount": 3.5,
                "process_violation_issues": 12,
                "process_violation_amount": 4.0,
                "grievances_issues": 5,
                "grievances_amount": 1.5,
                "total_issues": 35,
                "total_amount": 14.0,
                "source_url": "nrega.nic.in",
                "scraped_at": "2026-01-01T00:00:00",
            }
        ]
        count, rows = _load_and_query(db, load_issues_reported, "issues_reported", records)
        assert count == 1
        r = rows[0]
        assert r["total_gps"] == 200
        assert r["total_issues"] == 35


class TestMGNREGAFinancialStatement:
    def test_round_trip(self, db):
        records = [
            {
                "district": "PATNA",
                "state": "BIHAR",
                "state_code": "05",
                "col_2_num": 100.0,
                "col_3_num": 200.0,
                "col_5_num": 50.0,
                "col_6_num": 30.0,
                "col_7_num": 10.0,
                "col_9_num": 390.0,
                "col_10_num": 150.0,
                "col_11_num": 50.0,
                "col_12_num": 80.0,
                "col_13_num": 20.0,
                "col_14_num": 15.0,
                "col_15_num": 5.0,
                "col_16_num": 20.0,
                "col_17_num": 320.0,
                "col_18_num": 82.05,
                "col_19_num": 70.0,
                "source_url": "nrega.nic.in",
                "scraped_at": "2026-01-01T00:00:00",
            }
        ]
        count, rows = _load_and_query(db, load_financial_statement, "financial_statement", records)
        assert count == 1
        r = rows[0]
        assert r["opening_balance"] == 100.0
        assert r["total_availability"] == 390.0
        assert r["utilization_pct"] == 82.05
        assert r["exp_total"] == 300.0  # 150+50+80+20


class TestPMGSYProgress:
    def test_round_trip(self, db):
        records = [
            {
                "state": "BIHAR",
                "state_code": "05",
                "fin_year_or_scheme": "2024-2025",
                "roads_completed": 120,
                "length_completed_km": 450.5,
                "habitations_connected": 80,
                "expenditure_programme_cr": 250.0,
                "expenditure_admin_cr": 12.5,
                "source_url": "pmgsy.dord.gov.in",
                "scraped_at": "2026-01-01T00:00:00",
            }
        ]
        count, rows = _load_and_query(db, load_pmgsy_progress, "pmgsy_progress", records)
        assert count == 1
        r = rows[0]
        assert r["roads_completed"] == 120
        assert r["length_completed_km"] == 450.5


class TestPMGSYDistrict:
    def test_round_trip(self, db):
        records = [
            {
                "district": "PATNA",
                "state": "BIHAR",
                "state_code": "05",
                "scheme": "PMGSY-I",
                "roads_sanctioned": 50,
                "roads_completed": 40,
                "length_sanctioned_km": 100.0,
                "length_completed_km": 80.0,
                "habitations_covered": 20,
                "value_of_projects_cr": 10.0,
                "expenditure_cr": 8.0,
                "source_url": "pmgsy.dord.gov.in",
                "scraped_at": "2026-01-01T00:00:00",
            }
        ]
        count, rows = _load_and_query(db, load_pmgsy_district, "pmgsy_district", records)
        assert count == 1
        r = rows[0]
        assert r["roads_sanctioned"] == 50
        assert r["expenditure_cr"] == 8.0


class TestPMAYG:
    def test_round_trip(self, db):
        records = [
            {
                "district": "PATNA",
                "state": "BIHAR",
                "state_code": "05",
                "houses_sanctioned": 2000,
                "houses_completed": 1500,
                "houses_occupied": 1200,
                "funds_released_lakhs": 5000.0,
                "funds_utilized_lakhs": 3500.0,
                "completion_pct": 75.0,
                "source_url": "pmayg.dord.gov.in",
                "scraped_at": "2026-01-01T00:00:00",
            }
        ]
        count, rows = _load_and_query(db, load_pmayg_district, "pmayg_district", records)
        assert count == 1
        r = rows[0]
        assert r["houses_sanctioned"] == 2000
        assert r["funds_utilized_lakhs"] == 3500.0


class TestPMKisan:
    def test_round_trip(self, db):
        records = [
            {
                "district": "PATNA",
                "state": "BIHAR",
                "state_code": "05",
                "beneficiaries_registered": 50000,
                "beneficiaries_paid": 45000,
                "amount_paid_lakhs": 900.0,
                "beneficiaries_rejected": 1000,
                "installment": "17th",
                "source_url": "data.gov.in",
                "scraped_at": "2026-01-01T00:00:00",
            }
        ]
        count, rows = _load_and_query(db, load_pmkisan_district, "pmkisan_district", records)
        assert count == 1
        r = rows[0]
        assert r["beneficiaries_registered"] == 50000
        assert r["amount_paid_lakhs"] == 900.0
        assert r["beneficiaries_rejected"] == 1000

    def test_field_name_mismatch_detected(self, db):
        """Records with old field names should load as zeros (catching mismatches)."""
        records = [
            {
                "district": "PATNA",
                "state": "BIHAR",
                "state_code": "05",
                "registered_farmers": 50000,
                "amount_paid_cr": 9.0,
                "installment": "17th",
                "source_url": "test",
                "scraped_at": "2026-01-01T00:00:00",
            }
        ]
        count, rows = _load_and_query(db, load_pmkisan_district, "pmkisan_district", records)
        assert count == 1
        r = rows[0]
        # Old field names -> .get() defaults to 0
        assert r["beneficiaries_registered"] == 0
        assert r["amount_paid_lakhs"] == 0


class TestJJM:
    def test_round_trip(self, db):
        records = [
            {
                "district": "PATNA",
                "state": "BIHAR",
                "state_code": "05",
                "total_households": 10000,
                "households_with_tap": 7000,
                "tap_connections_provided": 7000,
                "coverage_pct": 70.0,
                "funds_released_lakhs": 3000.0,
                "funds_utilized_lakhs": 2100.0,
                "source_url": "ejalshakti.gov.in",
                "scraped_at": "2026-01-01T00:00:00",
            }
        ]
        count, rows = _load_and_query(db, load_jjm_district, "jjm_district", records)
        assert count == 1
        r = rows[0]
        assert r["total_households"] == 10000
        assert r["coverage_pct"] == 70.0


class TestPMPOSHAN:
    def test_round_trip(self, db):
        records = [
            {
                "district": "PATNA",
                "state": "BIHAR",
                "state_code": "05",
                "schools_covered": 500,
                "children_enrolled": 25000,
                "children_fed": 22000,
                "funds_released_lakhs": 1200.0,
                "funds_utilized_lakhs": 1000.0,
                "utilization_pct": 83.3,
                "source_url": "pmposhan-ams.education.gov.in",
                "scraped_at": "2026-01-01T00:00:00",
            }
        ]
        count, rows = _load_and_query(db, load_pmposhan_district, "pmposhan_district", records)
        assert count == 1
        r = rows[0]
        assert r["schools_covered"] == 500
        assert r["children_enrolled"] == 25000
        assert r["children_fed"] == 22000

    def test_field_name_mismatch_detected(self, db):
        """Records with old scraper field names should load as zeros."""
        records = [
            {
                "district": "PATNA",
                "state": "BIHAR",
                "state_code": "05",
                "total_schools": 500,
                "student_enrolment": 25000,
                "meals_served": 22000,
                "meals_served_pct": 83.3,
                "source_url": "test",
                "scraped_at": "2026-01-01T00:00:00",
            }
        ]
        count, rows = _load_and_query(db, load_pmposhan_district, "pmposhan_district", records)
        assert count == 1
        r = rows[0]
        # Old field names -> .get() defaults to 0
        assert r["schools_covered"] == 0
        assert r["children_fed"] == 0


class TestNSAP:
    def test_round_trip(self, db):
        records = [
            {
                "district": "PATNA",
                "state": "BIHAR",
                "state_code": "05",
                "district_lgd_code": "230",
                "source_month": "02",
                "scheme_type": "IGNOAPS",
                "beneficiaries_eligible": 8000,
                "beneficiaries_paid": 7500,
                "amount_paid_lakhs": 450.0,
                "pension_per_month": 500.0,
                "source_url": "nsap.nic.in",
                "scraped_at": "2026-01-01T00:00:00",
            }
        ]
        count, rows = _load_and_query(db, load_nsap_district, "nsap_district", records)
        assert count == 1
        r = rows[0]
        assert r["beneficiaries_eligible"] == 8000
        assert r["district_lgd_code"] == "230"
        assert r["source_month"] == "02"
        assert r["pension_per_month"] == 500.0


class TestNFSA:
    def test_round_trip(self, db):
        records = [
            {
                "district": "PATNA",
                "state": "BIHAR",
                "state_code": "05",
                "ration_cards_total": 100000,
                "ration_cards_active": 85000,
                "allocation_mt": 5000.0,
                "offtake_mt": 4200.0,
                "offtake_pct": 84.0,
                "beneficiaries_total": 300000,
                "date_of_data": "02 Jun 2026",
                "source_url": "nfsa.gov.in",
                "scraped_at": "2026-01-01T00:00:00",
            }
        ]
        count, rows = _load_and_query(db, load_nfsa_district, "nfsa_district", records)
        assert count == 1
        r = rows[0]
        assert r["ration_cards_total"] == 100000
        assert r["offtake_pct"] == 84.0
        assert r["beneficiaries_total"] == 300000
        assert r["date_of_data"] == "02 Jun 2026"


class TestJJMAllocation:
    def test_round_trip(self, db):
        records = [
            {
                "state": "BIHAR",
                "fin_year": "2024-2025",
                "allocated_crores": 3000.0,
                "released_crores": 2800.0,
                "expended_crores": 2500.0,
                "source_url": "ejalshakti.gov.in",
                "scraped_at": "2026-01-01T00:00:00",
            }
        ]
        count, rows = _load_and_query(db, load_jjm_allocation, "jjm_allocation", records)
        assert count == 1
        r = rows[0]
        assert r["state"] == "BIHAR"
        assert r["allocated_crores"] == 3000.0
        assert r["released_crores"] == 2800.0
        assert r["expended_crores"] == 2500.0

    def test_upsert(self, db):
        base = {
            "state": "BIHAR",
            "fin_year": "2024-2025",
            "allocated_crores": 3000.0,
            "released_crores": 2800.0,
            "expended_crores": 2500.0,
            "source_url": "ejalshakti.gov.in",
            "scraped_at": "2026-01-01T00:00:00",
        }
        _load_and_query(db, load_jjm_allocation, "jjm_allocation", [base])
        updated = {**base, "allocated_crores": 3200.0}
        count, rows = _load_and_query(db, load_jjm_allocation, "jjm_allocation", [updated])
        assert count == 1
        assert len(rows) == 1
        assert rows[0]["allocated_crores"] == 3200.0
        assert rows[0]["released_crores"] == 2800.0
        assert rows[0]["expended_crores"] == 2500.0


class TestSBMDistrict:
    def test_round_trip(self, db):
        records = [
            {
                "district": "PATNA",
                "state": "BIHAR",
                "state_code": "05",
                "total_villages": 460,
                "odf_plus_villages": 160,
                "odf_plus_pct": 34.78,
                "one_star_villages": 60,
                "three_star_villages": 0,
                "five_star_villages": 100,
                "model_village_pct": 21.74,
                "source_url": "sbm.gov.in",
                "scraped_at": "2026-01-01T00:00:00",
            }
        ]
        count, rows = _load_and_query(db, load_sbm_district, "sbm_district", records)
        assert count == 1
        r = rows[0]
        assert r["district"] == "PATNA"
        assert r["total_villages"] == 460
        assert r["odf_plus_villages"] == 160
        assert r["odf_plus_pct"] == 34.78
        assert r["five_star_villages"] == 100
        assert r["model_village_pct"] == 21.74

    def test_upsert(self, db):
        base = {
            "district": "PATNA",
            "state": "BIHAR",
            "state_code": "05",
            "total_villages": 460,
            "odf_plus_villages": 160,
            "odf_plus_pct": 34.78,
            "one_star_villages": 60,
            "three_star_villages": 0,
            "five_star_villages": 100,
            "model_village_pct": 21.74,
            "source_url": "sbm.gov.in",
            "scraped_at": "2026-01-01T00:00:00",
        }
        _load_and_query(db, load_sbm_district, "sbm_district", [base])
        updated = {**base, "odf_plus_villages": 200}
        count, rows = _load_and_query(db, load_sbm_district, "sbm_district", [updated])
        assert count == 1
        assert len(rows) == 1
        assert rows[0]["odf_plus_villages"] == 200


class TestNRLMDistrict:
    def test_round_trip(self, db):
        records = [
            {
                "district": "PATNA",
                "state": "BIHAR",
                "state_code": "05",
                "shgs_total": 12345,
                "shgs_new": 5000,
                "shgs_revived": 3000,
                "shgs_pre_nrlm": 4345,
                "members_total": 150000,
                "rf_shgs_provided": 8000,
                "rf_amount_lakhs": 450.5,
                "source_url": "nrlm.gov.in",
                "scraped_at": "2026-01-01T00:00:00",
            }
        ]
        count, rows = _load_and_query(db, load_nrlm_district, "nrlm_district", records)
        assert count == 1
        r = rows[0]
        assert r["district"] == "PATNA"
        assert r["shgs_total"] == 12345
        assert r["members_total"] == 150000
        assert r["rf_shgs_provided"] == 8000
        assert r["rf_amount_lakhs"] == 450.5

    def test_upsert(self, db):
        base = {
            "district": "PATNA",
            "state": "BIHAR",
            "state_code": "05",
            "shgs_total": 12345,
            "shgs_new": 5000,
            "shgs_revived": 3000,
            "shgs_pre_nrlm": 4345,
            "members_total": 150000,
            "rf_shgs_provided": 8000,
            "rf_amount_lakhs": 450.5,
            "source_url": "nrlm.gov.in",
            "scraped_at": "2026-01-01T00:00:00",
        }
        _load_and_query(db, load_nrlm_district, "nrlm_district", [base])
        updated = {**base, "rf_amount_lakhs": 500.0}
        count, rows = _load_and_query(db, load_nrlm_district, "nrlm_district", [updated])
        assert count == 1
        assert len(rows) == 1
        assert rows[0]["rf_amount_lakhs"] == 500.0


class TestUDISEState:
    def test_round_trip(self, db):
        records = [
            {
                "state": "BIHAR",
                "fin_year": "2024-2025",
                "total_schools": 85000,
                "schools_govt": 45000,
                "total_students": 8500000,
                "total_teachers": 450000,
                "ptr_primary": 25.3,
                "ger_primary": 98.5,
                "dropout_primary": 1.2,
                "schools_electricity_pct": 85.3,
                "source_url": "api.udiseplus.gov.in",
                "scraped_at": "2026-01-01T00:00:00",
            }
        ]
        count, rows = _load_and_query(db, load_udise_state, "udise_state", records)
        assert count == 1
        r = rows[0]
        assert r["state"] == "BIHAR"
        assert r["total_schools"] == 85000
        assert r["schools_govt"] == 45000
        assert r["total_students"] == 8500000
        assert r["total_teachers"] == 450000
        assert r["ptr_primary"] == 25.3
        assert r["ger_primary"] == 98.5
        assert r["dropout_primary"] == 1.2
        assert r["schools_electricity_pct"] == 85.3

    def test_upsert(self, db):
        base = {
            "state": "BIHAR",
            "fin_year": "2024-2025",
            "total_schools": 85000,
            "schools_govt": 45000,
            "total_students": 8500000,
            "total_teachers": 450000,
            "ptr_primary": 25.3,
            "ger_primary": 98.5,
            "dropout_primary": 1.2,
            "schools_electricity_pct": 85.3,
            "source_url": "api.udiseplus.gov.in",
            "scraped_at": "2026-01-01T00:00:00",
        }
        _load_and_query(db, load_udise_state, "udise_state", [base])
        updated = {**base, "total_students": 8750000}
        count, rows = _load_and_query(db, load_udise_state, "udise_state", [updated])
        assert count == 1
        assert len(rows) == 1
        assert rows[0]["total_students"] == 8750000


class TestPinConstituency:
    def test_round_trip(self, db):
        records = [
            {
                "pin_code": "110001",
                "constituency": "NEW DELHI",
                "state": "DELHI",
                "method": "spatial_geonames",
            }
        ]
        count, rows = _load_and_query(db, load_pin_constituency, "pin_constituency", records)
        assert count == 1
        r = rows[0]
        assert r["pin_code"] == "110001"
        assert r["constituency"] == "NEW DELHI"
        assert r["state"] == "DELHI"
        assert r["method"] == "spatial_geonames"

    def test_rejects_malformed_rows(self, db):
        records = [
            {"pin_code": "1100", "constituency": "NEW DELHI", "state": "DELHI"},
            {"pin_code": "11000X", "constituency": "NEW DELHI", "state": "DELHI"},
            {"pin_code": "110001", "constituency": "", "state": "DELHI"},
            {"pin_code": "110001", "constituency": "NEW DELHI", "state": ""},
        ]
        count, rows = _load_and_query(db, load_pin_constituency, "pin_constituency", records)
        assert count == 0
        assert rows == []

    def test_method_defaults_when_absent(self, db):
        records = [{"pin_code": "823001", "constituency": "GAYA", "state": "BIHAR"}]
        count, rows = _load_and_query(db, load_pin_constituency, "pin_constituency", records)
        assert count == 1
        assert rows[0]["method"] == "spatial_join"

    def test_registered_and_curated_file_matches_load_glob(self):
        """The March gap: the curated file existed but nothing loaded it.
        Guard both halves — registry entry AND a file matching run_all's
        `{loader_name}_*_latest.json` glob."""
        from db import LOADERS
        from db.connection import CURATED_DIR

        assert LOADERS.get("pin_constituency") is load_pin_constituency
        assert list(CURATED_DIR.glob("pin_constituency_*_latest.json")), (
            "no curated file matches the pin_constituency load glob"
        )
