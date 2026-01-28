export default function ActionBriefLoading() {
  return (
    <div className="flex-1">
      <main className="max-w-3xl mx-auto px-4 sm:px-6 py-8 space-y-10">
        {/* Header skeleton */}
        <div className="space-y-3 animate-fade-in-up">
          <div
            className="h-4 w-24 rounded-lg shimmer"
            style={{ background: "var(--border)" }}
          />
          <div
            className="h-9 w-48 rounded-lg shimmer"
            style={{ background: "var(--border)" }}
          />
          <div
            className="h-5 w-64 rounded-lg shimmer"
            style={{ background: "var(--border-subtle)" }}
          />
        </div>

        {/* Section: What's Wrong */}
        <div className="space-y-4 animate-fade-in-up stagger-1">
          <div
            className="h-5 w-36 rounded-lg shimmer"
            style={{ background: "var(--border)" }}
          />
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-28 rounded-xl shimmer"
                style={{ background: "var(--border-subtle)" }}
              />
            ))}
          </div>
        </div>

        {/* Section: Who's Responsible */}
        <div className="space-y-4 animate-fade-in-up stagger-2">
          <div
            className="h-5 w-44 rounded-lg shimmer"
            style={{ background: "var(--border)" }}
          />
          <div className="grid gap-4 sm:grid-cols-2">
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="h-48 rounded-xl shimmer"
                style={{ background: "var(--border-subtle)" }}
              />
            ))}
          </div>
        </div>

        {/* Section: What You Can Do */}
        <div className="space-y-4 animate-fade-in-up stagger-3">
          <div
            className="h-5 w-40 rounded-lg shimmer"
            style={{ background: "var(--border)" }}
          />
          <div className="space-y-3">
            {[1, 2].map((i) => (
              <div
                key={i}
                className="h-36 rounded-xl shimmer"
                style={{ background: "var(--border-subtle)" }}
              />
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
