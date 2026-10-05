"use client";

import { useEffect, useMemo, useState } from "react";
import picksData from "../../../data/nba_picks.json";
import seasonData from "../../../data/nba_season_2027.json";
import { fmtSpread, trim } from "../../lib/format";
import NbaTeamLogo from "../../lib/nba-team-logo";

type Mode = "combo" | "su";
type Side = "home" | "away";
type OuPick = "over" | "under";
type PickValue = Side | OuPick;
/** Storage bucket per pick kind — kept separate so old saved cards survive. */
type Store = "ats" | "su" | "ou";

type Game = {
  away: string;
  home: string;
  away_abbr: string;
  home_abbr: string;
  gameday: string;
  weekday: string;
  neutral?: boolean;
  our_spread: number;
  line_spread: number;
  line_total: number;
  pick_spread_label: string | null;
  pick_total: OuPick | null;
  pick_total_label: string | null;
  spread_labels?: { home: string; away: string };
  result?: { home_score: number; away_score: number; ats?: string; ou?: string } | null;
};

type Stored = { weeks: Record<string, Record<Store, Record<string, PickValue>>> };
const LS_KEY = "hl-nba-pickem-2026";

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

type Grade = "win" | "loss" | "push";
type GameDetail = {
  label: string;
  score: string;
  ats: { pick: string; result: Grade } | null;
  su: { pick: string; result: Grade } | null;
  ou: { pick: string; result: Grade } | null;
};

function ResultBadge({ r }: { r: Grade }) {
  const cls =
    r === "win"
      ? "bg-emerald-400/15 text-emerald-300 light:bg-emerald-600/10 light:text-emerald-700"
      : r === "loss"
        ? "bg-rose-400/15 text-rose-300 light:bg-rose-600/10 light:text-rose-700"
        : "bg-zinc-400/15 text-zinc-400 light:bg-zinc-500/10 light:text-zinc-600";
  const text = r === "win" ? "✓ Won" : r === "loss" ? "✗ Lost" : "Push";
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${cls}`}>
      {text}
    </span>
  );
}

type Tally = { w: number; l: number; p: number };
const blank = (): Tally => ({ w: 0, l: 0, p: 0 });
function fmtTally(t: Tally) {
  return `${t.w}-${t.l}${t.p ? `-${t.p}` : ""}`;
}

const picksFile = picksData as { week?: number | null; date?: string | null; picks: Game[]; preseason?: boolean; experimental_note?: string | null };
const slateKey = String(picksFile.week ?? picksFile.date ?? "slate");
const slateLabel = picksFile.week != null ? `Week ${picksFile.week}` : "Tonight's slate";
const showPreseason = picksFile.preseason === true;

function slateTitle(wn: string) {
  return /^\d+$/.test(wn) ? `Week ${wn}` : wn;
}

export default function NbaPickEm() {
  const [mode, setMode] = useState<Mode>("combo");
  const [stored, setStored] = useState<Stored>({ weeks: {} });
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setStored(loadStored());
    setReady(true);
  }, []);

  const games = picksFile.picks;
  const gradedWeeks = useMemo(() => {
    const d = (seasonData as { days: Record<string, { picks: Game[] }> }).days ?? {};
    return Object.keys(d)
      .sort((a, b) => (a < b ? -1 : a > b ? 1 : 0))
      .map((k) => ({ week: k, picks: d[k].picks ?? [] }));
  }, []);

  const weekPicks: Record<string, PickValue> =
    stored.weeks[slateKey]?.su ?? {};

  function setPick(g: Game, store: Store, value: PickValue) {
    setStored((prev) => {
      const wk = prev.weeks[slateKey] ?? { ats: {}, su: {}, ou: {} };
      const next: Stored = {
        weeks: {
          ...prev.weeks,
          [slateKey]: {
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
          [slateKey]: { ...prev.weeks[slateKey], ats: {}, su: {}, ou: {} },
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
      ? Object.keys(stored.weeks[slateKey]?.ats ?? {}).length +
        Object.keys(stored.weeks[slateKey]?.ou ?? {}).length
      : Object.keys(weekPicks).length;
  const pickedTotal = mode === "combo" ? games.length * 2 : games.length;

  // ---- You vs the model, from graded slates ----
  const { youAts, modelAts, youSu, modelSu, youOu, modelOu, rows } = useMemo(() => {
    const youAts = blank(), modelAts = blank(), youSu = blank(), modelSu = blank();
    const youOu = blank(), modelOu = blank();
    const rows: {
      week: string;
      youAts: Tally | null; modelAts: Tally;
      youSu: Tally | null; modelSu: Tally;
      youOu: Tally | null; modelOu: Tally;
      games: GameDetail[];
    }[] = [];
    for (const { week: wk, picks } of gradedWeeks) {
      const sp = stored.weeks[wk];
      const rAts: Tally | null = sp ? blank() : null;
      const rSu: Tally | null = sp ? blank() : null;
      const rOu: Tally | null = sp ? blank() : null;
      const mAts = blank(), mSu = blank(), mOu = blank();
      const details: GameDetail[] = [];
      for (const g of picks) {
        if (!g.result) continue;
        // per-game detail for your picks
        if (sp) {
          const k = gameKey(g);
          const ya = sp.ats?.[k] as Side | undefined;
          const ys = sp.su?.[k] as Side | undefined;
          const yo = sp.ou?.[k] as OuPick | undefined;
          const dAts = ya ? gradeSide(g, ya, "ats") : null;
          const dSu = ys ? gradeSide(g, ys, "su") : null;
          const dOu = yo ? gradeOu(g, yo) : null;
          if (dAts || dSu || dOu) {
            details.push({
              label: `${g.away_abbr} @ ${g.home_abbr}`,
              score: `${g.result.away_score}–${g.result.home_score}`,
              ats: dAts ? { pick: g.spread_labels?.[ya as Side] ?? fmtSpread(g.line_spread, g.home_abbr, g.away_abbr), result: dAts } : null,
              su: dSu ? { pick: ys === "home" ? g.home_abbr : g.away_abbr, result: dSu } : null,
              ou: dOu ? { pick: `${yo === "over" ? "Over" : "Under"} ${trim(g.line_total)}`, result: dOu } : null,
            });
          }
        }
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
      rows.push({ week: wk, youAts: rAts, modelAts: mAts, youSu: rSu, modelSu: mSu, youOu: rOu, modelOu: mOu, games: details });
    }
    return { youAts, modelAts, youSu, modelSu, youOu, modelOu, rows };
  }, [gradedWeeks, stored]);

  const modelHint = (g: Game, store: Store): string | null => {
    if (store === "ats") return g.pick_spread_label ?? null;
    if (store === "ou") return g.pick_total_label ?? null;
    const lean = modelSuLean(g.our_spread);
    return lean ? (lean === "home" ? g.home : g.away) : null;
  };

  const spreadLabel = (g: Game, side: Side) =>
    g.spread_labels?.[side] ?? fmtSpread(g.line_spread, g.home_abbr, g.away_abbr);

  return (
    <div>
      <div className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-amber-400/90 light:text-amber-700">
        <span className="h-px w-8 bg-amber-400/60 light:bg-amber-600/70" aria-hidden="true" />
        NBA · Beat the model, not the book
      </div>
      <h1 className="mt-3 font-display text-5xl font-semibold uppercase leading-[0.95] tracking-wide">
        Pick<span className="text-amber-400 light:text-amber-600">&rsquo;em</span>
      </h1>
      <p className="mt-4 max-w-2xl text-[15px] leading-relaxed text-zinc-400 light:text-zinc-600">
        Pick every game on the slate against the spread and on the total — or go straight up.
        We grade your card from the season log, and you can see exactly how you
        stack up against the model. Picks live in your browser — no account needed.
      </p>

      {/* Mode toggle */}
      {showPreseason && (
        <div className="mt-5 rounded-xl border border-sky-400/25 bg-sky-400/[0.07] px-4 py-3 light:bg-sky-50">
          <div className="text-xs font-bold uppercase tracking-[0.16em] text-sky-300 light:text-sky-700">Preseason — experimental</div>
          <p className="mt-1 text-sm text-zinc-400 light:text-zinc-600">
            {picksFile.experimental_note ?? "The model is running before it has seen a real regular-season game. Treat these numbers as a calibration exercise, not as picks."}
          </p>
        </div>
      )}
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

      {/* This slate's card */}
      <div className="mt-8 flex items-baseline justify-between">
        <h2 className="font-display text-2xl font-semibold uppercase tracking-wide">
          {slateLabel} <span className="font-sans text-sm font-medium normal-case tracking-normal text-zinc-500">· your card</span>
        </h2>
        <div className="flex items-center gap-3">
          <span className="text-sm text-zinc-400">
            {ready ? `${pickedCount} of ${pickedTotal} picked` : "…"}
          </span>
          <button
            onClick={clearWeek}
            className="rounded-lg border border-zinc-800 px-3 py-1.5 text-xs font-semibold text-zinc-400 hover:border-zinc-600 hover:text-white light:border-zinc-200 light:hover:border-zinc-400 light:hover:text-zinc-900"
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

      {games.length === 0 ? (
        <p className="mt-4 rounded-xl border border-white/10 bg-zinc-900/40 p-6 text-sm text-zinc-400 light:border-zinc-200 light:bg-zinc-50 light:text-zinc-600">
          No games on tonight&rsquo;s slate yet — the pipeline publishes the card once lines are logged.
        </p>
      ) : (
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          {games.map((g) => {
            const k = gameKey(g);
            const selAts = stored.weeks[slateKey]?.ats?.[k] as Side | undefined;
            const selOu = stored.weeks[slateKey]?.ou?.[k] as OuPick | undefined;
            const selSu = weekPicks[k] as Side | undefined;
            const hintAts = modelHint(g, "ats");
            const hintOu = modelHint(g, "ou");
            const hintSu = modelHint(g, "su");
            const spreadBtn = (side: Side) => {
              const active = selAts === side;
              const name = side === "home" ? g.home : g.away;
              const abbr = side === "home" ? g.home_abbr : g.away_abbr;
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
                    <NbaTeamLogo abbr={abbr} name={name} size={28} />
                    {spreadLabel(g, side)}
                  </div>
                  <div className="text-xs text-zinc-500">
                    {name}
                    {hintAts && spreadLabel(g, side) === hintAts && " · model's pick"}
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
              const name = side === "home" ? g.home : g.away;
              const abbr = side === "home" ? g.home_abbr : g.away_abbr;
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
                    <NbaTeamLogo abbr={abbr} name={name} size={28} />
                    {name}
                  </div>
                  <div className="text-xs text-zinc-500">
                    {name}
                    {hintSu && name === hintSu && " · model's lean"}
                  </div>
                </button>
              );
            };
            return (
              <article key={k} className="rounded-2xl border border-white/10 bg-gradient-to-b from-zinc-900/70 to-zinc-900/30 p-4 transition-colors hover:border-white/20 light:border-zinc-200 light:from-white light:to-zinc-50 light:hover:border-zinc-300">
                <div className="flex items-baseline justify-between">
                  <h3 className="flex flex-wrap items-center gap-x-2 font-bold">
                    <span className="inline-flex items-center gap-1.5">
                      <NbaTeamLogo abbr={g.away_abbr} name={g.away} size={22} />
                      {g.away}
                    </span>
                    <span className="font-medium text-zinc-500">{g.neutral ? "vs" : "@"}</span>
                    <span className="inline-flex items-center gap-1.5">
                      <NbaTeamLogo abbr={g.home_abbr} name={g.home} size={22} />
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
      )}
      <p className="mt-3 text-xs text-zinc-500">
        Honor system for now — lock your picks before tip-off. Your card is graded
        when the slate&rsquo;s results land.
      </p>

      {/* You vs the model */}
      <h2 className="mt-12 font-display text-3xl font-semibold uppercase tracking-wide">You vs the model</h2>
      {gradedWeeks.length === 0 ? (
        <p className="mt-2 max-w-2xl text-[15px] text-zinc-400 light:text-zinc-600">
          No graded slates yet — the first results land when games go final, and this
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
            <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-5 light:border-zinc-200 light:bg-white">
              <div className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
                Over/Under · season
              </div>
              <div className="mt-2 flex items-baseline gap-4">
                <div>
                  <div className="font-mono text-3xl font-extrabold text-amber-300 light:text-amber-700">{fmtTally(youOu)}</div>
                  <div className="text-xs text-zinc-500">You</div>
                </div>
                <div className="text-xl text-zinc-600">vs</div>
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
                <tr className="border-b border-zinc-800 text-xs uppercase tracking-wider text-zinc-500 light:border-zinc-200">
                  <th className="px-4 py-3">Slate</th>
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
                    <td className="px-4 py-3 font-semibold">{slateTitle(r.week)}</td>
                    <td className="px-4 py-3 font-mono text-amber-200/90 light:text-amber-700">{r.youAts ? fmtTally(r.youAts) : "—"}</td>
                    <td className="px-4 py-3 font-mono text-zinc-400">{fmtTally(r.modelAts)}</td>
                    <td className="px-4 py-3 font-mono text-amber-200/90 light:text-amber-700">{r.youSu ? fmtTally(r.youSu) : "—"}</td>
                    <td className="px-4 py-3 font-mono text-zinc-400">{fmtTally(r.modelSu)}</td>
                    <td className="px-4 py-3 font-mono text-amber-200/90 light:text-amber-700">{r.youOu ? fmtTally(r.youOu) : "—"}</td>
                    <td className="px-4 py-3 font-mono text-zinc-400">{fmtTally(r.modelOu)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-xs text-zinc-500">
            “—” means you didn&apos;t save picks that night on this browser.
          </p>
          {rows.some((r) => r.games.length > 0) && (
            <div className="mt-8">
              <h3 className="font-display text-xl font-semibold uppercase tracking-wide">
                Your picks, game by game
              </h3>
              <div className="mt-3 space-y-3">
                {rows.filter((r) => r.games.length > 0).map((r) => (
                  <details
                    key={r.week}
                    className="group rounded-2xl border border-zinc-800 light:border-zinc-200"
                  >
                    <summary className="cursor-pointer list-none px-4 py-3 font-semibold">
                      <span className="mr-2 inline-block transition-transform group-open:rotate-90">▸</span>
                      {slateTitle(r.week)}
                      <span className="ml-2 font-sans text-sm font-normal text-zinc-500">
                        {r.games.length} graded {r.games.length === 1 ? "pick" : "picks"}
                      </span>
                    </summary>
                    <ul className="space-y-2 border-t border-zinc-800/60 px-4 py-3 light:border-zinc-200">
                      {r.games.map((gd) => (
                        <li key={gd.label} className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
                          <span className="font-mono font-bold">{gd.label}</span>
                          <span className="font-mono text-xs text-zinc-500">{gd.score}</span>
                          {gd.ats && (
                            <span className="inline-flex items-center gap-1.5">
                              <span className="text-zinc-400 light:text-zinc-600">Spread: {gd.ats.pick}</span>
                              <ResultBadge r={gd.ats.result} />
                            </span>
                          )}
                          {gd.su && (
                            <span className="inline-flex items-center gap-1.5">
                              <span className="text-zinc-400 light:text-zinc-600">SU: {gd.su.pick}</span>
                              <ResultBadge r={gd.su.result} />
                            </span>
                          )}
                          {gd.ou && (
                            <span className="inline-flex items-center gap-1.5">
                              <span className="text-zinc-400 light:text-zinc-600">O/U: {gd.ou.pick}</span>
                              <ResultBadge r={gd.ou.result} />
                            </span>
                          )}
                        </li>
                      ))}
                    </ul>
                  </details>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
