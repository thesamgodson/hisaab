import Link from "next/link";

export default function NotFound() {
  return (
    <main className="flex-1 flex flex-col items-center justify-center px-4 py-24 text-center">
      <div
        className="w-16 h-16 mx-auto mb-6 rounded-2xl flex items-center justify-center"
        style={{ background: "var(--accent-light)" }}
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
          style={{ color: "var(--accent)" }}
          aria-hidden="true"
        >
          <circle cx="12" cy="12" r="10" />
          <path d="M16 16s-1.5-2-4-2-4 2-4 2" />
          <line x1="9" y1="9" x2="9.01" y2="9" />
          <line x1="15" y1="9" x2="15.01" y2="9" />
        </svg>
      </div>
      <h1
        className="text-4xl font-bold mb-2"
        style={{ color: "var(--text-primary)" }}
      >
        Page not found
      </h1>
      <p
        className="text-base mb-8"
        style={{ color: "var(--text-muted)" }}
      >
        The page you are looking for does not exist or has been moved.
      </p>
      <Link
        href="/"
        className="px-6 py-3 rounded-xl text-white text-sm font-semibold transition-opacity duration-150 hover:opacity-90"
        style={{ background: "var(--accent-gradient)" }}
      >
        Back to Home
      </Link>
    </main>
  );
}
