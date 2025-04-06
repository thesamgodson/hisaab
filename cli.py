"""
Hisaab CLI — Query MGNREGA and PMGSY financial data in your language.

Usage:
    python cli.py                          # Interactive mode
    python cli.py "misappropriation in villupuram"
    python cli.py --lang ta "villupuram corruption"
    python cli.py "roads patna"
"""

from __future__ import annotations

import argparse
import sys

from query import (
    district_overview,
    fto_pendency_summary,
    fto_status_by_district,
    fund_utilization_by_district,
    fund_utilization_state_summary,
    list_districts,
    misappropriation_by_district,
    misappropriation_state_summary,
    money_flow_by_district,
    money_flow_state_summary,
    pmgsy_district_summary,
    pmgsy_state_summary,
    pmgsy_worst_completion,
    social_audit_by_district,
    worst_misappropriation_districts,
)

# Simple keyword routing — maps intent keywords to query functions
INTENT_KEYWORDS = {
    "misappropriation": ["misappropriation", "corruption", "fraud", "theft", "ஊழல்", "भ्रष्टाचार"],
    "funds": ["funds", "money", "budget", "expenditure", "utilization", "நிதி", "பணம்", "धन", "बजट"],
    "audit": ["audit", "issues", "complaints", "grievances", "தணிக்கை", "ऑडिट", "शिकायत"],
    "fto": ["fto", "payment", "pending", "bank", "கட்டணம்", "भुगतान"],
    "roads": ["roads", "road", "pmgsy", "rural road", "sadak", "சாலை", "सड़क"],
    "housing": ["housing", "house", "awas", "pmayg", "pmay-g", "gramin awas", "வீடு", "आवास", "मकान"],
    "money_flow": ["money flow", "all schemes", "cross-scheme", "total flow", "எல்லா திட்டங்கள்"],
    "overview": ["overview", "summary", "all", "எல்லாம்", "सारांश"],
    "worst": ["worst", "top", "ranking", "மோசமான", "सबसे"],
}

# District name aliases (Tamil/Hindi → English)
DISTRICT_ALIASES = {
    "கடலூர்": "CUDDALORE",
    "விழுப்புரம்": "VILLUPURAM",
    "திருவண்ணாமலை": "TIRUVANNAMALAI",
    "சிவகங்கை": "SIVAGANGAI",
    "புதுக்கோட்டை": "PUDUKKOTTAI",
    "சேலம்": "SALEM",
    "மதுரை": "MADURAI",
    "கோயம்புத்தூர்": "COIMBATORE",
    "தஞ்சாவூர்": "THANJAVUR",
    "திருச்சி": "TIRUCHIRAPPALLI",
    "நீலகிரி": "THE NILGIRIS",
}


def resolve_district(text: str) -> str | None:
    """Try to find a district name in the input text.

    Searches across all states loaded in the DB, not just the default.
    """
    text_upper = text.upper()

    # Check Tamil/Hindi aliases
    for alias, english in DISTRICT_ALIASES.items():
        if alias in text:
            return english

    # Check all loaded districts (across all states)
    all_districts = _all_known_districts()
    for d in all_districts:
        if d.upper() in text_upper:
            return d

    # Fuzzy: check if any word matches start of district name
    words = text_upper.split()
    for word in words:
        if len(word) < 3:
            continue
        for d in all_districts:
            if d.upper().startswith(word) or word.startswith(d.upper()[:4]):
                return d

    return None


def _all_known_districts() -> list[str]:
    """Get all district names from all tables in the DB."""
    from db import get_connection

    conn = get_connection()
    names: set[str] = set()
    for table in ("misappropriation", "financial_statement", "pmgsy_district"):
        try:
            rows = conn.execute(f"SELECT DISTINCT district FROM {table}").fetchall()
            names.update(r[0] for r in rows if r[0])
        except Exception:
            pass
    return sorted(names)


def _state_for_district(district: str | None) -> str | None:
    """Look up which state a district belongs to from loaded data."""
    if not district:
        return None
    from db import get_connection

    conn = get_connection()
    for table in ("pmgsy_district", "misappropriation", "financial_statement"):
        try:
            row = conn.execute(
                f"SELECT state FROM {table} WHERE UPPER(district) = UPPER(?) LIMIT 1",
                (district,),
            ).fetchone()
            if row:
                return row[0]
        except Exception:
            pass
    return None


def _resolve_state(text: str) -> str | None:
    """Try to find a state name in the input text."""
    from db import get_connection

    conn = get_connection()
    states: set[str] = set()
    for table in ("pmgsy_district", "pmgsy_progress", "misappropriation", "financial_statement"):
        try:
            rows = conn.execute(f"SELECT DISTINCT state FROM {table}").fetchall()
            states.update(r[0] for r in rows if r[0])
        except Exception:
            pass

    text_upper = text.upper()
    for s in sorted(states, key=len, reverse=True):  # longest match first
        if s.upper() in text_upper:
            return s

    # Fuzzy: check if any word matches start of state name
    words = text_upper.split()
    for word in words:
        if len(word) < 4:
            continue
        for s in states:
            if s.upper().startswith(word) or word.startswith(s.upper()[:5]):
                return s
    return None


def _any_pmgsy_state() -> str | None:
    """Return any state that has PMGSY data loaded."""
    from db import get_connection

    conn = get_connection()
    try:
        row = conn.execute("SELECT DISTINCT state FROM pmgsy_district LIMIT 1").fetchone()
        return row[0] if row else None
    except Exception:
        return None


def detect_intent(text: str) -> str:
    """Detect query intent from keywords. Priority: worst > specific intents > overview."""
    text_lower = text.lower()
    # Check "worst/top/ranking" first — always takes priority
    for kw in INTENT_KEYWORDS["worst"]:
        if kw in text_lower:
            return "worst"
    for intent, keywords in INTENT_KEYWORDS.items():
        if intent == "worst":
            continue
        for kw in keywords:
            if kw in text_lower:
                return intent
    return "overview"


def handle_query(text: str) -> str:
    """Route a natural language query to the right function."""
    intent = detect_intent(text)
    district = resolve_district(text)

    if intent == "worst":
        # Check if query is about roads/PMGSY
        if any(kw in text.lower() for kw in ("road", "pmgsy", "sadak")):
            state = _resolve_state(text) or (_state_for_district(district) if district else None) or _any_pmgsy_state()
            return pmgsy_worst_completion(state=state or "TAMIL NADU")["answer"]
        return worst_misappropriation_districts()["answer"]

    if intent == "misappropriation":
        if district:
            return misappropriation_by_district(district)["answer"]
        return misappropriation_state_summary()["answer"]

    if intent == "funds":
        if district:
            return fund_utilization_by_district(district)["answer"]
        return fund_utilization_state_summary()["answer"]

    if intent == "audit":
        if district:
            return social_audit_by_district(district)["answer"]
        return "Specify a district for social audit data. Example: 'audit villupuram'"

    if intent == "fto":
        if district:
            return fto_status_by_district(district)["answer"]
        return fto_pendency_summary()["answer"]

    if intent == "roads":
        state = _resolve_state(text) or (_state_for_district(district) if district else None) or _any_pmgsy_state()
        if district:
            return pmgsy_district_summary(district, state=state or "TAMIL NADU")["answer"]
        return pmgsy_state_summary(state=state or "TAMIL NADU")["answer"]

    if intent == "housing":
        if district:
            return money_flow_by_district(district)["answer"]
        state = _resolve_state(text) or "TAMIL NADU"
        return money_flow_state_summary(state)["answer"]

    if intent == "money_flow":
        if district:
            return money_flow_by_district(district)["answer"]
        state = _resolve_state(text) or "TAMIL NADU"
        return money_flow_state_summary(state)["answer"]

    if intent == "overview":
        if district:
            return district_overview(district)["answer"]
        # Default: state summary
        lines = [
            misappropriation_state_summary()["answer"],
            "",
            fund_utilization_state_summary()["answer"],
            "",
            fto_pendency_summary()["answer"],
        ]
        return "\n".join(lines)

    return "I don't understand that query. Try: misappropriation, funds, audit, fto, or a district name."


def interactive_mode() -> None:
    """Run interactive REPL."""
    print("Hisaab — Government Scheme Transparency Tool")
    print("Schemes: MGNREGA, PMGSY | State: TAMIL NADU | FY: 2024-2025")
    print("Type a question or district name. Type 'quit' to exit.\n")
    print("Examples:")
    print("  misappropriation villupuram")
    print("  funds cuddalore")
    print("  worst corruption")
    print("  overview salem")
    print("  fto pending")
    print("  roads patna")
    print("  worst roads")
    print()

    while True:
        try:
            text = input("hisaab> ").strip()
        except EOFError, KeyboardInterrupt:
            print("\nBye.")
            break

        if not text:
            continue
        if text.lower() in ("quit", "exit", "q"):
            print("Bye.")
            break
        if text.lower() in ("districts", "list"):
            districts = list_districts()
            print(f"Districts ({len(districts)}):")
            for d in districts:
                print(f"  {d}")
            continue

        result = handle_query(text)
        print(result)
        print()


def main() -> int:
    parser = argparse.ArgumentParser(description="Hisaab — MGNREGA transparency CLI")
    parser.add_argument("query", nargs="*", help="Query text (interactive mode if omitted)")
    parser.add_argument("--lang", default="en", choices=["en", "ta", "hi"], help="Language")
    args = parser.parse_args()

    if args.query:
        text = " ".join(args.query)
        print(handle_query(text))
        return 0

    interactive_mode()
    return 0


if __name__ == "__main__":
    sys.exit(main())
