"""Electoral-consistency rule for the pin_constituency curated file.

Lok Sabha constituencies never cross state lines; the March-2026 spatial
join violated that for ~2% of PINs (e.g. 823001 GAYAJI/BIHAR mapped to
KARIMGANJ/ASSAM). scripts/clean_pin_constituency.py drops such rows while
keeping the two legitimate mismatch families (vintage pre-bifurcation
labels, PINs absent from the directory).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db.normalize_states import normalize_state
from scripts.clean_pin_constituency import is_electorally_consistent


class TestElectoralConsistency:
    def test_same_state_kept(self):
        assert is_electorally_consistent("BIHAR", {"BIHAR"})

    def test_cross_state_garbage_dropped(self):
        # The Gaya bug: a Bihar PIN spatially joined to an Assam constituency.
        assert not is_electorally_consistent("ASSAM", {"BIHAR"})

    def test_adjacent_state_still_dropped(self):
        # Border noise is still electorally impossible — a Bihar-directory
        # PIN's voters vote in a Bihar PC.
        assert not is_electorally_consistent("WEST BENGAL", {"BIHAR"})

    def test_vintage_telangana_kept(self):
        # datameet polygons predate the 2014 bifurcation: AP-labeled
        # constituencies legitimately serve Telangana PINs.
        assert is_electorally_consistent("ANDHRA PRADESH", {"TELANGANA"})

    def test_vintage_ladakh_kept(self):
        assert is_electorally_consistent("JAMMU AND KASHMIR", {"LADAKH"})

    def test_vintage_is_not_transitive_to_others(self):
        assert not is_electorally_consistent("ANDHRA PRADESH", {"ODISHA"})

    def test_pin_missing_from_directory_kept(self):
        assert is_electorally_consistent("BIHAR", None)
        assert is_electorally_consistent("BIHAR", set())

    def test_multi_state_pin_matches_any(self):
        assert is_electorally_consistent("BIHAR", {"JHARKHAND", "BIHAR"})


class TestUttarakhandSpelling:
    def test_datameet_variant_normalizes(self):
        # The datameet AC file spells it UTTARKHAND; unnormalized it produced
        # 223 phantom cross-state mismatches.
        assert normalize_state("UTTARKHAND") == "UTTARAKHAND"
        assert normalize_state("Uttarkhand") == "UTTARAKHAND"


class TestStatePortalSpellings:
    def test_state_context_variants_normalize(self):
        assert normalize_state("NCT DELHI") == "DELHI"
        assert normalize_state("UTTRAKHAND") == "UTTARAKHAND"
        assert normalize_state("TELENGANA") == "TELANGANA"
        assert normalize_state("TAMILNADU") == "TAMIL NADU"
