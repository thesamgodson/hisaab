import Link from "next/link";

/** Dead-end state for a PIN we can't brief on — malformed, or not in the
 *  postal directory. Both cases end at the same place: go back and retype. */
export default function PinNotice({
  heading,
  children,
}: {
  heading: string;
  children: React.ReactNode;
}) {
  return (
    <main className="max-w-3xl mx-auto px-4 py-20 text-center">
      <h1
        className="text-2xl font-bold mb-3"
        style={{ color: "var(--text-primary)" }}
      >
        {heading}
      </h1>
      <p style={{ color: "var(--text-secondary)" }}>{children}</p>
      <Link
        href="/"
        className="inline-block mt-6 px-5 py-2.5 rounded-xl text-sm font-medium text-white transition-opacity duration-150 hover:opacity-90"
        style={{ background: "var(--accent)" }}
      >
        Go back home
      </Link>
    </main>
  );
}
