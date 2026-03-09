import { type NextRequest } from "next/server";
import { query, queryOne } from "@/lib/db";

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

  const [constituencies, assemblyConstituencies] = await Promise.all([
    query<ConstituencyDistrict>(
      `SELECT * FROM constituency_district WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?)`,
      [district, state],
    ),
    query<AcDistrict>(
      `SELECT * FROM ac_district WHERE UPPER(district) = UPPER(?) AND UPPER(state) = UPPER(?)`,
      [district, state],
    ),
  ]);

  const constituenciesWithMp = await Promise.all(
    constituencies.map(async (c) => {
      const mp = await queryOne<MpInfo>(
        `SELECT * FROM mp_info WHERE UPPER(constituency) = UPPER(?)`,
        [c.constituency],
      );
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
      const mla = await queryOne<MlaInfo>(
        `SELECT * FROM mla_info WHERE UPPER(ac_name) = UPPER(?) AND UPPER(state) = UPPER(?)`,
        [ac.ac_name, ac.state],
      );
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
    constituencies: constituenciesWithMp,
    constituency_count: constituenciesWithMp.length,
    assembly_constituencies: acsWithMla,
    assembly_constituency_count: acsWithMla.length,
  });
}
