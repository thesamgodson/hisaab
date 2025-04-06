"""
Normalize state/UT names across all government portals.

Different portals use different spellings for the same state:
  - "A & N ISLANDS" vs "ANDAMAN AND NICOBAR" vs "ANDAMAN AND NICOBAR ISLAND"
  - "JAMMU & KASHMIR" vs "JAMMU AND KASHMIR"
  - "D&NH AND D&D" vs "DNH & DD" vs "THE DADRA AND NAGAR HAVELI AND DAMAN AND DIU"

This module maps all known variants to the canonical name used in states.json.
"""

from __future__ import annotations

# Canonical name -> list of known aliases (all UPPERCASE)
_ALIASES: dict[str, list[str]] = {
    "ANDAMAN AND NICOBAR": [
        "A & N ISLANDS",
        "A&N ISLANDS",
        "ANDAMAN & NICOBAR",
        "ANDAMAN AND NICOBAR ISLAND",
        "ANDAMAN AND NICOBAR ISLANDS",
        "ANDAMAN & NICOBAR ISLANDS",
    ],
    "DADRA AND NAGAR HAVELI AND DAMAN AND DIU": [
        "DADRA & NAGAR HAVELI",
        "DAMAN & DIU",
        "DADRA AND NAGAR HAVELI",
        "DAMAN AND DIU",
        "D&NH AND D&D",
        "DNH & DD",
        "DNH AND DD",
        "D & NH AND D & D",
        "THE DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
        "THE DADRA AND NAGAR HAVELI AND  DAMAN AND DIU",
        "DADRA & NAGAR HAVELI AND DAMAN & DIU",
        "DADRA AND NAGAR HAVELI AND DAMAN & DIU",
    ],
    "JAMMU AND KASHMIR": [
        "JAMMU & KASHMIR",
        "J&K",
        "J & K",
    ],
    "DELHI": [
        "NCT OF DELHI",
        "DELHI NCT",
        "NEW DELHI",
    ],
    "LADAKH": [],
    "ODISHA": [
        "ORISSA",
    ],
    "UTTARAKHAND": [
        "UTTARANCHAL",
    ],
    "CHHATTISGARH": [
        "CHATTISGARH",
        "CHHATISGARH",
    ],
    "TELANGANA": [
        "TELANAGANA",
    ],
    "PUDUCHERRY": [
        "PONDICHERRY",
    ],
}

# All canonical state names from states.json (hardcoded to avoid file I/O)
_CANONICAL = {
    "ANDAMAN AND NICOBAR",
    "ANDHRA PRADESH",
    "ARUNACHAL PRADESH",
    "ASSAM",
    "BIHAR",
    "CHANDIGARH",
    "CHHATTISGARH",
    "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
    "DELHI",
    "GOA",
    "GUJARAT",
    "HARYANA",
    "HIMACHAL PRADESH",
    "JAMMU AND KASHMIR",
    "JHARKHAND",
    "KARNATAKA",
    "KERALA",
    "LADAKH",
    "LAKSHADWEEP",
    "MADHYA PRADESH",
    "MAHARASHTRA",
    "MANIPUR",
    "MEGHALAYA",
    "MIZORAM",
    "NAGALAND",
    "ODISHA",
    "PUDUCHERRY",
    "PUNJAB",
    "RAJASTHAN",
    "SIKKIM",
    "TAMIL NADU",
    "TELANGANA",
    "TRIPURA",
    "UTTAR PRADESH",
    "UTTARAKHAND",
    "WEST BENGAL",
}

# Build reverse lookup: alias -> canonical name
_LOOKUP: dict[str, str] = {}
# Add all canonical names as self-mapping
for name in _CANONICAL:
    _LOOKUP[name] = name
# Add aliases
for canonical, aliases in _ALIASES.items():
    _LOOKUP[canonical] = canonical
    for alias in aliases:
        _LOOKUP[alias] = canonical


def normalize_state(name: str) -> str:
    """Normalize a state name to the canonical form used in states.json.

    Handles (UT) suffixes, extra whitespace, and known aliases.
    Returns the input unchanged (uppercased, stripped) if no mapping is found.
    """
    import re

    key = name.strip().upper()
    # Direct match first
    if key in _LOOKUP:
        return _LOOKUP[key]
    # Strip "(UT)" suffix that some portals add
    stripped = re.sub(r"\s*\(UT\)\s*$", "", key).strip()
    if stripped in _LOOKUP:
        return _LOOKUP[stripped]
    # Strip extra whitespace
    collapsed = re.sub(r"\s+", " ", stripped)
    if collapsed in _LOOKUP:
        return _LOOKUP[collapsed]
    return key


def normalize_records(records: list[dict], state_field: str = "state") -> list[dict]:
    """Return new list of records with normalized state names."""
    return [{**r, state_field: normalize_state(r.get(state_field, ""))} for r in records]
