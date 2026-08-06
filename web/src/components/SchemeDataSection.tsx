import SchemeRow, { type SchemeData } from "@/components/SchemeRow";

export default function SchemeDataSection({ schemes }: { schemes: SchemeData[] }) {
  if (schemes.length === 0) return null;

  return (
    <section id="evidence" className="result-section">
      <header className="section-title">
        <h2>Evidence</h2>
        <p>Reported money and delivery from official sources.</p>
      </header>
      <details className="evidence-disclosure">
        <summary>
          <strong>View scheme records</strong>
          <span className="evidence-disclosure__count">
            {schemes.length} scheme{schemes.length === 1 ? "" : "s"}
          </span>
        </summary>
        <div className="evidence-list">
          {schemes.map((scheme) => <SchemeRow key={scheme.scheme} data={scheme} />)}
        </div>
      </details>
    </section>
  );
}
