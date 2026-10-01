"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const LINKS = [
  { href: "/", label: "This week" },
  { href: "/pick-em", label: "Pick'em" },
  { href: "/track-record", label: "Track record" },
  { href: "/methodology", label: "Methodology" },
];

export default function Nav() {
  const pathname = usePathname();
  return (
    <nav className="flex max-w-full gap-1 overflow-x-auto" aria-label="Primary">
      {LINKS.map((l) => {
        const active = l.href === "/" ? pathname === "/" : pathname.startsWith(l.href);
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
  );
}
