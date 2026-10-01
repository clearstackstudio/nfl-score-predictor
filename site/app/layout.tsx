import type { Metadata } from "next";
import { Inter, Barlow_Condensed } from "next/font/google";
import Image from "next/image";
import Link from "next/link";
import Nav from "./nav";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], display: "swap" });
const barlow = Barlow_Condensed({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  display: "swap",
  variable: "--font-display",
});

export const metadata: Metadata = {
  title: "Honest Line — NFL picks with a public track record",
  description:
    "A fundamentals-only NFL prediction model. Every pick published, every result tracked, no hidden losers.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${inter.className} ${barlow.variable}`}>
      <body className="min-h-screen bg-zinc-950 text-zinc-100 antialiased light:bg-white light:text-zinc-900">
        <div className="page-glow">
          <header className="sticky top-0 z-40 border-b border-white/10 bg-zinc-950/85 backdrop-blur-md light:border-zinc-200 light:bg-white/85">
            <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-y-3 px-4 py-3.5">
              <Link href="/" className="flex shrink-0 items-center gap-2.5">
                <Image
                  src="/honest-line-mark.png"
                  alt="Honest Line logo"
                  width={48}
                  height={48}
                  className="h-12 w-12 rounded-lg"
                />
                <span className="font-display text-[32px] font-semibold uppercase leading-none tracking-wide">
                  Honest<span className="text-amber-400 light:text-amber-600">Line</span>
                </span>
                <span className="hidden text-xs text-zinc-500 md:inline">
                  NFL picks, tracked in public
                </span>
              </Link>
              <Nav />
            </div>
          </header>
          <main className="mx-auto max-w-6xl px-4 pb-16 pt-10">{children}</main>
        </div>
        <footer className="border-t border-white/10 bg-zinc-950 light:border-zinc-200 light:bg-zinc-50">
          <div className="mx-auto grid max-w-6xl gap-8 px-4 py-10 md:grid-cols-[1.2fr_1fr_1fr]">
            <div>
              <div className="font-display text-xl font-semibold uppercase tracking-wide">
                Honest<span className="text-amber-400 light:text-amber-600">Line</span>
              </div>
              <p className="mt-2 max-w-xs text-sm leading-relaxed text-zinc-500">
                A fundamentals-only NFL prediction model. Every pick published
                before kickoff, every result graded in public.
              </p>
            </div>
            <nav aria-label="Footer">
              <div className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
                Explore
              </div>
              <ul className="mt-3 space-y-2 text-sm">
                {[
                  ["This week's picks", "/"],
                  ["Pick'em game", "/pick-em"],
                  ["Track record", "/track-record"],
                  ["Methodology", "/methodology"],
                ].map(([label, href]) => (
                  <li key={href}>
                    <Link href={href} className="text-zinc-400 transition hover:text-white light:text-zinc-600 light:hover:text-zinc-900">
                      {label}
                    </Link>
                  </li>
                ))}
              </ul>
            </nav>
            <div>
              <div className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
                The fine print
              </div>
              <p className="mt-3 text-xs leading-relaxed text-zinc-500">
                Model probabilities are for entertainment and research. Our own
                backtest shows no edge against the closing line — the full
                record is on the Track record page. If you bet, bet responsibly.
              </p>
            </div>
          </div>
          <div className="border-t border-white/5 light:border-zinc-200">
            <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 py-4 text-xs text-zinc-600 light:text-zinc-500">
              <span>© 2026 HonestLine</span>
              <span>
                A{" "}
                <a
                  href="https://weclearstack.com"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-zinc-400 underline decoration-zinc-700 underline-offset-2 transition hover:text-zinc-200 light:text-zinc-600 light:decoration-zinc-300 light:hover:text-zinc-900"
                >
                  ClearStack Studio
                </a>{" "}
                project · Lines are a snapshot from generation time.
              </span>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
