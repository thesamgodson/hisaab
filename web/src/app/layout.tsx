import type { Metadata, Viewport } from "next";
import { Geist_Mono, Noto_Sans } from "next/font/google";
import Link from "next/link";
import "./globals.css";
import "./tokens.css";
import "./base.css";
import "./forms.css";
import "./surface.css";
import "./action.css";
import "./evidence.css";

const notoSans = Noto_Sans({ variable: "--font-noto-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });
export const metadata: Metadata = {
  title: { default: "Hisaab — Public welfare account", template: "%s | Hisaab" },
  description: "Read sourced district welfare money and delivery records, see what is missing, and use verified official routes when needed.",
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
      className={`${notoSans.variable} ${geistMono.variable}`}
    >
      <body>
        <a className="skip-link" href="#main-content">Skip to account</a>
        <header className="site-header">
          <nav className="site-header__inner" aria-label="Primary navigation">
            <Link href="/" className="wordmark">
              Hisaab
            </Link>
            <span className="site-header__context">
              Public welfare account
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
