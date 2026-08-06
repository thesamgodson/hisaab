import SchemeRow, { type SchemeData } from "@/components/SchemeRow";

export default function SchemeDataSection({
  schemes,
}: {
  schemes: SchemeData[];
}) {
  if (schemes.length === 0) return null;

  return (
    <section id="evidence" className="content-section">
      <details className="evidence-panel">
        <summary>
          <span className="evidence-panel__summary-copy">
            <span className="eyebrow">Evidence</span>
            <h2>Official figures behind this brief</h2>
            <p>Open to inspect reported money and delivery.</p>
          </span>
          <span className="evidence-panel__count">
            {schemes.length} scheme{schemes.length === 1 ? "" : "s"}
          </span>
        </summary>
        <div className="evidence-panel__body">
          <div className="scheme-grid">
            {schemes.map((scheme) => (
              <SchemeRow key={scheme.scheme} data={scheme} />
            ))}
          </div>
        </div>
      </details>
    </section>
  );
}
