import DistrictPicker from "@/components/DistrictPicker";
import PinEntry from "@/components/PinEntry";

interface ServiceStartProps {
  issue?: string | null;
  error?: string;
}

export default function ServiceStart({ issue, error }: ServiceStartProps) {
  return (
    <section className="account-start" aria-labelledby="service-heading">
      <header className="account-start__header">
        <p className="service-label">Independent public welfare account</p>
        <h1 id="service-heading">Where did the money go?</h1>
        <p>
          Enter a PIN to see what public records report about money and
          services in your district.
        </p>
        <ol className="account-start__path" aria-label="How Hisaab works">
          <li><span>01</span>Find your area</li>
          <li><span>02</span>Check a service</li>
          <li><span>03</span>Use official routes</li>
        </ol>
      </header>

      {error && <p className="service-error" role="alert">{error}</p>}

      <div className="account-entry" aria-label="Find an area account">
        <header className="account-entry__header">
          <p>Start here</p>
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

      <div className="account-start__truth">
        <p><strong>Area-wide records, not a personal benefit record.</strong> Hisaab does not decide eligibility.</p>
        <p>No account required. Do not enter a name, Aadhaar number, complaint text, or documents.</p>
      </div>
    </section>
  );
}
