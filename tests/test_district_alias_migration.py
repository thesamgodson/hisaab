from __future__ import annotations

import json
from pathlib import Path

from db.district_aliases import ALIASES
from db.normalize_districts import normalize_district

ROOT = Path(__file__).resolve().parent.parent

EXPECTED = {
    ("GUJARAT", "PANCH MAHALS"): "PANCHMAHAL",
    ("RAJASTHAN", "GANGANAGAR"): "SRI GANGANAGAR",
    ("UTTAR PRADESH", "BARA BANKI"): "BARABANKI",
    ("LAKSHADWEEP", "LAKSHADWEEP DISTRICT"): "LAKSHADWEEP",
    ("MAHARASHTRA", "BANDRA MSD"): "MUMBAI SUBURBAN",
    ("ANDHRA PRADESH", "ANANTAPUR"): "ANANTHAPURAMU",
    ("ANDHRA PRADESH", "SPSR NELLORE"): "SRI POTTI SRIRAMULU NELLORE",
    ("CHHATTISGARH", "DANTEWADA"): "DAKSHIN BASTAR DANTEWADA",
    ("SIKKIM", "EAST DISTRICT"): "GANGTOK",
    ("SIKKIM", "NORTH DISTRICT"): "MANGAN",
    ("SIKKIM", "SOUTH DISTRICT"): "NAMCHI",
    ("SIKKIM", "WEST DISTRICT"): "GYALSHING",
}


def test_audited_variants_resolve_to_one_state_scoped_name() -> None:
    for (state, variant), canonical in EXPECTED.items():
        assert normalize_district(variant, state) == canonical
        assert normalize_district(canonical, state) == canonical


def test_alias_registry_has_no_cycles() -> None:
    for state, variant in ALIASES:
        seen = {variant}
        value = ALIASES[(state, variant)]
        while (state, value) in ALIASES:
            assert value not in seen, (state, variant, value)
            seen.add(value)
            value = ALIASES[(state, value)]


def test_topology_uses_the_same_canonical_names() -> None:
    data = json.loads((ROOT / "web/public/india-districts.topojson").read_text())
    names = {
        (geometry.get("properties", {}).get("state"), geometry.get("properties", {}).get("district"))
        for item in data["objects"].values()
        for geometry in item["geometries"]
    }
    mapped_targets = {(state, canonical) for (state, _), canonical in EXPECTED.items()}
    mapped_variants = {(state, variant) for state, variant in EXPECTED}
    assert mapped_targets <= names
    assert not names & mapped_variants
