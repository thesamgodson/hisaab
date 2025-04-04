"""Scrape Social Audit geography catalog (state -> districts) from NregaArch pages."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE = "https://mnregaweb4.nic.in/NregaArch/SocialAudit/"
STATE_LIST = urljoin(BASE, "StateList.aspx")

OUT_DIR = Path("data/catalog")
OUT_DIR.mkdir(parents=True, exist_ok=True)


session = requests.Session()
session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; Hisaab/0.2)"})


def parse_states() -> list[dict]:
    r = session.get(STATE_LIST, timeout=60)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    states = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href.startswith("SA_LoginReport.aspx?id="):
            continue
        state_name = " ".join(a.get_text(" ", strip=True).split())
        m = re.search(r"id=(\d+)", href)
        if not m:
            continue
        state_id = m.group(1)
        states.append(
            {
                "state_name": state_name,
                "state_id": state_id,
                "url": urljoin(BASE, href),
            }
        )
    return states


def parse_districts(state: dict) -> list[dict]:
    r = session.get(state["url"], timeout=60)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    sel = soup.find("select", {"name": "ctl00$ContentPlaceHolder1$ddldist"})
    if not sel:
        return []

    rows: list[dict] = []
    for opt in sel.find_all("option"):
        value = opt.get("value", "").strip()
        name = " ".join(opt.get_text(" ", strip=True).split())
        if not value or value == "0" or name.startswith("[Select"):
            continue
        rows.append(
            {
                "state_id": state["state_id"],
                "state_name": state["state_name"],
                "district_code": value,
                "district_name": name,
            }
        )
    return rows


def main() -> int:
    states = parse_states()
    all_districts: list[dict] = []

    for i, st in enumerate(states, start=1):
        d = parse_districts(st)
        all_districts.extend(d)
        print(f"[{i:02d}/{len(states)}] {st['state_name']}: districts={len(d)}")

    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    states_path = OUT_DIR / f"states_{ts}.json"
    dists_path = OUT_DIR / f"districts_{ts}.json"
    latest_states = OUT_DIR / "states_latest.json"
    latest_dists = OUT_DIR / "districts_latest.json"

    states_path.write_text(json.dumps(states, ensure_ascii=False, indent=2), encoding="utf-8")
    dists_path.write_text(json.dumps(all_districts, ensure_ascii=False, indent=2), encoding="utf-8")
    latest_states.write_text(json.dumps(states, ensure_ascii=False, indent=2), encoding="utf-8")
    latest_dists.write_text(json.dumps(all_districts, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nCatalog scrape outcome")
    print(f"- States:    {len(states)}")
    print(f"- Districts: {len(all_districts)}")
    print(f"- States file:    {states_path}")
    print(f"- Districts file: {dists_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
