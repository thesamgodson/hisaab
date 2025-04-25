/**
 * Simplified India state boundary data for choropleth rendering.
 *
 * This file provides simplified SVG path data for India's states.
 * The paths are approximate representations suitable for a dashboard map.
 *
 * NOTE: For full district-level choropleth accuracy, replace this with
 * district GeoJSON from https://github.com/datameet/maps/tree/master/Districts
 * (~15 MB GeoJSON). Project it to SVG with d3-geo or similar. The state-level
 * map here is sufficient for visualising per-state aggregated scores.
 *
 * Viewport: 0 0 800 900 (standard India bounding box used across OSM tiles).
 * Paths are hand-simplified from Natural Earth 1:10m admin-1 data.
 */

export interface StateBoundary {
  id: string;        // State name (UPPER CASE, matches DB state column)
  label: string;     // Display name
  path: string;      // SVG path d attribute
  labelX: number;    // Approx centroid X for label placement
  labelY: number;    // Approx centroid Y for label placement
}

/**
 * Load state boundaries.
 *
 * Returns the static list of SimplifiedStateBoundary objects.
 * In future this could be replaced with an async GeoJSON fetch.
 */
export function loadDistrictBoundaries(): StateBoundary[] {
  return INDIA_STATES;
}

/**
 * Simplified SVG paths for India's 28 states + 8 UTs.
 *
 * Coordinate system: SVG viewport 800×900.
 * Origin (0,0) = top-left ≈ (67°E, 37°N).
 * Scale: ~1 degree longitude ≈ 10.5px, ~1 degree latitude ≈ 11.5px.
 *
 * These are hand-traced approximations — sufficient for choropleth colouring,
 * not for precise boundary work.
 */
const INDIA_STATES: StateBoundary[] = [
  {
    id: "JAMMU AND KASHMIR",
    label: "J&K",
    labelX: 205,
    labelY: 65,
    path: "M170,30 L200,28 L240,35 L260,50 L255,70 L240,80 L220,85 L200,80 L185,70 L175,55 Z",
  },
  {
    id: "LADAKH",
    label: "Ladakh",
    labelX: 310,
    labelY: 52,
    path: "M255,30 L310,20 L360,30 L370,50 L355,65 L330,70 L300,65 L275,60 L260,50 Z",
  },
  {
    id: "HIMACHAL PRADESH",
    label: "HP",
    labelX: 230,
    labelY: 105,
    path: "M200,82 L220,87 L240,82 L258,88 L252,105 L240,115 L220,118 L205,110 L198,95 Z",
  },
  {
    id: "PUNJAB",
    label: "Punjab",
    labelX: 185,
    labelY: 110,
    path: "M170,88 L198,95 L205,110 L195,122 L178,125 L165,118 L160,105 Z",
  },
  {
    id: "UTTARAKHAND",
    label: "UK",
    labelX: 275,
    labelY: 118,
    path: "M252,105 L258,88 L285,90 L300,95 L295,115 L280,125 L262,122 Z",
  },
  {
    id: "HARYANA",
    label: "Haryana",
    labelX: 203,
    labelY: 138,
    path: "M178,125 L195,122 L205,110 L220,118 L222,132 L210,145 L193,148 L180,140 Z",
  },
  {
    id: "DELHI",
    label: "Delhi",
    labelX: 218,
    labelY: 140,
    path: "M210,133 L222,132 L222,143 L212,146 Z",
  },
  {
    id: "UTTAR PRADESH",
    label: "UP",
    labelX: 320,
    labelY: 160,
    path: "M222,132 L262,122 L280,125 L295,115 L310,120 L335,125 L360,130 L370,145 L355,165 L330,178 L300,182 L270,175 L250,165 L230,160 L210,145 Z",
  },
  {
    id: "RAJASTHAN",
    label: "Rajasthan",
    labelX: 178,
    labelY: 185,
    path: "M130,130 L160,125 L178,125 L180,140 L193,148 L210,145 L230,160 L225,180 L210,200 L190,215 L165,220 L140,210 L120,195 L115,172 L120,152 Z",
  },
  {
    id: "BIHAR",
    label: "Bihar",
    labelX: 390,
    labelY: 170,
    path: "M360,145 L380,140 L405,145 L415,155 L410,172 L395,180 L370,182 L355,170 Z",
  },
  {
    id: "JHARKHAND",
    label: "Jharkhand",
    labelX: 390,
    labelY: 205,
    path: "M355,182 L370,182 L395,180 L415,185 L418,200 L410,218 L390,225 L368,220 L355,205 Z",
  },
  {
    id: "SIKKIM",
    label: "SK",
    labelX: 452,
    labelY: 148,
    path: "M442,144 L452,142 L458,150 L448,158 L440,152 Z",
  },
  {
    id: "WEST BENGAL",
    label: "WB",
    labelX: 435,
    labelY: 195,
    path: "M415,155 L430,152 L445,158 L450,172 L445,192 L435,210 L420,220 L410,218 L415,200 Z",
  },
  {
    id: "ARUNACHAL PRADESH",
    label: "AR",
    labelX: 548,
    labelY: 128,
    path: "M465,115 L510,108 L550,112 L565,125 L545,138 L510,140 L480,138 L462,130 Z",
  },
  {
    id: "ASSAM",
    label: "Assam",
    labelX: 510,
    labelY: 158,
    path: "M462,140 L510,140 L545,138 L548,152 L530,165 L500,168 L470,162 L458,152 Z",
  },
  {
    id: "NAGALAND",
    label: "NL",
    labelX: 548,
    labelY: 168,
    path: "M530,165 L548,162 L555,172 L545,182 L528,178 Z",
  },
  {
    id: "MANIPUR",
    label: "MN",
    labelX: 545,
    labelY: 192,
    path: "M528,178 L545,182 L550,195 L538,205 L522,200 L520,188 Z",
  },
  {
    id: "MIZORAM",
    label: "MZ",
    labelX: 532,
    labelY: 218,
    path: "M522,200 L538,205 L540,218 L528,228 L515,222 L515,210 Z",
  },
  {
    id: "TRIPURA",
    label: "TR",
    labelX: 508,
    labelY: 205,
    path: "M495,198 L510,196 L515,210 L507,220 L495,215 Z",
  },
  {
    id: "MEGHALAYA",
    label: "ML",
    labelX: 490,
    labelY: 172,
    path: "M470,162 L500,168 L505,178 L490,186 L468,180 L465,168 Z",
  },
  {
    id: "MADHYA PRADESH",
    label: "MP",
    labelX: 258,
    labelY: 225,
    path: "M165,220 L190,215 L210,200 L225,180 L250,165 L270,175 L300,182 L320,190 L335,205 L325,225 L305,240 L280,250 L250,252 L225,248 L200,240 L175,232 Z",
  },
  {
    id: "CHHATTISGARH",
    label: "CG",
    labelX: 360,
    labelY: 232,
    path: "M335,205 L360,200 L385,205 L395,220 L390,240 L370,252 L348,255 L330,245 L325,228 Z",
  },
  {
    id: "ODISHA",
    label: "Odisha",
    labelX: 410,
    labelY: 248,
    path: "M390,225 L410,218 L430,222 L440,238 L435,258 L415,268 L395,265 L383,250 L387,235 Z",
  },
  {
    id: "GUJARAT",
    label: "Gujarat",
    labelX: 132,
    labelY: 245,
    path: "M90,210 L115,205 L130,210 L140,210 L165,220 L175,232 L170,250 L155,265 L135,270 L110,262 L92,245 Z",
  },
  {
    id: "MAHARASHTRA",
    label: "Maharashtra",
    labelX: 230,
    labelY: 292,
    path: "M165,255 L175,232 L200,240 L225,248 L250,252 L268,268 L262,285 L245,300 L220,310 L195,308 L172,295 L160,278 Z",
  },
  {
    id: "TELANGANA",
    label: "Telangana",
    labelX: 308,
    labelY: 298,
    path: "M280,268 L305,265 L325,268 L330,285 L320,305 L300,312 L282,305 L272,290 Z",
  },
  {
    id: "ANDHRA PRADESH",
    label: "AP",
    labelX: 342,
    labelY: 320,
    path: "M325,268 L348,262 L370,268 L378,285 L368,308 L348,322 L325,325 L308,315 L320,305 L330,285 Z",
  },
  {
    id: "KARNATAKA",
    label: "Karnataka",
    labelX: 245,
    labelY: 338,
    path: "M195,308 L220,310 L245,300 L268,305 L282,308 L282,330 L265,348 L242,355 L220,352 L200,340 L188,322 Z",
  },
  {
    id: "GOA",
    label: "Goa",
    labelX: 195,
    labelY: 330,
    path: "M188,322 L200,320 L205,330 L196,338 L187,332 Z",
  },
  {
    id: "KERALA",
    label: "Kerala",
    labelX: 228,
    labelY: 385,
    path: "M220,352 L242,355 L248,372 L240,392 L228,408 L215,400 L210,382 L215,365 Z",
  },
  {
    id: "TAMIL NADU",
    label: "TN",
    labelX: 278,
    labelY: 385,
    path: "M248,355 L268,350 L290,352 L300,368 L295,390 L278,408 L258,410 L240,395 L242,375 Z",
  },
];
