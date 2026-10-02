"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  fetchScoreboard,
  fetchGameDetail,
  type LiveGame,
  type GameDetail,
  type League,
} from "../lib/espn";

function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-amber-400/90">
      <span className="relative flex h-2 w-2">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400 opacity-60" />
        <span className="relative inline-flex h-2 w-2 rounded-full bg-amber-400" />
      </span>
      {children}
    </div>
  );
}

function TeamMark({ logo, abbr, size = 28 }: { logo: string; abbr: string; size?: number }) {
  if (!logo) {
    return (
      <span
        className="inline-flex shrink-0 items-center justify-center rounded-full bg-zinc-800 font-mono font-bold text-zinc-400"
        style={{ width: size, height: size, fontSize: size * 0.35 }}
      >
        {abbr.slice(0, 2)}
      </span>
    );
  }
  return (
    <img src={logo} alt={`${abbr} logo`} width={size} height={size} className="shrink-0" loading="lazy" />
  );
}

function WinProbChart({ points, homeAbbr, awayAbbr }: { points: { homeWinPct: number }[]; homeAbbr: string; awayAbbr: string }) {
  const { path, area } = useMemo(() => {
    if (points.length < 2) return { path: "", area: "" };
    const W = 600, H = 120, PAD = 8;
    const x = (i: number) => PAD + (i / (points.length - 1)) * (W - 2 * PAD);
    const y = (p: number) => PAD + (1 - p) * (H - 2 * PAD);
    const pts = points.map((pt, i) => `${x(i).toFixed(1)},${y(pt.homeWinPct).toFixed(1)}`);
    return {
      path: `M${pts.join(" L")}`,
      area: `M${x(0).toFixed(1)},${H - PAD} L${pts.join(" L")} L${x(points.length - 1).toFixed(1)},${H - PAD} Z`,
    };
  }, [points]);
  if (points.length < 2) return null;
  const last = points[points.length - 1].homeWinPct;
  return (
    <div className="rounded-2xl border border-white/10 bg-zinc-950/70 p-5">
      <div className="flex items-baseline justify-between">
        <div className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
          Win probability
        </div>
        <div className="tnum font-mono text-base font-bold">
          <span className="text-zinc-400">{awayAbbr} {Math.round((1 - last) * 100)}%</span>
          <span className="mx-2 text-zinc-700">·</span>
          <span className="text-amber-300">{homeAbbr} {Math.round(last * 100)}%</span>
        </div>
      </div>
      <svg viewBox="0 0 600 120" className="mt-3 h-32 w-full" preserveAspectRatio="none" role="img" aria-label="Win probability chart">
        <line x1="0" y1="60" x2="600" y2="60" stroke="#3f3f46" strokeDasharray="4 4" strokeWidth="1" />
        <path d={area} fill="rgba(251,191,36,0.12)" />
        <path d={path} fill="none" stroke="#fbbf24" strokeWidth="2" vectorEffect="non-scaling-stroke" />
      </svg>
      <div className="mt-2 flex justify-between text-[11px] font-medium text-zinc-500">
        <span>Kickoff</span>
        <span>Now</span>
      </div>
    </div>
  );
}

function GameCard({ g, selected, onSelect }: { g: LiveGame; selected: boolean; onSelect: () => void }) {
  return (
    <button
      onClick={onSelect}
      className={`w-64 shrink-0 snap-start rounded-xl border p-3.5 text-left transition ${
        selected
          ? "border-amber-400/60 bg-amber-400/[0.08]"
          : "border-white/10 bg-zinc-900/60 hover:border-white/25"
      }`}
    >
      <div className="flex items-center justify-between">
        <span className={`text-[11px] font-bold uppercase tracking-wider ${g.state === "in" ? "text-amber-400" : "text-zinc-500"}`}>
          {g.state === "in" ? "● Live" : g.state === "post" ? "Final" : "Upcoming"}
        </span>
        <span className="text-[11px] text-zinc-500">{g.detail}</span>
      </div>
      <div className="mt-2.5 space-y-1.5">
        {[
          { abbr: g.awayAbbr, name: g.awayName, score: g.awayScore, logo: g.awayLogo },
          { abbr: g.homeAbbr, name: g.homeName, score: g.homeScore, logo: g.homeLogo },
        ].map((t) => (
          <div key={t.abbr} className="flex items-center gap-2">
            <TeamMark logo={t.logo} abbr={t.abbr} size={22} />
            <span className="flex-1 truncate text-sm font-semibold">{t.abbr}</span>
            <span className="tnum font-mono text-sm font-bold">{t.score}</span>
          </div>
        ))}
      </div>
    </button>
  );
}

function PlayRow({ p, homeAbbr }: { p: GameDetail["drives"][number]["plays"][number]; homeAbbr: string }) {
  return (
    <div
      className={`flex gap-4 border-b border-white/5 px-5 py-3.5 last:border-0 ${
        p.scoringPlay ? "border-l-2 border-l-amber-400 bg-amber-400/[0.07]" : ""
      }`}
    >
      <div className="w-[72px] shrink-0 pt-0.5">
        <div className="tnum font-mono text-xs font-bold text-zinc-300">
          Q{p.period || "–"}
        </div>
        <div className="tnum font-mono text-xs text-zinc-500">{p.clock}</div>
      </div>
      <div className="min-w-0 flex-1">
        <p className={`text-sm leading-relaxed ${p.scoringPlay ? "font-semibold text-amber-100" : "text-zinc-200"}`}>
          {p.scoringPlay && <span className="mr-1.5">🏈</span>}
          {p.turnover && !p.scoringPlay && <span className="mr-1.5">🔄</span>}
          {p.text}
        </p>
        {p.downDistance && (
          <p className="mt-1 font-mono text-[11px] uppercase tracking-wide text-zinc-500">{p.downDistance}</p>
        )}
      </div>
      <div className="tnum shrink-0 pt-0.5 font-mono text-xs font-semibold text-zinc-400">
        {p.awayScore}–{p.homeScore}
      </div>
    </div>
  );
}

export default function LivePage({ league = "nfl" as League, basePath = "" }: { league?: League; basePath?: string }) {
  const [games, setGames] = useState<LiveGame[] | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<GameDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  const loadBoard = useCallback(async () => {
    try {
      const gs = await fetchScoreboard(league);
      setGames(gs);
      setError(null);
      setSelectedId((prev) => {
        if (prev && gs.some((g) => g.id === prev)) return prev;
        const live = gs.find((g) => g.state === "in");
        return (live ?? gs[0])?.id ?? null;
      });
    } catch {
      setError("Could not reach the live score feed. Try again in a bit.");
    }
  }, [league]);

  const loadDetail = useCallback(async (id: string) => {
    try {
      const d = await fetchGameDetail(league, id);
      setDetail(d);
      setLastUpdate(new Date());
    } catch {
      /* keep previous detail on transient failure */
    }
  }, [league]);

  useEffect(() => {
    loadBoard();
    const t = setInterval(loadBoard, 60000);
    return () => clearInterval(t);
  }, [loadBoard]);

  useEffect(() => {
    if (!selectedId) return;
    setDetail(null);
    loadDetail(selectedId);
    const t = setInterval(() => loadDetail(selectedId), 30000);
    return () => clearInterval(t);
  }, [selectedId, loadDetail]);

  const sorted = useMemo(() => {
    if (!games) return [];
    const rank = { in: 0, pre: 1, post: 2 } as const;
    return [...games].sort((a, b) => rank[a.state] - rank[b.state]);
  }, [games]);
  const liveCount = games?.filter((g) => g.state === "in").length ?? 0;

  return (
    <div>
      <Eyebrow>{liveCount > 0 ? `${liveCount} game${liveCount > 1 ? "s" : ""} live now · auto-refreshes` : "Auto-refreshes during games"}</Eyebrow>
      <h1 className="mt-3 font-display text-5xl font-semibold uppercase leading-[0.95] tracking-wide sm:text-6xl">
        Live <span className="text-amber-400">play-by-play</span>
      </h1>
      <p className="mt-4 max-w-2xl text-[15px] leading-relaxed text-zinc-400">
        Every snap, as it happens — pulled live from the ESPN feed and refreshed
        every 30 seconds. Scores, drives, and win probability update together.
      </p>

      {error && (
        <p className="mt-6 rounded-xl border border-red-400/25 bg-red-400/10 px-4 py-3 text-sm text-red-200">
          {error}
        </p>
      )}

      {!games ? (
        <div className="mt-8 space-y-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-20 animate-pulse rounded-xl bg-zinc-900/60" />
          ))}
        </div>
      ) : games.length === 0 ? (
        <p className="mt-8 rounded-xl border border-white/10 bg-zinc-900/40 p-6 text-sm text-zinc-400">
          No games on the schedule right now. Check back on game day.
        </p>
      ) : (
        <>
          <div className="mt-8 flex snap-x gap-3 overflow-x-auto pb-2">
            {sorted.map((g) => (
              <GameCard key={g.id} g={g} selected={g.id === selectedId} onSelect={() => setSelectedId(g.id)} />
            ))}
          </div>

          {detail ? (
            <div className="mt-6">
              {/* Score header */}
              <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-gradient-to-b from-zinc-900/70 to-zinc-900/30 p-5">
                {[
                  { abbr: detail.game.awayAbbr, name: detail.game.awayName, score: detail.game.awayScore, logo: detail.game.awayLogo },
                  { abbr: detail.game.homeAbbr, name: detail.game.homeName, score: detail.game.homeScore, logo: detail.game.homeLogo },
                ].map((t, i) => (
                  <div key={t.abbr} className={`flex flex-1 items-center gap-3 ${i === 1 ? "flex-row-reverse text-right" : ""}`}>
                    <TeamMark logo={t.logo} abbr={t.abbr} size={44} />
                    <div className="min-w-0">
                      <div className="truncate text-sm font-bold sm:text-base">{t.name}</div>
                      <div className="text-xs text-zinc-500">{t.abbr}</div>
                    </div>
                    <div className="tnum font-display text-4xl font-semibold sm:text-5xl">{t.score}</div>
                  </div>
                ))}
                <div className="px-4 text-center">
                  <div className={`text-sm font-bold ${detail.game.state === "in" ? "text-amber-400" : "text-zinc-400"}`}>
                    {detail.game.state === "in" ? detail.game.detail || "Live" : detail.game.state === "post" ? "Final" : detail.game.detail}
                  </div>
                  {lastUpdate && (
                    <div className="mt-1 text-[11px] text-zinc-600">
                      updated {lastUpdate.toLocaleTimeString([], { hour: "numeric", minute: "2-digit", second: "2-digit" })}
                    </div>
                  )}
                </div>
              </div>

              <div className="mt-4">
                <WinProbChart points={detail.winProb} homeAbbr={detail.game.homeAbbr} awayAbbr={detail.game.awayAbbr} />
              </div>

              {/* Drives */}
              <h2 className="mt-8 font-display text-2xl font-semibold uppercase tracking-wide">
                Drives
              </h2>
              {detail.drives.length === 0 ? (
                <p className="mt-3 text-sm text-zinc-500">No drives yet — the game hasn&apos;t started.</p>
              ) : (
                <div className="mt-4 space-y-4">
                  {detail.drives.map((dr, di) => (
                    <section key={dr.id} className="overflow-hidden rounded-2xl border border-white/10 bg-zinc-900/40">
                      <div className="flex items-center justify-between gap-3 border-b border-white/5 bg-zinc-950/60 px-4 py-3">
                        <div className="flex min-w-0 items-center gap-2.5">
                          <TeamMark logo={dr.teamLogo} abbr={dr.teamAbbr} size={24} />
                          <div className="min-w-0">
                            <div className="truncate text-sm font-semibold">{dr.description || `${dr.teamAbbr} drive`}</div>
                          </div>
                        </div>
                        <div className="flex shrink-0 items-center gap-2">
                          {di === 0 && detail.game.state === "in" && (
                            <span className="rounded bg-amber-400/15 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-amber-300">
                              current
                            </span>
                          )}
                          {dr.result && (
                            <span className={`rounded px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${dr.isScore ? "bg-emerald-400/15 text-emerald-300" : "bg-zinc-800 text-zinc-400"}`}>
                              {dr.result}
                            </span>
                          )}
                        </div>
                      </div>
                      <div>
                        {dr.plays.map((p) => (
                          <PlayRow key={p.id} p={p} homeAbbr={detail.game.homeAbbr} />
                        ))}
                      </div>
                    </section>
                  ))}
                </div>
              )}
            </div>
          ) : (
            selectedId && (
              <div className="mt-6 h-64 animate-pulse rounded-2xl bg-zinc-900/60" />
            )
          )}
        </>
      )}

      <p className="mt-8 max-w-2xl text-xs leading-relaxed text-zinc-600">
        Live data via ESPN. Play-by-play and win probability refresh automatically
        while games are in progress; pre-game and final states update on the minute.
      </p>
    </div>
  );
}
