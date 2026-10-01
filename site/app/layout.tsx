import type { Metadata } from "next";
import { Inter } from "next/font/google";
import Link from "next/link";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], display: "swap" });

export const metadata: Metadata = {
  title: "Honest Line — NFL picks with a public track record",
  description:
    "A fundamentals-only NFL prediction model. Every pick published, every result tracked, no hidden losers.",
};

function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="rounded-md px-3 py-2 text-sm font-medium text-zinc-300 hover:bg-zinc-800 hover:text-white"
    >
      {children}
    </Link>
  );
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.className}>
      <body className="min-h-screen bg-zinc-950 text-zinc-100 antialiased">
        <header className="border-b border-zinc-800">
          <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-y-3 px-4 py-4">
            <Link href="/" className="flex shrink-0 items-baseline gap-2">
              <span className="text-xl font-extrabold tracking-tight">
                Honest<span className="text-amber-400">Line</span>
              </span>
              <span className="hidden text-xs text-zinc-500 sm:inline">
                NFL picks, tracked in public
              </span>
            </Link>
            <nav className="flex max-w-full gap-1 overflow-x-auto">
              <NavLink href="/">This week</NavLink>
              <NavLink href="/pick-em">Pick&apos;em</NavLink>
              <NavLink href="/track-record">Track record</NavLink>
              <NavLink href="/methodology">Methodology</NavLink>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
        <footer className="border-t border-zinc-800">
          <div className="mx-auto max-w-6xl px-4 py-6 text-xs text-zinc-500">
            Model probabilities are for entertainment and research. Our own
            backtest shows no edge against the closing line — the full record
            is on the Track record page. Bet responsibly.
          </div>
        </footer>
      </body>
    </html>
  );
}
