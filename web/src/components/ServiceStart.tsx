import DistrictPicker from "@/components/DistrictPicker";
import IndiaMap from "@/components/IndiaMap";
import PinEntry from "@/components/PinEntry";

interface ServiceStartProps {
  issue?: string | null;
  error?: string;
}

export default function ServiceStart({ issue, error }: ServiceStartProps) {
  return (
    <section className="entry rise-stagger" aria-labelledby="service-heading">
      <header className="entry-hero">
        <p className="section-eyebrow">Independent public accountability</p>
        <h1 id="service-heading">Where did the money go?</h1>
        <p className="entry-hero__sub">
          Enter a PIN to see what public records report about money and
          services in your district.
        </p>
      </header>

      {error && <p className="entry-alert" role="alert">{error}</p>}

      <div className="entry-card" aria-label="Find an area account">
        <header className="entry-card__header">
          <p className="section-eyebrow">Start here</p>
          <h2>Find your area</h2>
        </header>
        <PinEntry issue={issue} />
        <DistrictPicker issue={issue} />
        <noscript>
          <form action="/" method="get" className="district-form noscript-district">
            {issue && <input type="hidden" name="issue" value={issue} />}
            <label htmlFor="state-text">State</label>
            <input id="state-text" name="state" autoComplete="address-level1" required />
            <label htmlFor="district-text">District</label>
            <input id="district-text" name="district" autoComplete="address-level2" required />
            <button type="submit" className="button button--secondary">Use this district</button>
          </form>
        </noscript>
      </div>

      <div className="map-section">
        <IndiaMap />
      </div>

      <div className="entry-truth">
        <p><strong>Area-wide records, not a personal benefit record.</strong> Hisaab does not decide eligibility.</p>
        <p>No account required. Do not enter a name, Aadhaar number, complaint text, or documents.</p>
      </div>
    </section>
  );
}
