import Link from "next/link";
import ComplaintGuide from "@/components/ComplaintGuide";
import type { GrievanceChannel } from "@/lib/action-types";

export default function GeneralResult({
  universal,
}: {
  universal: GrievanceChannel[];
}) {
  return (
    <div id="result" className="result-shell">
      <nav className="result-nav no-print" aria-label="Change answers">
        <Link href="/">Start again</Link>
      </nav>
      <ComplaintGuide
        kits={[]}
        universal={universal}
        selectedScheme={null}
        selectedTrigger={null}
        district=""
        state=""
        general
      />
      <p className="print-disclaimer">
        Hisaab is an independent public-interest tool, not a government service.
      </p>
    </div>
  );
}
