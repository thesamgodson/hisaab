import Link from "next/link";
import DistrictPicker from "@/components/DistrictPicker";
import PinEntry from "@/components/PinEntry";
import type { ComplaintKit } from "@/lib/action-types";
import { schemeDisplay } from "@/lib/scheme-display";

interface AreaState {
  pin?: string;
  district?: string;
  state?: string;
}

interface ServiceStartProps {
  kits: ComplaintKit[];
  selectedKit?: ComplaintKit | null;
  triggerIndex?: number | null;
  area?: AreaState;
  error?: string;
}

function HiddenArea({ area }: { area?: AreaState }) {
  if (!area) return null;
  return (
    <>
      {area.pin && <input type="hidden" name="pin" value={area.pin} />}
      {area.district && <input type="hidden" name="district" value={area.district} />}
      {area.state && <input type="hidden" name="state" value={area.state} />}
    </>
  );
}

function problemHref(area?: AreaState): string {
  if (!area) return "/";
  const params = new URLSearchParams();
  if (area.pin) params.set("pin", area.pin);
  if (area.district) params.set("district", area.district);
  if (area.state) params.set("state", area.state);
  const query = params.toString();
  return query ? `/?${query}` : "/";
}

function ErrorMessage({ children }: { children?: string }) {
  if (!children) return null;
  return <p className="service-error" role="alert">{children}</p>;
}

function ProblemStep({ kits, area, error }: ServiceStartProps) {
  return (
    <section className="service-step" aria-labelledby="service-heading">
      <p className="service-step__count">Start</p>
      <h1 id="service-heading">What happened?</h1>
      <p className="service-step__intro">
        Choose the closest problem. You do not need to know the scheme name.
      </p>
      <ErrorMessage>{error}</ErrorMessage>
      <form action="/" method="get" className="service-form">
        <HiddenArea area={area} />
        <label htmlFor="problem-select">Welfare problem</label>
        <select id="problem-select" name="issue" defaultValue="" required>
          <option value="" disabled>Choose a problem</option>
          {[...kits].sort((left, right) =>
            schemeDisplay(left.scheme).need.localeCompare(schemeDisplay(right.scheme).need),
          ).map((kit) => (
            <option key={kit.scheme} value={kit.scheme}>
              {schemeDisplay(kit.scheme).need}
            </option>
          ))}
          <option value="ALL">Another government-service problem</option>
        </select>
        <button className="button button--primary" type="submit">Continue</button>
      </form>
      <p className="service-step__note">
        Hisaab does not decide eligibility or submit a complaint.
      </p>
    </section>
  );
}

function TriggerStep({ selectedKit, area, error }: ServiceStartProps) {
  if (!selectedKit) return null;
  const display = schemeDisplay(selectedKit.scheme);
  return (
    <section className="service-step" aria-labelledby="service-heading">
      <nav className="service-back" aria-label="Previous step">
        <Link href={problemHref(area)}>Back to problems</Link>
      </nav>
      <p className="service-step__count">Step 2 · {selectedKit.scheme}</p>
      <h1 id="service-heading">Which is closest?</h1>
      <p className="service-step__intro">
        These are sourced examples for {display.need.toLowerCase()}. Choose the
        one that best matches what happened.
      </p>
      <ErrorMessage>{error}</ErrorMessage>
      <form action="/" method="get" className="service-form">
        <input type="hidden" name="issue" value={selectedKit.scheme} />
        <HiddenArea area={area} />
        <fieldset className="trigger-list">
          <legend className="sr-only">Choose what happened</legend>
          {selectedKit.complain_when.map((trigger, index) => (
            <label className="trigger-option" key={trigger}>
              <input type="radio" name="trigger" value={index} required />
              <span>{trigger}</span>
            </label>
          ))}
        </fieldset>
        <button className="button button--primary" type="submit">Continue</button>
      </form>
    </section>
  );
}

function AreaStep({ selectedKit, triggerIndex, error }: ServiceStartProps) {
  const issue = selectedKit?.scheme;
  if (!issue) return null;
  const backHref = `/?issue=${encodeURIComponent(issue)}`;
  return (
    <section className="service-step" aria-labelledby="service-heading">
      <nav className="service-back" aria-label="Previous step">
        <Link href={backHref}>Back</Link>
      </nav>
      <p className="service-step__count">Final step</p>
      <h1 id="service-heading">Where is this happening?</h1>
      <p className="service-step__intro">
        Your area helps Hisaab show the relevant public context. It does not
        determine whether your complaint is valid.
      </p>
      <ErrorMessage>{error}</ErrorMessage>
      <PinEntry issue={issue} triggerIndex={triggerIndex} />
      <DistrictPicker issue={issue} triggerIndex={triggerIndex} />
      <noscript>
        <form action="/" method="get" className="district-form noscript-district">
          <input type="hidden" name="issue" value={issue} />
          {triggerIndex != null && <input type="hidden" name="trigger" value={triggerIndex} />}
          <label htmlFor="state-text">State</label>
          <input id="state-text" name="state" autoComplete="address-level1" required />
          <label htmlFor="district-text">District</label>
          <input id="district-text" name="district" autoComplete="address-level2" required />
          <button type="submit" className="button button--secondary">Use this district</button>
        </form>
      </noscript>
      <p className="service-step__note">
        No account required. Do not enter case details, Aadhaar, or documents.
      </p>
    </section>
  );
}

export default function ServiceStart(props: ServiceStartProps) {
  if (!props.selectedKit) {
    return <ProblemStep {...props} />;
  }
  if (props.selectedKit && props.triggerIndex == null) {
    return <TriggerStep {...props} />;
  }
  return <AreaStep {...props} />;
}
