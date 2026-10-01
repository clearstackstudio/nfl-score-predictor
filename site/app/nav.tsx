"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NFL_LINKS = [
  { href: "/", label: "This week" },
  { href: "/pick-em", label: "Pick'em" },
  { href: "/track-record", label: "Track record" },
  { href: "/methodology", label: "Methodology" },
];

const CFB_LINKS = [
  { href: "/cfb", label: "This week" },
  { href: "/cfb/track-record", label: "Track record" },
  { href: "/cfb/methodology", label: "Methodology" },
];

export default function Nav() {
  const pathname = usePathname();
  const isCfb = pathname === "/cfb" || pathname.startsWith("/cfb/");
  const links = isCfb ? CFB_LINKS : NFL_LINKS;

  return (
    <div className="flex items-center gap-2">
      {/* Sport switcher */}
      <div
        className="flex rounded-lg border border-white/10 bg-white/5 p-0.5 light:border-zinc-200 light:bg-zinc-100"
        role="tablist"
        aria-label="Sport"
      >
        {[
          { href: "/", label: "NFL", active: !isCfb },
          { href: "/cfb", label: "College", active: isCfb },
        ].map((s) => (
          <Link
            key={s.label}
            href={s.href}
            role="tab"
            aria-selected={s.active}
            className={`rounded-md px-3 py-1.5 text-sm font-semibold transition ${
              s.active
                ? "bg-amber-400 text-zinc-950 light:bg-amber-500 light:text-white"
                : "text-zinc-400 hover:text-zinc-100 light:text-zinc-600 light:hover:text-zinc-900"
            }`}
          >
            {s.label}
          </Link>
        ))}
      </div>

      <nav className="flex max-w-full gap-1 overflow-x-auto" aria-label="Primary">
        {links.map((l) => {
          const active =
            l.href === "/" || l.href === "/cfb"
              ? pathname === l.href
              : pathname.startsWith(l.href);
          return (
            <Link
              key={l.href}
              href={l.href}
              aria-current={active ? "page" : undefined}
              className={`whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium transition ${
                active
                  ? "bg-white/10 text-white light:bg-zinc-950/[0.06] light:text-zinc-900"
                  : "text-zinc-400 hover:bg-white/5 hover:text-zinc-100 light:text-zinc-600 light:hover:bg-zinc-950/[0.04] light:hover:text-zinc-900"
              }`}
            >
              {l.label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
