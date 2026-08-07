"""Build simplified district TopoJSON from raw GeoJSON.

Downloads the India district GeoJSON from datta07/INDIAN-SHAPEFILES,
simplifies geometry, normalizes district names, and outputs a ~3-5MB
TopoJSON file for the frontend choropleth map.

Usage:
    python scripts/build_geodata.py
    python scripts/build_geodata.py --skip-download  # Use cached GeoJSON
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.normalize_districts import normalize_district  # noqa: E402
from db.normalize_states import normalize_state  # noqa: E402

RAW_DIR = PROJECT_ROOT / "data" / "raw"
OUTPUT = PROJECT_ROOT / "web" / "public" / "india-districts.topojson"

GEOJSON_URL = (
    "https://raw.githubusercontent.com/datta07/INDIAN-SHAPEFILES"
    "/master/INDIA/INDIA_DISTRICTS.geojson"
)
RAW_GEOJSON = RAW_DIR / "INDIA_DISTRICTS.geojson"
CLEANED_GEOJSON = RAW_DIR / "india_districts_cleaned.geojson"


def download_geojson() -> None:
    """Download district GeoJSON if not cached."""
    if RAW_GEOJSON.exists():
        size_mb = RAW_GEOJSON.stat().st_size / 1e6
        print(f"Using cached {RAW_GEOJSON} ({size_mb:.1f}MB)")
        return

    print("Downloading district GeoJSON (~74MB)...")
    try:
        import requests
    except ImportError:
        print("ERROR: requests not installed. Run: pip install requests", file=sys.stderr)
        sys.exit(1)

    try:
        resp = requests.get(GEOJSON_URL, stream=True, timeout=120)
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"ERROR: Download failed: {exc}", file=sys.stderr)
        print(f"  URL: {GEOJSON_URL}", file=sys.stderr)
        print("  Check your internet connection and try again.", file=sys.stderr)
        sys.exit(1)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    downloaded = 0
    with open(RAW_GEOJSON, "wb") as f:
        for chunk in resp.iter_content(chunk_size=65536):
            f.write(chunk)
            downloaded += len(chunk)
            if downloaded % (5 * 1024 * 1024) < 65536:
                print(f"  {downloaded / 1e6:.0f}MB downloaded...")

    print(f"Downloaded {RAW_GEOJSON.stat().st_size / 1e6:.1f}MB → {RAW_GEOJSON}")


def normalize_properties() -> Path:
    """Load GeoJSON, normalize district/state names, strip extra fields."""
    print("Normalizing properties...")

    with open(RAW_GEOJSON, encoding="utf-8") as f:
        data = json.load(f)

    if data.get("type") != "FeatureCollection":
        print(f"ERROR: Expected FeatureCollection, got {data.get('type')}", file=sys.stderr)
        sys.exit(1)

    features = data.get("features", [])
    if not features:
        print("ERROR: No features found in GeoJSON.", file=sys.stderr)
        sys.exit(1)

    # Inspect first feature to understand property keys
    sample_props = features[0].get("properties", {}) if features else {}
    print(f"  Sample property keys: {list(sample_props.keys())[:10]}")

    cleaned_count = 0
    empty_district = 0

    for feature in features:
        props = feature.get("properties") or {}

        # Try multiple possible key names (case-insensitive lookup)
        district = ""
        state = ""
        for key, val in props.items():
            key_lower = key.lower()
            if key_lower in ("district", "dtname", "district_n", "dt_name", "name") and not district:
                district = str(val or "").strip().upper()
            if key_lower in ("state", "stname", "state_name", "st_name") and not state:
                state = str(val or "").strip().upper()

        state = normalize_state(state)
        district = normalize_district(district, state)
        feature["properties"] = {"district": district, "state": state}
        if not district:
            empty_district += 1
        cleaned_count += 1

    if empty_district > 0:
        print(f"  WARNING: {empty_district} features have no district name")

    cleaned = CLEANED_GEOJSON
    with open(cleaned, "w", encoding="utf-8") as f:
        json.dump(data, f)

    size_mb = cleaned.stat().st_size / 1e6
    print(f"  Cleaned: {cleaned_count} features, {size_mb:.1f}MB → {cleaned}")
    return cleaned


def _simplify_mapshaper(cleaned_path: Path) -> bool:
    """Attempt simplification via mapshaper (best quality). Returns True on success."""
    print("Trying mapshaper simplification...")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    try:
        result = subprocess.run(
            [
                "npx", "-y", "mapshaper",
                str(cleaned_path),
                "-simplify", "dp", "15%", "keep-shapes",
                "-o", "format=topojson", str(OUTPUT),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=180,
        )
        if result.stdout:
            print(f"  mapshaper: {result.stdout.strip()}")
        size_mb = OUTPUT.stat().st_size / 1e6
        print(f"  TopoJSON (mapshaper): {size_mb:.1f}MB → {OUTPUT}")
        return True

    except subprocess.TimeoutExpired:
        print("  mapshaper timed out after 3 minutes.")
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else ""
        print(f"  mapshaper failed: {stderr[:200]}")
    except FileNotFoundError:
        print("  npx/mapshaper not found.")

    return False


def _simplify_python(cleaned_path: Path) -> bool:
    """Fallback: Python topojson library. Returns True on success."""
    print("Trying Python topojson library...")
    try:
        import topojson as tp  # type: ignore[import]
    except ImportError:
        print("  topojson package not installed. Run: pip install topojson")
        return False

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(cleaned_path, encoding="utf-8") as f:
            data = json.load(f)

        # toposimplify=0.001 gives ~3-5MB output
        topo = tp.Topology(data, toposimplify=0.001, presimplify=False)
        topo_json = topo.to_json()

        with open(OUTPUT, "w", encoding="utf-8") as f:
            f.write(topo_json)

        size_mb = OUTPUT.stat().st_size / 1e6
        print(f"  TopoJSON (Python): {size_mb:.1f}MB → {OUTPUT}")
        return True

    except Exception as exc:  # noqa: BLE001
        print(f"  Python topojson failed: {exc}")

    return False


def _convert_raw_topojson(cleaned_path: Path) -> bool:
    """Last resort: convert GeoJSON to TopoJSON without simplification."""
    print("WARNING: No simplification available — converting raw GeoJSON to TopoJSON.")
    print("  Output may be large (>20MB). Install mapshaper or topojson for better results.")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with open(cleaned_path, encoding="utf-8") as f:
        data = json.load(f)

    # Minimal TopoJSON structure: wrap FeatureCollection as an object
    topo = {
        "type": "Topology",
        "objects": {
            "india_districts": {
                "type": "GeometryCollection",
                "geometries": [],
            }
        },
        "arcs": [],
        "transform": {"scale": [1, 1], "translate": [0, 0]},
    }

    # Without arc deduplication, just embed geometry directly
    geometries = []
    for feature in data.get("features", []):
        geom = feature.get("geometry") or {}
        props = feature.get("properties") or {}
        geometries.append({
            "type": geom.get("type"),
            "coordinates": geom.get("coordinates"),
            "properties": props,
        })

    topo["objects"]["india_districts"]["geometries"] = geometries

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(topo, f)

    size_mb = OUTPUT.stat().st_size / 1e6
    print(f"  TopoJSON (raw): {size_mb:.1f}MB → {OUTPUT}")
    return True


def simplify_to_topojson(cleaned_path: Path) -> None:
    """Simplify and convert to TopoJSON, trying multiple strategies."""
    if _simplify_mapshaper(cleaned_path):
        return
    if _simplify_python(cleaned_path):
        return
    # Last resort — still produces a valid file
    _convert_raw_topojson(cleaned_path)


def validate() -> None:
    """Check output file exists and has expected structure."""
    if not OUTPUT.exists():
        print(f"ERROR: Output file not found: {OUTPUT}", file=sys.stderr)
        sys.exit(1)

    with open(OUTPUT, encoding="utf-8") as f:
        data = json.load(f)

    topo_type = data.get("type")
    if topo_type != "Topology":
        print(f"WARNING: Expected type=Topology, got {topo_type!r}")

    objects = data.get("objects", {})
    if not objects:
        print("WARNING: No objects in TopoJSON")
        return

    layer_name = next(iter(objects))
    layer = objects[layer_name]
    geometries = layer.get("geometries", [])
    print(f"Validation: layer={layer_name!r}, {len(geometries)} geometries")

    missing_district = [
        g for g in geometries
        if not (g.get("properties") or {}).get("district")
    ]
    if missing_district:
        print(f"  WARNING: {len(missing_district)} geometries missing district name")

    states = {
        (g.get("properties") or {}).get("state", "")
        for g in geometries
    }
    states.discard("")
    print(f"  States/UTs found: {len(states)}")

    size_mb = OUTPUT.stat().st_size / 1e6
    if size_mb > 10:
        print(f"  WARNING: Output is {size_mb:.1f}MB — consider more aggressive simplification")
    else:
        print(f"  Output size: {size_mb:.1f}MB — OK")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build simplified district TopoJSON for Hisaab frontend."
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip download and use cached GeoJSON in data/raw/",
    )
    args = parser.parse_args()

    if not args.skip_download:
        download_geojson()
    elif not RAW_GEOJSON.exists():
        print(
            f"ERROR: --skip-download specified but {RAW_GEOJSON} not found.",
            file=sys.stderr,
        )
        sys.exit(1)

    cleaned = normalize_properties()
    simplify_to_topojson(cleaned)
    validate()
    print(f"\nDone! Output: {OUTPUT}")


if __name__ == "__main__":
    main()
