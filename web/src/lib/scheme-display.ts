export interface SchemeDisplay {
  need: string;
  shortNeed: string;
}

const SCHEME_DISPLAY: Record<string, SchemeDisplay> = {
  MGNREGA: { need: "Rural work and wages", shortNeed: "Work and wages" },
  PMGSY: { need: "Rural roads", shortNeed: "Rural roads" },
  "PMAY-G": { need: "Rural housing", shortNeed: "Rural housing" },
  "PM Kisan": { need: "Farm income support", shortNeed: "Farm payments" },
  JJM: { need: "Household tap water", shortNeed: "Tap water" },
  "PM POSHAN": { need: "School meals", shortNeed: "School meals" },
  NSAP: { need: "Pensions and social assistance", shortNeed: "Pension" },
  "PDS/NFSA": { need: "Ration and food security", shortNeed: "Ration" },
  "SBM-G": { need: "Rural sanitation", shortNeed: "Sanitation" },
  "DAY-NRLM": { need: "Self-help group support", shortNeed: "SHG support" },
  "UDISE+": { need: "Government schools", shortNeed: "Schools" },
};

export function schemeDisplay(scheme: string): SchemeDisplay {
  return SCHEME_DISPLAY[scheme] ?? { need: scheme, shortNeed: scheme };
}
