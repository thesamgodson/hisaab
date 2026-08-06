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
    <section className="status-page">
      <p className="eyebrow">PIN lookup</p>
      <h1>{heading}</h1>
      <p>{children}</p>
      <Link href="/" className="button button--primary">Try another PIN</Link>
    </section>
  );
}
