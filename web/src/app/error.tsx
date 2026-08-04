"use client";

export default function Error({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="flex-1 flex flex-col items-center justify-center px-4 py-24 text-center">
      <div
        className="w-16 h-16 mx-auto mb-6 rounded-2xl flex items-center justify-center"
        style={{ background: "oklch(0.93 0.05 25)" }}
      >
        <svg
          width="28"
          height="28"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{ color: "oklch(0.55 0.20 25)" }}
          aria-hidden="true"
        >
          <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
          <line x1="12" y1="9" x2="12" y2="13" />
          <line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
      </div>
      <h1
        className="text-3xl font-bold mb-2"
        style={{ color: "var(--text-primary)" }}
      >
        Something went wrong
      </h1>
      <p
        className="text-sm mb-8 max-w-md"
        style={{ color: "var(--text-muted)" }}
      >
        An unexpected error occurred. This could be a temporary issue with our data service.
      </p>
      <button
        onClick={() => reset()}
        className="px-6 py-3 rounded-xl text-white text-sm font-semibold transition-opacity duration-150 hover:opacity-90"
        style={{ background: "var(--accent-gradient)" }}
      >
        Try again
      </button>
    </main>
  );
}
