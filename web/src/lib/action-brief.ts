/**
 * Citizen action brief: PIN -> district reality -> who is accountable ->
 * what to do about it.
 *
 * Called directly by the /action/[pin] page (same process — no self-HTTP)
 * and wrapped by /api/v1/action/[pin_code] for external consumers.
 *
 * Diagnosis rules only use metrics with an honest shortfall interpretation.
 * PM POSHAN, NFSA, and NSAP have none at district level (daily-snapshot
 * feeding, active=total by construction, no eligibility target — see
 * DATA_CLAIMS.md), so they are never diagnosed, only reported.
 */

import { getLatestFinYear } from "@/lib/fin-year";
import { query, queryOne } from "@/lib/db";
import type {
  ActionBriefResponse,
  ActionItem,
  ActionStep,
  DiagnosisItem,
  GrievanceChannel,
  SchemeDataEntry,
} from "@/lib/action-types";

const SEVERITY_ORDER: Record<string, number> = { high: 0, medium: 1, low: 2 };

const SCHEME_ACTIONS: Record<string, ActionStep[]> = {
  MGNREGA: [
    { action: "File RTI on MGNREGA portal", url: "https://nrega.nic.in" },
    { action: "Escalate grievance via PG Portal", url: "https://pgportal.gov.in" },
  ],
  "PMAY-G": [
    { action: "Check beneficiary status on PMAY-G portal", url: "https://pmayg.nic.in" },
    { action: "File complaint on PMAY-G grievance portal", url: "https://pmayg.nic.in/grievance" },
  ],
  JJM: [
    { action: "Check tap connection status", url: "https://ejalshakti.gov.in" },
    { action: "File complaint on JJM portal", url: "https://jaljeevanmission.gov.in" },
  ],
  PMGSY: [
    { action: "Check road status on OMMS", url: "https://omms.nic.in" },
    { action: "File complaint on PMGSY portal", url: "https://pmgsy.nic.in" },
  ],
};

async function buildDiagnosis(
  district: string,
  state: string,
  finYear: string,
): Promise<DiagnosisItem[]> {
  const items: DiagnosisItem[] = [];

  // MGNREGA misappropriation
  const misapprop = await queryOne<Record<string, unknown>>(
    `SELECT * FROM misappropriation WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?) AND fin_year = ?`,
    [district, state, finYear],
  );
  if (misapprop) {
    const recoveryRate = Number(misapprop.recovery_rate_pct ?? 100);
    if (recoveryRate < 50) {
      items.push({
        severity: "high",
        scheme: "MGNREGA",
        summary: `Recovery rate only ${recoveryRate.toFixed(0)}%`,
        detail: `Rs ${Number(misapprop.amount_reported ?? 0).toFixed(2)}L reported misappropriated, only ${recoveryRate.toFixed(0)}% recovered`,
        amount: Number(misapprop.amount_reported ?? 0),
        source_url: (misapprop.source_url as string) ?? null,
      });
    }
  }

  // MGNREGA financial utilization
  const financial = await queryOne<Record<string, unknown>>(
    `SELECT * FROM financial_statement WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?) AND fin_year = ?`,
    [district, state, finYear],
  );
  if (financial) {
    const totalAvail = Number(financial.total_availability ?? 0);
    const totalExpend = Number(financial.cumulative_expenditure ?? 0);
    const utilizationPct = Number(
      financial.utilization_pct ??
        (totalAvail > 0 ? (totalExpend / totalAvail) * 100 : 100),
    );
    if (utilizationPct < 60) {
      items.push({
        severity: "high",
        scheme: "MGNREGA",
        summary: `Fund utilization only ${utilizationPct.toFixed(0)}%`,
        detail: `Rs ${totalExpend.toFixed(2)}L spent of Rs ${totalAvail.toFixed(2)}L available`,
        amount: totalAvail - totalExpend,
        source_url: (financial.source_url as string) ?? null,
      });
    }
  }

  // PMAY-G
  const pmayg = await queryOne<Record<string, unknown>>(
    `SELECT * FROM pmayg_district WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?) AND fin_year = ?`,
    [district, state, finYear],
  );
  if (pmayg) {
    const sanctioned = Number(pmayg.houses_sanctioned ?? 0);
    const completed = Number(pmayg.houses_completed ?? 0);
    const pct = sanctioned > 0 ? (completed / sanctioned) * 100 : 100;
    if (pct < 50) {
      items.push({
        severity: "high",
        scheme: "PMAY-G",
        summary: `House completion only ${pct.toFixed(0)}%`,
        detail: `${completed} of ${sanctioned} sanctioned houses completed`,
        amount: null,
        source_url: (pmayg.source_url as string) ?? null,
      });
    }
  }

  // JJM
  const jjm = await queryOne<Record<string, unknown>>(
    `SELECT * FROM jjm_district WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?) AND fin_year = ?`,
    [district, state, finYear],
  );
  if (jjm) {
    const coveragePct = Number(jjm.coverage_pct ?? 100);
    if (coveragePct < 50) {
      items.push({
        severity: "high",
        scheme: "JJM",
        summary: `Tap water coverage only ${coveragePct.toFixed(0)}%`,
        detail: `${Number(jjm.households_with_tap ?? 0).toLocaleString("en-IN")} households with tap connections`,
        amount: null,
        source_url: (jjm.source_url as string) ?? null,
      });
    }
  }

  // PMGSY
  const pmgsy = await queryOne<Record<string, unknown>>(
    `SELECT * FROM pmgsy_district WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?)`,
    [district, state],
  );
  if (pmgsy) {
    const sanctioned = Number(pmgsy.length_sanctioned_km ?? 0);
    const completed = Number(pmgsy.length_completed_km ?? 0);
    const pct = sanctioned > 0 ? (completed / sanctioned) * 100 : 100;
    if (pct < 50) {
      items.push({
        severity: "high",
        scheme: "PMGSY",
        summary: `Road completion only ${pct.toFixed(0)}%`,
        detail: `${completed.toFixed(1)} km of ${sanctioned.toFixed(1)} km sanctioned roads completed`,
        amount: null,
        source_url: (pmgsy.source_url as string) ?? null,
      });
    }
  }

  items.sort(
    (a, b) => (SEVERITY_ORDER[a.severity] ?? 9) - (SEVERITY_ORDER[b.severity] ?? 9),
  );
  return items.slice(0, 5);
}

/** Build the full action brief for a PIN, or null when the PIN is unknown. */
export async function buildActionBrief(
  pinCode: string,
): Promise<ActionBriefResponse | null> {
  const mapping = await queryOne<{
    pin_code: string;
    district: string;
    state: string;
    office_name: string;
  }>(`SELECT * FROM pin_district_mapping WHERE pin_code = ?`, [pinCode]);

  if (!mapping) return null;

  const { district, state } = mapping;
  const finYear = await getLatestFinYear();

  const [lineage, mpRow, mlaRow, diagnosis] = await Promise.all([
    queryOne<{ parent_district: string; split_year: number }>(
      `SELECT parent_district, split_year FROM district_lineage
       WHERE UPPER(new_district) = UPPER(?) AND UPPER(state) = UPPER(?)`,
      [district, state],
    ),
    queryOne<{
      mp_name: string;
      party: string;
      constituency: string;
      state: string;
      elected_year: number;
      source_url: string;
    }>(
      `SELECT m.mp_name, m.party, m.constituency, m.state, m.elected_year, m.source_url
       FROM constituency_district cd
       JOIN mp_info m ON UPPER(cd.constituency) = UPPER(m.constituency)
       WHERE UPPER(cd.district) = UPPER(?) AND UPPER(cd.state) = UPPER(?)
       LIMIT 1`,
      [district, state],
    ),
    queryOne<{
      mla_name: string;
      party: string;
      ac_name: string;
      state: string;
      source_url: string;
    }>(
      `SELECT ml.mla_name, ml.party, ml.ac_name, ml.state, ml.source_url
       FROM ac_district ac
       JOIN mla_info ml ON UPPER(ac.ac_name) = UPPER(ml.ac_name) AND UPPER(ac.state) = UPPER(ml.state)
       WHERE UPPER(ac.district) = UPPER(?) AND UPPER(ac.state) = UPPER(?)
       LIMIT 1`,
      [district, state],
    ),
    buildDiagnosis(district, state, finYear),
  ]);

  const flaggedSchemes = [...new Set(diagnosis.map((d) => d.scheme))];
  let grievanceChannels: GrievanceChannel[] = [];
  if (flaggedSchemes.length > 0) {
    const placeholders = flaggedSchemes.map(() => "?").join(",");
    grievanceChannels = await query<GrievanceChannel>(
      `SELECT * FROM grievance_channels
       WHERE scheme IN (${placeholders})
       ORDER BY scheme, CASE level WHEN 'district' THEN 1 WHEN 'state' THEN 2 WHEN 'national' THEN 3 ELSE 4 END`,
      flaggedSchemes,
    );
  }

  const actions: ActionItem[] = flaggedSchemes
    .filter((scheme) => SCHEME_ACTIONS[scheme])
    .map((scheme) => ({ scheme, steps: SCHEME_ACTIONS[scheme] }));

  const schemeData: Record<string, SchemeDataEntry> = {};
  for (const item of diagnosis) {
    if (!schemeData[item.scheme]) {
      schemeData[item.scheme] = {
        severity: item.severity,
        summary: item.summary,
        detail: item.detail,
        amount: item.amount,
        source_url: item.source_url,
      };
    }
  }

  return {
    pin: pinCode,
    district: mapping.district,
    state: mapping.state,
    formerly_part_of: lineage
      ? { parent_district: lineage.parent_district, split_year: lineage.split_year }
      : null,
    mp: mpRow ?? null,
    mla: mlaRow ?? null,
    diagnosis,
    actions,
    grievance_channels: grievanceChannels,
    scheme_data: schemeData,
    generated_at: new Date().toISOString(),
  };
}
