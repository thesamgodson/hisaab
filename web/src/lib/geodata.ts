/**
 * District-level boundary loader using TopoJSON.
 *
 * Fetches /india-districts.topojson (820 districts) and converts to GeoJSON
 * features via topojson-client. Results are cached in memory after first load.
 */

import { feature } from "topojson-client";
import type { Topology, GeometryCollection } from "topojson-specification";

export interface DistrictFeature {
  district: string;
  state: string;
  geometry: GeoJSON.Geometry;
}

// Re-export for backward compatibility (old map used StateBoundary)
export type StateBoundary = DistrictFeature;

let _cache: DistrictFeature[] | null = null;

/**
 * Load all 820 district boundaries from TopoJSON.
 *
 * Returns cached result on subsequent calls. The TopoJSON file must be
 * served from /india-districts.topojson (Next.js public directory).
 */
export async function loadDistrictBoundaries(): Promise<DistrictFeature[]> {
  if (_cache) return _cache;

  const resp = await fetch("/india-districts.topojson");
  if (!resp.ok) {
    throw new Error(`Failed to load TopoJSON: ${resp.status}`);
  }

  const topo = (await resp.json()) as Topology<{
    [key: string]: GeometryCollection<{ district: string; state: string }>;
  }>;

  const layerName = Object.keys(topo.objects)[0];
  const geojson = feature(topo, topo.objects[layerName]);

  const result: DistrictFeature[] = [];
  if ("features" in geojson) {
    for (const f of geojson.features) {
      result.push({
        district: (f.properties?.district as string) || "",
        state: (f.properties?.state as string) || "",
        geometry: f.geometry,
      });
    }
  }

  _cache = result;
  return _cache;
}
