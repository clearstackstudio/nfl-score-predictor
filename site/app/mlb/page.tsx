"use client";
import picksData from "../../data/mlb_picks.json";
import record from "../../data/mlb_track_record.json";
import { fmtPct } from "../lib/format";

type PicksFile = {
  sport: string; season: number; date?: string | null;
  generated: string | null; disclaimer: string;
  pending?: boolean; pending_reason?: string;
  picks: unknown[];
};

const data = picksData as PicksFile;
const overall = (record as unknown as { overall: {
  games: number; straight_up_pct: number;
  ml: { bets: number; roi: number };
  totals: { roi: number; ou: [number, number, number] };
} }).overall;

function fmtRoi(r: number) {
  return `${r < 0 ? "−" : "+"}${Math.abs(r * 100).toFixed(1)}%`;
}

function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-amber-400/90 light:text-amber-700">
      <span className="h-px w-8 bg-amber-400/60 light:bg-amber-600/70" aria-hidden="true" />
      {children}
    </div>
  );
}

export default function MlbHome() {
  const isPending = !!data.pending || data.picks.length === 0;

  return (
    <div>
      <div className="mb-8">
        <Eyebrow>MLB · {data.season} season</Eyebrow>
        <h1 className="mt-3 font-display text-5xl font-semibold uppercase leading-[0.95] tracking-wide sm:text-6xl">
          MLB <span className="text-amber-400 light:text-amber-600">picks</span>
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
          <div className="mt-6 rounded-2xl border border-amber-400/25 bg-amber-400/[0.06] p-8 text-center light:bg-amber-50">
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
              className="mt-5 inline-block rounded-xl bg-amber-400 px-6 py-3 text-sm font-bold uppercase tracking-wider text-zinc-950 transition hover:bg-amber-300"
            >
              Full track record →
            </a>
          </div>
        )}

        <p className="mt-5 max-w-2xl rounded-xl border border-amber-400/25 bg-amber-400/10 px-4 py-3 text-sm leading-relaxed text-amber-200/90 light:text-amber-800">
          {data.disclaimer}
        </p>
      </div>
    </div>
  );
}
