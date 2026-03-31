export default function Loading() {
  return (
    <main className="max-w-5xl mx-auto px-4 sm:px-6 py-8 animate-pulse space-y-6">
      {/* Header skeleton */}
      <div className="space-y-3">
        <div
          className="h-10 w-72 rounded-lg shimmer"
          style={{ background: "var(--surface-tinted)" }}
        />
        <div
          className="h-5 w-48 rounded-lg shimmer"
          style={{ background: "var(--surface-tinted)" }}
        />
      </div>

      {/* MP card skeleton */}
      <div
        className="rounded-2xl p-6 space-y-4"
        style={{
          background: "var(--surface)",
          border: "1px solid var(--border)",
        }}
      >
        <div className="flex items-center gap-4">
          <div
            className="w-16 h-16 rounded-xl shimmer"
            style={{ background: "var(--accent-light)" }}
          />
          <div className="space-y-2 flex-1">
            <div
              className="h-6 w-48 rounded-lg shimmer"
              style={{ background: "var(--surface-tinted)" }}
            />
            <div
              className="h-4 w-32 rounded-lg shimmer"
              style={{ background: "var(--surface-tinted)" }}
            />
          </div>
        </div>
      </div>

      {/* Scheme cards skeleton */}
      <div className="grid gap-4 sm:grid-cols-2">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="h-40 rounded-2xl shimmer"
            style={{ background: "var(--surface-tinted)" }}
          />
        ))}
      </div>
    </main>
  );
}
