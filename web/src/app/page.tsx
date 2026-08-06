import { Suspense } from "react";
import PinEntry from "@/components/PinEntry";
import IndiaMap from "@/components/IndiaMap";

export default function Home() {
  return (
    <div className="page-shell">
      <section className="home-hero" aria-labelledby="home-heading">
        <div className="home-hero__copy">
          <p className="eyebrow">Welfare rights in your area</p>
          <h1 id="home-heading">Know what you’re owed. Know what to do next.</h1>
          <p className="home-hero__lead">
            Start with your PIN. Hisaab brings together local welfare evidence,
            legal entitlements, official complaint routes, and the people who
            represent you.
          </p>
        </div>

        <div className="pin-panel">
          <p className="eyebrow">Step 01 · Find your area</p>
          <h2>Enter your 6-digit PIN</h2>
          <PinEntry />
          <p className="pin-panel__promise">
            No account required. Location matching is checked once and never stored.
          </p>
        </div>
      </section>

      <ol className="journey-line" aria-label="What your brief contains">
        <li>
          <strong>01</strong>
          <span>See what the public data flags locally.</span>
        </li>
        <li>
          <strong>02</strong>
          <span>Read your rights in plain language.</span>
        </li>
        <li>
          <strong>03</strong>
          <span>Take the complaint through an official route.</span>
        </li>
      </ol>

      <section className="map-section" aria-labelledby="map-heading">
        <div className="map-section__heading">
          <p className="eyebrow">Or browse by district</p>
          <h2 id="map-heading">Explore the country, district by district.</h2>
          <p>
            A map click opens the same accountability brief at district level.
            Use your PIN when you need your exact MP and MLA.
          </p>
        </div>
        <Suspense
          fallback={
            <div
              className="map-surface shimmer w-full aspect-[4/5] sm:aspect-[4/3]"
              aria-label="Loading district map"
            />
          }
        >
          <IndiaMap />
        </Suspense>
      </section>
    </div>
  );
}
