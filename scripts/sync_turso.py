"""Publish the local SQLite database to Turso (production).

THE missing link that broke prod in March 2026: data/hisaab.db evolved
locally while Turso held a hand-pushed snapshot — new tables (PIN mapping)
never arrived and the live PIN flow 500'd for months.

This script makes publishing repeatable:
  1. mirrors every table + index + view from data/hisaab.db to Turso
     (per-table transactional drop/create/insert — readers never see a
     half-written table)
  2. verifies remote row counts against local before declaring success

Usage:
    python3 scripts/sync_turso.py                # uses TURSO_* env vars
    python3 scripts/sync_turso.py --env-file web/.env.local
    python3 scripts/sync_turso.py --dry-run      # print plan, touch nothing

Credentials (never printed):
    TURSO_DATABASE_URL   libsql://... or https://...
    TURSO_AUTH_TOKEN     database auth token
Pull them from Vercel with:  cd web && vercel env pull .env.local
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from db.connection import DB_PATH  # noqa: E402

INSERT_CHUNK = 200  # rows per multi-value INSERT statement
BATCH_STATEMENTS = 40  # statements per libsql HTTP batch


def _load_env_file(path: Path) -> None:
    """Minimal .env parser — sets os.environ without echoing values."""
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _local_objects(conn: sqlite3.Connection) -> tuple[list[tuple[str, str]], list[str]]:
    """Return ([(table_name, create_sql)], [other_create_sqls]) from sqlite_master."""
    tables = conn.execute(
        """SELECT name, sql FROM sqlite_master
           WHERE type = 'table' AND name NOT LIKE 'sqlite_%' AND sql IS NOT NULL
           ORDER BY name"""
    ).fetchall()
    extras = conn.execute(
        """SELECT sql FROM sqlite_master
           WHERE type IN ('index', 'view') AND sql IS NOT NULL
           ORDER BY CASE type WHEN 'index' THEN 0 ELSE 1 END, name"""
    ).fetchall()
    return [(r[0], r[1]) for r in tables], [r[0] for r in extras]


def _quote(value: object) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, bytes):
        return "X'" + value.hex() + "'"
    return "'" + str(value).replace("'", "''") + "'"


def _table_statements(
    conn: sqlite3.Connection, name: str, create_sql: str
) -> list[str]:
    """DROP + CREATE + chunked multi-value INSERTs for one table."""
    stmts = [f"DROP TABLE IF EXISTS {name}", create_sql]
    cur = conn.execute(f"SELECT * FROM {name}")
    columns = [d[0] for d in cur.description]
    col_list = ", ".join(columns)
    while True:
        rows = cur.fetchmany(INSERT_CHUNK)
        if not rows:
            break
        values = ",\n".join(
            "(" + ", ".join(_quote(v) for v in row) + ")" for row in rows
        )
        stmts.append(f"INSERT INTO {name} ({col_list}) VALUES\n{values}")
    return stmts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, help="read TURSO_* from a .env file")
    parser.add_argument("--db", type=Path, default=DB_PATH, help="local SQLite path")
    parser.add_argument("--dry-run", action="store_true", help="plan only, no writes")
    args = parser.parse_args()

    if args.env_file:
        _load_env_file(args.env_file)

    url = os.environ.get("TURSO_DATABASE_URL", "")
    token = os.environ.get("TURSO_AUTH_TOKEN", "")
    if not args.dry_run and (not url or not token):
        print("ERROR: TURSO_DATABASE_URL / TURSO_AUTH_TOKEN not set.")
        print("Pull them with:  cd web && vercel env pull .env.local")
        print("Then run:        python3 scripts/sync_turso.py --env-file web/.env.local")
        return 2

    if not args.db.exists():
        print(f"ERROR: local DB not found at {args.db}")
        return 2

    local = sqlite3.connect(args.db)
    tables, extras = _local_objects(local)

    plan = [(name, local.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0])
            for name, _ in tables]
    total_rows = sum(n for _, n in plan)
    print(f"Sync plan: {len(tables)} tables, {total_rows:,} rows, "
          f"{len(extras)} indexes/views -> Turso")
    for name, n in plan:
        print(f"  {name}: {n:,}")
    if args.dry_run:
        return 0

    import libsql_client

    client = libsql_client.create_client_sync(
        url=url.replace("libsql://", "https://"), auth_token=token
    )

    def _with_retry(fn, what: str, attempts: int = 4):
        """Turso over HTTP throws transient errors under bursty writes —
        retry with backoff before giving up."""
        for attempt in range(1, attempts + 1):
            try:
                return fn()
            except Exception as exc:
                if "already exists" in str(exc):
                    return None
                if attempt == attempts:
                    raise
                wait = 2.0 * attempt
                print(f"  retry {attempt}/{attempts - 1} for {what} in {wait:.0f}s ({type(exc).__name__})")
                time.sleep(wait)

    local_counts = dict(plan)
    skipped: list[str] = []

    try:
        for name, create_sql in tables:
            # Never replace a populated remote table with an empty local one.
            # This is the March-2026 disaster class: a from-scratch DB build
            # that didn't re-seed a table (e.g. pin_district_mapping when the
            # refresh only ran --mla-only) would otherwise DROP+recreate it
            # empty on prod and 500 the PIN flow. Empty-both is fine to push.
            if local_counts[name] == 0:
                remote_existing = _with_retry(
                    lambda n=name: client.execute(
                        f"SELECT COUNT(*) FROM {n}"
                    ).rows[0][0],
                    f"{name} remote count",
                )
                if remote_existing:
                    print(f"  SKIP {name}: local empty, remote has {remote_existing:,} rows — kept")
                    skipped.append(name)
                    continue

            stmts = _table_statements(local, name, create_sql)
            # One transactional batch per table when small enough; otherwise
            # chunked batches (first batch carries DROP+CREATE).
            for i in range(0, len(stmts), BATCH_STATEMENTS):
                chunk = stmts[i : i + BATCH_STATEMENTS]
                _with_retry(lambda c=chunk: client.batch(c), f"{name} batch {i // BATCH_STATEMENTS}")
            print(f"  pushed {name}")

        # Indexes and views — drop views first; duplicate indexes are fine
        for sql in extras:
            if sql.upper().startswith("CREATE VIEW"):
                view_name = sql.split()[2]
                _with_retry(
                    lambda s=sql, v=view_name: client.batch(
                        [f"DROP VIEW IF EXISTS {v}", s]
                    ),
                    f"view {view_name}",
                )
            else:
                _with_retry(lambda s=sql: client.execute(s), "index")
        print(f"  pushed {len(extras)} indexes/views")

        # Verify
        print("\nVerification (local vs remote):")
        mismatches = 0
        for name, local_count in plan:
            remote = client.execute(f"SELECT COUNT(*) FROM {name}").rows[0][0]
            if name in skipped:
                # Intentionally not overwritten — prod kept its rows.
                print(f"  {name}: {local_count:,} / {remote:,}  KEPT (local empty)")
                continue
            status = "OK" if remote == local_count else "MISMATCH"
            if remote != local_count:
                mismatches += 1
            print(f"  {name}: {local_count:,} / {remote:,}  {status}")

        if mismatches:
            print(f"\nFAILED: {mismatches} table(s) mismatched")
            return 1
        print(f"\nSync complete: {len(tables)} tables, {total_rows:,} rows verified.")
        return 0
    finally:
        client.close()
        local.close()


if __name__ == "__main__":
    sys.exit(main())
