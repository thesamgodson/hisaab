"""Generate an evidence-first corruption watchlist from latest curated JSON files."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

CURATED_DIR = Path("data/curated")
REPORTS_DIR = Path("reports")


def read_latest_files() -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    file_count = 0
    for fp in sorted(CURATED_DIR.glob("misappropriation_*_latest.json")):
        file_count += 1
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
            if isinstance(data, list):
                rows.extend(data)
        except Exception:
            continue
    return rows, file_count


def fmt_inr(v: float) -> str:
    return f"₹{v:,.0f}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate public watchlist report")
    parser.add_argument("--top", type=int, default=100)
    args = parser.parse_args()

    rows, file_count = read_latest_files()
    if file_count == 0:
        print("No curated latest files found in data/curated/")
        return 1
    if not rows:
        print(f"Curated files found: {file_count}, but all are empty (no parsed rows yet).")
        return 2

    filtered = [r for r in rows if float(r.get("amount_unrecovered", 0)) > 0]
    sorted_rows = sorted(filtered, key=lambda r: float(r.get("amount_unrecovered", 0)), reverse=True)
    top = sorted_rows[: args.top]

    total_unrecovered = sum(float(r.get("amount_unrecovered", 0)) for r in sorted_rows)

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    json_path = REPORTS_DIR / f"watchlist_{ts}.json"
    md_path = REPORTS_DIR / f"watchlist_{ts}.md"

    json_path.write_text(json.dumps(top, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Hisaab Watchlist",
        "",
        f"Generated (UTC): {datetime.now(UTC).isoformat()}",
        f"Total districts with unrecovered amount: {len(sorted_rows)}",
        f"Total unrecovered amount (current dataset): {fmt_inr(total_unrecovered)}",
        "",
        "## Top Districts by Unrecovered Amount",
        "",
        "| Rank | State | District | Amount Unrecovered | Recovery Rate |",
        "|---|---|---|---:|---:|",
    ]
    for i, r in enumerate(top, start=1):
        lines.append(
            f"| {i} | {r.get('state', '')} | {r.get('district', '')} | "
            f"{fmt_inr(float(r.get('amount_unrecovered', 0)))} | {r.get('recovery_rate_pct', 0)}% |"
        )

    lines += [
        "",
        "## Transparency Note",
        "- This report is based only on publicly available portal data and parser outputs.",
        "- Treat this as a lead list for further verification, not a legal accusation against individuals.",
    ]

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("Watchlist generated")
    print(f"- JSON: {json_path}")
    print(f"- MD:   {md_path}")
    print(f"- Rows: {len(top)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
