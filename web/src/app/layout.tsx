import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: { default: "Hisaab — Where did the money go?", template: "%s | Hisaab" },
  description: "Public accountability data for Indian government welfare schemes. Enter your PIN code to see how schemes perform in your area.",
  icons: { icon: "/favicon.svg" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col">
        <header className="sticky top-0 z-50 glass border-b" style={{ borderColor: "var(--border-subtle)" }}>
          <nav className="max-w-5xl mx-auto px-4 sm:px-6 h-14 flex items-center">
            <Link href="/" className="flex items-center gap-2 group">
              <span className="text-lg font-bold tracking-tight transition-colors duration-150 group-hover:text-[var(--accent)]" style={{ color: "var(--text-primary)" }}>
                Hisaab
              </span>
              <span className="text-[11px] font-medium px-1.5 py-0.5 rounded-md" style={{ background: "var(--accent-light)", color: "var(--accent)" }}>
                BETA
              </span>
            </Link>
          </nav>
        </header>
        <main className="flex-1">{children}</main>
        <footer className="mt-auto border-t" style={{ borderColor: "var(--border-subtle)" }}>
          <div className="max-w-5xl mx-auto px-4 sm:px-6 py-6 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs" style={{ color: "var(--text-muted)" }}>
            <span>Hisaab — Open-source public accountability infrastructure</span>
            <span>Data from official government portals · Not affiliated with any government body</span>
          </div>
        </footer>
      </body>
    </html>
  );
}
