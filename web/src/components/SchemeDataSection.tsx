/** Per-scheme evidence cards (money + delivery) — shared by the district
 *  page and the PIN action page so both entry points show the same data. */

import SchemeRow, { type SchemeData } from "@/components/SchemeRow";
import SectionHeader from "@/components/SectionHeader";

export default function SchemeDataSection({
  schemes,
}: {
  schemes: SchemeData[];
}) {
  if (schemes.length === 0) return null;
  return (
    <section className="mb-12">
      <SectionHeader title="Scheme Data" count={schemes.length} />
      <div className="grid gap-5 sm:grid-cols-2">
        {schemes.map((s) => (
          <SchemeRow key={s.scheme} data={s} />
        ))}
      </div>
    </section>
  );
}
