"""Fail-closed bindings between root-account claims and persisted evidence.

The root account selects one current record for most scheme/geography pairs.
This gate hashes those exact selectable records, not whole history tables. Row
ids are deliberately excluded; geography, period, displayed values, source,
and retrieval timestamp are included.

Two classes of change, two policies (Scepter decision 2026-08-15 — the
2026-08-09 scheduled refresh died here BY DESIGN, see findings.md):

- **Claims text is fail-closed, always.** If ``DATA_CLAIMS.md`` changed, the
  gate fails and ``--write-contracts`` REFUSES to rebind until the change is
  reviewed and accepted explicitly (``--accept-claims``). No pipeline may
  auto-accept a claims edit.
- **Refreshed evidence rebinds inside the verified pipeline.** A scheduled
  scrape that passed ``verify_refresh`` (granularity/coverage/money guards)
  legitimately changes data content; the refresh workflow runs
  ``--write-contracts`` AFTER those gates and commits this file together with
  the curated data, so the binding always describes what git ships. Content
  drift OUTSIDE a verified refresh still fails the read-only gate on the next
  CI run.

Manual reviewed-change flow (claims edits, new datasets):

1. update or supersede the affected entries in ``DATA_CLAIMS.md``;
2. run the final load/alias reload;
3. run ``python scripts/verify_public_claims.py --write-contracts
   --accept-claims``; and
4. run this script without flags and the test suite.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB = ROOT / "data" / "hisaab.db"
CLAIMS_PATH = ROOT / "DATA_CLAIMS.md"
PUBLIC_ACCOUNT_FILES = (
    ROOT / "web" / "src" / "lib" / "area-account.ts",
    ROOT / "web" / "src" / "lib" / "state-account.ts",
)
CLAIM_PATTERN = re.compile(r"CLAIM-\d{4}-\d{4}")


@dataclass(frozen=True)
class Contract:
    name: str
    table: str
    columns: tuple[str, ...]
    claim_ids: tuple[str, ...]
    mode: str = "latest_district"
    where: str = ""


def _contract(
    name: str,
    table: str,
    values: str,
    claims: str,
    mode: str = "latest_district",
    where: str = "",
) -> Contract:
    state_modes = {"latest_state", "nfsa_state"}
    geography = ("state",) if mode in state_modes else ("state", "district")
    columns = (*geography, "fin_year", *values.split(), "source_url", "scraped_at")
    return Contract(name, table, columns, tuple(claims.split()), mode, where)


CONTRACTS = (
    _contract("mgnrega_finance", "financial_statement", "total_availability cumulative_expenditure", "CLAIM-2026-0025"),
    _contract("mgnrega_fto_generated", "fto_status", "total_fto_generated", "CLAIM-2026-0026"),
    _contract(
        "mgnrega_fto_signatures",
        "fto_status",
        "first_signatory_pending second_signatory_pending",
        "CLAIM-2026-0043",
    ),
    _contract(
        "pmgsy_district",
        "pmgsy_district",
        "roads_sanctioned roads_completed length_sanctioned_km length_completed_km value_of_projects_cr expenditure_cr",
        "CLAIM-2026-0042",
    ),
    _contract("pmayg_district", "pmayg_district", "houses_sanctioned houses_completed", "CLAIM-2026-0018"),
    _contract(
        "pmayg_state",
        "pmayg_finance",
        "allocated_lakhs released_lakhs utilized_lakhs",
        "CLAIM-2026-0034",
        "latest_state",
    ),
    _contract(
        "pmkisan_installment_22",
        "pmkisan_district",
        "installment beneficiaries_paid",
        "CLAIM-2026-0044",
        "filtered",
        "installment = '22' AND fin_year = '2025-2026'",
    ),
    _contract(
        "pmkisan_april_july",
        "pmkisan_district",
        "installment beneficiaries_registered beneficiaries_paid",
        "CLAIM-2026-0030",
        "filtered",
        "district = 'ALL' AND installment = 'April-July' AND fin_year = '2026-2027'",
    ),
    _contract("jjm_district", "jjm_district", "total_households households_with_tap", "CLAIM-2026-0045"),
    _contract(
        "jjm_state",
        "jjm_allocation",
        "allocated_crores released_crores expended_crores",
        "CLAIM-2026-0015",
        "latest_state",
    ),
    _contract("pmposhan_district", "pmposhan_district", "children_fed", "CLAIM-2026-0041"),
    _contract(
        "pmposhan_state",
        "pmposhan_finance",
        "allocated_lakhs released_lakhs utilized_lakhs",
        "CLAIM-2026-0012",
        "latest_state",
    ),
    _contract(
        "nfsa_district", "nfsa_district", "ration_cards_total beneficiaries_total date_of_data", "CLAIM-2026-0029"
    ),
    _contract("nfsa_state", "nfsa_allocation", "grain_type allocation_mt offtake_mt", "CLAIM-2026-0014", "nfsa_state"),
    _contract("sbm_district", "sbm_district", "total_villages odf_plus_villages", "CLAIM-2026-0046"),
    _contract(
        "nrlm_rf",
        "nrlm_district",
        "state_code shgs_total rf_shgs_provided rf_amount_lakhs",
        "CLAIM-2026-0027",
    ),
    _contract(
        "nrlm_cif",
        "nrlm_district",
        "state_code cif_shgs_provided cif_shgs_eligible cif_amount_lakhs",
        "CLAIM-2026-0033",
    ),
    _contract(
        "nsap_district",
        "nsap_district",
        "district_lgd_code source_month scheme_type beneficiaries_paid",
        "CLAIM-2026-0047",
        "nsap_district",
    ),
    _contract("nsap_state", "nsap_finance", "released_lakhs", "CLAIM-2026-0013", "latest_state"),
    _contract("udise_state", "udise_state", "total_schools total_students", "CLAIM-2026-0020", "latest_state"),
)

# Generated from the reviewed final load. Update manually; never generate in CI.
EXPECTED: dict[str, dict[str, int | str]] = {'jjm_district': {'claims_sha256': 'd4a707e592b6e532ae206c85e8975d50886b92af924c6ee9365f1e20f28d281d',
                  'data_sha256': '142ff8d42eea27fac6fa24ac9aa09bb7fd010f321ce4f1c10e6e6123b3a65758',
                  'rows': 754},
 'jjm_state': {'claims_sha256': '1462a23763c2c69751d1156cc603ee899d628b20239762ab823ff143c8a42a57',
               'data_sha256': '8d2501d4fce06739627cad4c531ee2b9daa46248cab69e138c942a574b0623d9',
               'rows': 33},
 'mgnrega_finance': {'claims_sha256': 'c1dce7eab4ee6abb62ec37d3eb58568451d25c0e00a0a9168d68a6010d690f3b',
                     'data_sha256': '440cd7f3f3a42cb816fed6701cda6af00c10ca44e45f9e79903dbd99f908796f',
                     'rows': 749},
 'mgnrega_fto_generated': {'claims_sha256': '2852fcbe9a42e39312f6b7c4b4abbac331c04c85c57cb514fe7d7dd62cd73317',
                           'data_sha256': '80589b93acec9e0c74905bd4ab1d995a78412974253c343385ea6068e35d004f',
                           'rows': 716},
 'mgnrega_fto_signatures': {'claims_sha256': '9ec6c0c9d33764c078f21245a255e5db02cb1750314bc14c5424a7cb980b5690',
                            'data_sha256': 'cd958df6d317a7752ce194144b699e2638e214d28e3e6370517bad8bb0c07ecc',
                            'rows': 716},
 'nfsa_district': {'claims_sha256': '46c68d957beb5f2746d0a61fa222f5f6f404eeea94b548d55d8f4d3c8fa968cf',
                   'data_sha256': 'ec8697bb3ec2584718e4439d359527e5aa7bfcfeffe2721d45cd3afc50fb9448',
                   'rows': 744},
 'nfsa_state': {'claims_sha256': '1f452150d74603937a74ec3b1da77efc6b8b20cc2ad57ba267487c8e09d7d9b7',
                'data_sha256': 'db0332a494b993fd824b06818fe9f1096e828c1dabce1bb46c4171ca3eecfbc5',
                'rows': 53},
 'nrlm_cif': {'claims_sha256': '653614a6cd341b19d8aad8b65010fdccb4d3cda800926da11e7225efbcf65cf2',
              'data_sha256': '2949fb935cf9a287b98de63a0cc85218535c81f81db395cf3bf54807e29f9883',
              'rows': 760},
 'nrlm_rf': {'claims_sha256': 'cc1d5d159a4aff2d4724da1d3eb301f40edbc05463c1a4629cfd651cd0ea49c8',
             'data_sha256': 'ac77f54f44f012569ac2cab775eb86bf88bb4e60356258570d844886cc352f31',
             'rows': 760},
 'nsap_district': {'claims_sha256': 'e5473c5dfce55ed22690aa7b010ff7cb6a5dc5fece70d454b93de8b600d37b30',
                   'data_sha256': '1d8e27e92382fb01eecef5cd63caa5acba3e476bb5d61a890c8525e04c0a3c9d',
                   'rows': 2183},
 'nsap_state': {'claims_sha256': '89d72f8a300a0c6a0c30b7bb7d2892189b20a6ad6c8114bd281703b0d647b633',
                'data_sha256': '650e7f008839a98037f150cc1813e92ac40b5b637d0146fc3f79c169b297dbd8',
                'rows': 36},
 'pmayg_district': {'claims_sha256': 'c66f31ea70b39ca5d0ba4523ace0ea45a797d2a6e32a2a5087628a92039bf27d',
                    'data_sha256': 'c52bceacdf8f64f71ec559de68ff37dcce0243ff130fbbf7ed0c8ab1595a1e2d',
                    'rows': 740},
 'pmayg_state': {'claims_sha256': 'a07be027d8887389e42a08cf2e93892c99c9b8dc552cf693522a6bc9aa62b9ae',
                 'data_sha256': 'e615f50738483649504941bdc68a7c32282933f2bfd8b67e176d5d989138b5de',
                 'rows': 31},
 'pmgsy_district': {'claims_sha256': 'b47279544035d00946822a66dede0045726293e925c500f435d7773dadd1fb34',
                    'data_sha256': '91a2780001a8d1b4ee5ebb93cd74d33d13d680f2cb1871b6c3b163ed053aadae',
                    'rows': 714},
 'pmkisan_april_july': {'claims_sha256': 'c78e831fa43feea0ae0e5b63833e9e21c753710d434f1f7a08ea702f960e9b0d',
                        'data_sha256': '5f872faf494824ff8561a0ff25627e0568c1d33d7612e80fea8b6246b83208cf',
                        'rows': 36},
 'pmkisan_installment_22': {'claims_sha256': '537f278f651211765889a57f82fd42f4b718d6a80e7b5e73744f9c8539df1313',
                            'data_sha256': '8d265c793027551673a84e42f40e4d3573af5c5a33644e014c9f82841d75af8d',
                            'rows': 776},
 'pmposhan_district': {'claims_sha256': 'a67cfaf4ac5320daad093109fa67fbda25029d2da2f592ca1061d607873773f2',
                       'data_sha256': '45b547a2103478ea84ecf202e01d1c80c00efc1da99934f1973c51ff9429ccb1',
                       'rows': 781},
 'pmposhan_state': {'claims_sha256': 'be46d3c0b8b4b3858212ecd34d23474657adb2a33ddaf09f2f7dc8ceb2891692',
                    'data_sha256': '970489eff5f9cecc7cbed59f780846070a0a0c9cac52aaa20908c31f96380701',
                    'rows': 36},
 'sbm_district': {'claims_sha256': 'c709a54eb0d6a040331ebc84bc68c899f6ee646cc08975d01949e59accadd8fc',
                  'data_sha256': '6194a2c8dd77cf70913092fb3697fd11068a0693784e6c322109507e46ed3a06',
                  'rows': 756},
 'udise_state': {'claims_sha256': '524cba341bae03a4730708e2019b79a2cb9d93215d4996dcae0f2cbfabd80fe4',
                 'data_sha256': '4d723f40dffc7debc53375d42efe45646feb1b90232fad86ddc99eed3a3a1950',
                 'rows': 27}}


def _latest_query(contract: Contract, keys: tuple[str, ...]) -> str:
    columns = ", ".join(contract.columns)
    partition = ", ".join(keys)
    return f"""
        WITH ranked AS (
          SELECT {columns}, ROW_NUMBER() OVER (
            PARTITION BY {partition} ORDER BY fin_year DESC, scraped_at DESC
          ) AS claim_rank
          FROM {contract.table}
        )
        SELECT {columns} FROM ranked WHERE claim_rank = 1
    """


def _nfsa_state_query(contract: Contract) -> str:
    columns = ", ".join(f"n.{column}" for column in contract.columns)
    return f"""
        SELECT {columns} FROM nfsa_allocation n
        WHERE n.fin_year = (
          SELECT MAX(years.fin_year) FROM nfsa_allocation years
          WHERE years.state = n.state
        ) AND (
          n.grain_type IN ('rice', 'wheat')
          OR (n.grain_type = 'total' AND NOT EXISTS (
            SELECT 1 FROM nfsa_allocation components
            WHERE components.state = n.state
              AND components.fin_year = n.fin_year
              AND components.grain_type IN ('rice', 'wheat')
          ))
        )
    """


def _nsap_district_query(contract: Contract) -> str:
    columns = ", ".join(f"n.{column}" for column in contract.columns)
    return f"""
        SELECT {columns} FROM nsap_district n
        WHERE n.fin_year = (
          SELECT MAX(years.fin_year) FROM nsap_district years
          WHERE years.state = n.state AND years.district = n.district
        )
    """


def contract_query(contract: Contract) -> str:
    if contract.mode == "latest_district":
        return _latest_query(contract, ("state", "district"))
    if contract.mode == "latest_state":
        return _latest_query(contract, ("state",))
    if contract.mode == "nfsa_state":
        return _nfsa_state_query(contract)
    if contract.mode == "nsap_district":
        return _nsap_district_query(contract)
    columns = ", ".join(contract.columns)
    return f"SELECT {columns} FROM {contract.table} WHERE {contract.where}"


def _canonical_row(columns: tuple[str, ...], row: sqlite3.Row) -> str:
    values = {column: row[column] for column in columns}
    return json.dumps(values, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def data_fingerprint(connection: sqlite3.Connection, contract: Contract) -> tuple[int, str]:
    connection.row_factory = sqlite3.Row
    rows = connection.execute(contract_query(contract)).fetchall()
    serialized = sorted(_canonical_row(contract.columns, row) for row in rows)
    payload = ("\n".join(serialized) + "\n").encode()
    return len(rows), hashlib.sha256(payload).hexdigest()


def claim_fingerprint(claim_ids: tuple[str, ...], claims_path: Path = CLAIMS_PATH) -> str:
    lines = claims_path.read_text().splitlines()
    entries: list[str] = []
    for claim_id in sorted(claim_ids):
        matches = [line.strip() for line in lines if line.startswith(f"| {claim_id} |")]
        if len(matches) != 1:
            raise ValueError(f"{claim_id}: expected one DATA_CLAIMS row, found {len(matches)}")
        entries.extend(matches)
    return hashlib.sha256(("\n".join(entries) + "\n").encode()).hexdigest()


def public_account_claim_ids() -> set[str]:
    text = "\n".join(path.read_text() for path in PUBLIC_ACCOUNT_FILES)
    return set(CLAIM_PATTERN.findall(text))


def configured_claim_ids() -> set[str]:
    return {claim_id for contract in CONTRACTS for claim_id in contract.claim_ids}


def current_contracts(db_path: Path, claims_path: Path = CLAIMS_PATH) -> dict[str, dict[str, int | str]]:
    results: dict[str, dict[str, int | str]] = {}
    with sqlite3.connect(db_path) as connection:
        for contract in CONTRACTS:
            rows, digest = data_fingerprint(connection, contract)
            results[contract.name] = {
                "rows": rows,
                "data_sha256": digest,
                "claims_sha256": claim_fingerprint(contract.claim_ids, claims_path),
            }
    return results


def verification_errors(db_path: Path, claims_path: Path = CLAIMS_PATH) -> list[str]:
    errors: list[str] = []
    missing = public_account_claim_ids() - configured_claim_ids()
    extra = configured_claim_ids() - public_account_claim_ids()
    if missing:
        errors.append(f"unbound public claim IDs: {', '.join(sorted(missing))}")
    if extra:
        errors.append(f"contracts for undisplayed claim IDs: {', '.join(sorted(extra))}")
    try:
        current = current_contracts(db_path, claims_path)
    except (OSError, sqlite3.Error, ValueError) as exc:
        return [*errors, f"could not evaluate claim contracts: {exc}"]
    for name, actual in current.items():
        expected = EXPECTED.get(name)
        if expected != actual:
            errors.append(f"{name}: expected {expected!r}, got {actual!r}")
    unknown = set(EXPECTED) - set(current)
    if unknown:
        errors.append(f"expected values exist for unknown contracts: {', '.join(sorted(unknown))}")
    return errors


def rewrite_expected(current: dict[str, dict[str, int | str]]) -> None:
    """Replace the EXPECTED literal in this file with `current`, formatted
    stably so the diff shows exactly which datasets moved."""
    import pprint

    script = Path(__file__)
    text = script.read_text(encoding="utf-8")
    marker = "EXPECTED: dict[str, dict[str, int | str]] = "
    start = text.index(marker) + len(marker)
    depth = 0
    end = start
    for index in range(start, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                end = index + 1
                break
    literal = pprint.pformat(current, width=100, sort_dicts=True)
    script.write_text(text[:start] + literal + text[end:], encoding="utf-8")


def write_contracts(db_path: Path, claims_path: Path, accept_claims: bool) -> int:
    current = current_contracts(db_path, claims_path)
    claims_drift = sorted(
        name
        for name, actual in current.items()
        if name in EXPECTED and EXPECTED[name].get("claims_sha256") != actual["claims_sha256"]
    )
    if claims_drift and not accept_claims:
        print("REFUSED: DATA_CLAIMS.md changed for: " + ", ".join(claims_drift), file=sys.stderr)
        print("Claims text is fail-closed. Review the claims edit, then re-run with --accept-claims.", file=sys.stderr)
        return 1
    moved = sorted(name for name, actual in current.items() if EXPECTED.get(name) != actual)
    if not moved:
        print("Contracts already bind the current data — nothing to write.")
        return 0
    rewrite_expected(current)
    print(f"Rebound {len(moved)} dataset contract(s): {', '.join(moved)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--claims", type=Path, default=CLAIMS_PATH)
    parser.add_argument("--print-contracts", action="store_true")
    parser.add_argument(
        "--write-contracts",
        action="store_true",
        help="Rebind data hashes to current evidence (post-verify_refresh only). Refuses on claims drift without --accept-claims.",
    )
    parser.add_argument("--accept-claims", action="store_true")
    args = parser.parse_args()
    if args.print_contracts:
        print(json.dumps(current_contracts(args.db, args.claims), indent=4, sort_keys=True))
        return 0
    if args.write_contracts:
        return write_contracts(args.db, args.claims, args.accept_claims)
    errors = verification_errors(args.db, args.claims)
    if errors:
        print("Public claim binding gate FAILED:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        print("Review DATA_CLAIMS.md, then regenerate with --print-contracts.", file=sys.stderr)
        return 1
    print(f"Public claim binding gate passed: {len(CONTRACTS)} datasets are bound.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
