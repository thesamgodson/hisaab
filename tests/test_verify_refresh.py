from scripts.verify_refresh import _pairs


def test_coverage_pairs_use_canonical_state_scoped_identity() -> None:
    rows = [
        {"state": "SIKKIM", "district": "EAST DISTRICT"},
        {"state": "SIKKIM", "district": "GANGTOK"},
        {"state": "RAJASTHAN", "district": "GANGANAGAR"},
        {"state": "RAJASTHAN", "district": "SRI GANGANAGAR"},
    ]

    assert _pairs(rows) == {
        ("SIKKIM", "GANGTOK"),
        ("RAJASTHAN", "SRI GANGANAGAR"),
    }
