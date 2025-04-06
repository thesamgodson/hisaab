"""Data completeness audit for Hisaab database.

Inspects every table, counts rows and distinct states, and checks each
numeric column for non-zero population.  Columns that are 100% zero are
flagged as HOLLOW.

Usage:
    python3 data_audit.py          # human-readable table
    python3 data_audit.py --json   # machine-readable JSON to stdout
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "data" / "hisaab.db"

AUDIT_TABLES = (
    "misappropriation",
    "financial_statement",
    "fto_status",
    "fto_pendency",
    "issues_reported",
    "pmgsy_progress",
    "pmgsy_district",
    "pmayg_district",
    "pmkisan_district",
    "jjm_district",
    "pmposhan_district",
    "nsap_district",
    "nfsa_district",
)

NUMERIC_TYPES = {"INTEGER", "REAL"}
SKIP_COLUMNS = {"id", "is_total", "amounts_in_lakhs"}


def _get_numeric_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    """Return column names whose declared type is numeric."""
    cur = conn.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cur.fetchall() if row[2].upper() in NUMERIC_TYPES and row[1] not in SKIP_COLUMNS]


def _audit_table(conn: sqlite3.Connection, table: str) -> dict:
    """Audit a single table: row count, states, per-column zero analysis."""
    total_rows = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    distinct_states = conn.execute(f"SELECT COUNT(DISTINCT state) FROM {table}").fetchone()[0]

    numeric_cols = _get_numeric_columns(conn, table)
    columns: list[dict] = []

    for col in numeric_cols:
        non_zero = conn.execute(f"SELECT COUNT(*) FROM {table} WHERE {col} != 0").fetchone()[0]
        pct = round(non_zero / total_rows * 100, 1) if total_rows > 0 else 0.0
        columns.append(
            {
                "column": col,
                "non_zero_rows": non_zero,
                "total_rows": total_rows,
                "pct_non_zero": pct,
                "status": "HOLLOW" if pct == 0.0 and total_rows > 0 else "OK",
            }
        )

    return {
        "table": table,
        "total_rows": total_rows,
        "distinct_states": distinct_states,
        "columns": columns,
    }


def run_audit(db_path: Path) -> dict:
    """Run the full audit and return a structured report."""
    conn = sqlite3.connect(str(db_path))
    try:
        tables = [_audit_table(conn, t) for t in AUDIT_TABLES]
    finally:
        conn.close()

    hollow_list: list[str] = []
    total_columns = 0
    hollow_count = 0

    for t in tables:
        for c in t["columns"]:
            total_columns += 1
            if c["status"] == "HOLLOW":
                hollow_count += 1
                hollow_list.append(f"{c['column']} ({t['table']})")

    return {
        "db_path": str(db_path),
        "tables": tables,
        "summary": {
            "total_numeric_columns": total_columns,
            "columns_with_data": total_columns - hollow_count,
            "hollow_columns": hollow_count,
            "hollow_list": hollow_list,
        },
    }


def _print_human(report: dict) -> None:
    """Print a human-readable table to stdout."""
    sep = "-" * 90
    print(f"\nData Completeness Audit: {report['db_path']}\n{sep}")

    for t in report["tables"]:
        print(f"\n  {t['table']}  ({t['total_rows']} rows, {t['distinct_states']} states)")
        if not t["columns"]:
            print("    (no numeric columns)")
            continue
        print(f"    {'Column':<35} {'Non-Zero':>10} {'Total':>10} {'%':>7}  Status")
        print(f"    {'-' * 35} {'-' * 10} {'-' * 10} {'-' * 7}  {'-' * 6}")
        for c in t["columns"]:
            status_marker = " ** HOLLOW **" if c["status"] == "HOLLOW" else ""
            print(
                f"    {c['column']:<35} {c['non_zero_rows']:>10} "
                f"{c['total_rows']:>10} {c['pct_non_zero']:>6.1f}%{status_marker}"
            )

    s = report["summary"]
    print(f"\n{sep}")
    print(
        f"Summary: {s['columns_with_data']}/{s['total_numeric_columns']} columns have "
        f"real data, {s['hollow_columns']} columns are HOLLOW"
    )
    if s["hollow_list"]:
        print("Hollow columns:")
        for h in s["hollow_list"]:
            print(f"  - {h}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Hisaab data completeness audit")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of table")
    parser.add_argument("--db", type=Path, default=DB_PATH, help="Path to database")
    args = parser.parse_args()

    if not args.db.exists():
        print(f"Error: database not found at {args.db}", file=sys.stderr)
        sys.exit(1)

    report = run_audit(args.db)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        _print_human(report)


if __name__ == "__main__":
    main()
