import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono, Newsreader } from "next/font/google";
import Link from "next/link";
import "./globals.css";
import "./tokens.css";
import "./base.css";
import "./forms.css";
import "./map.css";
import "./brief.css";
import "./complaints.css";
import "./evidence.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });
const newsreader = Newsreader({
  variable: "--font-newsreader",
  subsets: ["latin"],
  weight: "600",
  display: "swap",
});

export const metadata: Metadata = {
  title: { default: "Hisaab — Know what you’re owed", template: "%s | Hisaab" },
  description: "Enter your PIN to see local welfare evidence, legal entitlements, official complaint routes, and your elected representatives.",
  icons: { icon: "/favicon.svg" },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} ${newsreader.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <header className="site-header">
          <nav className="site-header__inner" aria-label="Primary navigation">
            <Link href="/" className="wordmark">
              Hisaab <small>beta</small>
            </Link>
            <span className="site-header__promise hidden sm:block">
              Rights · evidence · action
            </span>
          </nav>
        </header>
        <main className="flex-1">{children}</main>
        <footer className="site-footer">
          <div className="site-footer__inner">
            <span>Hisaab · open public-accountability infrastructure</span>
            <span>Official-source data · not a government service</span>
          </div>
        </footer>
      </body>
    </html>
  );
}
