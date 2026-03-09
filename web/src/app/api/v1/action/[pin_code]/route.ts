import { type NextRequest } from "next/server";
import { query, queryOne } from "@/lib/db";

interface PinMapping {
  pin_code: string;
  district: string;
  state: string;
  office_name: string;
}

interface MpInfo {
  mp_name: string;
  party: string;
  constituency: string;
  state: string;
  elected_year: number;
  source_url: string;
}

interface MlaInfo {
  mla_name: string;
  party: string;
  ac_name: string;
  state: string;
  source_url: string;
}

interface DiagnosisItem {
  severity: "high" | "medium" | "low";
  scheme: string;
  summary: string;
  detail: string;
  amount: number | null;
  source_url: string | null;
}

interface ContactInfo {
  name: string;
  designation: string;
  phone: string | null;
  email: string | null;
  district: string;
  state: string;
  freshness: "fresh" | "stale" | "expired";
}

interface GrievanceChannel {
  scheme: string;
  level: string;
  portal_name: string;
  portal_url: string;
  phone: string | null;
}

interface ActionItem {
  scheme: string;
  steps: { action: string; url: string | null }[];
}

const SEVERITY_ORDER: Record<string, number> = { high: 0, medium: 1, low: 2 };

const SCHEME_ACTIONS: Record<
  string,
  { action: string; url: string | null }[]
> = {
  MGNREGA: [
    { action: "File RTI on MGNREGA portal", url: "https://nrega.nic.in" },
    {
      action: "Escalate grievance via PG Portal",
      url: "https://pgportal.gov.in",
    },
  ],
  "PMAY-G": [
    {
      action: "Check beneficiary status on PMAY-G portal",
      url: "https://pmayg.nic.in",
    },
    {
      action: "File complaint on PMAY-G grievance portal",
      url: "https://pmayg.nic.in/grievance",
    },
  ],
  JJM: [
    {
      action: "Check tap connection status",
      url: "https://ejalshakti.gov.in",
    },
    {
      action: "File complaint on JJM portal",
      url: "https://jaljeevanmission.gov.in",
    },
  ],
  PMGSY: [
    { action: "Check road status on OMMS", url: "https://omms.nic.in" },
    {
      action: "File complaint on PMGSY portal",
      url: "https://pmgsy.nic.in",
    },
  ],
  "PM POSHAN": [
    {
      action: "Contact Mid-Day Meal district coordinator",
      url: null,
    },
    {
      action: "Escalate via PM POSHAN portal",
      url: "https://pmposhan.education.gov.in",
    },
  ],
  "PDS/NFSA": [
    { action: "File complaint on NFSA portal", url: "https://nfsa.gov.in" },
    {
      action: "Escalate grievance via PG Portal",
      url: "https://pgportal.gov.in",
    },
  ],
  NSAP: [
    {
      action: "Check pension status on NSAP portal",
      url: "https://nsap.nic.in",
    },
    {
      action: "Escalate grievance via PG Portal",
      url: "https://pgportal.gov.in",
    },
  ],
};

function daysSince(dateStr: string | null | undefined): number | null {
  if (!dateStr) return null;
  const scraped = new Date(dateStr);
  if (isNaN(scraped.getTime())) return null;
  return Math.floor(
    (Date.now() - scraped.getTime()) / (1000 * 60 * 60 * 24),
  );
}

function contactFreshness(
  scrapedAt: string | null | undefined,
): "fresh" | "stale" | "expired" {
  const days = daysSince(scrapedAt);
  if (days == null || days > 180) return "expired";
  if (days > 90) return "stale";
  return "fresh";
}

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
    const utilizationPct = Number(financial.utilization_pct ?? (totalAvail > 0 ? (totalExpend / totalAvail) * 100 : 100));
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

  // PM POSHAN
  const poshan = await queryOne<Record<string, unknown>>(
    `SELECT * FROM pmposhan_district WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?) AND fin_year = ?`,
    [district, state, finYear],
  );
  if (poshan) {
    const enrolled = Number(poshan.children_enrolled ?? 0);
    const fed = Number(poshan.children_fed ?? 0);
    const pct = enrolled > 0 ? (fed / enrolled) * 100 : 100;
    if (pct < 70) {
      items.push({
        severity: "medium",
        scheme: "PM POSHAN",
        summary: `Only ${pct.toFixed(0)}% children fed`,
        detail: `${fed.toLocaleString("en-IN")} of ${enrolled.toLocaleString("en-IN")} enrolled children being fed`,
        amount: null,
        source_url: (poshan.source_url as string) ?? null,
      });
    }
  }

  // NFSA
  const nfsa = await queryOne<Record<string, unknown>>(
    `SELECT * FROM nfsa_district WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?) AND fin_year = ?`,
    [district, state, finYear],
  );
  if (nfsa) {
    const total = Number(nfsa.ration_cards_total ?? 0);
    const active = Number(nfsa.ration_cards_active ?? 0);
    const pct = total > 0 ? (active / total) * 100 : 100;
    if (pct < 80) {
      items.push({
        severity: "medium",
        scheme: "PDS/NFSA",
        summary: `Only ${pct.toFixed(0)}% ration cards active`,
        detail: `${active.toLocaleString("en-IN")} of ${total.toLocaleString("en-IN")} cards are active`,
        amount: null,
        source_url: (nfsa.source_url as string) ?? null,
      });
    }
  }

  // NSAP
  const nsap = await queryOne<Record<string, unknown>>(
    `SELECT * FROM nsap_district WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?) AND fin_year = ?`,
    [district, state, finYear],
  );
  if (nsap) {
    const target = Number(nsap.beneficiaries_eligible ?? 0);
    const paid = Number(nsap.beneficiaries_paid ?? 0);
    if (target > 0 && paid < target) {
      items.push({
        severity: "medium",
        scheme: "NSAP",
        summary: `Only ${paid.toLocaleString("en-IN")} of ${target.toLocaleString("en-IN")} target beneficiaries paid`,
        detail: `${((paid / target) * 100).toFixed(0)}% pension coverage`,
        amount: Number(nsap.amount_paid_lakhs ?? 0),
        source_url: (nsap.source_url as string) ?? null,
      });
    }
  }

  // Sort by severity, cap at 5
  items.sort(
    (a, b) => (SEVERITY_ORDER[a.severity] ?? 9) - (SEVERITY_ORDER[b.severity] ?? 9),
  );
  return items.slice(0, 5);
}

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ pin_code: string }> },
) {
  const { pin_code } = await params;

  if (!/^\d{6}$/.test(pin_code)) {
    return Response.json(
      { error: "Invalid PIN code. Must be a 6-digit number." },
      { status: 400 },
    );
  }

  const mapping = await queryOne<PinMapping>(
    `SELECT * FROM pin_district_mapping WHERE pin_code = ?`,
    [pin_code],
  );

  if (!mapping) {
    return Response.json(
      {
        error: `PIN code ${pin_code} not found. Ensure this is a valid Indian postal code.`,
      },
      { status: 404 },
    );
  }

  const { district, state } = mapping;
  const finYear = "2024-2025";

  // Get MP via constituency_district -> mp_info
  const mpRow = await queryOne<MpInfo & { constituency_name: string }>(
    `SELECT m.mp_name, m.party, m.constituency, m.state, m.elected_year, m.source_url
     FROM constituency_district cd
     JOIN mp_info m ON UPPER(cd.constituency) = UPPER(m.constituency)
     WHERE UPPER(cd.district) = UPPER(?) AND UPPER(cd.state) = UPPER(?)
     LIMIT 1`,
    [district, state],
  );

  // Get MLA via ac_district -> mla_info
  const mlaRow = await queryOne<MlaInfo>(
    `SELECT ml.mla_name, ml.party, ml.ac_name, ml.state, ml.source_url
     FROM ac_district ac
     JOIN mla_info ml ON UPPER(ac.ac_name) = UPPER(ml.ac_name) AND UPPER(ac.state) = UPPER(ml.state)
     WHERE UPPER(ac.district) = UPPER(?) AND UPPER(ac.state) = UPPER(?)
     LIMIT 1`,
    [district, state],
  );

  // Build diagnosis
  const diagnosis = await buildDiagnosis(district, state, finYear);

  // Get contacts with freshness check
  const rawContacts = await query<Record<string, unknown>>(
    `SELECT * FROM district_officials WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?)`,
    [district, state],
  );

  const contacts: ContactInfo[] = rawContacts.map((c) => {
    const freshness = contactFreshness(c.scraped_at as string | null);
    return {
      name: String(c.name ?? ""),
      designation: String(c.role ?? ""),
      phone: freshness === "expired" ? null : (c.phone as string) ?? null,
      email: freshness === "expired" ? null : (c.email as string) ?? null,
      district: String(c.district ?? ""),
      state: String(c.state ?? ""),
      freshness,
    };
  });

  // Get grievance channels for flagged schemes
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

  // Build action items
  const actions: ActionItem[] = flaggedSchemes
    .filter((scheme) => SCHEME_ACTIONS[scheme])
    .map((scheme) => ({
      scheme,
      steps: SCHEME_ACTIONS[scheme],
    }));

  // Gather raw scheme data for transparency
  const schemeData: Record<string, unknown> = {};
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

  return Response.json({
    pin: pin_code,
    district: mapping.district,
    state: mapping.state,
    mp: mpRow
      ? {
          mp_name: mpRow.mp_name,
          party: mpRow.party,
          constituency: mpRow.constituency,
          state: mpRow.state,
          elected_year: mpRow.elected_year,
          source_url: mpRow.source_url,
        }
      : null,
    mla: mlaRow
      ? {
          mla_name: mlaRow.mla_name,
          party: mlaRow.party,
          ac_name: mlaRow.ac_name,
          state: mlaRow.state,
          source_url: mlaRow.source_url,
        }
      : null,
    diagnosis,
    contacts,
    actions,
    grievance_channels: grievanceChannels,
    scheme_data: schemeData,
    generated_at: new Date().toISOString(),
  });
}
