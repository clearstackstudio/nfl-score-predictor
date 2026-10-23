"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";

type LeagueId = "nfl" | "cfb" | "nba" | "ncaab" | "mlb";

const LEAGUES: { id: LeagueId; label: string; base: string; scoreboard: string }[] = [
  { id: "nfl", label: "NFL", base: "", scoreboard: "football/nfl" },
  { id: "nba", label: "NBA", base: "/nba", scoreboard: "basketball/nba" },
  { id: "mlb", label: "MLB", base: "/mlb", scoreboard: "baseball/mlb" },
  { id: "cfb", label: "NCAAF", base: "/cfb", scoreboard: "football/college-football" },
  { id: "ncaab", label: "NCAAB", base: "/ncaab", scoreboard: "basketball/mens-college-basketball" },
];

// League tabs are grouped: pro leagues first, then college.
const LEAGUE_GROUPS: { label: string; ids: LeagueId[] }[] = [
  { label: "Pro", ids: ["nfl", "nba", "mlb"] },
  { label: "College", ids: ["cfb", "ncaab"] },
];

const NAV_ITEMS = [
  { slug: "", label: "This week", nbaLabel: "Today" },
  { slug: "/live", label: "Live", liveDot: true },
  { slug: "/pick-em", label: "Pick'em" },
  { slug: "/track-record", label: "Track record" },
  { slug: "/rankings", label: "Rankings" },
];

function leagueOf(pathname: string): LeagueId {
  if (pathname === "/mlb" || pathname.startsWith("/mlb/")) return "mlb";
  if (pathname === "/ncaab" || pathname.startsWith("/ncaab/")) return "ncaab";
  if (pathname === "/nba" || pathname.startsWith("/nba/")) return "nba";
  if (pathname === "/cfb" || pathname.startsWith("/cfb/")) return "cfb";
  return "nfl";
}

function switchHref(pathname: string, target: LeagueId): string {
  const current = leagueOf(pathname);
  if (current === target) return pathname;
  const stripped =
    current === "nfl" ? pathname : pathname.replace(/^\/(cfb|nba|ncaab|mlb)/, "") || "/";
  // Only league subpages exist under every league; anything else (e.g.
  // /accuracy, /disclaimer) falls back to the league home.
  // MLB has no live page, so /live is not a valid MLB slug.
  const leagueSlugs = ["", "/live", "/pick-em", "/track-record", "/rankings"];
  const mlbSlugs = ["", "/pick-em", "/track-record", "/rankings"];
  const valid = (target === "mlb" ? mlbSlugs : leagueSlugs).includes(stripped);
  if (target === "nfl") return valid ? stripped : "/";
  const base = target === "cfb" ? "/cfb" : target === "nba" ? "/nba" : target === "ncaab" ? "/ncaab" : "/mlb";
  return valid && stripped !== "/" ? `${base}${stripped}` : base;
}

export default function Nav() {
  const pathname = usePathname();
  const league = leagueOf(pathname);
  const leagueCfg = LEAGUES.find((l) => l.id === league) ?? LEAGUES[0];
  const base = leagueCfg.base;
  const scoreboard = leagueCfg.scoreboard;
  const [anyLive, setAnyLive] = useState(false);
  const navRef = useRef<HTMLElement>(null);

  // The nav row scrolls horizontally on narrow screens, and later tabs
  // (e.g. Rankings) can sit off-screen after a navigation resets the
  // row's scroll. Keep the active tab visible: scroll the row so the
  // current page's tab is in view whenever the route changes.
  useEffect(() => {
    const nav = navRef.current;
    if (!nav) return;
    const active = nav.querySelector('[aria-current="page"]');
    if (!active) return;
    const delta =
      active.getBoundingClientRect().left - nav.getBoundingClientRect().left;
    if (delta < 0 || delta > nav.clientWidth - 48) {
      nav.scrollLeft += delta - 8;
    }
  }, [pathname]);

  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      try {
        const res = await fetch(
          `https://site.api.espn.com/apis/site/v2/sports/${scoreboard}/scoreboard`,
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
  }, [scoreboard]);

  return (
    <div className="flex max-w-full flex-wrap items-center gap-x-3 gap-y-2">
      {/* League toggle — pro leagues and college leagues in separate groups */}
      <div className="flex shrink-0 items-start gap-3">
        {LEAGUE_GROUPS.map((group, gi) => (
          <div
            key={group.label}
            className={`flex flex-col gap-1 ${gi > 0 ? "border-l border-white/10 pl-3 light:border-zinc-300" : ""}`}
          >
            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-zinc-400 light:text-zinc-500">
              {group.label}
            </span>
            <div
              className="inline-flex rounded-lg border border-white/10 bg-zinc-900 p-0.5"
              role="tablist"
              aria-label={`${group.label} leagues`}
            >
              {group.ids.map((id) => {
                const l = LEAGUES.find((x) => x.id === id) ?? LEAGUES[0];
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
          </div>
        ))}
      </div>
      <nav ref={navRef} className="flex max-w-full gap-1 overflow-x-auto" aria-label="Primary">
        {NAV_ITEMS.filter(
          (item) => !(league === "mlb" && item.slug === "/live")
        ).map((item) => {
          const href = `${base}${item.slug}` || "/";
          const label = (league === "nba" || league === "mlb") && item.nbaLabel ? item.nbaLabel : item.label;
          const active =
            item.slug === "" ? pathname === href || pathname === `${href}/` : pathname.startsWith(href);
          return (
            <Link
              key={item.slug}
              href={href}
              aria-current={active ? "page" : undefined}
              className={`flex items-center gap-1.5 whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium transition ${
                active
                  ? "bg-white/10 text-white light:bg-zinc-900/10 light:text-zinc-900"
                  : "text-zinc-400 hover:bg-white/5 hover:text-zinc-100 light:text-zinc-500 light:hover:bg-zinc-900/5 light:hover:text-zinc-900"
              }`}
            >
              {item.liveDot && anyLive && (
                <span className="relative flex h-1.5 w-1.5">
                  <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400 opacity-75" />
                  <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-amber-400" />
                </span>
              )}
              {label}
            </Link>
          );
        })}
        <Link
          href="/recaps"
          aria-current={pathname === "/recaps" || pathname.startsWith("/recaps/") ? "page" : undefined}
          className={`flex items-center gap-1.5 whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium transition ${
            pathname === "/recaps" || pathname.startsWith("/recaps/")
              ? "bg-white/10 text-white light:bg-zinc-900/10 light:text-zinc-900"
              : "text-zinc-400 hover:bg-white/5 hover:text-zinc-100 light:text-zinc-500 light:hover:bg-zinc-900/5 light:hover:text-zinc-900"
          }`}
        >
          Recaps
        </Link>
        <Link
          href="/tracker"
          aria-current={pathname === "/tracker" ? "page" : undefined}
          className={`flex items-center gap-1.5 whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium transition ${
            pathname === "/tracker"
              ? "bg-white/10 text-white light:bg-zinc-900/10 light:text-zinc-900"
              : "text-zinc-400 hover:bg-white/5 hover:text-zinc-100 light:text-zinc-500 light:hover:bg-zinc-900/5 light:hover:text-zinc-900"
          }`}
        >
          Tracker
        </Link>
        <Link
          href="/accuracy"
          aria-current={pathname === "/accuracy" ? "page" : undefined}
          className={`flex items-center gap-1.5 whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium transition ${
            pathname === "/accuracy"
              ? "bg-white/10 text-white light:bg-zinc-900/10 light:text-zinc-900"
              : "text-zinc-400 hover:bg-white/5 hover:text-zinc-100 light:text-zinc-500 light:hover:bg-zinc-900/5 light:hover:text-zinc-900"
          }`}
        >
          Accuracy
        </Link>
      </nav>
    </div>
  );
}
