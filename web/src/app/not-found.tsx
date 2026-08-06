import Link from "next/link";

export default function NotFound() {
  return (
    <section className="status-page">
      <p className="eyebrow">Not found</p>
      <h1>We couldn&apos;t find this page</h1>
      <p>The link may be incomplete. Start again with your PIN or browse the district map.</p>
      <Link href="/" className="button button--primary">Go to Hisaab</Link>
    </section>
  );
}
