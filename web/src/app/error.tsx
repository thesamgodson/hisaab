"use client";

export default function Error({ reset }: { reset: () => void }) {
  return (
    <section className="status-page">
      <p className="eyebrow">Temporary problem</p>
      <h1>We couldn&apos;t open this brief</h1>
      <p>The data service may be unavailable. Your PIN and location have not been saved.</p>
      <button type="button" onClick={reset} className="button button--primary">
        Try again
      </button>
    </section>
  );
}
