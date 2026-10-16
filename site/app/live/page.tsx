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
    <div className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-amber-400/90 light:text-amber-700">
      <span className="relative flex h-2 w-2">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-amber-400 opacity-60" />
        <span className="relative inline-flex h-2 w-2 rounded-full bg-amber-400 light:bg-amber-600" />
      </span>
      {children}
    </div>
  );
}

function TeamMark({ logo, abbr, size = 28 }: { logo: string; abbr: string; size?: number }) {
  if (!logo) {
    return (
      <span
        className="inline-flex shrink-0 items-center justify-center rounded-full bg-zinc-800 font-mono font-bold text-zinc-400 light:bg-zinc-200 light:text-zinc-600"
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
    <div className="rounded-2xl border border-white/15 bg-zinc-900/70 p-5 light:border-zinc-200 light:bg-white">
      <div className="flex items-baseline justify-between">
        <div className="text-xs font-semibold uppercase tracking-wider text-zinc-300 light:text-zinc-600">
          Win probability
        </div>
        <div className="tnum font-mono text-base font-bold">
          <span className="text-zinc-300 light:text-zinc-600">{awayAbbr} {Math.round((1 - last) * 100)}%</span>
          <span className="mx-2 text-zinc-600 light:text-zinc-300">·</span>
          <span className="text-amber-300 light:text-amber-600">{homeAbbr} {Math.round(last * 100)}%</span>
        </div>
      </div>
      <svg viewBox="0 0 600 120" className="mt-3 h-32 w-full" preserveAspectRatio="none" role="img" aria-label="Win probability chart">
        <line x1="0" y1="60" x2="600" y2="60" stroke="#52525b" strokeDasharray="4 4" strokeWidth="1" />
        <path d={area} fill="rgba(251,191,36,0.15)" />
        <path d={path} fill="none" stroke="#fbbf24" strokeWidth="2.5" vectorEffect="non-scaling-stroke" />
      </svg>
      <div className="mt-2 flex justify-between text-[11px] font-medium text-zinc-400 light:text-zinc-500">
        <span>Kickoff</span>
        <span>Now</span>
      </div>
    </div>
  );
}

function BallIcon({ size = 13 }: { size?: number }) {
  return (
    <svg aria-label="Possession" role="img" width={size} height={size} viewBox="0 0 16 16" className="shrink-0 text-amber-400 light:text-amber-600">
      <ellipse cx="8" cy="8" rx="7" ry="4.6" transform="rotate(-30 8 8)" fill="currentColor" />
      <line x1="6.2" y1="6.4" x2="9.8" y2="9.6" stroke="#09090b" strokeWidth="1.1" strokeLinecap="round" transform="rotate(-30 8 8)" />
      <line x1="8" y1="4.6" x2="8" y2="6.2" stroke="#09090b" strokeWidth="1" strokeLinecap="round" transform="rotate(-30 8 8)" />
      <line x1="8" y1="9.8" x2="8" y2="11.4" stroke="#09090b" strokeWidth="1" strokeLinecap="round" transform="rotate(-30 8 8)" />
    </svg>
  );
}

/** Column header for period i (0-based): Q1..Q4, then OT, 2OT… (basketball: P1, P2…). */
function periodLabel(i: number, football: boolean): string {
  if (!football) return `P${i + 1}`;
  return i < 4 ? `Q${i + 1}` : i === 4 ? "OT" : `${i - 3}OT`;
}

/** One game in the ESPN-style scoreboard list: status rail + team rows + linescore. */
function ScoreboardRow({ g, selected, onSelect, football }: { g: LiveGame; selected: boolean; onSelect: () => void; football: boolean }) {
  const teams = [
    { abbr: g.awayAbbr, score: g.awayScore, logo: g.awayLogo, record: g.awayRecord, lines: g.awayLinescores },
    { abbr: g.homeAbbr, score: g.homeScore, logo: g.homeLogo, record: g.homeRecord, lines: g.homeLinescores },
  ];
  const periods = Math.max(g.awayLinescores.length, g.homeLinescores.length);
  return (
    <button
      onClick={onSelect}
      aria-pressed={selected}
      className={`block w-full text-left transition ${
        selected
          ? "bg-amber-400/[0.08] light:bg-amber-400/15"
          : "hover:bg-white/[0.04] light:hover:bg-zinc-50"
      }`}
    >
      <div className="flex">
        <div className="flex w-[92px] shrink-0 flex-col justify-center border-r border-white/10 px-3 py-2.5 light:border-zinc-200">
          <span className={`text-[11px] font-bold uppercase tracking-wider ${g.state === "in" ? "text-amber-400 light:text-amber-600" : "text-zinc-400 light:text-zinc-500"}`}>
            {g.state === "in" ? "● Live" : g.state === "post" ? "Final" : "Upcoming"}
          </span>
          {g.detail && (
            <span className="tnum mt-0.5 text-[11px] leading-tight text-zinc-400 light:text-zinc-500">{g.detail}</span>
          )}
        </div>
        <div className="min-w-0 flex-1 py-1">
          {periods > 0 && (
            <div className="hidden items-center px-3 pt-1 sm:flex" aria-hidden="true">
              <span className="flex-1" />
              {Array.from({ length: periods }, (_, i) => (
                <span key={i} className="w-7 text-right text-[10px] font-semibold uppercase tracking-wider text-zinc-500 light:text-zinc-400">
                  {periodLabel(i, football)}
                </span>
              ))}
              <span className="w-9 text-right text-[10px] font-semibold uppercase tracking-wider text-zinc-500 light:text-zinc-400">T</span>
            </div>
          )}
          {teams.map((t) => {
            const hasBall = g.state === "in" && g.possessionAbbr === t.abbr;
            return (
              <div key={t.abbr} className="flex items-center gap-2 px-3 py-1.5">
                <TeamMark logo={t.logo} abbr={t.abbr} size={22} />
                <span className="flex min-w-0 items-center gap-1.5 text-sm font-semibold text-zinc-100 light:text-zinc-900">
                  {t.abbr}
                  {hasBall && (football ? <BallIcon /> : <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-amber-400 light:bg-amber-600" aria-label="Possession" />)}
                  {t.record && <span className="truncate text-[11px] font-normal text-zinc-500 light:text-zinc-400">{t.record}</span>}
                </span>
                <span className="ml-auto flex items-baseline">
                  {t.lines.map((ls, i) => (
                    <span key={i} className="tnum hidden w-7 text-right font-mono text-xs text-zinc-400 sm:inline-block light:text-zinc-500">
                      {ls}
                    </span>
                  ))}
                  <span className="tnum w-9 text-right font-mono text-sm font-bold text-white light:text-zinc-900">{t.score}</span>
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </button>
  );
}

interface LinescoreTeam {
  abbr: string;
  name: string;
  logo: string;
  record: string;
  lines: string[];
  total: string;
}

/** Gamecast-style linescore table: team rows × period columns + total. */
function LinescoreTable({ teams, periods, football }: { teams: LinescoreTeam[]; periods: number; football: boolean }) {
  return (
    <table className="w-full border-collapse">
      <thead>
        <tr className="border-b border-white/10 light:border-zinc-200">
          <th className="pb-2 text-left text-[11px] font-semibold uppercase tracking-wider text-zinc-400 light:text-zinc-500">Team</th>
          {Array.from({ length: periods }, (_, i) => (
            <th key={i} className="tnum hidden w-9 pb-2 text-right font-mono text-[11px] font-semibold uppercase tracking-wider text-zinc-400 sm:table-cell light:text-zinc-500">
              {periodLabel(i, football)}
            </th>
          ))}
          <th className="tnum w-12 pb-2 text-right font-mono text-[11px] font-semibold uppercase tracking-wider text-zinc-300 light:text-zinc-600">T</th>
        </tr>
      </thead>
      <tbody>
        {teams.map((t) => (
          <tr key={t.abbr} className="border-b border-white/5 last:border-0 light:border-zinc-100">
            <td className="py-2.5 pr-2">
              <div className="flex min-w-0 items-center gap-2.5">
                <TeamMark logo={t.logo} abbr={t.abbr} size={30} />
                <span className="truncate text-sm font-bold text-white light:text-zinc-900 sm:text-base">{t.name}</span>
                {t.record && <span className="hidden shrink-0 text-xs text-zinc-500 md:inline light:text-zinc-400">{t.record}</span>}
              </div>
            </td>
            {Array.from({ length: periods }, (_, i) => (
              <td key={i} className="tnum hidden w-9 py-2.5 text-right align-middle font-mono text-sm text-zinc-300 sm:table-cell light:text-zinc-600">
                {t.lines[i] ?? "–"}
              </td>
            ))}
            <td className="tnum w-12 py-2.5 text-right align-middle font-display text-2xl font-semibold text-white light:text-zinc-900">
              {t.total}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function PlayRow({ p, homeAbbr }: { p: GameDetail["drives"][number]["plays"][number]; homeAbbr: string }) {
  return (
    <div
      className={`flex gap-4 border-b border-white/10 px-5 py-3.5 last:border-0 light:border-zinc-100 ${
        p.scoringPlay ? "border-l-2 border-l-amber-400 bg-amber-400/[0.07]" : ""
      }`}
    >
      <div className="w-[72px] shrink-0 pt-0.5">
        <div className="tnum font-mono text-xs font-bold text-zinc-200 light:text-zinc-800">
          Q{p.period || "–"}
        </div>
        <div className="tnum font-mono text-xs text-zinc-400 light:text-zinc-500">{p.clock}</div>
      </div>
      <div className="min-w-0 flex-1">
        <p className={`text-sm leading-relaxed ${p.scoringPlay ? "font-semibold text-amber-100 light:text-amber-800" : "text-zinc-100 light:text-zinc-900"}`}>
          {p.scoringPlay && <span className="mr-1.5">🏈</span>}
          {p.turnover && !p.scoringPlay && <span className="mr-1.5">🔄</span>}
          {p.text}
        </p>
        {p.downDistance && (
          <p className="mt-1 font-mono text-[11px] uppercase tracking-wide text-zinc-400 light:text-zinc-500">{p.downDistance}</p>
        )}
      </div>
      <div className="tnum shrink-0 pt-0.5 font-mono text-xs font-semibold text-zinc-300 light:text-zinc-600">
        {p.awayScore}–{p.homeScore}
      </div>
    </div>
  );
}

function DrivesSection({ detail }: { detail: GameDetail }) {
  if (detail.drives.length === 0) {
    return <p className="mt-3 text-sm text-zinc-400 light:text-zinc-600">No drives yet — the game hasn&apos;t started.</p>;
  }
  return (
    <div className="mt-4 space-y-4">
      {detail.drives.map((dr, di) => (
        <section key={dr.id} className="overflow-hidden rounded-2xl border border-white/15 bg-zinc-900/70 light:border-zinc-200 light:bg-white">
          <div className="flex items-center justify-between gap-3 border-b border-white/10 bg-zinc-950/70 px-5 py-3 light:border-zinc-200 light:bg-zinc-50">
            <div className="flex min-w-0 items-center gap-2.5">
              <TeamMark logo={dr.teamLogo} abbr={dr.teamAbbr} size={24} />
              <div className="min-w-0">
                <div className="truncate text-sm font-semibold">{dr.description || `${dr.teamAbbr} drive`}</div>
              </div>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              {di === 0 && detail.game.state === "in" && (
                <span className="rounded bg-amber-400/15 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-amber-300 light:text-amber-700">
                  current
                </span>
              )}
              {dr.result && (
                <span className={`rounded px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${dr.isScore ? "bg-emerald-400/15 text-emerald-300 light:text-emerald-700" : "bg-zinc-800 text-zinc-400 light:bg-zinc-200 light:text-zinc-600"}`}>
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
  );
}

function ScoringSection({ detail, football }: { detail: GameDetail; football: boolean }) {
  const logoFor = (abbr: string) =>
    abbr === detail.game.awayAbbr ? detail.game.awayLogo : abbr === detail.game.homeAbbr ? detail.game.homeLogo : "";
  return (
    <div className="mt-4 overflow-hidden rounded-2xl border border-white/15 bg-zinc-900/70 light:border-zinc-200 light:bg-white">
      {detail.scoringPlays.map((p) => (
        <div key={p.id} className="flex gap-4 border-b border-white/10 px-5 py-3.5 last:border-0 light:border-zinc-100">
          <div className="w-[72px] shrink-0 pt-0.5">
            <div className="tnum font-mono text-xs font-bold text-zinc-200 light:text-zinc-800">
              {p.period ? (football ? `Q${p.period}` : `P${p.period}`) : "–"}
            </div>
            <div className="tnum font-mono text-xs text-zinc-400 light:text-zinc-500">{p.clock}</div>
          </div>
          <TeamMark logo={logoFor(p.teamAbbr)} abbr={p.teamAbbr} size={24} />
          <p className="min-w-0 flex-1 text-sm font-medium leading-relaxed text-zinc-100 light:text-zinc-900">{p.text}</p>
          <div className="tnum shrink-0 pt-0.5 font-mono text-xs font-semibold text-zinc-300 light:text-zinc-600">
            {p.awayScore}–{p.homeScore}
          </div>
        </div>
      ))}
    </div>
  );
}

function StatsSection({ detail }: { detail: GameDetail }) {
  const logoFor = (abbr: string) =>
    abbr === detail.game.awayAbbr ? detail.game.awayLogo : abbr === detail.game.homeAbbr ? detail.game.homeLogo : "";
  return (
    <div className="mt-4 grid items-start gap-4 lg:grid-cols-[1fr_320px]">
      {detail.teamStats.length > 0 && (
        <section className="overflow-hidden rounded-2xl border border-white/15 bg-zinc-900/70 light:border-zinc-200 light:bg-white">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-white/10 bg-zinc-950/70 light:border-zinc-200 light:bg-zinc-50">
                <th className="px-5 py-3 text-left">
                  <span className="flex items-center gap-2 text-sm font-bold text-white light:text-zinc-900">
                    <TeamMark logo={detail.game.awayLogo} abbr={detail.game.awayAbbr} size={22} />
                    {detail.game.awayAbbr}
                  </span>
                </th>
                <th className="px-2 py-3 text-center text-[11px] font-semibold uppercase tracking-wider text-zinc-400 light:text-zinc-500">Team stats</th>
                <th className="px-5 py-3 text-right">
                  <span className="flex items-center justify-end gap-2 text-sm font-bold text-white light:text-zinc-900">
                    {detail.game.homeAbbr}
                    <TeamMark logo={detail.game.homeLogo} abbr={detail.game.homeAbbr} size={22} />
                  </span>
                </th>
              </tr>
            </thead>
            <tbody>
              {detail.teamStats.map((r) => (
                <tr key={r.label} className="border-b border-white/5 last:border-0 light:border-zinc-100">
                  <td className="tnum px-5 py-2.5 font-mono text-sm font-semibold text-zinc-100 light:text-zinc-900">{r.awayValue || "–"}</td>
                  <td className="px-2 py-2.5 text-center text-xs text-zinc-400 light:text-zinc-500">{r.label}</td>
                  <td className="tnum px-5 py-2.5 text-right font-mono text-sm font-semibold text-zinc-100 light:text-zinc-900">{r.homeValue || "–"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
      {detail.leaders.length > 0 && (
        <div className="space-y-4">
          {detail.leaders.map((tl) => (
            <section key={tl.teamAbbr} className="rounded-2xl border border-white/15 bg-zinc-900/70 p-5 light:border-zinc-200 light:bg-white">
              <div className="flex items-center gap-2">
                <TeamMark logo={logoFor(tl.teamAbbr)} abbr={tl.teamAbbr} size={24} />
                <h3 className="text-sm font-bold text-white light:text-zinc-900">{tl.teamAbbr} leaders</h3>
              </div>
              <dl className="mt-3 space-y-2.5">
                {tl.leaders.map((l) => (
                  <div key={l.category} className="flex items-baseline justify-between gap-3">
                    <dt className="shrink-0 text-[11px] font-semibold uppercase tracking-wider text-zinc-400 light:text-zinc-500">{l.category}</dt>
                    <dd className="tnum min-w-0 text-right text-sm text-zinc-200 light:text-zinc-800">
                      <span className="font-semibold">{l.player}</span>
                      {l.value && <span className="ml-1.5 font-mono text-xs text-zinc-400 light:text-zinc-500">{l.value}</span>}
                    </dd>
                  </div>
                ))}
              </dl>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}

type TabId = "plays" | "scoring" | "stats";

export default function LivePage({ league = "nfl" as League, basePath = "" }: { league?: League; basePath?: string }) {
  const [games, setGames] = useState<LiveGame[] | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<GameDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [tab, setTab] = useState<TabId>("plays");
  const football = league === "nfl" || league === "college-football";

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
    setTab("plays");
    loadDetail(selectedId);
    const t = setInterval(() => loadDetail(selectedId), 30000);
    return () => clearInterval(t);
  }, [selectedId, loadDetail]);

  const sorted = useMemo(() => {
    if (!games) return [];
    const rank = { post: 0, in: 1, pre: 2 } as const;
    return [...games].sort((a, b) => rank[a.state] - rank[b.state]);
  }, [games]);
  const liveCount = games?.filter((g) => g.state === "in").length ?? 0;
  const boardGame = games?.find((g) => g.id === selectedId) ?? null;

  // Tabs degrade with the feed: basketball summaries carry no drives, and a
  // pre-game feed has nothing yet — show only tabs that have content.
  const tabs: { id: TabId; label: string }[] = detail
    ? [
        ...(detail.drives.length > 0 ? [{ id: "plays" as TabId, label: "Play-by-Play" }] : []),
        ...(detail.scoringPlays.length > 0 ? [{ id: "scoring" as TabId, label: "Scoring Summary" }] : []),
        ...(detail.teamStats.length > 0 || detail.leaders.length > 0
          ? [{ id: "stats" as TabId, label: "Team Stats" }]
          : []),
      ]
    : [];
  const activeTab: TabId | null = tabs.some((t) => t.id === tab) ? tab : (tabs[0]?.id ?? null);

  // Linescore + live situation: prefer the detail feed, fall back to the
  // scoreboard row (the summary feed carries no situation object).
  const awayLines = detail
    ? detail.awayLinescores.length > 0
      ? detail.awayLinescores
      : (boardGame?.awayLinescores ?? [])
    : [];
  const homeLines = detail
    ? detail.homeLinescores.length > 0
      ? detail.homeLinescores
      : (boardGame?.homeLinescores ?? [])
    : [];
  const headerPeriods = Math.max(awayLines.length, homeLines.length);
  const situationText =
    detail && detail.game.state === "in"
      ? (boardGame?.situationText ?? detail.game.situationText ?? null)
      : null;

  return (
    <div>
      <Eyebrow>{liveCount > 0 ? `${liveCount} game${liveCount > 1 ? "s" : ""} live now · auto-refreshes` : "Auto-refreshes during games"}</Eyebrow>
      <h1 className="mt-3 font-display text-5xl font-semibold uppercase leading-[0.95] tracking-wide sm:text-6xl">
        Live <span className="text-amber-400 light:text-amber-500">play-by-play</span>
      </h1>
      <p className="mt-4 max-w-2xl text-[15px] leading-relaxed text-zinc-300 light:text-zinc-600">
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
            <div key={i} className="h-20 animate-pulse rounded-xl bg-zinc-900/60 light:bg-zinc-200" />
          ))}
        </div>
      ) : games.length === 0 ? (
        <p className="mt-8 rounded-xl border border-white/10 bg-zinc-900/40 p-6 text-sm text-zinc-400 light:border-zinc-200 light:bg-zinc-50 light:text-zinc-600">
          No games on the schedule right now. Check back on game day.
        </p>
      ) : (
        <>
          <div className="mt-8 divide-y divide-white/10 overflow-hidden rounded-2xl border border-white/15 bg-zinc-900/70 light:divide-zinc-100 light:border-zinc-200 light:bg-white">
            {sorted.map((g) => (
              <ScoreboardRow key={g.id} g={g} selected={g.id === selectedId} onSelect={() => setSelectedId(g.id)} football={football} />
            ))}
          </div>

          {detail ? (
            <div className="mt-6">
              {/* Gamecast header: status + live situation over a linescore table */}
              <div className="rounded-2xl border border-white/20 bg-zinc-800/90 p-5 shadow-lg shadow-black/30 light:border-zinc-200 light:bg-white light:shadow-zinc-300/40">
                <div className="flex items-start justify-between gap-3 pb-2">
                  <div className="min-w-0">
                    <div className={`text-sm font-bold ${detail.game.state === "in" ? "text-amber-300 light:text-amber-600" : "text-zinc-200 light:text-zinc-600"}`}>
                      {detail.game.state === "in" ? detail.game.detail || "Live" : detail.game.state === "post" ? "Final" : detail.game.detail}
                    </div>
                    {situationText && (
                      <div className="mt-1 flex items-center gap-1.5 text-sm font-semibold text-amber-300 light:text-amber-700">
                        {football && <BallIcon size={14} />}
                        {situationText}
                      </div>
                    )}
                  </div>
                  {lastUpdate && (
                    <div className="shrink-0 text-[11px] text-zinc-400 light:text-zinc-500">
                      updated {lastUpdate.toLocaleTimeString([], { hour: "numeric", minute: "2-digit", second: "2-digit" })}
                    </div>
                  )}
                </div>
                <LinescoreTable
                  football={football}
                  periods={headerPeriods}
                  teams={[
                    {
                      abbr: detail.game.awayAbbr,
                      name: detail.game.awayName,
                      logo: boardGame?.awayLogo || detail.game.awayLogo,
                      record: detail.game.awayRecord || boardGame?.awayRecord || "",
                      lines: awayLines,
                      total: detail.game.awayScore,
                    },
                    {
                      abbr: detail.game.homeAbbr,
                      name: detail.game.homeName,
                      logo: boardGame?.homeLogo || detail.game.homeLogo,
                      record: detail.game.homeRecord || boardGame?.homeRecord || "",
                      lines: homeLines,
                      total: detail.game.homeScore,
                    },
                  ]}
                />
              </div>

              <div className="mt-4">
                <WinProbChart points={detail.winProb} homeAbbr={detail.game.homeAbbr} awayAbbr={detail.game.awayAbbr} />
              </div>

              {/* Tabs: play-by-play / scoring summary / team stats */}
              {tabs.length > 0 && activeTab ? (
                <>
                  <div className="mt-8 flex gap-1 overflow-x-auto border-b border-white/10 light:border-zinc-200" role="tablist" aria-label="Game detail sections">
                    {tabs.map((t) => (
                      <button
                        key={t.id}
                        role="tab"
                        aria-selected={activeTab === t.id}
                        onClick={() => setTab(t.id)}
                        className={`-mb-px shrink-0 border-b-2 px-4 py-2.5 text-sm font-semibold transition ${
                          activeTab === t.id
                            ? "border-amber-400 text-amber-300 light:border-amber-600 light:text-amber-700"
                            : "border-transparent text-zinc-400 hover:text-zinc-200 light:text-zinc-500 light:hover:text-zinc-800"
                        }`}
                      >
                        {t.label}
                      </button>
                    ))}
                  </div>
                  {activeTab === "plays" && <DrivesSection detail={detail} />}
                  {activeTab === "scoring" && <ScoringSection detail={detail} football={football} />}
                  {activeTab === "stats" && <StatsSection detail={detail} />}
                </>
              ) : (
                detail.game.state === "pre" && (
                  <p className="mt-8 text-sm text-zinc-400 light:text-zinc-600">
                    Play-by-play, scoring summary, and team stats appear here once the game is underway.
                  </p>
                )
              )}
            </div>
          ) : (
            selectedId && (
              <div className="mt-6 h-64 animate-pulse rounded-2xl bg-zinc-900/60 light:bg-zinc-200" />
            )
          )}
        </>
      )}

      <p className="mt-8 max-w-2xl text-xs leading-relaxed text-zinc-500 light:text-zinc-500">
        Live data via ESPN. Play-by-play and win probability refresh automatically
        while games are in progress; pre-game and final states update on the minute.
      </p>
    </div>
  );
}
