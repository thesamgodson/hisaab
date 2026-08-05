"""PC-name registry: unit behavior, invariants, TS lockstep, DB acceptance.

The DB acceptance tests run against data/hisaab.db and skip when the civic
tables are empty (CI builds the DB from curated JSON only — constituency_
district/mp_info are seeded locally by constituency.ingest).
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from constituency.pc_name_registry import (
    PC_NAME_REGISTRY,
    canonical_pc_name,
    pc_name_lookup_candidates,
    strip_reservation,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "hisaab.db"


class TestCanonicalPcName:
    def test_truncated_suffix_repair(self):
        assert canonical_pc_name("JANJGIR-CHAMPA (SC", "CHHATTISGARH") == "JANJGIR-CHAMPA (SC)"
        assert canonical_pc_name("FATEHGARH SAHIB (SC", "PUNJAB") == "FATEHGARH SAHIB (SC)"

    def test_mojibake_repair(self):
        assert canonical_pc_name("KARAULI ?DHOLPUR(SC)", "RAJASTHAN") == "KARAULI-DHOLPUR (SC)"
        assert canonical_pc_name("TONK ? SAWAI MADHOPUR", "RAJASTHAN") == "TONK-SAWAI MADHOPUR"
        assert canonical_pc_name("RATNAGIRI ?SINDHUDUR", "MAHARASHTRA") == "RATNAGIRI-SINDHUDURG"

    def test_truncation_repair(self):
        assert canonical_pc_name("THIRUVANANTHAPURA", "KERALA") == "THIRUVANANTHAPURAM"
        assert canonical_pc_name("NAINITAL-UDHAMSINGH NAG", "UTTARAKHAND") == "NAINITAL-UDHAMSINGH NAGAR"
        assert canonical_pc_name("MUMBAI SOUTH -CENTRA", "MAHARASHTRA") == "MUMBAI SOUTH CENTRAL"

    def test_delimitation_successors(self):
        assert canonical_pc_name("KALIABOR", "ASSAM") == "KAZIRANGA"
        assert canonical_pc_name("AUTONOMOUS DISTRICT", "ASSAM") == "DIPHU"
        assert canonical_pc_name("ANANTANAG", "JAMMU AND KASHMIR") == "ANANTNAG-RAJOURI"

    def test_rename_reattaches_callers_suffix(self):
        assert canonical_pc_name("ARAMBAG (SC)", "WEST BENGAL") == "ARAMBAGH (SC)"
        assert canonical_pc_name("ARAMBAG", "WEST BENGAL") == "ARAMBAGH"

    def test_opencity_variants_fold(self):
        assert canonical_pc_name("BAHARAICH", "UTTAR PRADESH") == "BAHRAICH"
        assert canonical_pc_name("THIRUPATHI(SC)", "ANDHRA PRADESH") == "TIRUPATI (SC)"
        assert canonical_pc_name("PATLIPUTRA", "BIHAR") == "PATALIPUTRA"
        assert canonical_pc_name("DADAR & NAGAR HAVELI", "DADRA AND NAGAR HAVELI AND DAMAN AND DIU") == "DADRA & NAGAR HAVELI"

    def test_state_scoping_blocks_cross_state_folds(self):
        # KALIABOR only exists as an Assam variant; other states pass through.
        assert canonical_pc_name("KALIABOR", "BIHAR") == "KALIABOR"
        # AURANGABAD is a real seat in two states — never in the registry.
        assert canonical_pc_name("AURANGABAD", "BIHAR") == "AURANGABAD"
        assert canonical_pc_name("AURANGABAD", "MAHARASHTRA") == "AURANGABAD"

    def test_passthrough_collapses_whitespace_only(self):
        assert canonical_pc_name("  GAYA   (SC) ", "BIHAR") == "GAYA (SC)"
        assert canonical_pc_name("VARANASI", "UTTAR PRADESH") == "VARANASI"


class TestRegistryInvariants:
    def test_keys_and_values_are_collapsed_uppercase(self):
        for (state, variant), canon in PC_NAME_REGISTRY.items():
            for text in (state, variant, canon):
                assert text == " ".join(text.strip().upper().split()), text

    def test_no_identity_entries(self):
        for (state, variant), canon in PC_NAME_REGISTRY.items():
            assert variant != canon, (state, variant)

    def test_no_chained_mappings(self):
        # A canonical value must never itself be a variant key in its state —
        # otherwise two passes would disagree with one pass.
        for (state, _variant), canon in PC_NAME_REGISTRY.items():
            assert (state, canon) not in PC_NAME_REGISTRY, (state, canon)
            assert (state, strip_reservation(canon)) not in PC_NAME_REGISTRY, (state, canon)

    def test_states_are_canonical(self):
        from db.normalize_states import normalize_state

        for state, _variant in PC_NAME_REGISTRY:
            assert normalize_state(state) == state, state


class TestLookupCandidates:
    def test_legacy_name_expands(self):
        assert "PUDUCHERRY" in pc_name_lookup_candidates("PONDICHERRY")
        assert pc_name_lookup_candidates("TEZPUR", states=["ASSAM"]) == ["TEZPUR", "SONITPUR"]

    def test_state_scope_blocks_other_states(self):
        assert pc_name_lookup_candidates("TEZPUR", states=["BIHAR"]) == ["TEZPUR"]

    def test_plain_name_passes_through(self):
        assert pc_name_lookup_candidates("GAYA (SC)") == ["GAYA"]

    def test_suffixed_variant_expands(self):
        assert "ARAMBAGH" in pc_name_lookup_candidates("ARAMBAG (SC)")


class TestTsLockstep:
    def test_generated_ts_matches_python_registry(self):
        import sys

        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from gen_pc_name_registry import TS_PATH, render_ts

        assert TS_PATH.exists(), "web/src/lib/pc-name-registry.ts missing — run scripts/gen_pc_name_registry.py"
        assert TS_PATH.read_text() == render_ts(), (
            "web/src/lib/pc-name-registry.ts is stale — run scripts/gen_pc_name_registry.py"
        )


# ---------------------------------------------------------------------------
# Acceptance against the real DB (skipped when civic tables are empty, e.g. CI)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def db():
    if not DB_PATH.exists():
        pytest.skip(f"Database not found at {DB_PATH}")
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


def _civic_ready(conn: sqlite3.Connection) -> bool:
    try:
        cd = conn.execute("SELECT COUNT(*) FROM constituency_district").fetchone()[0]
        mp = conn.execute("SELECT COUNT(*) FROM mp_info").fetchone()[0]
    except sqlite3.OperationalError:
        return False
    return cd > 0 and mp > 0


class TestDbAcceptance:
    def test_every_cd_row_finds_its_mp(self, db):
        if not _civic_ready(db):
            pytest.skip("civic tables empty (CI builds from curated JSON only)")
        from constituency.mapper import get_mp_info

        unmatched = [
            (r["constituency"], r["state"])
            for r in db.execute(
                "SELECT DISTINCT constituency, state FROM constituency_district"
            )
            if get_mp_info(r["constituency"], state=r["state"]) is None
        ]
        assert unmatched == [], f"{len(unmatched)} cd rows without an MP: {unmatched[:10]}"

    def test_mp_orphans_are_exactly_the_delhi_gap(self, db):
        # Delhi's PC↔district mapping is a recorded gap (datameet has blank
        # DIST_NAME for all Delhi features); every other seat must be reachable.
        if not _civic_ready(db):
            pytest.skip("civic tables empty (CI builds from curated JSON only)")
        from db.normalize_states import candidate_states

        cd_keys = set()
        for r in db.execute("SELECT DISTINCT constituency, state FROM constituency_district"):
            cd_keys.add((strip_reservation(r["constituency"]), r["state"].upper()))

        orphans = []
        for m in db.execute("SELECT constituency, state FROM mp_info"):
            name = strip_reservation(m["constituency"])
            if not any((name, st) in cd_keys for st in candidate_states(m["state"])):
                orphans.append((name, m["state"]))

        assert sorted(orphans) == sorted(
            [
                ("CHANDNI CHOWK", "DELHI"),
                ("EAST DELHI", "DELHI"),
                ("NEW DELHI", "DELHI"),
                ("NORTH EAST DELHI", "DELHI"),
                ("NORTH WEST DELHI", "DELHI"),
                ("SOUTH DELHI", "DELHI"),
                ("WEST DELHI", "DELHI"),
            ]
        ), orphans

    def test_stored_labels_contain_no_known_variant(self, db):
        if not _civic_ready(db):
            pytest.skip("civic tables empty (CI builds from curated JSON only)")
        variants_by_state: dict[str, set[str]] = {}
        for (state, variant), _canon in PC_NAME_REGISTRY.items():
            variants_by_state.setdefault(state, set()).add(variant)

        offenders = []
        for table, col in [
            ("constituency_district", "constituency"),
            ("mp_info", "constituency"),
            ("pin_constituency", "constituency"),
            ("ac_district", "pc_name"),
        ]:
            for r in db.execute(
                f"SELECT DISTINCT {col} AS name, state FROM {table} WHERE {col} IS NOT NULL"
            ):
                state = r["state"].upper()
                name = " ".join(r["name"].strip().upper().split())
                if name in variants_by_state.get(state, set()):
                    offenders.append((table, state, name))
        assert offenders == [], offenders

    def test_spot_check_delimitation_mps(self, db):
        if not _civic_ready(db):
            pytest.skip("civic tables empty (CI builds from curated JSON only)")
        from constituency.mapper import get_mp_info

        kaziranga = get_mp_info("KALIABOR", state="ASSAM")
        assert kaziranga and "TASA" in kaziranga["mp_name"].upper()
        haridwar = get_mp_info("HARDWAR", state="UTTARAKHAND")
        assert haridwar and "TRIVENDRA" in haridwar["mp_name"].upper()
        puducherry = get_mp_info("PONDICHERRY", state="PUDUCHERRY")
        assert puducherry and "VAITHILINGAM" in puducherry["mp_name"].upper()

    def test_ut_seats_have_district_rows(self, db):
        if not _civic_ready(db):
            pytest.skip("civic tables empty (CI builds from curated JSON only)")
        rows = {
            r["constituency"]: r["n"]
            for r in db.execute(
                """SELECT constituency, COUNT(*) AS n FROM constituency_district
                   WHERE constituency IN ('ANDAMAN & NICOBAR ISLANDS', 'CHANDIGARH',
                                          'LAKSHADWEEP', 'DADRA & NAGAR HAVELI', 'DAMAN & DIU')
                   GROUP BY constituency"""
            )
        }
        assert rows.get("ANDAMAN & NICOBAR ISLANDS") == 3
        assert rows.get("CHANDIGARH") == 1
        assert rows.get("LAKSHADWEEP") == 1
        assert rows.get("DADRA & NAGAR HAVELI") == 1
        assert rows.get("DAMAN & DIU") == 2
