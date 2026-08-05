import { type NextRequest } from "next/server";
import { query, queryOne } from "@/lib/db";
import { candidateStates } from "@/lib/vintage-states";

interface PinMapping {
  pin_code: string;
  district: string;
  state: string;
  office_name: string;
}

interface ConstituencyDistrict {
  constituency: string;
  district: string;
  state: string;
  [key: string]: unknown;
}

interface MpInfo {
  mp_name: string;
  party: string;
  constituency: string;
  state: string;
  elected_year: number;
  source_url: string;
}

interface AcDistrict {
  ac_name: string;
  ac_no: number;
  pc_name: string;
  district: string;
  state: string;
  [key: string]: unknown;
}

interface MlaInfo {
  mla_name: string;
  party: string;
  ac_name: string;
  state: string;
  source_url: string;
}

// India reuses PC names across states (AURANGABAD is a Bihar seat and a
// Maharashtra seat), so a name-only lookup can return another state's
// representative. Match name+state (with the vintage equivalence above);
// an honest null beats a wrong MP/MLA. Names compare with " (SC)"/" (ST)"
// stripped: datameet carries the reservation suffix (250 of 543 PCs, 953
// ACs) while OpenCity/MyNeta mostly drop it — exact matching left every
// reserved seat without its representative.
async function findMp(constituency: string, state: string): Promise<MpInfo | null> {
  for (const st of candidateStates(state)) {
    const mp = await queryOne<MpInfo>(
      `SELECT * FROM mp_info
       WHERE UPPER(REPLACE(REPLACE(constituency, ' (SC)', ''), ' (ST)', ''))
           = UPPER(REPLACE(REPLACE(?, ' (SC)', ''), ' (ST)', ''))
         AND UPPER(state) = ?`,
      [constituency, st],
    );
    if (mp) return mp;
  }
  return null;
}

async function findMla(acName: string, state: string): Promise<MlaInfo | null> {
  for (const st of candidateStates(state)) {
    const mla = await queryOne<MlaInfo>(
      `SELECT * FROM mla_info
       WHERE UPPER(REPLACE(REPLACE(ac_name, ' (SC)', ''), ' (ST)', ''))
           = UPPER(REPLACE(REPLACE(?, ' (SC)', ''), ' (ST)', ''))
         AND UPPER(state) = ?`,
      [acName, st],
    );
    if (mla) return mla;
  }
  return null;
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

  // Check if this district was carved out of a parent district
  const lineage = await queryOne<{ parent_district: string; split_year: number }>(
    `SELECT parent_district, split_year FROM district_lineage
     WHERE UPPER(new_district) = UPPER(?) AND UPPER(state) = UPPER(?)`,
    [district, state],
  );

  // Try precise PIN→constituency mapping first (spatial join table)
  const pinConstituency = await queryOne<{ constituency: string; state: string }>(
    `SELECT constituency, state FROM pin_constituency WHERE pin_code = ?`,
    [pin_code],
  );

  let constituencies: ConstituencyDistrict[];
  if (pinConstituency) {
    // Precise match — try exact name first, then fuzzy (strip SC/ST suffix)
    constituencies = await query<ConstituencyDistrict>(
      `SELECT * FROM constituency_district WHERE UPPER(constituency) = UPPER(?) AND UPPER(state) = UPPER(?)`,
      [pinConstituency.constituency, pinConstituency.state],
    );
    if (constituencies.length === 0) {
      // Try matching without (SC)/(ST) suffix, or match base name
      constituencies = await query<ConstituencyDistrict>(
        `SELECT * FROM constituency_district
         WHERE (UPPER(REPLACE(REPLACE(constituency, ' (SC)', ''), ' (ST)', '')) = UPPER(?)
            OR UPPER(?) LIKE UPPER(REPLACE(REPLACE(constituency, ' (SC)', ''), ' (ST)', '')))
           AND UPPER(state) = UPPER(?)`,
        [pinConstituency.constituency, pinConstituency.constituency, pinConstituency.state],
      );
    }
    // Deduplicate by constituency name
    const seen = new Set<string>();
    constituencies = constituencies.filter((c) => {
      const key = c.constituency.toUpperCase();
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
    if (constituencies.length === 0 && pinConstituency) {
      // Constituency identified via spatial mapping but not in constituency_district table
      constituencies = [{
        constituency: pinConstituency.constituency,
        district,
        state: pinConstituency.state || state,
      } as ConstituencyDistrict];
    }
  } else {
    // Fallback: all constituencies in district
    constituencies = await query<ConstituencyDistrict>(
      `SELECT * FROM constituency_district WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?)`,
      [district, state],
    );
  }

  const assemblyConstituencies = pinConstituency
    ? await query<AcDistrict>(
        `SELECT * FROM ac_district WHERE UPPER(pc_name) = UPPER(?) AND UPPER(state) = UPPER(?)`,
        [pinConstituency.constituency, pinConstituency.state],
      )
    : await query<AcDistrict>(
        `SELECT * FROM ac_district WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?)`,
        [district, state],
      );

  const constituenciesWithMp = await Promise.all(
    constituencies.map(async (c) => {
      const mp = await findMp(c.constituency, c.state);
      return {
        ...c,
        mp: mp
          ? {
              mp_name: mp.mp_name,
              party: mp.party,
              state: mp.state,
              elected_year: mp.elected_year,
              source_url: mp.source_url,
            }
          : null,
      };
    }),
  );

  const acsWithMla = await Promise.all(
    assemblyConstituencies.map(async (ac) => {
      const mla = await findMla(ac.ac_name, ac.state);
      return {
        type: "VIDHAN_SABHA" as const,
        ac_name: ac.ac_name,
        ac_no: ac.ac_no,
        pc_name: ac.pc_name,
        mla: mla
          ? {
              mla_name: mla.mla_name,
              party: mla.party,
              state: mla.state,
              source_url: mla.source_url,
            }
          : null,
      };
    }),
  );

  return Response.json({
    pin_code,
    district: mapping.district,
    state: mapping.state,
    office_name: mapping.office_name,
    formerly_part_of: lineage
      ? { parent_district: lineage.parent_district, split_year: lineage.split_year }
      : null,
    precise: !!pinConstituency,
    constituencies: constituenciesWithMp,
    constituency_count: constituenciesWithMp.length,
    assembly_constituencies: acsWithMla,
    assembly_constituency_count: acsWithMla.length,
  });
}
