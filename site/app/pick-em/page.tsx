"use client";

import { useEffect, useMemo, useState } from "react";
import picksData from "../../data/picks.json";
import seasonData from "../../data/season_2026.json";
import TeamLogo from "../lib/team-logo";
import { trim } from "../lib/format";

type Mode = "combo" | "su";
type Side = "home" | "away";
type OuPick = "over" | "under";
type PickValue = Side | OuPick;
/** Storage bucket per pick kind — kept separate so old saved cards survive. */
type Store = "ats" | "su" | "ou";

type Game = {
  away_abbr: string;
  home_abbr: string;
  gameday: string;
  weekday: string;
  our_spread: number;
  line_spread: number;
  line_total: number;
  pick_spread_label: string | null;
  pick_total: OuPick | null;
  pick_total_label: string | null;
  spread_labels: { home: string; away: string };
  result?: { home_score: number; away_score: number; ats?: string; ou?: string } | null;
};

type Stored = { weeks: Record<string, Record<Store, Record<string, PickValue>>> };
const LS_KEY = "hl-pickem-2026";

function gameKey(g: { away_abbr: string; home_abbr: string }) {
  return `${g.away_abbr}@${g.home_abbr}`;
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
  g: Game, side: Side, mode: "ats" | "su"
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

function gradeOu(g: Game, pick: OuPick): "win" | "loss" | "push" | null {
  const r = g.result;
  if (!r) return null;
  const diff = r.home_score + r.away_score - g.line_total;
  if (Math.abs(diff) < 0.01) return "push";
  return (diff > 0) === (pick === "over") ? "win" : "loss";
}

type Tally = { w: number; l: number; p: number };
const blank = (): Tally => ({ w: 0, l: 0, p: 0 });
function fmtTally(t: Tally) {
  return `${t.w}-${t.l}${t.p ? `-${t.p}` : ""}`;
}

export default function PickEm() {
  const [mode, setMode] = useState<Mode>("combo");
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

  const weekPicks: Record<string, PickValue> =
    stored.weeks[week]?.su ?? {};

  function setPick(g: Game, store: Store, value: PickValue) {
    setStored((prev) => {
      const wk = prev.weeks[week] ?? { ats: {}, su: {}, ou: {} };
      const next: Stored = {
        weeks: {
          ...prev.weeks,
          [week]: {
            ats: { ...wk.ats },
            su: { ...wk.su },
            ou: { ...wk.ou },
            [store]: { ...wk[store], [gameKey(g)]: value },
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
          [week]: { ...prev.weeks[week], ats: {}, su: {}, ou: {} },
        },
      };
      try {
        localStorage.setItem(LS_KEY, JSON.stringify(next));
      } catch { /* storage unavailable */ }
      return next;
    });
  }

  const pickedCount =
    mode === "combo"
      ? Object.keys(stored.weeks[week]?.ats ?? {}).length +
        Object.keys(stored.weeks[week]?.ou ?? {}).length
      : Object.keys(weekPicks).length;
  const pickedTotal = mode === "combo" ? games.length * 2 : games.length;

  // ---- You vs the model, from graded weeks ----
  const { youAts, modelAts, youSu, modelSu, youOu, modelOu, rows } = useMemo(() => {
    const youAts = blank(), modelAts = blank(), youSu = blank(), modelSu = blank();
    const youOu = blank(), modelOu = blank();
    const rows: {
      week: string;
      youAts: Tally | null; modelAts: Tally;
      youSu: Tally | null; modelSu: Tally;
      youOu: Tally | null; modelOu: Tally;
    }[] = [];
    for (const { week: wk, picks } of gradedWeeks) {
      const sp = stored.weeks[wk];
      const rAts: Tally | null = sp ? blank() : null;
      const rSu: Tally | null = sp ? blank() : null;
      const rOu: Tally | null = sp ? blank() : null;
      const mAts = blank(), mSu = blank(), mOu = blank();
      for (const g of picks) {
        if (!g.result) continue;
        // model ATS (result.ats exists only when the model made a spread pick,
        // and it already grades the model's own pick_spread side)
        const mAtsR = g.result.ats as "win" | "loss" | "push" | undefined;
        if (mAtsR === "win") mAts.w++; else if (mAtsR === "loss") mAts.l++; else if (mAtsR) mAts.p++;
        // model over/under (result.ou grades the model's own pick_total)
        const mOuR = g.result.ou as "win" | "loss" | "push" | undefined;
        if (mOuR === "win") mOu.w++; else if (mOuR === "loss") mOu.l++; else if (mOuR) mOu.p++;
        // model straight-up
        const lean = modelSuLean(g.our_spread);
        if (lean) {
          const mr = gradeSide(g, lean, "su");
          if (mr === "win") mSu.w++; else if (mr === "loss") mSu.l++; else if (mr) mSu.p++;
        }
        // your picks
        if (sp) {
          const k = gameKey(g);
          const ya = sp.ats?.[k] as Side | undefined;
          if (ya && rAts) {
            const r = gradeSide(g, ya, "ats");
            if (r === "win") rAts.w++; else if (r === "loss") rAts.l++; else if (r) rAts.p++;
          }
          const ys = sp.su?.[k] as Side | undefined;
          if (ys && rSu) {
            const r = gradeSide(g, ys, "su");
            if (r === "win") rSu.w++; else if (r === "loss") rSu.l++; else if (r) rSu.p++;
          }
          const yo = sp.ou?.[k] as OuPick | undefined;
          if (yo && rOu) {
            const r = gradeOu(g, yo);
            if (r === "win") rOu.w++; else if (r === "loss") rOu.l++; else if (r) rOu.p++;
          }
        }
      }
      for (const [dst, src] of [[youAts, rAts], [modelAts, mAts], [youSu, rSu], [modelSu, mSu], [youOu, rOu], [modelOu, mOu]] as const) {
        if (src) { dst.w += src.w; dst.l += src.l; dst.p += src.p; }
      }
      rows.push({ week: wk, youAts: rAts, modelAts: mAts, youSu: rSu, modelSu: mSu, youOu: rOu, modelOu: mOu });
    }
    return { youAts, modelAts, youSu, modelSu, youOu, modelOu, rows };
  }, [gradedWeeks, stored]);

  const modelHint = (g: Game, store: Store): string | null => {
    if (store === "ats") return g.pick_spread_label ?? null;
    if (store === "ou") return g.pick_total_label ?? null;
    const lean = modelSuLean(g.our_spread);
    return lean ? (lean === "home" ? g.home_abbr : g.away_abbr) : null;
  };

  return (
    <div>
      <div className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-amber-400/90 light:text-amber-700">
        <span className="h-px w-8 bg-amber-400/60 light:bg-amber-600/70" aria-hidden="true" />
        Beat the model, not the book
      </div>
      <h1 className="mt-3 font-display text-5xl font-semibold uppercase leading-[0.95] tracking-wide">
        Pick<span className="text-amber-400 light:text-amber-600">&rsquo;em</span>
      </h1>
      <p className="mt-4 max-w-2xl text-[15px] leading-relaxed text-zinc-400 light:text-zinc-600">
        Pick every game against the spread and on the total — or go straight up.
        We grade your card every Tuesday from the season log, and you can see
        exactly how you stack up against the model. Picks live in your browser —
        no account needed.
      </p>

      {/* Mode toggle */}
      <div className="mt-5 inline-flex rounded-xl border border-zinc-800 bg-zinc-900 p-1 light:border-zinc-200 light:bg-zinc-100">
        {([
          ["combo", "Spread + Totals"],
          ["su", "Straight up"],
        ] as [Mode, string][]).map(([m, label]) => (
          <button
            key={m}
            onClick={() => setMode(m)}
            className={`rounded-lg px-4 py-2 text-sm font-semibold transition ${
              mode === m ? "bg-amber-400 text-zinc-950" : "text-zinc-400 hover:text-white light:text-zinc-600 light:hover:text-zinc-900"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* This week's card */}
      <div className="mt-8 flex items-baseline justify-between">
        <h2 className="font-display text-2xl font-semibold uppercase tracking-wide">
          Week {week} <span className="font-sans text-sm font-medium normal-case tracking-normal text-zinc-500">· your card</span>
        </h2>
        <div className="flex items-center gap-3">
          <span className="text-sm text-zinc-400 light:text-zinc-600">
            {ready ? `${pickedCount} of ${pickedTotal} picked` : "…"}
          </span>
          <button
            onClick={clearWeek}
            className="rounded-lg border border-zinc-800 px-3 py-1.5 text-xs font-semibold text-zinc-400 hover:border-zinc-600 hover:text-white light:border-zinc-300 light:text-zinc-600 light:hover:border-zinc-500 light:hover:text-zinc-900"
          >
            Clear
          </button>
        </div>
      </div>
      {ready && pickedCount > 0 && pickedCount < pickedTotal && (
        <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-zinc-800 light:bg-zinc-200">
          <div
            className="h-full rounded-full bg-amber-400 transition-all"
            style={{ width: `${(pickedCount / pickedTotal) * 100}%` }}
          />
        </div>
      )}

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        {games.map((g) => {
          const k = gameKey(g);
          const selAts = stored.weeks[week]?.ats?.[k] as Side | undefined;
          const selOu = stored.weeks[week]?.ou?.[k] as OuPick | undefined;
          const selSu = weekPicks[k] as Side | undefined;
          const hintAts = modelHint(g, "ats");
          const hintOu = modelHint(g, "ou");
          const hintSu = modelHint(g, "su");
          const spreadBtn = (side: Side) => {
            const active = selAts === side;
            const label = g.spread_labels[side];
            return (
              <button
                key={side}
                onClick={() => setPick(g, "ats", side)}
                className={`flex-1 rounded-xl border px-4 py-3 text-left transition ${
                  active
                    ? "border-amber-400 bg-amber-400/15"
                    : "border-zinc-800 bg-zinc-900 hover:border-zinc-600 light:border-zinc-200 light:bg-white light:hover:border-zinc-400"
                }`}
              >
                <div className={`flex items-center gap-2 font-mono text-lg font-bold ${active ? "text-amber-300 light:text-amber-700" : "text-zinc-100 light:text-zinc-900"}`}>
                  <TeamLogo abbr={side === "home" ? g.home_abbr : g.away_abbr} size={28} />
                  {label}
                </div>
                <div className="text-xs text-zinc-500">
                  {side === "home" ? g.home_abbr : g.away_abbr}
                  {hintAts && g.spread_labels[side] === hintAts && " · model's pick"}
                </div>
              </button>
            );
          };
          const ouBtn = (pick: OuPick) => {
            const active = selOu === pick;
            const label = `${pick === "over" ? "Over" : "Under"} ${trim(g.line_total)}`;
            return (
              <button
                key={pick}
                onClick={() => setPick(g, "ou", pick)}
                className={`flex-1 rounded-xl border px-4 py-3 text-left transition ${
                  active
                    ? "border-amber-400 bg-amber-400/15"
                    : "border-zinc-800 bg-zinc-900 hover:border-zinc-600 light:border-zinc-200 light:bg-white light:hover:border-zinc-400"
                }`}
              >
                <div className={`font-mono text-lg font-bold ${active ? "text-amber-300 light:text-amber-700" : "text-zinc-100 light:text-zinc-900"}`}>
                  {label}
                </div>
                <div className="text-xs text-zinc-500">
                  {hintOu && g.pick_total === pick && "· model's pick"}
                </div>
              </button>
            );
          };
          const suBtn = (side: Side) => {
            const active = selSu === side;
            return (
              <button
                key={side}
                onClick={() => setPick(g, "su", side)}
                className={`flex-1 rounded-xl border px-4 py-3 text-left transition ${
                  active
                    ? "border-amber-400 bg-amber-400/15"
                    : "border-zinc-800 bg-zinc-900 hover:border-zinc-600 light:border-zinc-200 light:bg-white light:hover:border-zinc-400"
                }`}
              >
                <div className={`flex items-center gap-2 font-mono text-lg font-bold ${active ? "text-amber-300 light:text-amber-700" : "text-zinc-100 light:text-zinc-900"}`}>
                  <TeamLogo abbr={side === "home" ? g.home_abbr : g.away_abbr} size={28} />
                  {side === "home" ? g.home_abbr : g.away_abbr}
                </div>
                <div className="text-xs text-zinc-500">
                  {side === "home" ? g.home_abbr : g.away_abbr}
                  {hintSu && (side === "home" ? g.home_abbr : g.away_abbr) === hintSu && " · model's lean"}
                </div>
              </button>
            );
          };
          return (
            <article key={k} className="rounded-2xl border border-white/10 bg-gradient-to-b from-zinc-900/70 to-zinc-900/30 p-4 transition-colors hover:border-white/20 light:border-zinc-200 light:from-white light:to-zinc-50 light:hover:border-zinc-300">
              <div className="flex items-baseline justify-between">
                <h3 className="flex flex-wrap items-center gap-x-2 font-bold">
                  <span className="inline-flex items-center gap-1.5">
                    <TeamLogo abbr={g.away_abbr} size={22} />
                    {g.away_abbr}
                  </span>
                  <span className="font-medium text-zinc-500">@</span>
                  <span className="inline-flex items-center gap-1.5">
                    <TeamLogo abbr={g.home_abbr} size={22} />
                    {g.home_abbr}
                  </span>
                </h3>
                <span className="text-xs text-zinc-500">
                  {g.weekday ? `${g.weekday}, ` : ""}{g.gameday}
                </span>
              </div>
              {mode === "combo" ? (
                <>
                  <div className="mt-3">
                    <div className="mb-1.5 flex items-baseline justify-between">
                      <span className="text-[11px] font-bold uppercase tracking-wider text-zinc-500">Spread</span>
                      {hintAts && <span className="text-[11px] text-zinc-500">Model: {hintAts}</span>}
                    </div>
                    <div className="flex gap-2">
                      {spreadBtn("away")}{spreadBtn("home")}
                    </div>
                  </div>
                  <div className="mt-3">
                    <div className="mb-1.5 flex items-baseline justify-between">
                      <span className="text-[11px] font-bold uppercase tracking-wider text-zinc-500">Total</span>
                      {hintOu && <span className="text-[11px] text-zinc-500">Model: {hintOu}</span>}
                    </div>
                    <div className="flex gap-2">
                      {ouBtn("over")}{ouBtn("under")}
                    </div>
                  </div>
                </>
              ) : (
                <div className="mt-3 flex gap-2">
                  {suBtn("away")}{suBtn("home")}
                </div>
              )}
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
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-5 light:border-zinc-200 light:bg-white">
              <div className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
                Against the spread · season
              </div>
              <div className="mt-2 flex items-baseline gap-4">
                <div>
                  <div className="font-mono text-3xl font-extrabold text-amber-300 light:text-amber-700">{fmtTally(youAts)}</div>
                  <div className="text-xs text-zinc-500">You</div>
                </div>
                <div className="text-xl text-zinc-600 light:text-zinc-400">vs</div>
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
                <div className="text-xl text-zinc-600 light:text-zinc-400">vs</div>
                <div>
                  <div className="font-mono text-3xl font-extrabold">{fmtTally(modelSu)}</div>
                  <div className="text-xs text-zinc-500">Model</div>
                </div>
              </div>
            </div>
            <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-5 light:border-zinc-200 light:bg-white">
              <div className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
                Over/Under · season
              </div>
              <div className="mt-2 flex items-baseline gap-4">
                <div>
                  <div className="font-mono text-3xl font-extrabold text-amber-300 light:text-amber-700">{fmtTally(youOu)}</div>
                  <div className="text-xs text-zinc-500">You</div>
                </div>
                <div className="text-xl text-zinc-600 light:text-zinc-400">vs</div>
                <div>
                  <div className="font-mono text-3xl font-extrabold">{fmtTally(modelOu)}</div>
                  <div className="text-xs text-zinc-500">Model</div>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-4 overflow-x-auto rounded-2xl border border-zinc-800 light:border-zinc-200">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-zinc-800 text-xs uppercase tracking-wider text-zinc-500 light:border-zinc-200 light:text-zinc-600">
                  <th className="px-4 py-3">Week</th>
                  <th className="px-4 py-3">You ATS</th>
                  <th className="px-4 py-3">Model ATS</th>
                  <th className="px-4 py-3">You SU</th>
                  <th className="px-4 py-3">Model SU</th>
                  <th className="px-4 py-3">You O/U</th>
                  <th className="px-4 py-3">Model O/U</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.week} className="border-b border-zinc-800/60 last:border-0 light:border-zinc-200">
                    <td className="px-4 py-3 font-semibold">{r.week}</td>
                    <td className="px-4 py-3 font-mono text-amber-200/90 light:text-amber-700">{r.youAts ? fmtTally(r.youAts) : "—"}</td>
                    <td className="px-4 py-3 font-mono text-zinc-400 light:text-zinc-600">{fmtTally(r.modelAts)}</td>
                    <td className="px-4 py-3 font-mono text-amber-200/90 light:text-amber-700">{r.youSu ? fmtTally(r.youSu) : "—"}</td>
                    <td className="px-4 py-3 font-mono text-zinc-400 light:text-zinc-600">{fmtTally(r.modelSu)}</td>
                    <td className="px-4 py-3 font-mono text-amber-200/90 light:text-amber-700">{r.youOu ? fmtTally(r.youOu) : "—"}</td>
                    <td className="px-4 py-3 font-mono text-zinc-400 light:text-zinc-600">{fmtTally(r.modelOu)}</td>
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
