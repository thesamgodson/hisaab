from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from scripts.verify_public_claims import (
    CLAIMS_PATH,
    CONTRACTS,
    DEFAULT_DB,
    EXPECTED,
    claim_fingerprint,
    configured_claim_ids,
    current_contracts,
    data_fingerprint,
    public_account_claim_ids,
    verification_errors,
)

EXPECTED_VALUE_COLUMNS = {
    "mgnrega_finance": {"total_availability", "cumulative_expenditure"},
    "mgnrega_fto_generated": {"total_fto_generated"},
    "mgnrega_fto_signatures": {
        "first_signatory_pending",
        "second_signatory_pending",
    },
    "pmgsy_district": {
        "roads_sanctioned",
        "roads_completed",
        "length_sanctioned_km",
        "length_completed_km",
        "value_of_projects_cr",
        "expenditure_cr",
    },
    "pmayg_district": {"houses_sanctioned", "houses_completed"},
    "pmayg_state": {"allocated_lakhs", "released_lakhs", "utilized_lakhs"},
    "pmkisan_installment_22": {"installment", "beneficiaries_paid"},
    "pmkisan_april_july": {
        "installment",
        "beneficiaries_registered",
        "beneficiaries_paid",
    },
    "jjm_district": {"total_households", "households_with_tap"},
    "jjm_state": {"allocated_crores", "released_crores", "expended_crores"},
    "pmposhan_district": {"children_fed"},
    "pmposhan_state": {"allocated_lakhs", "released_lakhs", "utilized_lakhs"},
    "nfsa_district": {"ration_cards_total", "beneficiaries_total", "date_of_data"},
    "nfsa_state": {"grain_type", "allocation_mt", "offtake_mt"},
    "sbm_district": {"total_villages", "odf_plus_villages"},
    "nrlm_rf": {
        "state_code",
        "shgs_total",
        "rf_shgs_provided",
        "rf_amount_lakhs",
    },
    "nrlm_cif": {
        "state_code",
        "cif_shgs_provided",
        "cif_shgs_eligible",
        "cif_amount_lakhs",
    },
    "nsap_district": {"district_lgd_code", "source_month", "scheme_type", "beneficiaries_paid"},
    "nsap_state": {"released_lakhs"},
    "udise_state": {"total_schools", "total_students"},
}


def _copy_database(target: Path) -> None:
    with sqlite3.connect(DEFAULT_DB) as source, sqlite3.connect(target) as destination:
        source.backup(destination)


def _contract(name: str):
    return next(contract for contract in CONTRACTS if contract.name == name)


def test_loaded_public_datasets_match_reviewed_contracts():
    assert current_contracts(DEFAULT_DB) == EXPECTED
    assert verification_errors(DEFAULT_DB) == []


def test_every_root_account_claim_id_has_a_contract():
    assert configured_claim_ids() == public_account_claim_ids()


def test_contracts_bind_exact_displayed_fields_and_provenance():
    for contract in CONTRACTS:
        columns = set(contract.columns)
        expected = EXPECTED_VALUE_COLUMNS[contract.name]
        geography = {"state"} if contract.mode in {"latest_state", "nfsa_state"} else {"state", "district"}
        assert columns == expected | geography | {"fin_year", "source_url", "scraped_at"}
        assert "id" not in columns


@pytest.mark.parametrize(
    ("assignment", "value"),
    [
        ("value_of_projects_cr = value_of_projects_cr + 1", "displayed value"),
        ("source_url = source_url || '#changed'", "source URL"),
        ("scraped_at = '2099-01-01T00:00:00Z'", "retrieval timestamp"),
    ],
)
def test_public_evidence_mutation_breaks_digest(tmp_path: Path, assignment: str, value: str):
    db_path = tmp_path / "mutated.db"
    _copy_database(db_path)
    contract = _contract("pmgsy_district")
    with sqlite3.connect(db_path) as connection:
        connection.execute(f"UPDATE pmgsy_district SET {assignment} WHERE id = (SELECT MIN(id) FROM pmgsy_district)")
        actual = data_fingerprint(connection, contract)
    assert actual != (EXPECTED[contract.name]["rows"], EXPECTED[contract.name]["data_sha256"]), value


def test_unstable_row_id_is_excluded_from_digest(tmp_path: Path):
    db_path = tmp_path / "renumbered.db"
    _copy_database(db_path)
    contract = _contract("pmgsy_district")
    with sqlite3.connect(db_path) as connection:
        before = data_fingerprint(connection, contract)
        connection.execute(
            "UPDATE pmgsy_district SET id = id + 1000000 WHERE id = (SELECT MIN(id) FROM pmgsy_district)"
        )
        after = data_fingerprint(connection, contract)
    assert after == before


def test_claim_ledger_change_breaks_paired_digest(tmp_path: Path):
    claims_path = tmp_path / "DATA_CLAIMS.md"
    lines = CLAIMS_PATH.read_text().splitlines()
    claim_id = "CLAIM-2026-0042"
    index = next(i for i, line in enumerate(lines) if line.startswith(f"| {claim_id} |"))
    lines[index] = lines[index][:-1] + " reviewed change |"
    claims_path.write_text("\n".join(lines) + "\n")
    assert claim_fingerprint((claim_id,), claims_path) != EXPECTED["pmgsy_district"]["claims_sha256"]


def test_missing_schema_fails_closed(tmp_path: Path):
    db_path = tmp_path / "empty.db"
    sqlite3.connect(db_path).close()
    errors = verification_errors(db_path)
    assert any("could not evaluate claim contracts" in error for error in errors)
