export interface SchemeDisplay {
  need: string;
  shortNeed: string;
}

const SCHEME_DISPLAY: Record<string, SchemeDisplay> = {
  MGNREGA: { need: "Work, job card or wages", shortNeed: "Work and wages" },
  PMGSY: { need: "Rural-road quality", shortNeed: "Rural roads" },
  "PMAY-G": { need: "Rural-house selection or payment", shortNeed: "Rural housing" },
  "PM Kisan": { need: "Farm instalment or status", shortNeed: "Farm payments" },
  JJM: { need: "Tap water", shortNeed: "Tap water" },
  "PM POSHAN": { need: "School meals", shortNeed: "School meals" },
  NSAP: { need: "Pension or social assistance", shortNeed: "Pension" },
  "PDS/NFSA": { need: "Ration or foodgrain", shortNeed: "Ration" },
  "SBM-G": { need: "Toilet or village sanitation", shortNeed: "Sanitation" },
  "DAY-NRLM": { need: "Women’s SHG or bank support", shortNeed: "SHG support" },
  "UDISE+": { need: "School admission, fees, punishment or facilities", shortNeed: "School rights" },
};

export function schemeDisplay(scheme: string): SchemeDisplay {
  return SCHEME_DISPLAY[scheme] ?? { need: scheme, shortNeed: scheme };
}
