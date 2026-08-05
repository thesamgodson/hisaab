"""pin_geo: builder centroid math, loader validation, real-DB acceptance."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "hisaab.db"

sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from build_pin_geo import pin_centroid  # noqa: E402

from db import init_db  # noqa: E402
from db.loaders import load_pin_geo  # noqa: E402


class TestPinCentroid:
    def test_single_locality_zero_spread(self):
        lat, lng, spread = pin_centroid([(28.6, 77.2)])
        assert (lat, lng, spread) == (28.6, 77.2, 0.0)

    def test_median_resists_one_bad_geocode(self):
        # Two localities agree; the third is ~550km off (bad geocode).
        pts = [(28.60, 77.20), (28.62, 77.22), (23.60, 77.21)]
        lat, lng, spread = pin_centroid(pts)
        assert abs(lat - 28.60) < 0.03 and abs(lng - 77.21) < 0.03
        assert spread > 500  # the outlier is still visible in the quality signal

    def test_spread_is_kilometre_scaled(self):
        # ~0.01 deg apart at the equatorish latitude ≈ 1.5km extent
        _, _, spread = pin_centroid([(10.00, 76.00), (10.01, 76.01)])
        assert 1.0 < spread < 2.5


class TestLoadPinGeo:
    @pytest.fixture()
    def conn(self):
        conn = sqlite3.connect(":memory:")
        init_db(conn)
        yield conn
        conn.close()

    def test_round_trip(self, conn):
        records = [
            {"pin_code": "110001", "lat": 28.6431, "lng": 77.2197,
             "locality_count": 21, "spread_km": 0.8,
             "source": "geonames.org IN.zip, CC BY 4.0", "scraped_at": "2026-08-05T00:00:00Z"},
        ]
        assert load_pin_geo(conn, records, "2024-2025") == 1
        row = conn.execute(
            "SELECT lat, lng, locality_count FROM pin_geo WHERE pin_code='110001'"
        ).fetchone()
        assert row == (28.6431, 77.2197, 21)

    def test_rejects_bad_pins_and_out_of_india_coords(self, conn):
        records = [
            {"pin_code": "1101", "lat": 28.6, "lng": 77.2},          # short pin
            {"pin_code": "ABC123", "lat": 28.6, "lng": 77.2},        # non-numeric
            {"pin_code": "110002", "lat": 51.5, "lng": -0.1},        # London
            {"pin_code": "110003", "lat": None, "lng": 77.2},        # missing lat
            {"pin_code": "110004", "lat": 28.6, "lng": 77.2},        # valid
        ]
        assert load_pin_geo(conn, records, "2024-2025") == 1
        pins = [r[0] for r in conn.execute("SELECT pin_code FROM pin_geo")]
        assert pins == ["110004"]


class TestDbAcceptance:
    @pytest.fixture(scope="class")
    def db(self):
        if not DB_PATH.exists():
            pytest.skip(f"Database not found at {DB_PATH}")
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        yield conn
        conn.close()

    def _ready(self, db) -> bool:
        try:
            return db.execute("SELECT COUNT(*) FROM pin_geo").fetchone()[0] > 0
        except sqlite3.OperationalError:
            return False

    def test_row_count_and_directory_coverage(self, db):
        if not self._ready(db):
            pytest.skip("pin_geo empty (CI before curated file lands, or unloaded)")
        n = db.execute("SELECT COUNT(*) FROM pin_geo").fetchone()[0]
        assert n >= 19000
        covered = db.execute(
            "SELECT COUNT(*) FROM pin_district_mapping p "
            "WHERE EXISTS (SELECT 1 FROM pin_geo g WHERE g.pin_code = p.pin_code)"
        ).fetchone()[0]
        total = db.execute("SELECT COUNT(*) FROM pin_district_mapping").fetchone()[0]
        if total:
            assert covered / total >= 0.97

    def test_all_rows_inside_india_bbox(self, db):
        if not self._ready(db):
            pytest.skip("pin_geo empty (CI before curated file lands, or unloaded)")
        out = db.execute(
            "SELECT COUNT(*) FROM pin_geo "
            "WHERE lat < 6 OR lat > 38 OR lng < 68 OR lng > 98"
        ).fetchone()[0]
        assert out == 0
