"""Scrape Social Audit geography hierarchy (state -> district -> block -> panchayat).

This captures the administrative catalog needed for Hisaab's knowledge base,
without bypassing CAPTCHA or protected report pages.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

BASE = "https://mnregaweb4.nic.in/NregaArch/SocialAudit/"
STATE_LIST_URL = urljoin(BASE, "StateList.aspx")

OUT_DIR = Path("data/catalog")
OUT_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class StateRef:
    state_name: str
    state_id: str
    url: str


class Scraper:
    def __init__(self, timeout_sec: int = 60, sleep_sec: float = 0.2, max_retries: int = 3):
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": "Mozilla/5.0 (compatible; Hisaab/0.3)"})
        self.timeout_sec = timeout_sec
        self.sleep_sec = sleep_sec
        self.max_retries = max_retries

    def _get(self, url: str) -> requests.Response:
        last_err: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                r = self.s.get(url, timeout=self.timeout_sec)
                r.raise_for_status()
                return r
            except Exception as exc:
                last_err = exc
                if attempt < self.max_retries:
                    time.sleep(self.sleep_sec)
        raise RuntimeError(f"GET failed after retries: {url} | {last_err}")

    def _post(self, url: str, data: dict[str, Any]) -> requests.Response:
        last_err: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                r = self.s.post(url, data=data, timeout=self.timeout_sec)
                r.raise_for_status()
                return r
            except Exception as exc:
                last_err = exc
                if attempt < self.max_retries:
                    time.sleep(self.sleep_sec)
        raise RuntimeError(f"POST failed after retries: {url} | {last_err}")

    @staticmethod
    def _soup(html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "html.parser")

    @staticmethod
    def _hidden_fields(soup: BeautifulSoup) -> dict[str, str]:
        out: dict[str, str] = {}
        for name in ["__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION", "ctl00$ContentPlaceHolder1$dynSalt"]:
            el = soup.find("input", {"name": name})
            if el:
                out[name] = el.get("value", "")
        return out

    @staticmethod
    def _select_options(soup: BeautifulSoup, name: str) -> list[tuple[str, str]]:
        sel = soup.find("select", {"name": name})
        if not sel:
            return []
        out: list[tuple[str, str]] = []
        for opt in sel.find_all("option"):
            v = opt.get("value", "").strip()
            t = " ".join(opt.get_text(" ", strip=True).split())
            if not v or v == "0" or t.startswith("[Select"):
                continue
            out.append((v, t))
        return out

    def list_states(self) -> list[StateRef]:
        soup = self._soup(self._get(STATE_LIST_URL).text)
        states: list[StateRef] = []
        for a in soup.find_all("a", href=True):
            h = a["href"]
            if not h.startswith("SA_LoginReport.aspx?id="):
                continue
            state_name = " ".join(a.get_text(" ", strip=True).split())
            state_id = h.split("id=")[-1].strip()
            states.append(StateRef(state_name=state_name, state_id=state_id, url=urljoin(BASE, h)))
        return states

    def _base_payload(
        self, soup: BeautifulSoup, fin_year: str, district: str, block: str, panchayat: str
    ) -> dict[str, str]:
        payload = self._hidden_fields(soup)
        payload.update(
            {
                "__EVENTTARGET": "",
                "__EVENTARGUMENT": "",
                "__LASTFOCUS": "",
                "ctl00$ContentPlaceHolder1$ddlFin": fin_year,
                "ctl00$ContentPlaceHolder1$ddldist": district,
                "ctl00$ContentPlaceHolder1$ddlblock": block,
                "ctl00$ContentPlaceHolder1$ddlpanchayat": panchayat,
            }
        )
        rb = soup.find("input", {"name": "ctl00$ContentPlaceHolder1$rbLoginLevel", "checked": True})
        if rb:
            payload["ctl00$ContentPlaceHolder1$rbLoginLevel"] = rb.get("value", "0")
        return payload

    def scrape_state_hierarchy(self, st: StateRef) -> dict[str, Any]:
        root = self._soup(self._get(st.url).text)
        fin_opts = self._select_options(root, "ctl00$ContentPlaceHolder1$ddlFin")
        fin_year = fin_opts[0][0] if fin_opts else ""
        district_opts = self._select_options(root, "ctl00$ContentPlaceHolder1$ddldist")

        districts: list[dict[str, Any]] = []
        block_total = 0
        panch_total = 0

        for dist_code, dist_name in district_opts:
            p1 = self._base_payload(root, fin_year, dist_code, "0", "0")
            p1["__EVENTTARGET"] = "ctl00$ContentPlaceHolder1$ddldist"
            s_dist = self._soup(self._post(st.url, p1).text)
            block_opts = self._select_options(s_dist, "ctl00$ContentPlaceHolder1$ddlblock")

            blocks: list[dict[str, Any]] = []
            for blk_code, blk_name in block_opts:
                p2 = self._base_payload(s_dist, fin_year, dist_code, blk_code, "0")
                p2["__EVENTTARGET"] = "ctl00$ContentPlaceHolder1$ddlblock"
                s_blk = self._soup(self._post(st.url, p2).text)
                panch_opts = self._select_options(s_blk, "ctl00$ContentPlaceHolder1$ddlpanchayat")

                panchayats = [{"panchayat_code": pc, "panchayat_name": pn} for pc, pn in panch_opts]
                blocks.append(
                    {
                        "block_code": blk_code,
                        "block_name": blk_name,
                        "panchayats": panchayats,
                    }
                )
                panch_total += len(panchayats)
                time.sleep(self.sleep_sec)

            districts.append(
                {
                    "district_code": dist_code,
                    "district_name": dist_name,
                    "blocks": blocks,
                }
            )
            block_total += len(blocks)
            time.sleep(self.sleep_sec)

        return {
            "state_id": st.state_id,
            "state_name": st.state_name,
            "state_url": st.url,
            "financial_year_default": fin_year,
            "districts": districts,
            "counts": {
                "districts": len(districts),
                "blocks": block_total,
                "panchayats": panch_total,
            },
        }


def main() -> int:
    ap = argparse.ArgumentParser(description="Scrape Social Audit geography hierarchy")
    ap.add_argument("--limit", type=int, default=0, help="Process first N states (0=all)")
    ap.add_argument("--sleep-sec", type=float, default=0.2)
    ap.add_argument("--timeout-sec", type=int, default=60)
    args = ap.parse_args()

    sc = Scraper(timeout_sec=args.timeout_sec, sleep_sec=args.sleep_sec)
    states = sc.list_states()
    if args.limit > 0:
        states = states[: args.limit]

    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    all_out: list[dict[str, Any]] = []
    summary: list[dict[str, Any]] = []

    for i, st in enumerate(states, start=1):
        try:
            info = sc.scrape_state_hierarchy(st)
            all_out.append(info)
            c = info["counts"]
            summary.append({"state": st.state_name, **c})
            print(
                f"[{i:02d}/{len(states)}] {st.state_name}: districts={c['districts']} blocks={c['blocks']} panchayats={c['panchayats']}"
            )
        except Exception as exc:
            print(f"[{i:02d}/{len(states)}] {st.state_name}: ERROR {exc}")
            summary.append({"state": st.state_name, "error": str(exc)})

    out_full = OUT_DIR / f"hierarchy_{ts}.json"
    out_latest = OUT_DIR / "hierarchy_latest.json"
    out_summary = OUT_DIR / f"hierarchy_summary_{ts}.json"
    out_summary_latest = OUT_DIR / "hierarchy_summary_latest.json"

    out_full.write_text(json.dumps(all_out, ensure_ascii=False, indent=2), encoding="utf-8")
    out_latest.write_text(json.dumps(all_out, ensure_ascii=False, indent=2), encoding="utf-8")
    out_summary.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    out_summary_latest.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    totals = {
        "states": len([x for x in all_out]),
        "districts": sum(x.get("counts", {}).get("districts", 0) for x in all_out),
        "blocks": sum(x.get("counts", {}).get("blocks", 0) for x in all_out),
        "panchayats": sum(x.get("counts", {}).get("panchayats", 0) for x in all_out),
    }

    print("\nHierarchy scrape outcome")
    print(f"- States:     {totals['states']}")
    print(f"- Districts:  {totals['districts']}")
    print(f"- Blocks:     {totals['blocks']}")
    print(f"- Panchayats: {totals['panchayats']}")
    print(f"- Full:       {out_full}")
    print(f"- Summary:    {out_summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
