"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

type LeagueId = "nfl" | "cfb" | "nba" | "ncaab" | "mlb";

// Same league → ESPN scoreboard mapping as nav.tsx.
const LEAGUES: { id: LeagueId; base: string; scoreboard: string }[] = [
  { id: "nfl", base: "", scoreboard: "football/nfl" },
  { id: "nba", base: "/nba", scoreboard: "basketball/nba" },
  { id: "mlb", base: "/mlb", scoreboard: "baseball/mlb" },
  { id: "cfb", base: "/cfb", scoreboard: "football/college-football" },
  { id: "ncaab", base: "/ncaab", scoreboard: "basketball/mens-college-basketball" },
];

function leagueOf(pathname: string): LeagueId {
  if (pathname === "/mlb" || pathname.startsWith("/mlb/")) return "mlb";
  if (pathname === "/ncaab" || pathname.startsWith("/ncaab/")) return "ncaab";
  if (pathname === "/nba" || pathname.startsWith("/nba/")) return "nba";
  if (pathname === "/cfb" || pathname.startsWith("/cfb/")) return "cfb";
  return "nfl";
}

type TeamRow = {
  abbr: string;
  logo?: string;
  score: string;
  winner: boolean;
};

type Game = {
  id: string;
  status: string;
  state: string; // "pre" | "in" | "post"
  teams: TeamRow[];
};

/**
 * ESPN-style score strip: a horizontally scrollable row of compact
 * game tiles for the current league, living inside the always-black
 * header (so dark-only styling is correct here by design). Data comes
 * from the same public ESPN scoreboard feed the nav's live dot uses;
 * renders nothing when the league has no games on the board.
 */
export default function ScoreStrip() {
  const pathname = usePathname();
  const league = leagueOf(pathname);
  const cfg = LEAGUES.find((l) => l.id === league) ?? LEAGUES[0];
  const [games, setGames] = useState<Game[]>([]);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const res = await fetch(
          `https://site.api.espn.com/apis/site/v2/sports/${cfg.scoreboard}/scoreboard`,
          { cache: "no-store" }
        );
        if (!res.ok) return;
        const d = await res.json();
        const parsed: Game[] = (d.events ?? [])
          .map((ev: any) => {
            const comp = ev.competitions?.[0];
            const type = comp?.status?.type ?? ev.status?.type ?? {};
            const competitors = [...(comp?.competitors ?? [])].sort(
              (a: any, b: any) =>
                a.homeAway === "away" ? -1 : b.homeAway === "away" ? 1 : 0
            );
            return {
              id: String(ev.id),
              status: type.shortDetail ?? type.detail ?? "",
              state: type.state ?? "pre",
              teams: competitors.map((c: any) => ({
                abbr: c.team?.abbreviation ?? "",
                logo: c.team?.logo,
                score: c.score != null ? String(c.score) : "",
                winner: Boolean(c.winner),
              })),
            } as Game;
          })
          .filter((g: Game) => g.teams.length === 2);
        if (!cancelled) setGames(parsed);
      } catch {
        /* silent — the strip just won't show */
      }
    };
    load();
    const t = setInterval(load, 120000);
    return () => {
      cancelled = true;
      clearInterval(t);
    };
  }, [cfg.scoreboard]);

  if (games.length === 0) return null;

  // MLB has no live page; its tiles link to the league home instead.
  const href = league === "mlb" ? "/mlb" : `${cfg.base}/live`;

  return (
    <div className="border-t border-white/10">
      <div className="mx-auto max-w-6xl px-4">
        <div className="flex overflow-x-auto" aria-label="Latest scores">
          {games.map((g) => {
            const live = g.state === "in";
            const final = g.state === "post";
            return (
              <Link
                key={g.id}
                href={href}
                className="min-w-[148px] shrink-0 border-l border-white/10 px-3 py-2 transition first:border-l-0 hover:bg-white/5"
              >
                <div
                  className={`flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-wider ${
                    live ? "text-red-500" : "text-zinc-500"
                  }`}
                >
                  {live && (
                    <span className="relative flex h-1.5 w-1.5">
                      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-500 opacity-75" />
                      <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-red-500" />
                    </span>
                  )}
                  {g.status}
                </div>
                {g.teams.map((t, i) => {
                  const bold = final && t.winner;
                  return (
                    <div key={i} className="mt-1 flex items-center gap-2">
                      {t.logo ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                          src={t.logo}
                          alt=""
                          width={18}
                          height={18}
                          loading="lazy"
                          className="h-[18px] w-[18px] shrink-0"
                        />
                      ) : (
                        <span className="h-[18px] w-[18px] shrink-0" />
                      )}
                      <span
                        className={`text-xs ${
                          bold ? "font-bold text-white" : "text-zinc-300"
                        }`}
                      >
                        {t.abbr}
                      </span>
                      <span
                        className={`tnum ml-auto text-xs ${
                          bold
                            ? "font-bold text-white"
                            : "font-semibold text-zinc-100"
                        }`}
                      >
                        {t.score}
                      </span>
                    </div>
                  );
                })}
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}
