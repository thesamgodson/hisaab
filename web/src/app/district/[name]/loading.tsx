export default function Loading() {
  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 animate-pulse space-y-6">
      <div
        className="h-10 w-64 rounded-lg shimmer"
        style={{ background: "var(--surface-tinted)" }}
      />
      <div
        className="h-6 w-40 rounded-lg shimmer"
        style={{ background: "var(--surface-tinted)" }}
      />
      <div
        className="h-10 w-36 rounded-xl shimmer"
        style={{ background: "var(--accent-light)" }}
      />
      <div className="grid gap-4 sm:grid-cols-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <div
            key={i}
            className="h-48 rounded-2xl shimmer"
            style={{ background: "var(--surface-tinted)" }}
          />
        ))}
      </div>
    </div>
  );
}
