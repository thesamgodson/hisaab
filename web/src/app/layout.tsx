import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";
import "./tokens.css";
import "./theme.css"; /* after tokens.css — every variable here wins the cascade */
import "./base.css";
import "./forms.css";
import "./surface.css";
import "./action.css";
import "./evidence.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });
export const metadata: Metadata = {
  title: { default: "Hisaab — Where did the money go?", template: "%s | Hisaab" },
  description: "Enter your PIN. See what government schemes owe your district, what actually arrived, and exactly how to complain — every number from official sources.",
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
      className={`${geistSans.variable} ${geistMono.variable}`}
    >
      <body>
        <a className="skip-link" href="#main-content">Skip to account</a>
        <header className="site-header">
          <nav className="site-header__inner" aria-label="Primary navigation">
            <Link href="/" className="wordmark">
              Hisaab
            </Link>
            <span className="site-header__context">
              Where did the money go?
            </span>
          </nav>
        </header>
        <main id="main-content">{children}</main>
        <footer className="site-footer">
          <div className="site-footer__inner">
            <span>Independent public-interest tool</span>
            <span>Official sources. Not a government service.</span>
          </div>
        </footer>
      </body>
    </html>
  );
}
