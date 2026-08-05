"""Regenerate db/district_aliases.py from data evidence.

Unifies the three district-name systems that meet in this codebase:
  1. Government scheme portals (data/hisaab.db scheme tables — many spellings)
  2. India Post PIN directory (pin_district_mapping — the PIN-flow join anchor)
  3. Census map boundaries (web/public/india-districts.topojson)

Canonical names = India Post form, except where _OVERRIDES pins the official
spelling (e.g. NORTH 24 PARGANAS, not "24 PARAGANAS NORTH").

Safety guards against merging genuinely different districts:
  - direction/number tokens must match exactly (EAST/WEST GODAVARI,
    BANGALORE R/U, NORTH WEST I/II never merge)
  - first letters must match (AGAR never merges into SAGAR)
  - similarity >= 0.88 on token-sorted names (catches word permutations
    and misspellings together)

Run after major data refreshes:  python3 scripts/gen_district_aliases.py
"""

from __future__ import annotations

import difflib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "hisaab.db"
TOPO = ROOT / "web" / "public" / "india-districts.topojson"
OUT = ROOT / "db" / "district_aliases.py"

# Script-dir invocation doesn't put the repo root on sys.path — without this
# the existing-registry import silently fails and the registry SHRINKS.
import sys  # noqa: E402

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

THRESH = 0.88

GUARD_TOKENS = {
    "EAST", "WEST", "NORTH", "SOUTH", "UPPER", "LOWER", "CENTRAL", "MIDDLE",
    "I", "II", "III", "IV", "1", "2", "3", "4",
    "R", "U", "RURAL", "URBAN",
    "METRO", "METROPOLITAN", "UTTAR", "DAKSHIN", "PURBA", "PURBI", "PASCHIM",
}
GUARD_EQUIV = {"METROPOLITAN": "METRO", "RURAL": "R", "URBAN": "U", "PURBI": "PURBA"}

# Hand-curated official spellings. Two roles:
#   - remap India Post registry forms to the official canonical
#   - resolve variants the fuzzy pass cannot (word-order swaps across
#     guard tokens, renames, abbreviations)
_OVERRIDES: dict[tuple[str, str], str] = {
    # West Bengal — India Post + census forms -> official
    ("WEST BENGAL", "24 PARAGANAS NORTH"): "NORTH 24 PARGANAS",
    ("WEST BENGAL", "24 PARGANAS NORTH"): "NORTH 24 PARGANAS",
    ("WEST BENGAL", "NORTH TWENTY FOUR PARGANAS"): "NORTH 24 PARGANAS",
    ("WEST BENGAL", "24 PARAGANAS SOUTH"): "SOUTH 24 PARGANAS",
    ("WEST BENGAL", "24 PARGANAS SOUTH"): "SOUTH 24 PARGANAS",
    ("WEST BENGAL", "SOUTH TWENTY FOUR PARGANAS"): "SOUTH 24 PARGANAS",
    ("WEST BENGAL", "SOUTH 24PARGANAS"): "SOUTH 24 PARGANAS",
    ("WEST BENGAL", "DINAJPUR UTTAR"): "UTTAR DINAJPUR",
    ("WEST BENGAL", "DINAJPUR DAKSHIN"): "DAKSHIN DINAJPUR",
    ("WEST BENGAL", "MEDINIPUR EAST"): "PURBA MEDINIPUR",
    ("WEST BENGAL", "MEDINIPUR WEST"): "PASCHIM MEDINIPUR",
    ("WEST BENGAL", "PASCHIM BARDDHAMAN"): "PASCHIM BARDHAMAN",
    ("WEST BENGAL", "PURBA BARDDHAMAN"): "PURBA BARDHAMAN",
    ("WEST BENGAL", "COOCHBEHAR"): "COOCH BEHAR",
    ("WEST BENGAL", "COOCH BIHAR"): "COOCH BEHAR",
    ("WEST BENGAL", "KOCH BIHAR"): "COOCH BEHAR",
    ("WEST BENGAL", "MALDAH"): "MALDA",
    ("WEST BENGAL", "DARJILING"): "DARJEELING",
    ("WEST BENGAL", "HAORA"): "HOWRAH",
    ("WEST BENGAL", "HUGLI"): "HOOGHLY",
    ("WEST BENGAL", "PURULIYA"): "PURULIA",
    # Official district renames — old name still used by some portals
    # (NSAP and PMGSY carry pre-rename names; newer scrapes carry post-rename)
    ("KARNATAKA", "BELGAUM"): "BELAGAVI",
    ("KARNATAKA", "BELLARY"): "BALLARI",
    ("KARNATAKA", "MYSORE"): "MYSURU",
    ("KARNATAKA", "SHIMOGA"): "SHIVAMOGGA",
    ("KARNATAKA", "TUMKUR"): "TUMAKURU",
    ("KARNATAKA", "BIJAPUR"): "VIJAYAPURA",
    ("KARNATAKA", "GULBARGA"): "KALABURAGI",
    ("HARYANA", "GURGAON"): "GURUGRAM",
    ("MADHYA PRADESH", "HOSHANGABAD"): "NARMADAPURAM",
    ("MAHARASHTRA", "AHMADNAGAR"): "AHILYANAGAR",
    ("MAHARASHTRA", "AHMEDNAGAR"): "AHILYANAGAR",
    ("MAHARASHTRA", "AURANGABAD"): "CHHATRAPATI SAMBHAJINAGAR",
    ("MAHARASHTRA", "CHATRAPATI SAMBHAJI NAGAR"): "CHHATRAPATI SAMBHAJINAGAR",
    ("MAHARASHTRA", "OSMANABAD"): "DHARASHIV",
    ("UTTAR PRADESH", "FAIZABAD"): "AYODHYA",
    ("UTTAR PRADESH", "ALLAHABAD"): "PRAYAGRAJ",
    # Other verified spellings the fuzzy pass cannot resolve safely
    ("BIHAR", "AURANGABAD BIHAR"): "AURANGABAD",
    ("MADHYA PRADESH", "AGAR"): "AGAR MALWA",
    ("MADHYA PRADESH", "AAGAR"): "AGAR MALWA",
    ("BIHAR", "AURANAGABAD"): "AURANGABAD",
    ("HARYANA", "MAHINDERGARH"): "MAHENDRAGARH",
    ("HARYANA", "MOHINDERGARH"): "MAHENDRAGARH",
    ("KARNATAKA", "VIJAYNAGAR"): "VIJAYANAGARA",
    ("KARNATAKA", "VIJAYANAGAR"): "VIJAYANAGARA",
    ("JHARKHAND", "EAST SINGHBUM"): "EAST SINGHBHUM",
    ("JHARKHAND", "WEST SINGHBUM"): "WEST SINGHBHUM",
    ("ANDHRA PRADESH", "VISAKHAPATANAM"): "VISAKHAPATNAM",
    ("MAHARASHTRA", "AMRAWATI"): "AMRAVATI",
    # Odisha — unify to the India Post / PIN-directory forms (also the
    # majority of scheme tables). pmgsy/pmposhan carry the other spelling.
    ("ODISHA", "BALASORE"): "BALESHWAR",
    ("ODISHA", "BOLANGIR"): "BALANGIR",
    ("ODISHA", "KEONJHAR"): "KENDUJHAR",
    ("ODISHA", "KHURDA"): "KHORDHA",
    ("ODISHA", "NUAPARA"): "NUAPADA",
    ("ODISHA", "SUBARNAPUR"): "SONEPUR",
    # Gujarat — official spelling: Dohad was renamed Dahod; the scheme
    # majority already carries DAHOD while India Post still prints DOHAD.
    ("GUJARAT", "DOHAD"): "DAHOD",
    # Recent official renames (2024-2026), FLIPPED to the official post-rename
    # canon on 2026-08-04 (dedicated rename-migration pass) — old portal / PIN /
    # map spellings now map INTO the new name, same direction as the
    # AYODHYA/PRAYAGRAJ entries above. The topojson map polygons (GAYA,
    # KARIMGANJ) were renamed to match; Ramanagara has no map polygon.
    # normalize_civic_tables folds the seed_data.py old GAYA/RAMANAGARA forms.
    ("BIHAR", "GAYA"): "GAYAJI",
    ("ASSAM", "KARIMGANJ"): "SRIBHUMI",
    ("KARNATAKA", "RAMANAGARA"): "BENGALURU SOUTH",
    # LokOS (DAY-NRLM) spellings
    ("ASSAM", "DIMA HASAO NORTH CACHAR HILLS"): "DIMA HASAO",
    ("KARNATAKA", "DHARWAR"): "DHARWAD",
    ("WEST BENGAL", "ALIPURUDUAR"): "ALIPURDUAR",
    ("WEST BENGAL", "SILIGURI MAHAKUMA PARISHAD DMMU"): "SILIGURI M P DMMU",
}


def mech(name: str) -> str:
    """Mechanical normalization: upper, unify separators, drop parens/dots."""
    s = str(name).upper().strip()
    s = s.replace("-", " ").replace("_", " ").replace(".", " ")
    s = re.sub(r"[()]", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def guard_sig(name: str) -> frozenset:
    toks = set(name.split())
    return frozenset(GUARD_EQUIV.get(t, t) for t in toks if t in GUARD_TOKENS)


def sorted_form(name: str) -> str:
    return " ".join(sorted(name.split()))


def compatible(a: str, b: str) -> bool:
    return guard_sig(a) == guard_sig(b) and a[:1] == b[:1]


def similar(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, sorted_form(a), sorted_form(b)).ratio()


def apply_override(state: str, name: str) -> str:
    return _OVERRIDES.get((state, name), name)


def _existing_aliases() -> dict[tuple[str, str], str]:
    """The registry is monotonic: once the DB is normalized, the variant
    evidence disappears from it, so a fresh run can only ADD aliases on top
    of the committed set — never shrink it. A missing registry is only legal
    when the file genuinely doesn't exist yet."""
    if not (ROOT / "db" / "district_aliases.py").exists():
        return {}
    from db.district_aliases import ALIASES  # import failure = hard error

    return dict(ALIASES)


def main() -> None:
    conn = sqlite3.connect(DB)
    scheme_tables = [
        "misappropriation", "financial_statement", "fto_status", "fto_pendency",
        "issues_reported", "pmgsy_district", "pmayg_district", "pmkisan_district",
        "jjm_district", "pmposhan_district", "nsap_district", "nfsa_district",
        "sbm_district", "nrlm_district",
    ]

    # Evidence: frequency of each mech form per state across scheme tables
    freq: dict[str, Counter] = defaultdict(Counter)
    for t in scheme_tables:
        try:
            rows = conn.execute(
                f"SELECT state, district, COUNT(*) FROM {t} "
                "WHERE district != 'ALL' GROUP BY 1, 2"
            ).fetchall()
        except sqlite3.OperationalError:
            continue
        for st, d, c in rows:
            m = mech(d)
            if m and m not in ("ALL", "NA"):
                freq[mech(st)][m] += c

    # Canonical registry: India Post names, passed through overrides
    registry: dict[str, set] = defaultdict(set)
    for st, d in conn.execute("SELECT DISTINCT state, district FROM pin_district_mapping"):
        s, m = mech(st), mech(d)
        if m and m not in ("NA", "ALL"):
            registry[s].add(apply_override(s, m))

    # Census map names join the variant pool
    variants: dict[str, set] = defaultdict(set)
    for st, counter in freq.items():
        variants[st] |= set(counter)
    topo = json.loads(TOPO.read_text(encoding="utf-8"))
    for obj in topo["objects"].values():
        for g in obj["geometries"]:
            p = g.get("properties", {})
            s, m = mech(p.get("state", "")), mech(p.get("district", ""))
            if s and m:
                variants[s].add(m)

    aliases: dict[tuple[str, str], str] = _existing_aliases()
    aliases.update(_OVERRIDES)

    for st in sorted(variants):
        reg = registry.get(st, set())
        names = variants[st]

        # Pass 1: guarded fuzzy match into the canonical registry
        for n in sorted(names):
            if n in reg or (st, n) in aliases:
                continue
            best, best_r = None, 0.0
            for r in reg:
                if not compatible(n, r):
                    continue
                ratio = similar(n, r)
                if ratio > best_r:
                    best, best_r = r, ratio
            if best and best_r >= THRESH:
                aliases[(st, n)] = best

        # Pass 2: cluster leftovers among themselves; most frequent form wins
        remaining = sorted(
            n for n in names if n not in reg and (st, n) not in aliases
        )
        resolved: set = set()
        for i, a in enumerate(remaining):
            if a in resolved:
                continue
            cluster = [a]
            for b in remaining[i + 1:]:
                if b in resolved or not compatible(a, b):
                    continue
                if similar(a, b) >= THRESH:
                    cluster.append(b)
                    resolved.add(b)
            if len(cluster) > 1:
                canon = max(cluster, key=lambda x: (freq[st][x], -len(x)))
                canon = apply_override(st, canon)
                for v in cluster:
                    if v != canon:
                        aliases[(st, v)] = canon

    conn.close()

    # Chase alias chains (variant -> variant -> canonical)
    for k in list(aliases):
        v, seen = aliases[k], {aliases[k]}
        while (k[0], v) in aliases:
            v = aliases[(k[0], v)]
            if v in seen:
                break
            seen.add(v)
        aliases[k] = v
    aliases = {k: v for k, v in aliases.items() if k[1] != v}

    lines = [
        '"""District name aliases: (STATE, VARIANT) -> CANONICAL.',
        "",
        "AUTO-GENERATED by scripts/gen_district_aliases.py — edit _OVERRIDES there,",
        "not this file. Unifies portal, India Post, and census map spellings.",
        '"""',
        "",
        "ALIASES: dict[tuple[str, str], str] = {",
    ]
    for (st, v), c in sorted(aliases.items()):
        lines.append(f'    ("{st}", "{v}"): "{c}",')
    lines.append("}")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)} with {len(aliases)} aliases")


if __name__ == "__main__":
    main()
