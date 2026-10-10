"use client";

import { useMemo } from "react";
import type { ReactNode } from "react";
import calibration from "../../data/calibration.json";
import nflSeason from "../../data/season_2026.json";
import cfbSeason from "../../data/cfb_season_2026.json";
import nbaSeason from "../../data/nba_season_2027.json";
import ncaabSeason from "../../data/ncaab_season_2027.json";
import mlbSeason from "../../data/mlb_season_2027.json";
import { fmtPct } from "../lib/format";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

type CalBin = { label: string; n: number; predicted: number; actual: number };
type CalBacktest = { label: string; games: number; bins: CalBin[] };
type CalMarket = {
  id: string;
  label: string;
  backtest: CalBacktest;
  curve: [number, number][] | null;
  verdict: string;
};
type CalSport = { id: string; label: string; markets: CalMarket[] };
type CalFile = { generated: string; note: string; sports: CalSport[] };

const cal = calibration as unknown as CalFile;

type DayLog = { picks?: Record<string, unknown>[] };
type SeasonLog = { season: number; weeks?: Record<string, DayLog>; days?: Record<string, DayLog> };

const SEASON_FILES: Record<string, SeasonLog> = {
  nfl: nflSeason as unknown as SeasonLog,
  cfb: cfbSeason as unknown as SeasonLog,
  nba: nbaSeason as unknown as SeasonLog,
  ncaab: ncaabSeason as unknown as SeasonLog,
  mlb: mlbSeason as unknown as SeasonLog,
};

const SPORT_ORDER = ["nfl", "cfb", "nba", "ncaab", "mlb"];
const sports = [...cal.sports].sort(
  (a, b) => SPORT_ORDER.indexOf(a.id) - SPORT_ORDER.indexOf(b.id)
);

/* ------------------------------------------------------------------ */
/* Live-season binning (client-side, from the deployed season files)   */
/* ------------------------------------------------------------------ */

function seasonPicks(sportId: string): Record<string, unknown>[] {
  const log = SEASON_FILES[sportId];
  if (!log) return [];
  const groups = Object.values(log.weeks ?? log.days ?? {});
  return groups.flatMap((g) => g.picks ?? []);
}

type Wlp = "win" | "loss" | "push" | null;

function probOf(p: Record<string, unknown>, marketId: string): number | null {
  if (marketId === "moneyline") {
    // Field name is still unconfirmed — the season file is empty pre-season.
    for (const f of ["win_prob", "home_win_prob", "ml_prob", "p_home", "prob"]) {
      const v = p[f];
      if (typeof v === "number" && Number.isFinite(v)) return v;
    }
    return null;
  }
  const v = p[marketId === "ats" ? "cover_prob" : "ou_prob"];
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}

function resultOf(p: Record<string, unknown>, marketId: string): Wlp {
  const r = p.result as Record<string, unknown> | string | null | undefined;
  if (!r) return null;
  if (marketId === "moneyline") {
    if (typeof r === "string") return r === "win" || r === "loss" || r === "push" ? r : null;
    const ml = r.ml;
    return ml === "win" || ml === "loss" || ml === "push" ? ml : null;
  }
  const v = (r as Record<string, unknown>)[marketId === "ats" ? "ats" : "ou"];
  return v === "win" || v === "loss" || v === "push" ? v : null;
}

type Edge = { lo: number; hi: number | null; label: string };

/* Published probabilities are on the recalibrated scale (hugging 50%), so the
   live bins are tight around 50%. Bins with n < 30 are flagged, not hidden. */
const LIVE_EDGES: Edge[] = [
  { lo: 0.5, hi: 0.51, label: "50–51%" },
  { lo: 0.51, hi: 0.52, label: "51–52%" },
  { lo: 0.52, hi: 0.53, label: "52–53%" },
  { lo: 0.53, hi: null, label: "53%+" },
];

/* MLB win probabilities span 30–70%, so reuse the backtest's own bin edges. */
function parseBinLabel(label: string): Edge {
  const nums = (label.match(/[\d.]+/g) ?? []).map(Number);
  if (label.startsWith("<")) return { lo: 0, hi: nums[0] / 100, label };
  if (label.endsWith("+")) return { lo: nums[0] / 100, hi: null, label };
  return { lo: nums[0] / 100, hi: nums[1] / 100, label };
}

type LiveBin = { label: string; n: number; predicted: number | null; actual: number | null };

function liveBinsFor(sportId: string, market: CalMarket): LiveBin[] {
  const edges =
    market.id === "moneyline"
      ? market.backtest.bins.map((b) => parseBinLabel(b.label))
      : LIVE_EDGES;
  const picks = seasonPicks(sportId);
  return edges.map((e) => {
    let n = 0, wins = 0, sumP = 0;
    for (const p of picks) {
      const prob = probOf(p, market.id);
      const res = resultOf(p, market.id);
      if (prob == null || res == null || res === "push") continue;
      if (prob >= e.lo && (e.hi == null || prob < e.hi)) {
        n++;
        sumP += prob;
        if (res === "win") wins++;
      }
    }
    return { label: e.label, n, predicted: n ? sumP / n : null, actual: n ? wins / n : null };
  });
}

/* ------------------------------------------------------------------ */
/* Hand-rolled SVG calibration plot                                    */
/* ------------------------------------------------------------------ */

const W = 560, H = 430;
const M = { l: 58, r: 20, t: 20, b: 56 };

function CalibrationPlot({ market, live }: { market: CalMarket; live: LiveBin[] }) {
  const bins = market.backtest.bins;
  const curve = market.curve ?? [];

  const xs: number[] = [], ys: number[] = [];
  for (const b of bins) { xs.push(b.predicted); ys.push(b.actual); }
  for (const [x, y] of curve) { xs.push(x); ys.push(y); }
  for (const b of live) {
    if (b.n > 0 && b.predicted != null && b.actual != null) { xs.push(b.predicted); ys.push(b.actual); }
  }
  if (xs.length === 0) return null;

  let lo = Math.min(0.45, ...xs, ...ys);
  lo = Math.floor(lo * 20) / 20;
  let hi = Math.max(0.55, ...xs, ...ys);
  hi = Math.ceil(hi * 20) / 20;

  const iw = W - M.l - M.r, ih = H - M.t - M.b;
  const X = (v: number) => M.l + ((v - lo) / (hi - lo)) * iw;
  const Y = (v: number) => M.t + (1 - (v - lo) / (hi - lo)) * ih;

  const ticks: number[] = [];
  for (let t = lo; t <= hi + 1e-9; t += 0.05) ticks.push(Math.round(t * 100) / 100);

  const maxN = Math.max(1, ...bins.map((b) => b.n));
  const rOf = (n: number) => 5 + 9 * Math.sqrt(n / maxN);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img"
      aria-label={`${market.label} calibration plot: published probability versus actual hit rate`}
      className="h-auto w-full">
      {/* grid + ticks */}
      {ticks.map((t) => (
        <g key={t}>
          <line x1={M.l} x2={W - M.r} y1={Y(t)} y2={Y(t)}
            className="stroke-zinc-800 light:stroke-zinc-200" strokeWidth={t === 0.5 ? 1.5 : 1} />
          <text x={M.l - 8} y={Y(t) + 3.5} textAnchor="end" fontSize={10}
            className="fill-zinc-500 font-mono">{fmtPct(t)}</text>
          <line x1={X(t)} x2={X(t)} y1={M.t} y2={H - M.b}
            className="stroke-zinc-800 light:stroke-zinc-200" strokeWidth={1} />
          <text x={X(t)} y={H - M.b + 18} textAnchor="middle" fontSize={10}
            className="fill-zinc-500 font-mono">{fmtPct(t)}</text>
        </g>
      ))}

      {/* ideal diagonal */}
      <line x1={X(lo)} y1={Y(lo)} x2={X(hi)} y2={Y(hi)}
        className="stroke-zinc-500" strokeWidth={1.5} strokeDasharray="6 5" />
      <text x={X(hi) - 4} y={Y(hi) - 8} textAnchor="end" fontSize={10}
        className="fill-zinc-500 italic">perfect calibration</text>

      {/* fitted recalibration curve */}
      {curve.length > 1 && (
        <polyline
          points={curve.map(([x, y]) => `${X(x)},${Y(y)}`).join(" ")}
          fill="none" strokeWidth={2.5}
          className="stroke-emerald-400 light:stroke-emerald-600" />
      )}

      {/* backtest bins — circles sized by n */}
      {bins.map((b) => (
        <circle key={b.label} cx={X(b.predicted)} cy={Y(b.actual)} r={rOf(b.n)}
          strokeWidth={1.5} opacity={0.92}
          className="fill-zinc-100 stroke-zinc-500 light:fill-zinc-700 light:stroke-zinc-300">
          <title>{`Backtest ${b.label}: published ${fmtPct(b.predicted)}, hit ${fmtPct(b.actual)} (n=${b.n.toLocaleString()})`}</title>
        </circle>
      ))}

      {/* live-season bins — emerald diamonds; hollow = small sample */}
      {live.filter((b) => b.n > 0).map((b) => {
        const cx = X(b.predicted!), cy = Y(b.actual!), r = 7;
        const small = b.n < 30;
        return (
          <polygon key={b.label}
            points={`${cx},${cy - r} ${cx + r},${cy} ${cx},${cy + r} ${cx - r},${cy}`}
            strokeWidth={2}
            className={small
              ? "fill-transparent stroke-emerald-400 light:stroke-emerald-600"
              : "fill-emerald-400 stroke-emerald-400 light:fill-emerald-600 light:stroke-emerald-600"}
            strokeDasharray={small ? "3 2" : undefined}>
            <title>{`This season ${b.label}: published ${fmtPct(b.predicted)}, hit ${fmtPct(b.actual)} (n=${b.n})${small ? " — small sample" : ""}`}</title>
          </polygon>
        );
      })}

      {/* axis titles */}
      <text x={(M.l + W - M.r) / 2} y={H - 8} textAnchor="middle" fontSize={11}
        className="fill-zinc-400 font-semibold light:fill-zinc-600">Published probability</text>
      <text x={16} y={(M.t + H - M.b) / 2} textAnchor="middle" fontSize={11} transform={`rotate(-90 16 ${(M.t + H - M.b) / 2})`}
        className="fill-zinc-400 font-semibold light:fill-zinc-600">Actual hit rate</text>
    </svg>
  );
}

function Legend() {
  const items: { label: string; swatch: ReactNode }[] = [
    {
      label: "Perfect calibration",
      swatch: <span className="inline-block h-0 w-8 border-t-2 border-dashed border-zinc-500" aria-hidden="true" />,
    },
    {
      label: "Backtest bin (size = picks)",
      swatch: <span className="inline-block h-3.5 w-3.5 rounded-full bg-zinc-100 ring-1 ring-zinc-500 light:bg-zinc-700 light:ring-zinc-300" aria-hidden="true" />,
    },
    {
      label: "Fitted calibration curve",
      swatch: <span className="inline-block h-0 w-8 border-t-[3px] border-emerald-400 light:border-emerald-600" aria-hidden="true" />,
    },
    {
      label: "This season (live)",
      swatch: <span className="inline-block h-3 w-3 rotate-45 bg-emerald-400 light:bg-emerald-600" aria-hidden="true" />,
    },
    {
      label: "Small sample (n < 30)",
      swatch: <span className="inline-block h-3 w-3 rotate-45 border-2 border-dashed border-emerald-400 light:border-emerald-600" aria-hidden="true" />,
    },
  ];
  return (
    <div className="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-xs text-zinc-500 light:text-zinc-600">
      {items.map((it) => (
        <span key={it.label} className="inline-flex items-center gap-2">
          {it.swatch}{it.label}
        </span>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Tables                                                              */
/* ------------------------------------------------------------------ */

const thCls = "px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wider text-zinc-500 light:text-zinc-600";
const tdCls = "px-3 py-2 font-mono text-[13px]";
const rowCls = "border-t border-zinc-800 light:border-zinc-200";

function BinTable({ bins, caption }: { bins: CalBin[]; caption: string }) {
  return (
    <div>
      <div className="mb-2 text-xs font-bold uppercase tracking-wider text-zinc-400 light:text-zinc-600">{caption}</div>
      <div className="overflow-x-auto rounded-xl border border-zinc-800 light:border-zinc-200">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-zinc-900/60 text-left light:bg-zinc-100">
              <th className={thCls}>Bin</th>
              <th className={thCls}>Published</th>
              <th className={thCls}>Actual</th>
              <th className={thCls}>n</th>
            </tr>
          </thead>
          <tbody>
            {bins.map((b) => (
              <tr key={b.label} className={rowCls}>
                <td className="px-3 py-2 font-semibold">{b.label}</td>
                <td className={`${tdCls} text-zinc-300 light:text-zinc-700`}>{fmtPct(b.predicted)}</td>
                <td className={`${tdCls} font-semibold ${b.actual >= b.predicted ? "text-emerald-400 light:text-emerald-700" : "text-amber-400 light:text-amber-700"}`}>
                  {fmtPct(b.actual)}
                </td>
                <td className={`${tdCls} text-zinc-400 light:text-zinc-600`}>{b.n.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function SmallSampleFlag() {
  return (
    <span className="ml-2 rounded bg-amber-400/15 px-1.5 py-0.5 align-middle font-sans text-[10px] font-bold uppercase tracking-wide text-amber-300 light:bg-amber-600/15 light:text-amber-700">
      small sample
    </span>
  );
}

function LiveTable({ bins, season }: { bins: LiveBin[]; season: number }) {
  const hasAny = bins.some((b) => b.n > 0);
  return (
    <div>
      <div className="mb-2 text-xs font-bold uppercase tracking-wider text-zinc-400 light:text-zinc-600">
        {season} season · live
      </div>
      {!hasAny ? (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 px-4 py-5 text-sm text-zinc-500 light:border-zinc-200 light:bg-zinc-50 light:text-zinc-600">
          No graded picks yet — check back as this season&rsquo;s games go final.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-emerald-400/25 light:border-emerald-600/30">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-zinc-900/60 text-left light:bg-zinc-100">
                <th className={thCls}>Bin</th>
                <th className={thCls}>Published</th>
                <th className={thCls}>Actual</th>
                <th className={thCls}>n</th>
              </tr>
            </thead>
            <tbody>
              {bins.filter((b) => b.n > 0).map((b) => (
                <tr key={b.label} className={rowCls}>
                  <td className="px-3 py-2 font-semibold">
                    {b.label}
                    {b.n < 30 && <SmallSampleFlag />}
                  </td>
                  <td className={`${tdCls} text-zinc-300 light:text-zinc-700`}>{fmtPct(b.predicted)}</td>
                  <td className={`${tdCls} font-semibold text-emerald-400 light:text-emerald-700`}>
                    {fmtPct(b.actual)}
                  </td>
                  <td className={`${tdCls} text-zinc-400 light:text-zinc-600`}>{b.n.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Market + sport sections                                             */
/* ------------------------------------------------------------------ */

function MarketSection({ sportId, market, season }: { sportId: string; market: CalMarket; season: number }) {
  const live = useMemo(() => liveBinsFor(sportId, market), [sportId, market]);
  const honest = market.id === "moneyline"; // MLB: no recalibration needed
  const hasCurve = (market.curve ?? []).length > 1;

  return (
    <div className="mt-10">
      <h3 className="font-display text-2xl font-semibold uppercase tracking-wide">{market.label}</h3>
      <div className={`mt-3 max-w-3xl border-l-2 pl-4 text-[15px] leading-relaxed light:border-amber-700 ${
        honest ? "border-emerald-400/70" : "border-amber-400/70"}`}>
        <span className={`font-bold ${honest ? "text-emerald-300 light:text-emerald-700" : "text-amber-200 light:text-amber-700"}`}>
          The verdict:{" "}
        </span>
        <span className="text-zinc-300 light:text-zinc-700">{market.verdict}</span>
      </div>
      <p className="mt-3 max-w-3xl text-sm text-zinc-500 light:text-zinc-600">
        {market.backtest.games.toLocaleString()} graded picks in bins · {market.backtest.label}
        {!hasCurve && " · no recalibration curve — the raw model was already honest"}
      </p>

      <div className="mt-6 grid gap-8 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-4 sm:p-6 light:border-zinc-200 light:bg-white">
            <CalibrationPlot market={market} live={live} />
            <Legend />
          </div>
        </div>
        <div className="space-y-6 lg:col-span-2">
          <BinTable bins={market.backtest.bins} caption="Backtest" />
          <LiveTable bins={live} season={season} />
        </div>
      </div>
    </div>
  );
}

const SPORT_NOTES: Record<string, string> = {
  nfl: "EPA ratings, walk-forward — the live model, not the legacy 45-season Elo table.",
  cfb: "PPA-based ratings, 13 seasons of walk-forward history.",
  nba: "Margin-adjusted Elo with efficiency totals and rest-day adjustment.",
  ncaab: "Efficiency ratings, walk-forward across 2013–2021 and 2025–2026.",
  mlb: "Park-adjusted runs ratings with a Normal-CDF win probability. Already honest — no recalibration needed.",
};

function SportSection({ sport }: { sport: CalSport }) {
  const season = SEASON_FILES[sport.id]?.season ?? 0;
  return (
    <section className="mt-16 border-t border-zinc-800/80 pt-10 light:border-zinc-200" id={sport.id}>
      <div className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-emerald-400/90 light:text-emerald-700">
        <span className="h-px w-8 bg-emerald-400/60 light:bg-emerald-600/70" aria-hidden="true" />
        {sport.label} · calibration
      </div>
      <h2 className="mt-3 font-display text-4xl font-semibold uppercase tracking-wide">
        {sport.label}
      </h2>
      <p className="mt-2 max-w-2xl text-[15px] text-zinc-400 light:text-zinc-600">
        {SPORT_NOTES[sport.id]}
      </p>
      {sport.id === "mlb" && (
        <div className="mt-5 max-w-3xl rounded-2xl border border-emerald-400/25 bg-emerald-400/[0.06] p-6 light:bg-emerald-50">
          <div className="font-display text-xl font-semibold uppercase tracking-wide text-emerald-300 light:text-emerald-700">
            The contrast: already honest
          </div>
          <p className="mt-2 text-[15px] leading-relaxed text-zinc-300 light:text-zinc-700">
            Baseball is the one sport where the textbook formula survived contact with reality.
            A published 57% won 57%; the bins sit on the diagonal with no fitted curve needed.
            Its Brier score (0.2456 vs the closing line&rsquo;s 0.2402) still says the line is
            sharper — but at least the probabilities mean what they claim. Every other sport
            on this site needed recalibration to earn that sentence.
          </p>
        </div>
      )}
      {sport.markets.map((m) => (
        <MarketSection key={m.id} sportId={sport.id} market={m} season={season} />
      ))}
    </section>
  );
}

/* ------------------------------------------------------------------ */
/* Page                                                                */
/* ------------------------------------------------------------------ */

export default function CalibrationPage() {
  return (
    <div>
      {/* Hero */}
      <div className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-emerald-400/90 light:text-emerald-700">
        <span className="h-px w-8 bg-emerald-400/60 light:bg-emerald-600/70" aria-hidden="true" />
        The honesty page · backtest evidence {cal.generated}
      </div>
      <h1 className="mt-3 max-w-3xl font-display text-5xl font-semibold uppercase leading-[0.95] tracking-wide sm:text-6xl">
        Most sites show <span className="text-emerald-400 light:text-emerald-600">confidence</span>.
        We show receipts.
      </h1>
      <div className="mt-6 max-w-3xl space-y-4 text-[15px] leading-relaxed text-zinc-300 light:text-zinc-700">
        <p>
          Calibration is the only thing a probability claim has to be: when we publish 55%,
          does it hit 55%? On every plot below, published probability runs along the bottom
          and actual hit rate up the side. Perfect calibration is the dashed diagonal.
        </p>
        <p>
          Our raw models sat far off it — a published 77% was hitting 45%. The gap between
          our number and the Vegas line turned out to be mostly our error, not our insight.
          So on 2026-10-09 we replaced the textbook formula with an empirical calibration:
          every published probability now runs through the actual hit rates from that
          model&rsquo;s own walk-forward backtest. A number we publish as 55% is a number
          that hit about 55% in testing.
        </p>
        <p>
          The curves cluster near 50% because that&rsquo;s the honest answer. The models
          barely beat a coin flip against the line, and we say so — right here, in public,
          with the bins anyone can re-derive.
        </p>
      </div>

      {/* How to read */}
      <div className="mt-8 max-w-3xl rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6 light:border-zinc-200 light:bg-zinc-50">
        <div className="font-display text-lg font-semibold uppercase tracking-wide">How to read this page</div>
        <ul className="mt-3 space-y-2 text-sm leading-relaxed text-zinc-400 light:text-zinc-600">
          <li><span className="font-semibold text-zinc-200 light:text-zinc-800">Circles</span> are backtest bins, sized by picks. <span className="font-semibold text-zinc-200 light:text-zinc-800">Emerald line</span> is the fitted recalibration curve — what we actually publish now.</li>
          <li><span className="font-semibold text-zinc-200 light:text-zinc-800">Emerald diamonds</span> are this season&rsquo;s live receipts, computed in your browser from the graded picks as games go final. <span className="font-semibold text-zinc-200 light:text-zinc-800">Hollow diamonds</span> are small samples (n &lt; 30) — shown, not hidden.</li>
          <li><span className="font-semibold text-zinc-200 light:text-zinc-800">“Graded picks in bins”</span> means picks that fell into the published-probability bins — pushes and below-threshold exclusions omitted. It is not total walk-forward games.</li>
        </ul>
      </div>

      {sports.map((s) => (
        <SportSection key={s.id} sport={s} />
      ))}

      <div className="mt-16 max-w-3xl rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6 light:border-zinc-200 light:bg-zinc-50">
        <p className="text-sm leading-relaxed text-zinc-400 light:text-zinc-600">
          Published probabilities switched to the recalibrated scale on 2026-10-09. Weeks
          generated before that (NFL week 4, CFB weeks 5–6) show the old formula&rsquo;s
          numbers — they&rsquo;re still in the live bins, because deleting bad history
          would be the opposite of the point. The backtest tables, the code, and the
          grading crons are all in the repo. Audit us.
        </p>
      </div>
    </div>
  );
}
