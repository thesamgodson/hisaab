import { type NextRequest } from "next/server";
import { query, queryOne } from "@/lib/db";

// POST { lat, lng } -> nearest PIN (GeoNames centroids in pin_geo, CC BY 4.0)
// + its district/state from the postal directory.
//
// Privacy contract (DATA_CLAIMS CLAIM-2026-0038): coordinates are processed
// transiently for this one lookup. POST body — never GET query params — so
// coordinates cannot land in request logs; nothing is written anywhere; the
// response is uncacheable. Do not add logging to this route.

interface PinGeoRow {
  pin_code: string;
  lat: number;
  lng: number;
  spread_km: number | null;
}

const INDIA_BOUNDS = { latMin: 6, latMax: 38, lngMin: 68, lngMax: 98 };

function haversineKm(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const rad = Math.PI / 180;
  const dLat = (lat2 - lat1) * rad;
  const dLng = (lng2 - lng1) * rad;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(dLng / 2) ** 2;
  return 6371 * 2 * Math.asin(Math.sqrt(a));
}

async function candidatesWithin(lat: number, lng: number, windowDeg: number) {
  const lngWindow = windowDeg / Math.max(Math.cos((lat * Math.PI) / 180), 0.2);
  return query<PinGeoRow>(
    `SELECT pin_code, lat, lng, spread_km FROM pin_geo
     WHERE lat BETWEEN ? AND ? AND lng BETWEEN ? AND ?`,
    [lat - windowDeg, lat + windowDeg, lng - lngWindow, lng + lngWindow],
  );
}

export async function POST(request: NextRequest) {
  let lat: number, lng: number;
  try {
    const body = await request.json();
    lat = Number(body?.lat);
    lng = Number(body?.lng);
  } catch {
    return Response.json({ error: "Body must be JSON: { lat, lng }" }, { status: 400 });
  }
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
    return Response.json({ error: "lat and lng must be numbers" }, { status: 400 });
  }
  if (
    lat < INDIA_BOUNDS.latMin || lat > INDIA_BOUNDS.latMax ||
    lng < INDIA_BOUNDS.lngMin || lng > INDIA_BOUNDS.lngMax
  ) {
    return Response.json(
      { error: "This location appears to be outside India." },
      { status: 404, headers: { "Cache-Control": "no-store" } },
    );
  }

  // Expanding bounding-box prefilter, then exact haversine over candidates.
  let rows = await candidatesWithin(lat, lng, 0.5);
  if (rows.length === 0) rows = await candidatesWithin(lat, lng, 2.0);
  if (rows.length === 0) {
    return Response.json(
      { error: "No PIN found near this location." },
      { status: 404, headers: { "Cache-Control": "no-store" } },
    );
  }

  const ranked = rows
    .map((r) => ({ ...r, distance_km: haversineKm(lat, lng, r.lat, r.lng) }))
    .sort((a, b) => a.distance_km - b.distance_km)
    .slice(0, 5);

  // Nearest centroid first; a handful of GeoNames PINs (~2%) are absent from
  // the postal directory — fall through to the nearest one the directory knows.
  for (const cand of ranked) {
    const mapping = await queryOne<{ district: string; state: string }>(
      `SELECT district, state FROM pin_district_mapping WHERE pin_code = ?`,
      [cand.pin_code],
    );
    if (mapping) {
      return Response.json(
        {
          pin_code: cand.pin_code,
          district: mapping.district,
          state: mapping.state,
          distance_km: Math.round(cand.distance_km * 10) / 10,
          pin_spread_km: cand.spread_km,
          method: "nearest_pin_centroid",
          attribution: "Location matching via GeoNames postal data (CC BY 4.0)",
        },
        { headers: { "Cache-Control": "no-store" } },
      );
    }
  }

  return Response.json(
    { error: "No PIN found near this location." },
    { status: 404, headers: { "Cache-Control": "no-store" } },
  );
}
