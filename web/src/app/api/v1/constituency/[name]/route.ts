import { type NextRequest } from "next/server";
import { query, queryOne } from "@/lib/db";

interface MpInfo {
  mp_name: string;
  party: string;
  constituency: string;
  state: string;
  elected_year: number;
  source_url: string;
}

interface DistrictRow {
  district: string;
}

interface DeliveryRow {
  scheme: string;
  delivery_pct: number;
}

interface FinanceRow {
  scheme: string;
  utilization_pct: number;
}

const GRADE_THRESHOLDS: [number, string][] = [
  [80, "A"],
  [60, "B"],
  [40, "C"],
  [20, "D"],
  [0, "F"],
];

function grade(score: number): string {
  for (const [threshold, letter] of GRADE_THRESHOLDS) {
    if (score >= threshold) return letter;
  }
  return "F";
}

function avg(values: number[]): number | null {
  const valid = values.filter((v) => v != null && v >= 0 && v <= 100);
  if (valid.length === 0) return null;
  return valid.reduce((a, b) => a + b, 0) / valid.length;
}

function schemeStatus(score: number): string {
  if (score >= 80) return "good";
  if (score >= 60) return "fair";
  if (score >= 40) return "needs_attention";
  return "critical";
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ name: string }> },
) {
  const { name } = await params;
  const constituency = decodeURIComponent(name);
  const finYear =
    request.nextUrl.searchParams.get("fin_year") ?? "2024-2025";

  const mp = await queryOne<MpInfo>(
    `SELECT * FROM mp_info WHERE UPPER(constituency) = UPPER(?)`,
    [constituency],
  );

  const districtRows = await query<DistrictRow>(
    `SELECT DISTINCT district FROM constituency_district WHERE UPPER(constituency) = UPPER(?)`,
    [constituency],
  );

  const districts = districtRows.map((r) => r.district);

  if (districts.length === 0) {
    return Response.json({
      constituency: constituency.toUpperCase(),
      state: mp?.state ?? "Unknown",
      mp_name: mp?.mp_name ?? "Unknown",
      party: mp?.party ?? null,
      elected_year: mp?.elected_year ?? null,
      districts: [],
      fin_year: finYear,
      composite_score: null,
      composite_grade: null,
      national_avg_score: null,
      red_flags: [],
      schemes: [],
      source_note:
        "Scores based on scheme_delivery and scheme_finance VIEWs. 60% delivery + 40% utilization.",
    });
  }

  // Fetch delivery and finance for each district
  const schemeDelivery: Record<string, number[]> = {};
  const schemeFinance: Record<string, number[]> = {};

  for (const district of districts) {
    const [deliveryRows, financeRows] = await Promise.all([
      query<DeliveryRow>(
        `SELECT scheme, delivery_pct FROM scheme_delivery
         WHERE UPPER(district) = UPPER(?) AND fin_year = ? AND delivery_pct IS NOT NULL`,
        [district, finYear],
      ),
      query<FinanceRow>(
        `SELECT scheme, utilization_pct FROM scheme_finance
         WHERE UPPER(district) = UPPER(?) AND fin_year = ? AND utilization_pct IS NOT NULL AND utilization_pct > 0 AND utilization_pct <= 150`,
        [district, finYear],
      ),
    ]);

    for (const row of deliveryRows) {
      if (!schemeDelivery[row.scheme]) schemeDelivery[row.scheme] = [];
      schemeDelivery[row.scheme].push(row.delivery_pct);
    }

    for (const row of financeRows) {
      if (!schemeFinance[row.scheme]) schemeFinance[row.scheme] = [];
      schemeFinance[row.scheme].push(Math.min(100, row.utilization_pct));
    }
  }

  // Compute per-scheme averages
  const allSchemes = [
    ...new Set([
      ...Object.keys(schemeDelivery),
      ...Object.keys(schemeFinance),
    ]),
  ].sort();

  const redFlags: string[] = [];
  const schemes = allSchemes.map((scheme) => {
    const deliveryAvg = avg(schemeDelivery[scheme] ?? []);
    const utilizationAvg = avg(schemeFinance[scheme] ?? []);

    // 60% delivery + 40% utilization
    let score: number | null = null;
    if (deliveryAvg != null && utilizationAvg != null) {
      score = Math.round((deliveryAvg * 0.6 + utilizationAvg * 0.4) * 10) / 10;
    } else if (deliveryAvg != null) {
      score = Math.round(deliveryAvg * 10) / 10;
    } else if (utilizationAvg != null) {
      score = Math.round(utilizationAvg * 10) / 10;
    }

    if (deliveryAvg != null && deliveryAvg < 40) {
      redFlags.push(`${scheme} delivery only ${deliveryAvg.toFixed(0)}%`);
    }
    if (utilizationAvg != null && utilizationAvg < 30) {
      redFlags.push(
        `${scheme} utilization only ${utilizationAvg.toFixed(0)}%`,
      );
    }

    return {
      scheme,
      delivery_pct: deliveryAvg != null ? Math.round(deliveryAvg * 10) / 10 : null,
      utilization_pct:
        utilizationAvg != null ? Math.round(utilizationAvg * 10) / 10 : null,
      score,
      grade: score != null ? grade(score) : null,
      status: score != null ? schemeStatus(score) : "no_data",
    };
  });

  // Composite score across all schemes
  const schemeScores = schemes
    .map((s) => s.score)
    .filter((s): s is number => s != null);
  const compositeScore =
    schemeScores.length > 0
      ? Math.round(
          (schemeScores.reduce((a, b) => a + b, 0) / schemeScores.length) * 10,
        ) / 10
      : null;

  // National average
  const nationalRow = await queryOne<{ avg_score: number }>(
    `SELECT AVG(delivery_pct) as avg_score FROM scheme_delivery
     WHERE fin_year = ? AND delivery_pct IS NOT NULL AND district != 'ALL'`,
    [finYear],
  );
  const nationalAvg =
    nationalRow?.avg_score != null
      ? Math.round(nationalRow.avg_score * 10) / 10
      : null;

  return Response.json({
    constituency: constituency.toUpperCase(),
    state: mp?.state ?? "Unknown",
    mp_name: mp?.mp_name ?? "Unknown",
    party: mp?.party ?? null,
    elected_year: mp?.elected_year ?? null,
    districts,
    fin_year: finYear,
    composite_score: compositeScore,
    composite_grade: compositeScore != null ? grade(compositeScore) : null,
    national_avg_score: nationalAvg,
    red_flags: redFlags.slice(0, 5),
    schemes,
    source_note:
      "Scores based on scheme_delivery and scheme_finance VIEWs. 60% delivery + 40% utilization.",
  });
}
