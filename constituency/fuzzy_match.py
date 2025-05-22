"""District name normalization and fuzzy matching for constituency mapping.

Handles the many spelling variations found across government portals:
  - "NORTH TWENTY FOUR PARGANAS" vs "NORTH 24 PARGANAS"
  - "GAUTAM BUDDHA NAGAR" vs "GAUTAM BUDDH NAGAR"
  - "Y.S.R." vs "YSR"

Follows the same pattern as normalize_states.py.
"""

from __future__ import annotations

import difflib
import re
import sqlite3

from db.connection import DB_PATH

# ---------------------------------------------------------------------------
# Static alias table for known mismatches
# ---------------------------------------------------------------------------

_DISTRICT_ALIASES: dict[str, str] = {
    # West Bengal — spelled-out numbers
    "NORTH TWENTY FOUR PARGANAS": "NORTH 24 PARGANAS",
    "SOUTH TWENTY FOUR PARGANAS": "SOUTH 24 PARGANAS",
    "24 PARGANAS NORTH": "NORTH 24 PARGANAS",
    "24 PARGANAS SOUTH": "SOUTH 24 PARGANAS",
    "NORTH 24 PARAGANAS": "NORTH 24 PARGANAS",
    "SOUTH 24 PARAGANAS": "SOUTH 24 PARGANAS",
    # Delhi
    "NCT OF DELHI": "DELHI",
    "DELHI NCT": "DELHI",
    "NEW DELHI": "DELHI",
    # Andhra Pradesh / Telangana
    "Y.S.R.": "YSR",
    "Y S R": "YSR",
    "Y.S.R": "YSR",
    "YADADRI BHUVANAGIRI": "YADADRI BHUVANGIRI",
    # Uttar Pradesh
    "GAUTAM BUDDHA NAGAR": "GAUTAM BUDDH NAGAR",
    "BARABANKI": "BARA BANKI",
    # Rajasthan
    "GANGANAGAR": "SRI GANGANAGAR",
    "SHRI GANGANAGAR": "SRI GANGANAGAR",
    # Maharashtra
    "AHMEDNAGAR": "AHMADNAGAR",
    "AURANGABAD": "CHHATRAPATI SAMBHAJINAGAR",
    "OSMANABAD": "DHARASHIV",
    # Odisha
    "JAJAPUR": "JAJPUR",
    "BOUDH": "BAUDH",
    # Karnataka
    "TUMKUR": "TUMAKURU",
    "SHIMOGA": "SHIVAMOGGA",
    "BELGAUM": "BELAGAVI",
    "BIJAPUR": "VIJAYAPURA",
    "GULBARGA": "KALABURAGI",
    "BIDAR": "BIDAR",
    "BELLARY": "BALLARI",
    "MYSORE": "MYSURU",
    "HASSAN": "HASSAN",
    "DAKSHINA KANNADA": "DAKSHINA KANNADA",
    "MANGALORE": "DAKSHINA KANNADA",
    # Tamil Nadu
    "KANCHEEPURAM": "KANCHIPURAM",
    "TIRUCHIRAPALLI": "TIRUCHIRAPPALLI",
    "CUDDALORE": "CUDDALORE",
    "VILLUPURAM": "VILLUPURAM",
    # Himachal Pradesh
    "LAHUL AND SPITI": "LAHAUL AND SPITI",
    "LAHAUL & SPITI": "LAHAUL AND SPITI",
    # Jammu and Kashmir
    "BADGAM": "BUDGAM",
    # Assam
    "KAMRUP METRO": "KAMRUP METROPOLITAN",
    "KAMRUP (METRO)": "KAMRUP METROPOLITAN",
    "KAMRUP METROPOLITAN": "KAMRUP METROPOLITAN",
    # Jharkhand
    "SARAIKELA KHARSAWAN": "SARAIKELA-KHARSAWAN",
    "SARAIKELA": "SARAIKELA-KHARSAWAN",
    # Punjab
    "SHAHID BHAGAT SINGH NAGAR": "SHAHEED BHAGAT SINGH NAGAR",
    "SBS NAGAR": "SHAHEED BHAGAT SINGH NAGAR",
    # Gujarat
    "DOHAD": "DAHOD",
    "PANCH MAHALS": "PANCHMAHAL",
    "PANCHMAHALS": "PANCHMAHAL",
    # Madhya Pradesh
    "NARSIMHAPUR": "NARSINGHPUR",
}

# ---------------------------------------------------------------------------
# Number-word mapping for spelled-out digit normalization
# ---------------------------------------------------------------------------

_WORD_TO_NUM: dict[str, str] = {
    "ONE": "1",
    "TWO": "2",
    "THREE": "3",
    "FOUR": "4",
    "FIVE": "5",
    "SIX": "6",
    "SEVEN": "7",
    "EIGHT": "8",
    "NINE": "9",
    "TEN": "10",
    "ELEVEN": "11",
    "TWELVE": "12",
    "THIRTEEN": "13",
    "FOURTEEN": "14",
    "FIFTEEN": "15",
    "SIXTEEN": "16",
    "SEVENTEEN": "17",
    "EIGHTEEN": "18",
    "NINETEEN": "19",
    "TWENTY": "20",
    "TWENTY ONE": "21",
    "TWENTY TWO": "22",
    "TWENTY THREE": "23",
    "TWENTY FOUR": "24",
    "TWENTY FIVE": "25",
}

# Suffixes to strip from district names
_STRIP_SUFFIXES: tuple[str, ...] = (
    r"\s*\(URBAN\)\s*$",
    r"\s*\(RURAL\)\s*$",
    r"\s*\(M CORP\)\s*$",
    r"\s*\(M\)\s*$",
    r"\s*\(U\)\s*$",
    r"\s*\(R\)\s*$",
    r"\s*DISTRICT$",
)


def normalize_district(name: str) -> str:
    """Normalize a district name for matching.

    Applies:
    - UPPERCASE, strip whitespace
    - & → AND
    - Strip parenthetical suffixes: (URBAN), (RURAL), (M CORP), (M), etc.
    - Collapse multiple spaces
    - Check static alias table
    """
    if not name:
        return ""

    key = name.strip().upper()

    # Ampersand → AND
    key = key.replace("&", "AND")

    # Strip known suffixes
    for suffix_pat in _STRIP_SUFFIXES:
        key = re.sub(suffix_pat, "", key).strip()

    # Collapse multiple spaces
    key = re.sub(r"\s+", " ", key).strip()

    # Check alias table
    if key in _DISTRICT_ALIASES:
        return _DISTRICT_ALIASES[key]

    return key


def _replace_spelled_numbers(name: str) -> str:
    """Replace spelled-out number words with digits (e.g., TWENTY FOUR → 24).

    Only applies multi-word spans first, then single words.
    """
    result = name
    # Try multi-word numbers first (longer matches take priority)
    for word, digit in sorted(_WORD_TO_NUM.items(), key=lambda x: -len(x[0])):
        result = result.replace(word, digit)
    # Collapse double-spaces that may result
    return re.sub(r"\s+", " ", result).strip()


def build_canonical_districts() -> dict[str, set[str]]:
    """Extract all unique district names per state from existing scheme tables.

    Queries the scheme_delivery VIEW which unions all scheme district tables.
    Returns {state: {district1, district2, ...}}
    """
    conn = sqlite3.connect(str(DB_PATH))
    try:
        rows = conn.execute(
            "SELECT DISTINCT district, state FROM scheme_delivery "
            "WHERE district IS NOT NULL AND district != '' AND district != 'ALL'"
        ).fetchall()
    finally:
        conn.close()

    canonical: dict[str, set[str]] = {}
    for district, state in rows:
        canonical.setdefault(state, set()).add(district.strip().upper())
    return canonical


def match_district(
    name: str,
    state: str,
    canonical: dict[str, set[str]],
) -> str | None:
    """Match a district name against canonical names for a given state.

    Strategy:
    1. Normalize the input.
    2. Exact match after normalization.
    3. Try number-word expansion/contraction.
    4. difflib.SequenceMatcher ratio > 0.85, same state only.

    Returns the canonical district name or None if no match found.
    """
    normalized = normalize_district(name)
    if not normalized:
        return None

    state_upper = state.strip().upper()
    candidates = canonical.get(state_upper, set())
    if not candidates:
        return None

    # 1. Exact match
    if normalized in candidates:
        return normalized

    # 2. Number-word expansion: try with digits replacing words
    expanded = _replace_spelled_numbers(normalized)
    if expanded in candidates:
        return expanded

    # Also try the reverse: replace digits with words (rare but possible)
    for word, digit in _WORD_TO_NUM.items():
        contracted = normalized.replace(digit, word)
        contracted = re.sub(r"\s+", " ", contracted).strip()
        if contracted in candidates:
            return contracted

    # 3. Fuzzy match via SequenceMatcher
    best_ratio = 0.0
    best_match: str | None = None
    for candidate in candidates:
        ratio = difflib.SequenceMatcher(None, normalized, candidate).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = candidate

    if best_ratio >= 0.85 and best_match is not None:
        return best_match

    return None
