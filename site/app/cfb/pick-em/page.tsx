"use client";

import { useEffect, useMemo, useState } from "react";
import picksData from "../../../data/cfb_picks.json";
import seasonData from "../../../data/cfb_season_2026.json";
import CfbTeamLogo from "../../lib/cfb-team-logo";

type Mode = "ats" | "su";
type Side = "home" | "away";

type Game = {
  away: string;
  home: string;
  away_abbr: string;
  home_abbr: string;
  gameday: string;
  weekday: string;
  neutral: boolean;
  our_spread: number;
  line_spread: number;
  pick_spread_label: string | null;
  spread_labels: { home: string; away: string };
  result?: { home_score: number; away_score: number; ats?: string; ou?: string } | null;
};

type Stored = { weeks: Record<string, Record<Mode, Record<string, Side>>> };
const LS_KEY = "hl-cfb-pickem-2026";

function gameKey(g: { away: string; home: string }) {
  return `${g.away}@${g.home}`;
}

function loadStored(): Stored {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (raw) {
      const d = JSON.parse(raw);
      if (d && typeof d.weeks === "object") return d as Stored;
    }
  } catch { /* fresh start */ }
  return { weeks: {} };
}

/** Model's straight-up lean from its spread number. */
function modelSuLean(ourSpread: number): Side | null {
  if (ourSpread > 0.05) return "home";
  if (ourSpread < -0.05) return "away";
  return null;
}

function gradeSide(
  g: Game, side: Side, mode: Mode
): "win" | "loss" | "push" | null {
  const r = g.result;
  if (!r) return null;
  const hs = r.home_score;
  const as = r.away_score;
  if (mode === "su") {
    if (hs === as) return "push";
    return (hs > as ? "home" : "away") === side ? "win" : "loss";
  }
  const cover = hs - as - g.line_spread;
  if (Math.abs(cover) < 0.01) return "push";
  return (cover > 0) === (side === "home") ? "win" : "loss";
}

type Tally = { w: number; l: number; p: number };
const blank = (): Tally => ({ w: 0, l: 0, p: 0 });
function fmtTally(t: Tally) {
  return `${t.w}-${t.l}${t.p ? `-${t.p}` : ""}`;
}

export default function CfbPickEm() {
  const [mode, setMode] = useState<Mode>("ats");
  const [stored, setStored] = useState<Stored>({ weeks: {} });
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setStored(loadStored());
    setReady(true);
  }, []);

  const week = String((picksData as { week: number }).week);
  const games = (picksData as { picks: Game[] }).picks;
  const gradedWeeks = useMemo(() => {
    const w = (seasonData as { weeks: Record<string, { picks: Game[] }> }).weeks ?? {};
    return Object.keys(w)
      .sort((a, b) => Number(a) - Number(b))
      .map((k) => ({ week: k, picks: w[k].picks ?? [] }));
  }, []);

  const weekPicks: Record<string, Side> =
    stored.weeks[week]?.[mode] ?? {};

  function setPick(g: Game, side: Side) {
    setStored((prev) => {
      const next: Stored = {
        weeks: {
          ...prev.weeks,
          [week]: {
            ats: { ...(prev.weeks[week]?.ats ?? {}) },
            su: { ...(prev.weeks[week]?.su ?? {}) },
            [mode]: { ...(prev.weeks[week]?.[mode] ?? {}), [gameKey(g)]: side },
          },
        },
      };
      try {
        localStorage.setItem(LS_KEY, JSON.stringify(next));
      } catch { /* storage unavailable */ }
      return next;
    });
  }

  function clearWeek() {
    setStored((prev) => {
      const next: Stored = {
        weeks: {
          ...prev.weeks,
          [week]: { ...prev.weeks[week], ats: {}, su: {} },
        },
      };
      try {
        localStorage.setItem(LS_KEY, JSON.stringify(next));
      } catch { /* storage unavailable */ }
      return next;
    });
  }

  const pickedCount = Object.keys(weekPicks).length;

  // ---- You vs the model, from graded weeks ----
  const { youAts, modelAts, youSu, modelSu, rows } = useMemo(() => {
    const youAts = blank(), modelAts = blank(), youSu = blank(), modelSu = blank();
    const rows: {
      week: string;
      youAts: Tally | null; modelAts: Tally;
      youSu: Tally | null; modelSu: Tally;
    }[] = [];
    for (const { week: wk, picks } of gradedWeeks) {
      const sp = stored.weeks[wk];
      const rAts: Tally | null = sp ? blank() : null;
      const rSu: Tally | null = sp ? blank() : null;
      const mAts = blank(), mSu = blank();
      for (const g of picks) {
        if (!g.result) continue;
        // model ATS (result.ats exists only when the model made a spread pick,
        // and it already grades the model's own pick_spread side)
        const mAtsR = g.result.ats as "win" | "loss" | "push" | undefined;
        if (mAtsR === "win") mAts.w++; else if (mAtsR === "loss") mAts.l++; else if (mAtsR) mAts.p++;
        // model straight-up
        const lean = modelSuLean(g.our_spread);
        if (lean) {
          const mr = gradeSide(g, lean, "su");
          if (mr === "win") mSu.w++; else if (mr === "loss") mSu.l++; else if (mr) mSu.p++;
        }
        // your picks
        if (sp) {
          const k = gameKey(g);
          const ya = sp.ats[k];
          if (ya && rAts) {
            const r = gradeSide(g, ya, "ats");
            if (r === "win") rAts.w++; else if (r === "loss") rAts.l++; else if (r) rAts.p++;
          }
          const ys = sp.su[k];
          if (ys && rSu) {
            const r = gradeSide(g, ys, "su");
            if (r === "win") rSu.w++; else if (r === "loss") rSu.l++; else if (r) rSu.p++;
          }
        }
      }
      for (const [dst, src] of [[youAts, rAts], [modelAts, mAts], [youSu, rSu], [modelSu, mSu]] as const) {
        if (src) { dst.w += src.w; dst.l += src.l; dst.p += src.p; }
      }
      rows.push({ week: wk, youAts: rAts, modelAts: mAts, youSu: rSu, modelSu: mSu });
    }
    return { youAts, modelAts, youSu, modelSu, rows };
  }, [gradedWeeks, stored]);

  const modelHint = (g: Game): string | null =>
    mode === "ats"
      ? (g.pick_spread_label ?? null)
      : (() => {
          const lean = modelSuLean(g.our_spread);
          return lean ? (lean === "home" ? g.home : g.away) : null;
        })();

  return (
    <div>
      <div className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-amber-400/90 light:text-amber-700">
        <span className="h-px w-8 bg-amber-400/60 light:bg-amber-600/70" aria-hidden="true" />
        College football · Beat the model, not the book
      </div>
      <h1 className="mt-3 font-display text-5xl font-semibold uppercase leading-[0.95] tracking-wide">
        Pick<span className="text-amber-400 light:text-amber-600">&rsquo;em</span>
      </h1>
      <p className="mt-4 max-w-2xl text-[15px] leading-relaxed text-zinc-400 light:text-zinc-600">
        Pick every FBS game against the spread or straight up. We grade your card
        every Tuesday from the season log, and you can see exactly how you
        stack up against the model. Picks live in your browser — no account needed.
      </p>

      {/* Mode toggle */}
      <div className="mt-5 inline-flex rounded-xl border border-zinc-800 bg-zinc-900 p-1 light:border-zinc-200 light:bg-zinc-100">
        {(["ats", "su"] as Mode[]).map((m) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={`rounded-lg px-4 py-2 text-sm font-semibold transition ${
              mode === m ? "bg-amber-400 text-zinc-950" : "text-zinc-400 hover:text-white light:text-zinc-600 light:hover:text-zinc-900"
            }`}
          >
            {m === "ats" ? "Against the spread" : "Straight up"}
          </button>
        ))}
      </div>

      {/* This week's card */}
      <div className="mt-8 flex items-baseline justify-between">
        <h2 className="font-display text-2xl font-semibold uppercase tracking-wide">
          Week {week} <span className="font-sans text-sm font-medium normal-case tracking-normal text-zinc-500">· your card</span>
        </h2>
        <div className="flex items-center gap-3">
          <span className="text-sm text-zinc-400">
            {ready ? `${pickedCount} of ${games.length} picked` : "…"}
          </span>
          <button
            onClick={clearWeek}
            className="rounded-lg border border-zinc-800 px-3 py-1.5 text-xs font-semibold text-zinc-400 hover:border-zinc-600 hover:text-white light:border-zinc-200 light:hover:border-zinc-400 light:hover:text-zinc-900"
          >
            Clear
          </button>
        </div>
      </div>
      {ready && pickedCount > 0 && pickedCount < games.length && (
        <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-zinc-800 light:bg-zinc-200">
          <div
            className="h-full rounded-full bg-amber-400 transition-all"
            style={{ width: `${(pickedCount / games.length) * 100}%` }}
          />
        </div>
      )}

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        {games.map((g) => {
          const k = gameKey(g);
          const sel = weekPicks[k];
          const hint = modelHint(g);
          const btn = (side: Side) => {
            const active = sel === side;
            const name = side === "home" ? g.home : g.away;
            const label =
              mode === "ats"
                ? g.spread_labels[side]
                : name;
            return (
              <button
                key={side}
                onClick={() => setPick(g, side)}
                className={`flex-1 rounded-xl border px-4 py-3 text-left transition ${
                  active
                    ? "border-amber-400 bg-amber-400/15"
                    : "border-zinc-800 bg-zinc-900 hover:border-zinc-600 light:border-zinc-200 light:bg-white light:hover:border-zinc-400"
                }`}
              >
                <div className={`flex items-center gap-2 font-mono text-lg font-bold ${active ? "text-amber-300 light:text-amber-700" : "text-zinc-100 light:text-zinc-900"}`}>
                  <CfbTeamLogo name={name} size={28} />
                  {label}
                </div>
                <div className="text-xs text-zinc-500">
                  {name}
                  {mode === "su" && hint && name === hint && " · model's lean"}
                </div>
              </button>
            );
          };
          return (
            <article key={k} className="rounded-2xl border border-white/10 bg-gradient-to-b from-zinc-900/70 to-zinc-900/30 p-4 transition-colors hover:border-white/20 light:border-zinc-200 light:from-white light:to-zinc-50 light:hover:border-zinc-300">
              <div className="flex items-baseline justify-between">
                <h3 className="flex flex-wrap items-center gap-x-2 font-bold">
                  <span className="inline-flex items-center gap-1.5">
                    <CfbTeamLogo name={g.away} size={22} />
                    {g.away}
                  </span>
                  <span className="font-medium text-zinc-500">{g.neutral ? "vs" : "@"}</span>
                  <span className="inline-flex items-center gap-1.5">
                    <CfbTeamLogo name={g.home} size={22} />
                    {g.home}
                  </span>
                  {g.neutral && (
                    <span className="rounded-full border border-white/10 bg-white/5 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-zinc-400 light:border-zinc-200 light:bg-zinc-100 light:text-zinc-600">
                      Neutral
                    </span>
                  )}
                </h3>
                <span className="text-xs text-zinc-500">
                  {g.weekday ? `${g.weekday}, ` : ""}{g.gameday}
                </span>
              </div>
              {mode === "ats" && hint && (
                <p className="mt-1 text-xs text-zinc-500">Model&apos;s pick: {hint}</p>
              )}
              <div className="mt-3 flex gap-2">
                {btn("away")}
                {btn("home")}
              </div>
            </article>
          );
        })}
      </div>
      <p className="mt-3 text-xs text-zinc-500">
        Honor system for now — lock your picks before kickoff. Your card is graded
        Tuesday morning when the week&apos;s results land.
      </p>

      {/* You vs the model */}
      <h2 className="mt-12 font-display text-3xl font-semibold uppercase tracking-wide">You vs the model</h2>
      {gradedWeeks.length === 0 ? (
        <p className="mt-2 max-w-2xl text-[15px] text-zinc-400 light:text-zinc-600">
          No graded weeks yet — the first results land Tuesday morning, and this
          is where your record appears next to the model&apos;s.
        </p>
      ) : (
        <div className="mt-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-5 light:border-zinc-200 light:bg-white">
              <div className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
                Against the spread · season
              </div>
              <div className="mt-2 flex items-baseline gap-4">
                <div>
                  <div className="font-mono text-3xl font-extrabold text-amber-300 light:text-amber-700">{fmtTally(youAts)}</div>
                  <div className="text-xs text-zinc-500">You</div>
                </div>
                <div className="text-xl text-zinc-600">vs</div>
                <div>
                  <div className="font-mono text-3xl font-extrabold">{fmtTally(modelAts)}</div>
                  <div className="text-xs text-zinc-500">Model</div>
                </div>
              </div>
            </div>
            <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-5 light:border-zinc-200 light:bg-white">
              <div className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
                Straight up · season
              </div>
              <div className="mt-2 flex items-baseline gap-4">
                <div>
                  <div className="font-mono text-3xl font-extrabold text-amber-300 light:text-amber-700">{fmtTally(youSu)}</div>
                  <div className="text-xs text-zinc-500">You</div>
                </div>
                <div className="text-xl text-zinc-600">vs</div>
                <div>
                  <div className="font-mono text-3xl font-extrabold">{fmtTally(modelSu)}</div>
                  <div className="text-xs text-zinc-500">Model</div>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-4 overflow-x-auto rounded-2xl border border-zinc-800 light:border-zinc-200">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-zinc-800 text-xs uppercase tracking-wider text-zinc-500 light:border-zinc-200">
                  <th className="px-4 py-3">Week</th>
                  <th className="px-4 py-3">You ATS</th>
                  <th className="px-4 py-3">Model ATS</th>
                  <th className="px-4 py-3">You SU</th>
                  <th className="px-4 py-3">Model SU</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.week} className="border-b border-zinc-800/60 last:border-0 light:border-zinc-200">
                    <td className="px-4 py-3 font-semibold">{r.week}</td>
                    <td className="px-4 py-3 font-mono text-amber-200/90 light:text-amber-700">{r.youAts ? fmtTally(r.youAts) : "—"}</td>
                    <td className="px-4 py-3 font-mono text-zinc-400">{fmtTally(r.modelAts)}</td>
                    <td className="px-4 py-3 font-mono text-amber-200/90 light:text-amber-700">{r.youSu ? fmtTally(r.youSu) : "—"}</td>
                    <td className="px-4 py-3 font-mono text-zinc-400">{fmtTally(r.modelSu)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-xs text-zinc-500">
            “—” means you didn&apos;t save picks that week on this browser.
          </p>
        </div>
      )}
    </div>
  );
}
