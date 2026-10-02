"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

const LINKS = [
  { href: "/", label: "This week" },
  { href: "/live", label: "Live", liveDot: true },
  { href: "/pick-em", label: "Pick'em" },
  { href: "/track-record", label: "Track record" },
  { href: "/methodology", label: "Methodology" },
];

export default function Nav() {
  const pathname = usePathname();
  const [anyLive, setAnyLive] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      try {
        const res = await fetch(
          "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
          { cache: "no-store" }
        );
        if (!res.ok) return;
        const d = await res.json();
        const live = (d.events ?? []).some(
          (ev: any) => ev.competitions?.[0]?.status?.type?.state === "in"
        );
        if (!cancelled) setAnyLive(live);
      } catch {
        /* silent — the dot just won't show */
      }
    };
    check();
    const t = setInterval(check, 120000);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, []);

  return (
    <nav className="flex max-w-full gap-1 overflow-x-auto" aria-label="Primary">
      {LINKS.map((l) => {
        const active = l.href === "/" ? pathname === "/" : pathname.startsWith(l.href);
        return (
          <Link
            key={l.href}
            href={l.href}
            aria-current={active ? "page" : undefined}
            className={`flex items-center gap-1.5 whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium transition ${
              active
                ? "bg-white/10 text-white"
                : "text-zinc-400 hover:bg-white/5 hover:text-zinc-100"
            }`}
          >
            {l.liveDot && anyLive && (
              <span className="relative flex h-1.5 w-1.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400 opacity-75" />
                <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-amber-400" />
              </span>
            )}
            {l.label}
          </Link>
        );
      })}
    </nav>
  );
}
