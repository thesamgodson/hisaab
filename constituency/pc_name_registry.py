"""Canonical Lok Sabha constituency (PC) name registry.

One canonical name per 2024 seat, applied at every boundary that WRITES a PC
label (constituency_district / ac_district.pc_name / mp_info ingest, and the
pin_constituency loader). Both sources deviate from the official names:
datameet's 2008-delimitation GeoJSON carries truncations ("THIRUVANANTHAPURA"),
mojibake ("KARAULI ?DHOLPUR(SC)") and pre-delimitation names (GAUHATI,
ANANTANAG), while the OpenCity 2024 results CSV carries typos (KURNOOLU,
BAHARAICH, "DADAR & NAGAR HAVELI") and spacing/hyphen variants.

Canonical form = the seat name as recorded for the 18th Lok Sabha
(Sansad/ECI-derived; see DATA_CLAIMS.md CLAIM-2026-0036 for the per-seat
verification protocol and sources). Where ECI's delimitation-order spelling
differs from Lok Sabha records (HARDWAR/Haridwar, PALAMAU/Palamu), both spell
forms resolve here and the Lok Sabha form is served.

Keys are STATE-SCOPED — India reuses PC names across states, and any civic
name key that omits state is a recorded landmine (learnings.md 2026-08-05).
Keys use canonical state labels (db.normalize_states output). Two key styles:

- exact raw label as a source writes it (repairs truncated/mojibake labels,
  including broken reservation suffixes: "JANJGIR-CHAMPA (SC"), or
- suffix-stripped name (renames; the caller's own " (SC)"/" (ST)" suffix is
  re-attached after mapping, so "ARAMBAG (SC)" -> "ARAMBAGH (SC)").

Assam entries map 2008-delimitation seats to their 2023-delimitation
successors (boundaries changed, not just names) — the approximation is
documented in CLAIM-2026-0036; same for Jammu & Kashmir's 2022 delimitation
(ANANTANAG -> ANANTNAG-RAJOURI).

The web twin `web/src/lib/pc-name-registry.ts` is GENERATED from this module
by scripts/gen_pc_name_registry.py; tests/test_pc_name_registry.py fails if
the two drift.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

_RESERVATION_RE = re.compile(r"\s*\((?:SC|ST)\)\s*$", re.IGNORECASE)


def strip_reservation(name: str) -> str:
    """Uppercase and drop a trailing '(SC)'/'(ST)' reservation suffix."""
    return _RESERVATION_RE.sub("", name.strip().upper()).strip()


def _collapse(name: str) -> str:
    return " ".join(name.strip().upper().split())


# (state, variant) -> canonical label. Every entry verified against the 2024
# general election result: the canonical seat's winner is named in the comment
# and must match the mp_info row the mapping joins to.
PC_NAME_REGISTRY: dict[tuple[str, str], str] = {
    # --- Andhra Pradesh (OpenCity spelling variants) ---
    ("ANDHRA PRADESH", "ANANTHAPUR"): "ANANTAPUR",  # G. Lakshminarayana Valmiki (TDP)
    ("ANDHRA PRADESH", "KURNOOLU"): "KURNOOL",  # B. Nagaraju Panchalingala (TDP)
    ("ANDHRA PRADESH", "NARSARAOPET"): "NARASARAOPET",  # Lavu Sri Krishna Devarayalu (TDP)
    ("ANDHRA PRADESH", "THIRUPATHI(SC)"): "TIRUPATI (SC)",  # Maddila Gurumoorthy (YSRCP)
    # --- Andaman & Nicobar (user-lookup variant) ---
    ("ANDAMAN AND NICOBAR", "ANDAMAN AND NICOBAR ISLANDS"): "ANDAMAN & NICOBAR ISLANDS",  # Bishnu Pada Ray (BJP)
    # --- Assam: 2023 delimitation successors (boundaries changed; see claim) ---
    ("ASSAM", "AUTONOMOUS DISTRICT"): "DIPHU",  # Amarsing Tisso (UPPL)
    ("ASSAM", "GAUHATI"): "GUWAHATI",  # Bijuli Kalita Medhi (BJP)
    ("ASSAM", "KALIABOR"): "KAZIRANGA",  # Kamakhya Prasad Tasa (BJP)
    ("ASSAM", "MANGALDOI"): "DARRANG-UDALGURI",  # Dilip Saikia (BJP)
    ("ASSAM", "NOWGONG"): "NAGAON",  # Pradyut Bordoloi (INC)
    ("ASSAM", "TEZPUR"): "SONITPUR",  # Ranjit Dutta (BJP)
    # --- Bihar (OpenCity spelling; ECI/LS records use Pataliputra) ---
    ("BIHAR", "PATLIPUTRA"): "PATALIPUTRA",  # Misa Bharti (RJD)
    # --- Chhattisgarh (datameet truncated suffix) ---
    ("CHHATTISGARH", "JANJGIR-CHAMPA (SC"): "JANJGIR-CHAMPA (SC)",  # Kamlesh Jangde (BJP)
    # --- Dadra & Nagar Haveli and Daman & Diu ---
    ("DADRA AND NAGAR HAVELI AND DAMAN AND DIU", "DADAR & NAGAR HAVELI"): "DADRA & NAGAR HAVELI",  # Kalaben Delkar (BJP); OpenCity typo DADAR
    ("DADRA AND NAGAR HAVELI AND DAMAN AND DIU", "DADRA AND NAGAR HAVELI"): "DADRA & NAGAR HAVELI",  # user-lookup variant
    # --- Delhi (OpenCity hyphenates; official form is unhyphenated) ---
    ("DELHI", "NORTH-EAST DELHI"): "NORTH EAST DELHI",  # Manoj Tiwari (BJP)
    ("DELHI", "NORTH-WEST DELHI"): "NORTH WEST DELHI",  # Yogender Chandoliya (BJP)
    # --- Jammu & Kashmir: 2022 delimitation successor (see claim) ---
    ("JAMMU AND KASHMIR", "ANANTANAG"): "ANANTNAG-RAJOURI",  # Mian Altaf Ahmad (JKNC)
    # --- Jharkhand (ECI results say Palamau; LS records say Palamu) ---
    ("JHARKHAND", "PALAMAU"): "PALAMU",  # Vishnu Dayal Ram (BJP)
    # --- Kerala (datameet truncation) ---
    ("KERALA", "THIRUVANANTHAPURA"): "THIRUVANANTHAPURAM",  # Shashi Tharoor (INC)
    # --- Maharashtra (datameet hyphens/mojibake; OpenCity spacing variants) ---
    ("MAHARASHTRA", "BHANDARA GONDIYA"): "BHANDARA-GONDIYA",  # Prashant Padole (INC)
    ("MAHARASHTRA", "GADCHIROLI - CHIMUR"): "GADCHIROLI-CHIMUR",  # Kirsan Namdeo (INC)
    ("MAHARASHTRA", "HATKANANGALE"): "HATKANANGLE",  # Dhairyasheel Mane (SS)
    ("MAHARASHTRA", "MUMBAI NORTH-CENTRAL"): "MUMBAI NORTH CENTRAL",  # Varsha Gaikwad (INC)
    ("MAHARASHTRA", "MUMBAI NORTH-EAST"): "MUMBAI NORTH EAST",  # Sanjay Dina Patil (SS-UBT)
    ("MAHARASHTRA", "MUMBAI NORTH-WEST"): "MUMBAI NORTH WEST",  # Ravindra Waikar (SS)
    ("MAHARASHTRA", "MUMBAI SOUTH -CENTRA"): "MUMBAI SOUTH CENTRAL",  # Anil Desai (SS-UBT)
    ("MAHARASHTRA", "RATNAGIRI ?SINDHUDUR"): "RATNAGIRI-SINDHUDURG",  # Narayan Rane (BJP)
    ("MAHARASHTRA", "RATNAGIRI- SINDHUDURG"): "RATNAGIRI-SINDHUDURG",  # OpenCity spacing
    ("MAHARASHTRA", "YAVATMAL- WASHIM"): "YAVATMAL-WASHIM",  # Sanjay Deshmukh (SS-UBT)
    # --- Puducherry (renamed from Pondicherry, 2006) ---
    ("PUDUCHERRY", "PONDICHERRY"): "PUDUCHERRY",  # V. Vaithilingam (INC)
    # --- Punjab (datameet truncated suffix) ---
    ("PUNJAB", "FATEHGARH SAHIB (SC"): "FATEHGARH SAHIB (SC)",  # Amar Singh (INC)
    # --- Rajasthan (datameet mojibake for the hyphen) ---
    ("RAJASTHAN", "KARAULI ?DHOLPUR(SC)"): "KARAULI-DHOLPUR (SC)",  # Bhajan Lal Jatav (INC)
    ("RAJASTHAN", "TONK ? SAWAI MADHOPUR"): "TONK-SAWAI MADHOPUR",  # Harish Chandra Meena (INC)
    # --- Uttar Pradesh (OpenCity typo) ---
    ("UTTAR PRADESH", "BAHARAICH"): "BAHRAICH",  # Anand Kumar Gond (BJP)
    # --- Uttarakhand (ECI order says Hardwar; LS records say Haridwar) ---
    ("UTTARAKHAND", "HARDWAR"): "HARIDWAR",  # Trivendra Singh Rawat (BJP)
    ("UTTARAKHAND", "NAINITAL-UDHAMSINGH NAG"): "NAINITAL-UDHAMSINGH NAGAR",  # Ajay Bhatt (BJP)
    # --- West Bengal ---
    ("WEST BENGAL", "ARAMBAG"): "ARAMBAGH",  # Mitali Bag (AITC); datameet drops the H
    ("WEST BENGAL", "JOYNAGAR"): "JAYNAGAR",  # Pratima Mondal (AITC); ECI results form
    ("WEST BENGAL", "SERAMPORE"): "SREERAMPUR",  # user-lookup variant (anglicised)
    ("WEST BENGAL", "SRERAMPUR"): "SREERAMPUR",  # Kalyan Banerjee (AITC); OpenCity drops an E
}


def canonical_pc_name(name: str, state: str) -> str:
    """Return the canonical PC label for a source-written label.

    `state` must already be canonical (db.normalize_states). Lookup order:
    exact raw label (repairs truncations/mojibake, broken suffixes included),
    then suffix-stripped name with the caller's own suffix re-attached.
    Unknown names pass through with whitespace collapsed.
    """
    raw = _collapse(name)
    key_state = state.strip().upper()

    exact = PC_NAME_REGISTRY.get((key_state, raw))
    if exact is not None:
        return exact

    stripped = strip_reservation(raw)
    mapped = PC_NAME_REGISTRY.get((key_state, stripped))
    if mapped is None:
        return raw
    suffix = _RESERVATION_RE.search(raw)
    if suffix:
        tag = "SC" if "SC" in suffix.group(0).upper() else "ST"
        return f"{mapped} ({tag})"
    return mapped


def pc_name_lookup_candidates(name: str, states: Iterable[str] | None = None) -> list[str]:
    """Canonical names a user-supplied PC name could mean, for lookups.

    Always includes the suffix-stripped input itself (stored labels are
    canonical, so known names match directly); adds forward translations of
    any registry variant equal to the input — scoped to `states` when given,
    across all states otherwise (the caller's state filter still applies at
    query time, so cross-state candidates cannot leak another state's seat).
    """
    raw = _collapse(name)
    stripped = strip_reservation(raw)
    scope = {s.strip().upper() for s in states} if states is not None else None

    out = [stripped]
    for (st, variant), canon in PC_NAME_REGISTRY.items():
        if scope is not None and st not in scope:
            continue
        if variant in (raw, stripped):
            clean = strip_reservation(canon)
            if clean not in out:
                out.append(clean)
    return out
