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
  title: "Hisaab — Where did the money go?",
  description:
    "Public accountability data for 11 Indian government welfare schemes. Search any district to see MGNREGA, PMGSY, PMAY-G, PM Kisan, JJM, PM POSHAN, NSAP, and PDS/NFSA data.",
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
            { href: "/", label: "Home" },
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
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="p-2 rounded-lg transition-colors duration-150 hover:bg-[var(--accent-light)]"
            style={{ color: "var(--text-muted)" }}
            aria-label="GitHub"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
              <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z" />
            </svg>
          </a>
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
