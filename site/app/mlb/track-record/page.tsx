import type { Metadata } from "next";
import record from "../../../data/mlb_track_record.json";
import { fmtPct } from "../../lib/format";

export const metadata: Metadata = {
  title: "MLB track record",
  description:
    "The Honest Line MLB track record: a 10-season walk-forward backtest over 22,765 games, published honestly — including the losing ROI.",
  alternates: { canonical: "/mlb/track-record" },
};

type Season = {
  season: number; games: number; straight_up_pct: number;
  brier_model: number; brier_line: number;
  ml: { bets: number; wins: number; losses: number; win_pct: number; profit: number; roi: number };
  totals: { our_rmse: number; line_rmse: number; ou: [number, number, number]; ou_pct: number; roi: number };
};

type Overall = {
  games: number; straight_up_pct: number;
  brier_model: number; brier_line: number;
  ml: { bets: number; wins: number; losses: number; win_pct: number; profit: number; roi: number };
  totals: { our_rmse: number; line_rmse: number; ou: [number, number, number]; ou_pct: number; profit: number; roi: number };
};

type RecordFile = { model: string; overall: Overall; seasons: Season[] };

const rec = record as unknown as RecordFile;
const overall = rec.overall;
const seasons = rec.seasons;

function fmtRoi(r: number) {
  return `${r < 0 ? "−" : "+"}${Math.abs(r * 100).toFixed(1)}%`;
}

function roiCls(r: number) {
  return r >= 0
    ? "text-emerald-400 light:text-emerald-700"
    : "text-red-400 light:text-red-600";
}

export default function MlbTrackRecord() {
  return (
    <div>
      <div className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-amber-400/90 light:text-amber-700">
        <span className="h-px w-8 bg-amber-400/60 light:bg-amber-600/70" aria-hidden="true" />
        MLB · Full history · nothing hidden
      </div>
      <h1 className="mt-3 font-display text-5xl font-semibold uppercase leading-[0.95] tracking-wide">
        Track <span className="text-amber-400 light:text-amber-600">record</span>
      </h1>
      <p className="mt-4 max-w-2xl text-sm text-zinc-400 light:text-zinc-600">{rec.model}</p>

      <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        {[
          { label: "Seasons backtested", value: "2012–2021" },
          { label: "Games", value: overall.games.toLocaleString() },
          { label: "Straight-up", value: fmtPct(overall.straight_up_pct) },
          { label: "Brier (model vs line)", value: `${overall.brier_model.toFixed(4)} vs ${overall.brier_line.toFixed(4)}` },
        ].map((c) => (
          <div key={c.label} className="rounded-xl border border-white/10 bg-zinc-900/50 p-4 light:border-zinc-200 light:bg-white">
            <div className="tnum text-2xl font-extrabold">{c.value}</div>
            <div className="mt-1 text-xs text-zinc-500">{c.label}</div>
          </div>
        ))}
      </div>

      <h2 className="mt-12 font-display text-3xl font-semibold uppercase tracking-wide">Model vs the closing line</h2>
      <p className="mt-1 max-w-2xl text-[15px] leading-relaxed text-zinc-400 light:text-zinc-600">
        The walk-forward verdict, in full: the model is a decent forecaster and loses to the
        closing line everywhere that matters.
      </p>
      <div className="mt-4 overflow-x-auto rounded-xl border border-zinc-800 light:border-zinc-200">
        <table className="w-full min-w-[560px] text-sm">
          <thead>
            <tr className="bg-zinc-900 text-left text-xs uppercase tracking-wider text-zinc-400 light:bg-zinc-100 light:text-zinc-600">
              <th className="px-4 py-3">Metric</th>
              <th className="px-4 py-3">Us</th>
              <th className="px-4 py-3">Closing line</th>
              <th className="px-4 py-3">Verdict</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-t border-zinc-800 light:border-zinc-200">
              <td className="px-4 py-3 font-semibold">Brier score</td>
              <td className="px-4 py-3 font-mono">{overall.brier_model.toFixed(4)}</td>
              <td className="px-4 py-3 font-mono">{overall.brier_line.toFixed(4)}</td>
              <td className="px-4 py-3 font-mono font-semibold text-red-400 light:text-red-600">+{(overall.brier_model - overall.brier_line).toFixed(4)} worse</td>
            </tr>
            <tr className="border-t border-zinc-800 light:border-zinc-200">
              <td className="px-4 py-3 font-semibold">Total RMSE</td>
              <td className="px-4 py-3 font-mono">{overall.totals.our_rmse.toFixed(2)}</td>
              <td className="px-4 py-3 font-mono">{overall.totals.line_rmse.toFixed(2)}</td>
              <td className="px-4 py-3 font-mono font-semibold text-red-400 light:text-red-600">+{(overall.totals.our_rmse - overall.totals.line_rmse).toFixed(2)} worse</td>
            </tr>
            <tr className="border-t border-zinc-800 light:border-zinc-200">
              <td className="px-4 py-3 font-semibold">Moneyline (≥0.05 edge)</td>
              <td className="px-4 py-3 font-mono">{overall.ml.wins.toLocaleString()}-{overall.ml.losses.toLocaleString()} · {fmtPct(overall.ml.win_pct)}</td>
              <td className="px-4 py-3 font-mono text-zinc-400 light:text-zinc-600">—</td>
              <td className={`px-4 py-3 font-mono font-semibold ${roiCls(overall.ml.roi)}`}>{fmtRoi(overall.ml.roi)} ROI</td>
            </tr>
            <tr className="border-t border-zinc-800 light:border-zinc-200">
              <td className="px-4 py-3 font-semibold">O/U (≥0.5-run disagreement)</td>
              <td className="px-4 py-3 font-mono">{overall.totals.ou[0].toLocaleString()}-{overall.totals.ou[1].toLocaleString()}-{overall.totals.ou[2].toLocaleString()} · {fmtPct(overall.totals.ou_pct)}</td>
              <td className="px-4 py-3 font-mono text-zinc-400 light:text-zinc-600">—</td>
              <td className={`px-4 py-3 font-mono font-semibold ${roiCls(overall.totals.roi)}`}>{fmtRoi(overall.totals.roi)} ROI</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="mt-8 rounded-2xl border border-amber-400/25 bg-amber-400/[0.06] p-6 light:bg-amber-50">
        <div className="text-xs font-bold uppercase tracking-[0.16em] text-amber-400/90 light:text-amber-700">The honest verdict</div>
        <p className="mt-2 max-w-2xl text-[15px] leading-relaxed text-zinc-300 light:text-zinc-700">
          Walk-forward, 2012–2021 ({overall.games.toLocaleString()} games): the model picks the
          winner {fmtPct(overall.straight_up_pct)} straight up — barely above the{" "}
          {fmtPct(0.535)} the home team won on its own. Flat $100 moneyline bets went{" "}
          {overall.ml.wins.toLocaleString()}-{overall.ml.losses.toLocaleString()} ({fmtPct(overall.ml.win_pct)}) for{" "}
          <span className={`font-semibold ${roiCls(overall.ml.roi)}`}>{fmtRoi(overall.ml.roi)} ROI</span>{" "}
          over {overall.ml.bets.toLocaleString()} bets; on the post-tuning 2016–2021 slice it was{" "}
          <span className="font-semibold text-red-400 light:text-red-600">−1.0% ROI</span>. Totals went{" "}
          {overall.totals.ou[0].toLocaleString()}-{overall.totals.ou[1].toLocaleString()}-{overall.totals.ou[2].toLocaleString()} ({fmtPct(overall.totals.ou_pct)}) for{" "}
          <span className={`font-semibold ${roiCls(overall.totals.roi)}`}>{fmtRoi(overall.totals.roi)} ROI</span>.{" "}
          <span className="font-semibold text-zinc-100 light:text-zinc-900">Competent forecaster, no betting edge.</span>{" "}
          Team strength alone does not beat the closing MLB line.
        </p>
      </div>

      <h2 className="mt-12 font-display text-3xl font-semibold uppercase tracking-wide">Season by season</h2>
      <p className="mt-1 max-w-2xl text-[15px] text-zinc-400 light:text-zinc-600">
        Every season the model was tested on. Green ROI seasons were profitable; the rest weren&rsquo;t.
      </p>
      <div className="mt-4 overflow-x-auto rounded-xl border border-zinc-800 light:border-zinc-200">
        <table className="w-full min-w-[860px] text-sm">
          <thead>
            <tr className="bg-zinc-900 text-left text-xs uppercase tracking-wider text-zinc-400 light:bg-zinc-100 light:text-zinc-600">
              <th className="px-4 py-3">Season</th>
              <th className="px-4 py-3">Games</th>
              <th className="px-4 py-3">Straight-up</th>
              <th className="px-4 py-3">Brier (us / line)</th>
              <th className="px-4 py-3">Moneyline</th>
              <th className="px-4 py-3">ML ROI</th>
              <th className="px-4 py-3">Total RMSE (us / line)</th>
              <th className="px-4 py-3">O/U</th>
              <th className="px-4 py-3">O/U ROI</th>
            </tr>
          </thead>
          <tbody>
            {[...seasons].reverse().map((s) => (
              <tr key={s.season} className="border-t border-zinc-800 hover:bg-zinc-900/50 light:border-zinc-200 light:hover:bg-zinc-100">
                <td className="px-4 py-3 font-semibold">{s.season}{s.season === 2020 ? "*" : ""}</td>
                <td className="px-4 py-3 font-mono">{s.games.toLocaleString()}</td>
                <td className="px-4 py-3 font-mono">{fmtPct(s.straight_up_pct)}</td>
                <td className="px-4 py-3 font-mono text-zinc-400 light:text-zinc-600">{s.brier_model.toFixed(4)} / {s.brier_line.toFixed(4)}</td>
                <td className="px-4 py-3 font-mono">{s.ml.wins.toLocaleString()}-{s.ml.losses.toLocaleString()}</td>
                <td className={`px-4 py-3 font-mono font-semibold ${roiCls(s.ml.roi)}`}>{fmtRoi(s.ml.roi)}</td>
                <td className="px-4 py-3 font-mono text-zinc-400 light:text-zinc-600">{s.totals.our_rmse.toFixed(2)} / {s.totals.line_rmse.toFixed(2)}</td>
                <td className="px-4 py-3 font-mono">{s.totals.ou[0].toLocaleString()}-{s.totals.ou[1].toLocaleString()}-{s.totals.ou[2].toLocaleString()}</td>
                <td className={`px-4 py-3 font-mono font-semibold ${roiCls(s.totals.roi)}`}>{fmtRoi(s.totals.roi)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-xs text-zinc-500">* 2020: the shortened 60-game season.</p>
    </div>
  );
}
