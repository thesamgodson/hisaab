"""Coverage and provenance laws for the citizen complaint registry."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHANNELS = json.loads(
    (ROOT / "data/curated/grievance_channels_all_latest.json").read_text()
)
ENTITLEMENTS = json.loads(
    (ROOT / "data/curated/scheme_entitlements_all_latest.json").read_text()
)


def test_registry_keeps_all_claimed_coverage():
    counts = Counter(row["scheme"] for row in CHANNELS)
    schemes = {row["scheme"] for row in ENTITLEMENTS}
    assert len(CHANNELS) == 52
    assert counts["ALL"] == 7
    assert sum(count for scheme, count in counts.items() if scheme != "ALL") == 45
    assert len(schemes) == 11
    assert set(counts) - {"ALL"} == schemes
    assert "UDISE+" in schemes


def test_every_citizen_claim_keeps_provenance():
    for row in [*CHANNELS, *ENTITLEMENTS]:
        assert row["source_url"].startswith("https://")
        assert row["scraped_at"]
    for row in CHANNELS:
        assert row["portal_url"].startswith("https://")
        assert row["description"]
        assert row["authority"]


def test_only_verified_registry_phones_ship():
    phones = {row["phone"] for row in CHANNELS if row.get("phone")}
    assert phones == {
        "1967",
        "011-24010690",
        "011-24362705",
        "011-24650535",
        "011-23478200",
        "14448",
    }
