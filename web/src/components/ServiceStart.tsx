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
        <p className="service-label">Public welfare account</p>
        <h1 id="service-heading">Where did the money go?</h1>
        <p>
          Enter your area to read what official records report about welfare
          money, delivery, and missing data. Then use the sourced rights and
          complaint routes if you need them.
        </p>
      </header>

      {error && <p className="service-error" role="alert">{error}</p>}

      <div className="account-entry" aria-label="Find an area account">
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
        <p><strong>Public, area-wide records only.</strong> This is not your personal benefit record and does not decide eligibility.</p>
        <p>No account required. Do not enter a name, Aadhaar number, complaint text, or documents.</p>
      </div>
    </section>
  );
}
