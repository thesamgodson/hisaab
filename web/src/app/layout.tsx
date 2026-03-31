import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "Hisaab — Where did the money go?",
    template: "%s | Hisaab",
  },
  description:
    "Public accountability data for 11 Indian government welfare schemes. Search any district to see MGNREGA, PMGSY, PMAY-G, PM Kisan, JJM, PM POSHAN, NSAP, PDS/NFSA, SBM-G, DAY-NRLM, and UDISE+ data.",
  icons: {
    icon: "/favicon.svg",
  },
};

function NavBar() {
  return (
    <header className="sticky top-0 z-50 glass border-b" style={{ borderColor: "var(--border-subtle)" }}>
      <nav className="max-w-5xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
        <Link
          href="/"
          className="flex items-center gap-2 group"
        >
          <span
            className="text-lg font-bold tracking-tight transition-colors duration-150 group-hover:text-[var(--accent)]"
            style={{ color: "var(--text-primary)" }}
          >
            Hisaab
          </span>
          <span
            className="text-[11px] font-medium px-1.5 py-0.5 rounded-md hidden sm:inline-block"
            style={{
              background: "var(--accent-light)",
              color: "var(--accent)",
            }}
          >
            BETA
          </span>
        </Link>

        <div className="flex items-center gap-1 sm:gap-2">
          {[
            { href: "/", label: "Check Your Area" },
            { href: "/constituency", label: "MP Cards" },
          ].map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="px-3 py-1.5 text-sm font-medium rounded-lg transition-colors duration-150 hover:bg-[var(--accent-light)]"
              style={{ color: "var(--text-secondary)" }}
            >
              {link.label}
            </Link>
          ))}
        </div>
      </nav>
    </header>
  );
}

function Footer() {
  return (
    <footer className="mt-auto border-t" style={{ borderColor: "var(--border-subtle)" }}>
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <span className="text-sm font-semibold" style={{ color: "var(--text-primary)" }}>
              Hisaab
            </span>
            <span className="text-xs" style={{ color: "var(--text-muted)" }}>
              Open-source public accountability infrastructure
            </span>
          </div>
          <div className="flex items-center gap-4 text-xs" style={{ color: "var(--text-muted)" }}>
            <span>Data from official government portals</span>
            <span style={{ color: "var(--border)" }}>|</span>
            <span>Not affiliated with any government body</span>
          </div>
        </div>
      </div>
    </footer>
  );
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <NavBar />
        {children}
        <Footer />
      </body>
    </html>
  );
}
