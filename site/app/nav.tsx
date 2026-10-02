"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

type LeagueId = "nfl" | "cfb";

const LEAGUES: { id: LeagueId; label: string; base: string; espn: string }[] = [
  { id: "nfl", label: "NFL", base: "", espn: "nfl" },
  { id: "cfb", label: "College", base: "/cfb", espn: "college-football" },
];

const NAV_ITEMS = [
  { slug: "", label: "This week" },
  { slug: "/live", label: "Live", liveDot: true },
  { slug: "/pick-em", label: "Pick'em" },
  { slug: "/track-record", label: "Track record" },
  { slug: "/methodology", label: "Methodology" },
];

function leagueOf(pathname: string): LeagueId {
  return pathname === "/cfb" || pathname.startsWith("/cfb/") ? "cfb" : "nfl";
}

function switchHref(pathname: string, target: LeagueId): string {
  const current = leagueOf(pathname);
  if (current === target) return pathname;
  if (target === "cfb") return pathname === "/" ? "/cfb" : `/cfb${pathname}`;
  return pathname.replace(/^\/cfb/, "") || "/";
}

export default function Nav() {
  const pathname = usePathname();
  const league = leagueOf(pathname);
  const base = league === "cfb" ? "/cfb" : "";
  const espnLeague = league === "cfb" ? "college-football" : "nfl";
  const [anyLive, setAnyLive] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      try {
        const res = await fetch(
          `https://site.api.espn.com/apis/site/v2/sports/football/${espnLeague}/scoreboard`,
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
  }, [espnLeague]);

  return (
    <div className="flex max-w-full flex-wrap items-center gap-x-3 gap-y-2">
      {/* League toggle */}
      <div
        className="inline-flex shrink-0 rounded-lg border border-white/10 bg-zinc-900 p-0.5"
        role="tablist"
        aria-label="League"
      >
        {LEAGUES.map((l) => {
          const active = l.id === league;
          return (
            <Link
              key={l.id}
              href={switchHref(pathname, l.id)}
              role="tab"
              aria-selected={active}
              className={`rounded-md px-3 py-1.5 text-xs font-bold uppercase tracking-wider transition ${
                active ? "bg-amber-400 text-zinc-950" : "text-zinc-400 hover:text-white"
              }`}
            >
              {l.label}
            </Link>
          );
        })}
      </div>
      <nav className="flex max-w-full gap-1 overflow-x-auto" aria-label="Primary">
        {NAV_ITEMS.map((item) => {
          const href = `${base}${item.slug}` || "/";
          const active =
            item.slug === "" ? pathname === href || pathname === `${href}/` : pathname.startsWith(href);
          return (
            <Link
              key={item.slug}
              href={href}
              aria-current={active ? "page" : undefined}
              className={`flex items-center gap-1.5 whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium transition ${
                active
                  ? "bg-white/10 text-white"
                  : "text-zinc-400 hover:bg-white/5 hover:text-zinc-100"
              }`}
            >
              {item.liveDot && anyLive && (
                <span className="relative flex h-1.5 w-1.5">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400 opacity-75" />
                  <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-amber-400" />
                </span>
              )}
              {item.label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
