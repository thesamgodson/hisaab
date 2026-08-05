"""Generate web/src/lib/pc-name-registry.ts from constituency/pc_name_registry.py.

The Python module is the single source of truth (entries carry per-seat
verification comments there). The web build cannot import Python, so the
mapping is emitted as a checked-in TS module; tests/test_pc_name_registry.py
fails whenever the two drift.

Usage:
    python3 scripts/gen_pc_name_registry.py            # write the TS file
    python3 scripts/gen_pc_name_registry.py --check    # exit 1 on drift
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from constituency.pc_name_registry import PC_NAME_REGISTRY  # noqa: E402

TS_PATH = _PROJECT_ROOT / "web" / "src" / "lib" / "pc-name-registry.ts"


def render_ts() -> str:
    by_state: dict[str, dict[str, str]] = {}
    for (state, variant), canon in PC_NAME_REGISTRY.items():
        by_state.setdefault(state, {})[variant] = canon

    lines = [
        "// GENERATED FILE — do not edit.",
        "// Source of truth: constituency/pc_name_registry.py (per-seat verification",
        "// comments live there; see DATA_CLAIMS.md CLAIM-2026-0036).",
        "// Regenerate: python3 scripts/gen_pc_name_registry.py",
        "",
        "/** State-scoped PC-name variants -> canonical 2024 seat name. */",
        "export const PC_NAME_REGISTRY: Record<string, Record<string, string>> = {",
    ]
    for state in sorted(by_state):
        lines.append(f"  {json.dumps(state)}: {{")
        for variant in sorted(by_state[state]):
            lines.append(f"    {json.dumps(variant)}: {json.dumps(by_state[state][variant])},")
        lines.append("  },")
    lines.append("};")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    rendered = render_ts()
    if "--check" in sys.argv:
        current = TS_PATH.read_text() if TS_PATH.exists() else ""
        if current != rendered:
            print(f"DRIFT: {TS_PATH} is stale — run python3 scripts/gen_pc_name_registry.py")
            return 1
        print(f"OK: {TS_PATH} matches the Python registry")
        return 0
    TS_PATH.write_text(rendered)
    print(f"Wrote {TS_PATH} ({len(PC_NAME_REGISTRY)} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
