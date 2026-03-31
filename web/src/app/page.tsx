import { Suspense } from "react";
import PinEntry from "@/components/PinEntry";
import IndiaMap from "@/components/IndiaMap";

export default function Home() {
  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6">
      {/* PIN entry */}
      <section className="py-10 text-center">
        <h1
          className="text-2xl sm:text-3xl font-bold mb-1"
          style={{ color: "var(--text-primary)" }}
        >
          Where did the money go?
        </h1>
        <p className="text-sm mb-8" style={{ color: "var(--text-muted)" }}>
          Enter your PIN code to see how government schemes perform in your area
        </p>
        <PinEntry />
      </section>

      {/* Map */}
      <section className="pb-12">
        <Suspense
          fallback={
            <div
              className="w-full aspect-[4/3] rounded-xl animate-pulse"
              style={{ background: "var(--surface)" }}
            />
          }
        >
          <IndiaMap />
        </Suspense>
      </section>
    </div>
  );
}
