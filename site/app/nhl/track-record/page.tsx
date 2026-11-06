import type { Metadata } from "next";
import record from "../../../data/nhl_track_record.json";
import seasonLog from "../../../data/nhl_season_2027.json";
import { fmtPct } from "../../lib/format";
import CollapsibleGroup from "../../lib/collapsible-group";
import NhlTeamLogo from "../../lib/nhl-team-logo";

export const metadata: Metadata = {
  title: "NHL track record",
  description:
    "The complete Honest Line NHL track record: the pre-launch shadow record, the backtest, and every published pick graded in public.",
  alternates: { canonical: "/nhl/track-record" },
};

type Backtest = {
  discovery: { games: number; brier_cal: number; su_pct: number };
  validation: { games: number; brier_cal: number; su_pct: number };
  market_eval_2025_26: {
    games: number; model_brier: number; market_brier: number;
    model_su_pct: number; market_su_pct: number;
  };
};

type ShadowSeed = {
  label: string; dates: string;
  games_logged: number; games_graded: number; paired_games: number;
  brier_raw: number; brier_cal: number; market_brier: number;
  su_pct_ex_invalid: number; su_record_ex_invalid: string;
  su_pct_all_games: number; note: string;
  excluded_game: {
    date: string; game_id: number; matchup: string;
    frozen_home_ml: number; books: number; market_p_home: number;
    market_brier: number; final_score: string;
    reason: string; model_line: string;
  };
};

type Season = {
  season: number; days: string[]; games: number;
  straight_up_pct: number | null; paired_games: number;
  brier_raw: number | null; brier_cal: number | null;
  market_brier: number | null;
  pick_w: number; pick_l: number; pick_pct: number | null;
  totals_rmse: number | null;
};

type RecordFile = {
  model: string;
  backtest: Backtest;
  shadow_seed: ShadowSeed;
  seasons: Season[];
};

type GradedPick = {
  away: string; home: string; away_abbr: string; home_abbr: string;
  market_p_home: number | null; p_home_cal: number;
  pick_side: "home" | "away" | null;
  pick_label: string | null; pick_prob: number | null;
  market_excluded?: boolean;
  result: {
    home_score: number; away_score: number;
    su?: "win" | "loss" | null;
  } | null;
};

type DayLog = {
  generated: string; complete: boolean; picks: GradedPick[];
  source?: string;
};
type SeasonLog = { sport: string; season: number; days: Record<string, DayLog> };

const rec = record as unknown as RecordFile;
const seed = rec.shadow_seed;
const bt = rec.backtest;
const seasons = rec.seasons ?? [];

function resultBadge(r?: "win" | "loss" | null) {
  if (!r) return <span className="text-zinc-600 light:text-zinc-400">—</span>;
  const cls =
    r === "win" ? "bg-emerald-500/15 text-emerald-400 light:bg-emerald-600/15 light:text-emerald-700"
    : "bg-red-500/15 text-red-400 light:bg-red-600/15 light:text-red-600";
  return <span className={`rounded px-2 py-0.5 text-xs font-bold uppercase ${cls}`}>{r}</span>;
}

function fmtBrier(x: number | null | undefined): string {
  return x == null ? "—" : x.toFixed(4);
}

function fmtDay(dk: string): string {
  const parts = dk.split("-").map(Number);
  if (parts.length < 3 || parts.some(Number.isNaN)) return dk;
  const [, m, d] = parts;
  const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  return `${months[m - 1]} ${d}`;
}

function winPct(w: number, l: number): number | null {
  return w + l === 0 ? null : w / (w + l);
}

export default function NhlTrackRecord() {
  return (
    <div>
      <div className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-red-500/90 light:text-red-700">
        <span className="h-px w-8 bg-red-500/60 light:bg-red-600/70" aria-hidden="true" />
        NHL · Full history · nothing hidden
      </div>
      <h1 className="mt-3 font-display text-5xl font-semibold uppercase leading-[0.95] tracking-wide">
        Track <span className="text-red-500 light:text-red-600">record</span>
      </h1>
      <p className="mt-4 max-w-2xl text-sm text-zinc-400 light:text-zinc-600">{rec.model}</p>

      <h2 className="mt-12 font-display text-3xl font-semibold uppercase tracking-wide">
        {seed.label} — {seed.dates}
      </h2>
      <p className="mt-1 max-w-2xl text-[15px] leading-relaxed text-zinc-400 light:text-zinc-600">
        {seed.note}
      </p>
      <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
        {[
          { label: "Games graded", value: String(seed.games_graded) },
          { label: "Straight-up (excl. invalid game)", value: `${fmtPct(seed.su_pct_ex_invalid)} · ${seed.su_record_ex_invalid}` },
          { label: "Brier, calibrated (paired)", value: fmtBrier(seed.brier_cal) },
          { label: "Market Brier (paired)", value: fmtBrier(seed.market_brier) },
        ].map((c) => (
          <div key={c.label} className="rounded-xl border border-white/10 bg-zinc-900/50 p-4 light:border-zinc-200 light:bg-white">
            <div className="tnum text-2xl font-extrabold">{c.value}</div>
            <div className="mt-1 text-xs text-zinc-500">{c.label}</div>
          </div>
        ))}
      </div>
      <div className="mt-4 overflow-x-auto rounded-xl border border-zinc-800 light:border-zinc-200">
        <table className="w-full min-w-[560px] text-sm">
          <thead>
            <tr className="bg-zinc-900 text-left text-xs uppercase tracking-wider text-zinc-400 light:bg-zinc-100 light:text-zinc-600">
              <th className="px-4 py-3">Moneyline Brier (lower is better)</th>
              <th className="px-4 py-3">Model, raw</th>
              <th className="px-4 py-3">Model, calibrated</th>
              <th className="px-4 py-3">Market</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-t border-zinc-800 light:border-zinc-200">
              <td className="px-4 py-3 font-semibold">Paired games, n={seed.paired_games}</td>
              <td className="px-4 py-3 font-mono">{fmtBrier(seed.brier_raw)}</td>
              <td className="px-4 py-3 font-mono">{fmtBrier(seed.brier_cal)}</td>
              <td className="px-4 py-3 font-mono">{fmtBrier(seed.market_brier)}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p className="mt-2 max-w-2xl text-[13px] leading-relaxed text-zinc-500">
        Five of the 110 graded games froze without a market line and sit outside the paired
        comparison entirely. Counted over all 110 games, the model&rsquo;s straight-up record
        is {fmtPct(seed.su_pct_all_games)} — the one excluded game below was a model miss,
        and it counts in the model&rsquo;s own numbers.
      </p>

      <div className="mt-6 max-w-3xl rounded-2xl border border-red-500/25 bg-red-500/[0.06] p-6 light:bg-red-50">
        <div className="text-xs font-bold uppercase tracking-[0.16em] text-red-500/90 light:text-red-700">
          Excluded from market comparisons — {seed.excluded_game.matchup}, {seed.excluded_game.date}
        </div>
        <p className="mt-2 text-sm leading-relaxed text-zinc-300 light:text-zinc-700">
          {seed.excluded_game.reason}
        </p>
        <p className="mt-2 text-sm leading-relaxed text-zinc-300 light:text-zinc-700">
          {seed.excluded_game.model_line} Final: {seed.excluded_game.final_score}.
        </p>
      </div>

      <LiveSeason log={seasonLog as unknown as SeasonLog} />

      <h2 className="mt-12 font-display text-3xl font-semibold uppercase tracking-wide">The backtest</h2>
      <p className="mt-1 max-w-2xl text-[15px] leading-relaxed text-zinc-400 light:text-zinc-600">
        Walk-forward: every prediction made before learning the result, ratings refitted
        season by season. The honest summary is the same as the shadow record&rsquo;s — a
        competent forecaster at market level, not ahead of it.
      </p>
      <div className="mt-4 overflow-x-auto rounded-xl border border-zinc-800 light:border-zinc-200">
        <table className="w-full min-w-[560px] text-sm">
          <thead>
            <tr className="bg-zinc-900 text-left text-xs uppercase tracking-wider text-zinc-400 light:bg-zinc-100 light:text-zinc-600">
              <th className="px-4 py-3">Sample</th>
              <th className="px-4 py-3">Games</th>
              <th className="px-4 py-3">Brier, calibrated</th>
              <th className="px-4 py-3">Straight-up</th>
            </tr>
          </thead>
          <tbody>
            <tr className="border-t border-zinc-800 light:border-zinc-200">
              <td className="px-4 py-3 font-semibold">Discovery (fit)</td>
              <td className="px-4 py-3 font-mono">{bt.discovery.games.toLocaleString()}</td>
              <td className="px-4 py-3 font-mono">{fmtBrier(bt.discovery.brier_cal)}</td>
              <td className="px-4 py-3 font-mono">{fmtPct(bt.discovery.su_pct)}</td>
            </tr>
            <tr className="border-t border-zinc-800 light:border-zinc-200">
              <td className="px-4 py-3 font-semibold">Validation (held out)</td>
              <td className="px-4 py-3 font-mono">{bt.validation.games.toLocaleString()}</td>
              <td className="px-4 py-3 font-mono">{fmtBrier(bt.validation.brier_cal)}</td>
              <td className="px-4 py-3 font-mono">{fmtPct(bt.validation.su_pct)}</td>
            </tr>
            <tr className="border-t border-zinc-800 light:border-zinc-200">
              <td className="px-4 py-3 font-semibold">2025–26 vs the market</td>
              <td className="px-4 py-3 font-mono">{bt.market_eval_2025_26.games.toLocaleString()}</td>
              <td className="px-4 py-3 font-mono">
                {fmtBrier(bt.market_eval_2025_26.model_brier)} vs {fmtBrier(bt.market_eval_2025_26.market_brier)} market
              </td>
              <td className="px-4 py-3 font-mono">
                {fmtPct(bt.market_eval_2025_26.model_su_pct)} vs {fmtPct(bt.market_eval_2025_26.market_su_pct)} market
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p className="mt-2 max-w-2xl text-[13px] leading-relaxed text-zinc-500">
        Over a full season against real closing lines, the market was the better forecaster.
        We publish anyway and grade every game in public — that is the point of this site.
      </p>

      <h2 className="mt-12 font-display text-3xl font-semibold uppercase tracking-wide">Season by season</h2>
      {seasons.length > 0 ? (
        <div className="mt-4 overflow-x-auto rounded-xl border border-zinc-800 light:border-zinc-200">
          <table className="w-full min-w-[720px] text-sm">
            <thead className="sticky-head">
              <tr className="bg-zinc-900 text-left text-xs uppercase tracking-wider text-zinc-400 light:bg-zinc-100 light:text-zinc-600">
                <th className="px-4 py-3">Season</th>
                <th className="px-4 py-3">Games</th>
                <th className="px-4 py-3">Straight-up</th>
                <th className="px-4 py-3">Brier, calibrated</th>
                <th className="px-4 py-3">Market Brier</th>
                <th className="px-4 py-3">Picks record</th>
                <th className="px-4 py-3">Picks %</th>
              </tr>
            </thead>
            <tbody>
              {[...seasons].reverse().map((s) => (
                <tr key={s.season} className="border-t border-zinc-800 hover:bg-zinc-900/50 light:border-zinc-200 light:hover:bg-zinc-100">
                  <td className="px-4 py-3 font-semibold">{s.season - 1}–{String(s.season).slice(2)}</td>
                  <td className="px-4 py-3 font-mono">{s.games}</td>
                  <td className="px-4 py-3 font-mono">{s.straight_up_pct != null ? fmtPct(s.straight_up_pct) : "—"}</td>
                  <td className="px-4 py-3 font-mono text-zinc-400 light:text-zinc-600">{fmtBrier(s.brier_cal)}</td>
                  <td className="px-4 py-3 font-mono text-zinc-400 light:text-zinc-600">{fmtBrier(s.market_brier)}</td>
                  <td className="px-4 py-3 font-mono">{s.pick_w}-{s.pick_l}</td>
                  <td className="px-4 py-3 font-mono">{s.pick_pct != null ? fmtPct(s.pick_pct) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="mt-4 text-[15px] text-zinc-400 light:text-zinc-600">No graded season yet.</p>
      )}
      <p className="mt-2 max-w-2xl text-[13px] leading-relaxed text-zinc-500">
        Brier scores are paired: model and market are compared on the same games — only
        games that froze with a valid market line count, for either side. The 2026–27 row
        opens with the shadow seed above; from Nov 6, 2026 onward it counts published
        boards only, where a pick requires a 2-point disagreement.
      </p>

      <h2 className="mt-12 font-display text-3xl font-semibold uppercase tracking-wide">How it works — briefly</h2>
      <div className="mt-4 max-w-3xl space-y-3 text-[15px] leading-relaxed text-zinc-400 light:text-zinc-600">
        <p>
          Each team carries an offense and a defense rating, fitted walk-forward on
          expected goals — a team is credited for the chances it creates, not just the
          goals that happened to go in. Expected goals for a matchup add a 0.20-goal
          home-ice term and a rest-day term (a team on short rest attacks a little less),
          then a Poisson model turns expected goals into a win probability. A calibration
          map fitted on the 4,573-game discovery period adjusts the raw probabilities;
          the calibrated number is the one we publish and grade.
        </p>
        <p>
          The market comparison uses the median moneyline across US books (The Odds API),
          de-vigged. A pick publishes when the model&rsquo;s calibrated probability and
          the market&rsquo;s disagree by 2.0 points or more; closer than that, the board
          shows no play. Totals are context only: the model&rsquo;s expected total is
          displayed next to the market total, but no totals pick is published and no
          totals record is kept. There is no NHL parlay.
        </p>
        <p>
          Data sources: historical expected goals from{" "}
          <a href="https://moneypuck.com" target="_blank" rel="noopener noreferrer" className="underline">MoneyPuck</a>;
          scores and schedules from the official NHL API; lines from The Odds API.
        </p>
      </div>
    </div>
  );
}

function LiveSeason({ log }: { log: SeasonLog }) {
  const days = Object.entries(log.days).sort(([a], [b]) => (a < b ? 1 : a > b ? -1 : 0));
  if (days.length === 0) return null;

  let w = 0, l = 0;
  for (const [, d] of days) {
    for (const p of d.picks) {
      if (p.result?.su === "win") w++; else if (p.result?.su === "loss") l++;
    }
  }

  return (
    <div className="mt-8">
      <h2 className="font-display text-3xl font-semibold uppercase tracking-wide">
        {log.season - 1}–{String(log.season).slice(2)} season — live
        <span className="ml-3 rounded bg-red-500/15 px-2 py-0.5 align-middle font-sans text-xs font-bold uppercase tracking-wider text-red-300 light:bg-red-600/15 light:text-red-700">
          grading in progress
        </span>
      </h2>
      <p className="mt-1 text-sm text-zinc-400 light:text-zinc-600">
        This season&rsquo;s picks, graded as games go final. The Oct 21 – Nov 5 days below
        are the pre-launch shadow record — in shadow, the model&rsquo;s favored side counted
        as the pick in every game; published boards from Nov 6 apply the 2-point gate.
        Nothing hidden, nothing rewritten.
      </p>
      <div className="mt-4 grid grid-cols-2 gap-4">
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4 light:border-zinc-200 light:bg-white">
          <div className="text-2xl font-extrabold">{w}-{l}</div>
          <div className="mt-0.5 text-sm font-semibold text-zinc-400 light:text-zinc-600">{fmtPct(winPct(w, l))}</div>
          <div className="mt-1 text-xs text-zinc-500">Moneyline picks</div>
        </div>
        <div className="rounded-xl border border-red-500/25 bg-red-500/[0.06] p-4 light:bg-red-50">
          <div className="text-2xl font-extrabold">Context only</div>
          <div className="mt-0.5 text-sm font-semibold text-zinc-400 light:text-zinc-600">No totals record</div>
          <div className="mt-1 text-xs text-zinc-500">Model totals are displayed, never published as picks</div>
        </div>
      </div>
      {days.map(([dk, d], i) => (
        <CollapsibleGroup
          key={dk}
          className="mt-6"
          defaultOpen={i === 0}
          header={
            <h3 className="text-sm font-bold uppercase tracking-wider text-zinc-400 light:text-zinc-600">
              {fmtDay(dk)} {d.complete ? "" : "· partial"}{d.source === "shadow" ? " · shadow" : ""}
            </h3>
          }
        >
          <div className="mt-2 overflow-x-auto rounded-xl border border-zinc-800 light:border-zinc-200">
            <table className="w-full min-w-[720px] text-sm">
              <thead>
                <tr className="bg-zinc-900 text-left text-xs uppercase tracking-wider text-zinc-400 light:bg-zinc-100 light:text-zinc-600">
                  <th className="px-4 py-3">Game</th>
                  <th className="px-4 py-3">Score</th>
                  <th className="px-4 py-3">Model (home win %)</th>
                  <th className="px-4 py-3">Market</th>
                  <th className="px-4 py-3">Pick</th>
                  <th className="px-4 py-3">Result</th>
                </tr>
              </thead>
              <tbody>
                {d.picks.map((p) => (
                  <tr key={`${p.away}-${p.home}`} className="border-t border-zinc-800 light:border-zinc-200">
                    <td className="px-4 py-3 font-semibold">
                      <span className="inline-flex items-center gap-1.5">
                        <NhlTeamLogo abbr={p.away_abbr} name={p.away} size={20} />{p.away}
                      </span>
                      <span className="text-zinc-500"> @ </span>
                      <span className="inline-flex items-center gap-1.5">
                        <NhlTeamLogo abbr={p.home_abbr} name={p.home} size={20} />{p.home}
                      </span>
                      {p.market_excluded && (
                        <span className="ml-2 rounded bg-zinc-500/15 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-zinc-400 light:text-zinc-600">
                          market excluded
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 font-mono">{p.result ? `${p.result.away_score}-${p.result.home_score}` : "—"}</td>
                    <td className="px-4 py-3 font-mono text-zinc-400 light:text-zinc-600">{fmtPct(p.p_home_cal)}</td>
                    <td className="px-4 py-3 font-mono text-zinc-400 light:text-zinc-600">
                      {p.market_excluded ? "invalid line" : p.market_p_home != null ? fmtPct(p.market_p_home) : "—"}
                    </td>
                    <td className="px-4 py-3 text-zinc-400 light:text-zinc-600">
                      {p.pick_side ? `${p.pick_label ?? p.pick_side} (${fmtPct(p.pick_prob)})` : "No play"}
                    </td>
                    <td className="px-4 py-3">{resultBadge(p.result?.su)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CollapsibleGroup>
      ))}
    </div>
  );
}
