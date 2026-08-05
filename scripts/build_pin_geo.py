"""Build data/curated/pin_geo_all_latest.json from the GeoNames postal dataset.

GeoNames publishes per-locality rows (~155k for India, several per PIN); this
script reduces them to one centroid per distinct 6-digit PIN: the MEDIAN of the
localities' coordinates (robust to the occasional badly-geocoded locality),
plus a spread_km quality signal recording how far the PIN's localities scatter
(rural/island PINs cover large delivery areas).

Source: https://download.geonames.org/export/zip/ (IN.zip) — CC BY 4.0,
attribution "GeoNames" (see DATA_CLAIMS.md CLAIM-2026-0038). The zip is cached
at data/raw/geonames_IN.zip; delete it to force a re-download.

Usage:
    python3 scripts/build_pin_geo.py
"""

from __future__ import annotations

import io
import json
import math
import os
import statistics
import sys
import zipfile
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import requests

ROOT_DIR = Path(__file__).resolve().parent.parent
ZIP_PATH = ROOT_DIR / "data" / "raw" / "geonames_IN.zip"
CURATED_PATH = ROOT_DIR / "data" / "curated" / "pin_geo_all_latest.json"
GEONAMES_URL = "https://download.geonames.org/export/zip/IN.zip"
SOURCE_LABEL = "geonames.org IN.zip, CC BY 4.0"

# GeoNames zip-format columns (tab-separated, no header)
_COL_POSTAL = 1
_COL_LAT = 9
_COL_LNG = 10


def pin_centroid(points: list[tuple[float, float]]) -> tuple[float, float, float]:
    """Return (median lat, median lng, spread_km) for one PIN's localities.

    spread_km approximates the max extent of the locality cloud:
    hypot(dlat, dlng * cos(mean lat)) * 111.
    """
    lats = [p[0] for p in points]
    lngs = [p[1] for p in points]
    lat = statistics.median(lats)
    lng = statistics.median(lngs)
    if len(points) == 1:
        return lat, lng, 0.0
    dlat = max(lats) - min(lats)
    dlng = (max(lngs) - min(lngs)) * math.cos(math.radians(sum(lats) / len(lats)))
    return lat, lng, math.hypot(dlat, dlng) * 111


def _download_zip() -> None:
    if ZIP_PATH.exists() and ZIP_PATH.stat().st_size > 0:
        print(f"  [cache] {ZIP_PATH.name} already present")
        return
    print(f"  Downloading {GEONAMES_URL} ...")
    resp = requests.get(GEONAMES_URL, timeout=60)
    resp.raise_for_status()
    ZIP_PATH.parent.mkdir(parents=True, exist_ok=True)
    ZIP_PATH.write_bytes(resp.content)
    print(f"  Saved {ZIP_PATH.stat().st_size // 1024} KB")


def _parse_localities() -> dict[str, list[tuple[float, float]]]:
    pins: dict[str, list[tuple[float, float]]] = defaultdict(list)
    with zipfile.ZipFile(ZIP_PATH) as zf, zf.open("IN.txt") as raw:
        for line in io.TextIOWrapper(raw, encoding="utf-8"):
            cols = line.rstrip("\n").split("\t")
            if len(cols) <= _COL_LNG:
                continue
            pin = cols[_COL_POSTAL].strip()
            if len(pin) != 6 or not pin.isdigit():
                continue
            try:
                pins[pin].append((float(cols[_COL_LAT]), float(cols[_COL_LNG])))
            except ValueError:
                continue
    return pins


def build() -> int:
    _download_zip()
    pins = _parse_localities()
    print(f"  Distinct PINs: {len(pins)}")

    scraped_at = datetime.now(UTC).isoformat()
    records = []
    for pin in sorted(pins):
        lat, lng, spread = pin_centroid(pins[pin])
        records.append(
            {
                "pin_code": pin,
                "lat": round(lat, 4),
                "lng": round(lng, 4),
                "locality_count": len(pins[pin]),
                "spread_km": round(spread, 1),
                "source": SOURCE_LABEL,
                "scraped_at": scraped_at,
            }
        )

    # A refresh must never reduce coverage (learnings.md 2026-08-04).
    if CURATED_PATH.exists():
        try:
            existing = json.loads(CURATED_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing = []
        if existing and len(records) < len(existing):
            print(
                f"REFUSED: new build has {len(records)} PINs < existing "
                f"{len(existing)} — keeping the existing file."
            )
            return 1

    tmp_path = CURATED_PATH.with_suffix(".json.tmp")
    tmp_path.write_text(
        json.dumps(records, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    os.replace(tmp_path, CURATED_PATH)
    print(f"  Wrote {len(records)} PINs -> {CURATED_PATH.name}")
    return 0


if __name__ == "__main__":
    sys.exit(build())
