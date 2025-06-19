"""Scrape hierarchy for a single state from NregaArch Social Audit page."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime

from scrapers.scrape_geo_hierarchy import OUT_DIR, Scraper


def main() -> int:
    ap = argparse.ArgumentParser(description="Scrape hierarchy for one state")
    ap.add_argument("--state", required=True, help="State name contains match, e.g. 'TAMIL NADU'")
    ap.add_argument("--sleep-sec", type=float, default=0.0)
    ap.add_argument("--timeout-sec", type=int, default=30)
    args = ap.parse_args()

    sc = Scraper(timeout_sec=args.timeout_sec, sleep_sec=args.sleep_sec)
    states = sc.list_states()

    needle = args.state.strip().lower()
    matches = [s for s in states if needle in s.state_name.lower()]
    if not matches:
        print(f"No state matched: {args.state}")
        return 1

    st = matches[0]
    info = sc.scrape_state_hierarchy(st)

    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    slug = st.state_name.lower().replace(" ", "-")
    out = OUT_DIR / f"hierarchy_{slug}_{ts}.json"
    out_latest = OUT_DIR / f"hierarchy_{slug}_latest.json"

    out.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    out_latest.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")

    c = info["counts"]
    print("State hierarchy scrape outcome")
    print(f"- State:      {st.state_name}")
    print(f"- Districts:  {c['districts']}")
    print(f"- Blocks:     {c['blocks']}")
    print(f"- Panchayats: {c['panchayats']}")
    print(f"- File:       {out}")
    print(f"- Latest:     {out_latest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
