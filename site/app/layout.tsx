import type { Metadata } from "next";
import { Inter, Barlow_Condensed } from "next/font/google";
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
      <body className="min-h-screen bg-zinc-950 text-zinc-100 antialiased">
        <div className="page-glow">
          <header className="sticky top-0 z-40 border-b border-white/10 bg-zinc-950/85 backdrop-blur-md">
            <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-y-3 px-4 py-3.5">
              <Link href="/" className="flex shrink-0 items-baseline gap-2.5">
                <span className="font-display text-[26px] font-semibold uppercase leading-none tracking-wide">
                  Honest<span className="text-amber-400">Line</span>
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
        <footer className="border-t border-white/10 bg-zinc-950">
          <div className="mx-auto grid max-w-6xl gap-8 px-4 py-10 md:grid-cols-[1.2fr_1fr_1fr]">
            <div>
              <div className="font-display text-xl font-semibold uppercase tracking-wide">
                Honest<span className="text-amber-400">Line</span>
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
                    <Link href={href} className="text-zinc-400 transition hover:text-white">
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
          <div className="border-t border-white/5">
            <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 py-4 text-xs text-zinc-600">
              <span>© 2026 HonestLine</span>
              <span>Lines are a snapshot from generation time.</span>
            </div>
          </div>
        </footer>
      </body>
    </html>
  );
}
