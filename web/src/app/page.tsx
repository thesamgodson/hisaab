import Link from "next/link";
import SearchBar from "@/components/SearchBar";
import IndiaMap from "@/components/IndiaMap";
import PinInput from "@/components/PinInput";

const SCHEMES = [
  { name: "MGNREGA", desc: "Employment", accent: "oklch(0.65 0.16 65)" },
  { name: "PMGSY", desc: "Rural Roads", accent: "oklch(0.55 0.10 250)" },
  { name: "PMAY-G", desc: "Housing", accent: "oklch(0.60 0.16 45)" },
  { name: "PM Kisan", desc: "Farmer Income", accent: "oklch(0.60 0.17 145)" },
  { name: "JJM", desc: "Tap Water", accent: "oklch(0.60 0.14 200)" },
  { name: "PM POSHAN", desc: "School Meals", accent: "oklch(0.60 0.16 15)" },
  { name: "NSAP", desc: "Pensions", accent: "oklch(0.55 0.16 300)" },
  { name: "PDS/NFSA", desc: "Rations", accent: "oklch(0.55 0.14 170)" },
] as const;

const STATS = [
  { value: "11", label: "Schemes" },
  { value: "700+", label: "Districts" },
  { value: "11,942", label: "Records" },
] as const;

export default function Home() {
  return (
    <main className="flex-1">
      {/* Hero Section */}
      <section className="relative px-4 sm:px-6 pt-16 sm:pt-24 pb-12">
        <div className="max-w-3xl mx-auto text-center">
          {/* Hindi script */}
          <p
            className="text-2xl sm:text-3xl font-medium mb-2 animate-fade-in-up"
            style={{ color: "var(--text-muted)" }}
          >
            &#x0939;&#x093F;&#x0938;&#x093E;&#x092C;
          </p>

          {/* Main heading */}
          <h1 className="text-5xl sm:text-7xl font-bold tracking-tight mb-4 animate-fade-in-up stagger-1"
              style={{ color: "var(--text-primary)" }}>
            Hisaab
          </h1>

          {/* Tagline with gradient */}
          <p className="text-xl sm:text-2xl font-medium mb-3 animate-fade-in-up stagger-2 text-gradient">
            Where did the money go?
          </p>

          {/* Subtitle */}
          <p
            className="text-base sm:text-lg max-w-lg mx-auto mb-8 animate-fade-in-up stagger-3"
            style={{ color: "var(--text-secondary)" }}
          >
            Enter your PIN code to see what&apos;s wrong, who&apos;s responsible,
            and what you can do about it.
          </p>

          {/* PIN Input — primary CTA */}
          <div className="animate-fade-in-up stagger-4 mb-6">
            <PinInput />
          </div>

          {/* District search — secondary */}
          <div className="animate-fade-in-up stagger-5">
            <p className="text-xs font-medium mb-2" style={{ color: "var(--text-muted)" }}>
              or search by district name
            </p>
            <SearchBar />
          </div>

          {/* Stats bar */}
          <div className="flex items-center justify-center gap-6 sm:gap-10 mt-10 animate-fade-in-up stagger-6">
            {STATS.map((stat) => (
              <div key={stat.label} className="text-center">
                <p
                  className="text-2xl sm:text-3xl font-bold tabular-nums"
                  style={{ color: "var(--text-primary)" }}
                >
                  {stat.value}
                </p>
                <p className="text-xs sm:text-sm font-medium" style={{ color: "var(--text-muted)" }}>
                  {stat.label}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Map Section */}
      <section className="px-4 sm:px-6 py-8">
        <div className="max-w-4xl mx-auto animate-fade-in-up stagger-6">
          <IndiaMap />
        </div>
      </section>

      {/* Scheme Grid */}
      <section className="px-4 sm:px-6 py-12">
        <div className="max-w-3xl mx-auto">
          <h2
            className="text-xs font-semibold uppercase tracking-widest text-center mb-6"
            style={{ color: "var(--text-muted)" }}
          >
            Schemes tracked
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {SCHEMES.map((s, i) => (
              <div
                key={s.name}
                className={`gradient-border-top rounded-xl px-4 py-4 text-center animate-fade-in-up stagger-${i + 1}`}
                style={{
                  background: "var(--surface)",
                  boxShadow: "var(--shadow-sm)",
                  ["--card-accent" as string]: `linear-gradient(135deg, ${s.accent}, ${s.accent})`,
                }}
              >
                <p
                  className="text-sm font-semibold"
                  style={{ color: "var(--text-primary)" }}
                >
                  {s.name}
                </p>
                <p className="text-xs mt-0.5" style={{ color: "var(--text-muted)" }}>
                  {s.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA: MP Report Cards */}
      <section className="px-4 sm:px-6 py-12">
        <div className="max-w-xl mx-auto animate-fade-in-up">
          <Link
            href="/constituency"
            className="group block rounded-2xl p-6 sm:p-8 text-center card-hover"
            style={{
              background: "var(--surface-tinted)",
              boxShadow: "var(--shadow-md)",
            }}
          >
            <h3
              className="text-xl sm:text-2xl font-bold mb-2"
              style={{ color: "var(--text-primary)" }}
            >
              MP Report Cards
            </h3>
            <p className="text-sm mb-4" style={{ color: "var(--text-secondary)" }}>
              See how your MP&apos;s constituency performs across all 11 welfare schemes.
            </p>
            <span
              className="inline-flex items-center gap-2 text-sm font-semibold transition-all duration-200 group-hover:gap-3"
              style={{ color: "var(--accent)" }}
            >
              View Report Cards
              <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M3 8h10M9 4l4 4-4 4" />
              </svg>
            </span>
          </Link>
        </div>
      </section>
    </main>
  );
}
