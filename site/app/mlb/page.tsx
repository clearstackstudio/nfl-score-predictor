"use client";
import picksData from "../../data/mlb_picks.json";
import record from "../../data/mlb_track_record.json";
import { fmtPct } from "../lib/format";
import AdSlot from "../lib/ad-slot";

type PicksFile = {
  sport: string; season: number; date?: string | null;
  generated: string | null; disclaimer: string;
  pending?: boolean; pending_reason?: string;
  picks: unknown[];
};

const data = picksData as PicksFile;
const overall = (record as unknown as { overall: {
  games: number; straight_up_pct: number;
  brier_model: number; brier_line: number;
  ml: { bets: number; roi: number };
  totals: { roi: number; ou: [number, number, number] };
} }).overall;

function fmtRoi(r: number) {
  return `${r < 0 ? "−" : "+"}${Math.abs(r * 100).toFixed(1)}%`;
}

function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-red-500/90 light:text-red-700">
      <span className="h-px w-8 bg-red-500/60 light:bg-red-600/70" aria-hidden="true" />
      {children}
    </div>
  );
}

export default function MlbHome() {
  const isPending = !!data.pending || data.picks.length === 0;

  return (
    <div>
      <AdSlot format="leaderboard" league="mlb" />
      <div className="mb-8">
        <Eyebrow>MLB · {data.season} season</Eyebrow>
        <h1 className="mt-3 font-display text-5xl font-semibold uppercase leading-[0.95] tracking-wide sm:text-6xl">
          MLB <span className="text-red-500 light:text-red-600">picks</span>
        </h1>
        <p className="mt-4 max-w-2xl text-[15px] leading-relaxed text-zinc-400 light:text-zinc-600">
          Daily MLB picks from park-adjusted exponential runs ratings — with a fitted
          home edge of 0.130 runs, a Normal-CDF win probability (sigma 4.135), and a
          totals model off the same ratings. The model never sees the betting line;
          the line is only the benchmark we measure against. Same honesty rules as
          every sport here: every pick published before first pitch, every result
          graded in public.
        </p>

        {isPending && (
          <div className="mt-6 rounded-2xl border border-red-500/25 bg-red-500/[0.06] p-8 text-center light:bg-red-50">
            <div className="font-display text-2xl font-semibold uppercase tracking-wide">
              2027 season starts late March
            </div>
            <p className="mx-auto mt-3 max-w-xl text-[15px] leading-relaxed text-zinc-400 light:text-zinc-600">
              {data.pending_reason ??
                "No MLB games until Opening Day 2027. Showing the walk-forward backtest record instead."}
            </p>
            <div className="mx-auto mt-6 grid max-w-xl grid-cols-1 gap-3 sm:grid-cols-3">
              <div className="rounded-xl border border-white/10 bg-zinc-900/50 p-4 light:border-zinc-200 light:bg-white">
                <div className="tnum text-2xl font-extrabold">{fmtPct(overall.straight_up_pct)}</div>
                <div className="mt-1 text-xs text-zinc-500">Straight-up, {overall.games.toLocaleString()} games</div>
              </div>
              <div className="rounded-xl border border-white/10 bg-zinc-900/50 p-4 light:border-zinc-200 light:bg-white">
                <div className="tnum text-2xl font-extrabold text-red-400 light:text-red-600">{fmtRoi(overall.ml.roi)}</div>
                <div className="mt-1 text-xs text-zinc-500">Moneyline ROI, {overall.ml.bets.toLocaleString()} bets</div>
              </div>
              <div className="rounded-xl border border-white/10 bg-zinc-900/50 p-4 light:border-zinc-200 light:bg-white">
                <div className="tnum text-2xl font-extrabold text-red-400 light:text-red-600">{fmtRoi(overall.totals.roi)}</div>
                <div className="mt-1 text-xs text-zinc-500">O/U ROI, {(overall.totals.ou[0] + overall.totals.ou[1] + overall.totals.ou[2]).toLocaleString()} bets</div>
              </div>
            </div>
            <p className="mx-auto mt-6 max-w-xl text-[15px] leading-relaxed text-zinc-300 light:text-zinc-700">
              The backtest verdict:{" "}
              <span className="font-semibold text-zinc-100 light:text-zinc-900">
                competent forecaster, no betting edge.
              </span>
            </p>
            <a
              href="/mlb/track-record"
              className="mt-5 inline-block rounded-xl bg-red-500 px-6 py-3 text-sm font-bold uppercase tracking-wider text-white transition hover:bg-red-600"
            >
              Full track record →
            </a>
          </div>
        )}

        <p className="mt-5 max-w-2xl rounded-xl border border-red-500/25 bg-red-500/10 px-4 py-3 text-sm leading-relaxed text-red-200/90 light:text-red-800">
          {data.disclaimer}
        </p>
      </div>

      <section className="mt-4 max-w-3xl">
        <h2 className="font-display text-3xl font-semibold uppercase tracking-wide">
          The model in brief
        </h2>
        <div className="mt-4 space-y-4 text-[15px] leading-relaxed text-zinc-300 light:text-zinc-700">
          <p>
            Every team carries two park-adjusted ratings — one for runs scored, one for
            runs allowed — updated after every game with a slow exponential learning
            rate (alpha = 1/40), because baseball&rsquo;s long season rewards patience
            over reaction. Park factors are estimated from the games themselves, with
            expanding park factors shrunk toward the league over a 100-game prior, so a
            slugfest at Coors Field and a pitchers&rsquo; duel at Petco Park aren&rsquo;t
            judged on raw runs. A quarter of last season&rsquo;s ratings carry into
            April (a 0.25 prior-season carryover), the home team gets a fitted edge of
            0.130 runs, and neutral-site games get no home edge at all. The predicted
            run margin becomes a win probability through a Normal CDF (sigma 4.135)
            with a Platt recalibration layer on top. The betting line is never an input
            to any of this — it exists only as the benchmark the model is measured
            against.
          </p>
        </div>

        <h2 className="mt-10 font-display text-3xl font-semibold uppercase tracking-wide">
          The evidence so far
        </h2>
        <div className="mt-4 space-y-4 text-[15px] leading-relaxed text-zinc-300 light:text-zinc-700">
          <p>
            The MLB model is still in development, and it has not published a single
            live pick. What exists — and what this section presents until the live
            launch — is a walk-forward backtest over ten full seasons:{" "}
            {overall.games.toLocaleString()} games from 2012 through 2021, processed in
            chronological order, with every prediction made only from games already
            played. The model picked the winner {fmtPct(overall.straight_up_pct)} of
            the time straight up — the home team alone won {fmtPct(0.535)} — and its
            probabilities scored a Brier of {overall.brier_model.toFixed(4)} against
            the closing line&rsquo;s {overall.brier_line.toFixed(4)}. Flat moneyline
            bets at the model&rsquo;s edge threshold returned {fmtRoi(overall.ml.roi)}{" "}
            ROI over {overall.ml.bets.toLocaleString()} bets, and totals returned{" "}
            {fmtRoi(overall.totals.roi)} ROI. In plain terms: a competent forecaster
            that does not beat the market. Those numbers, losses included, are
            published in full on the track-record page, season by season.
          </p>
          <p>
            Live picks are scheduled to begin with the 2027 season — Opening Day is
            late March 2027 — with the daily pipeline (probable pitchers from the free
            MLB Stats API, that day&rsquo;s lines, picks published before first pitch,
            nightly grading) being built in February and March 2027. A starting-pitcher
            adjustment is designed for the live model but was never part of the
            team-level backtest, and it will claim nothing until it has been measured
            the same walk-forward way. Until the first live pick posts, everything in
            this section is backtest evidence and the final 2026 ratings — labeled as
            such, never dressed up as a live record.
          </p>
        </div>
      </section>

      <AdSlot format="rectangle" league="mlb" />
    </div>
  );
}
