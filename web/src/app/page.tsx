import { Suspense } from "react";
import PinEntry from "@/components/PinEntry";
import IndiaMap from "@/components/IndiaMap";

export default function Home() {
  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6">
      {/* PIN entry — glass card treatment */}
      <section className="pt-16 pb-14 sm:pt-20 sm:pb-16 text-center">
        <div
          className="max-w-lg mx-auto rounded-2xl px-6 py-10 sm:px-10 sm:py-12"
          style={{
            background: "var(--surface)",
            boxShadow: "var(--shadow-md)",
            border: "1px solid var(--border-subtle)",
          }}
        >
          <h1
            className="text-2xl sm:text-3xl font-bold mb-2 tracking-tight"
            style={{ color: "var(--text-primary)" }}
          >
            Where did the money go?
          </h1>
          <p
            className="text-sm mb-8 max-w-xs mx-auto"
            style={{ color: "var(--text-muted)", lineHeight: "1.6" }}
          >
            Enter your PIN code to see how government schemes perform in your
            area
          </p>
          <PinEntry />
        </div>
      </section>

      {/* Map */}
      <section className="pb-16">
        <Suspense
          fallback={
            <div
              className="w-full aspect-[4/3] rounded-xl shimmer"
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
