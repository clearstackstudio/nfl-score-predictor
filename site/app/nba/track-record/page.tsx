import record from "../../../data/nba_track_record.json";
import seasonLog from "../../../data/nba_season_2027.json";
import { fmtPct } from "../../lib/format";
import NbaTeamLogo from "../../lib/nba-team-logo";

type Era = {
  label: string; games?: number | null;
  our_rmse: number; line_rmse: number;
  ats_pct: number | null; ou_pct: number | null; su_pct: number | null;
};

type Season = {
  season: number; games: number; straight_up_pct: number;
  our_rmse: number; line_rmse: number;
  ats_w: number; ats_l: number; ats_p: number; ats_pct: number | null;
  ou_w?: number; ou_l?: number; ou_p?: number; ou_pct?: number | null;
};

type GradedPick = {
  away: string; home: string; away_abbr?: string; home_abbr?: string;
  line_spread: number; line_total: number;
  our_spread: number; our_total: number;
  pick_spread: "home" | "away" | null;
  pick_total: "over" | "under" | null;
  pick_spread_label: string | null;
  pick_total_label: string | null;
  cover_prob: number | null; ou_prob: number | null;
  result: {
    home_score: number; away_score: number;
    ats?: "win" | "loss" | "push"; ou?: "win" | "loss" | "push";
  } | null;
};

type ParlayLeg = { game: string; market: string; label: string; prob: number };
type WeekLog = {
  generated: string; complete: boolean; picks: GradedPick[];
  parlay: { legs: ParlayLeg[]; result: "win" | "loss" | "push" | null } | null;
};
type SeasonLog = { sport: string; season: number; days: Record<string, WeekLog> };

type Overall = {
  games: number; straight_up_pct: number;
  our_margin_rmse: number; line_margin_rmse: number;
  ats: [number, number, number]; ats_pct: number;
  our_total_rmse: number; line_total_rmse: number;
  ou: [number, number, number]; ou_pct: number;
};

type RecordFile = {
  model: string; overall: Overall | null;
  eras?: Era[]; pending?: boolean; pending_reason?: string;
  pending_seasons?: boolean; pending_season_reason?: string;
  seasons: Season[];
};

const rec = record as unknown as RecordFile;
const overall = rec.overall;
const eras = rec.eras ?? [];
const seasons = rec.seasons;

function resultBadge(r?: "win" | "loss" | "push") {
  if (!r) return <span className="text-zinc-600 light:text-zinc-400">—</span>;
  const cls =
    r === "win" ? "bg-emerald-500/15 text-emerald-400 light:bg-emerald-600/15 light:text-emerald-700"
    : r === "loss" ? "bg-red-500/15 text-red-400 light:bg-red-600/15 light:text-red-600"
    : "bg-zinc-500/15 text-zinc-400 light:bg-zinc-500/15 light:text-zinc-600";
  return <span className={`rounded px-2 py-0.5 text-xs font-bold uppercase ${cls}`}>{r}</span>;
}

function fmtWlp(wlp: [number, number, number]) {
  return `${wlp[0].toLocaleString()}-${wlp[1].toLocaleString()}-${wlp[2].toLocaleString()}`;
}

export default function NbaTrackRecord() {
  if (!overall && eras.length === 0 && seasons.length === 0) {
    return (
      <div>
        <div className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-amber-400/90 light:text-amber-700">
          <span className="h-px w-8 bg-amber-400/60 light:bg-amber-600/70" aria-hidden="true" />
          NBA · Full history · nothing hidden
        </div>
        <h1 className="mt-3 font-display text-5xl font-semibold uppercase leading-[0.95] tracking-wide">
          Track <span className="text-amber-400 light:text-amber-600">record</span>
        </h1>
        <div className="mt-8 rounded-2xl border border-amber-400/25 bg-amber-400/[0.06] p-8 text-center light:bg-amber-50">
          <div className="font-display text-2xl font-semibold uppercase tracking-wide">Backtest warming up</div>
          <p className="mx-auto mt-3 max-w-xl text-[15px] leading-relaxed text-zinc-400 light:text-zinc-600">
            {rec.pending_reason ?? "The walk-forward backtest is still running."} Once it lands, every season — winners, losers, and the
            ATS record against the closing line — appears here, same as the other sports.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-amber-400/90 light:text-amber-700">
        <span className="h-px w-8 bg-amber-400/60 light:bg-amber-600/70" aria-hidden="true" />
        NBA · Full history · nothing hidden
      </div>
      <h1 className="mt-3 font-display text-5xl font-semibold uppercase leading-[0.95] tracking-wide">
        Track <span className="text-amber-400 light:text-amber-600">record</span>
      </h1>
      <p className="mt-4 max-w-2xl text-sm text-zinc-400 light:text-zinc-600">{rec.model}</p>

      {overall && (
        <>
          <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
            {[
              { label: "Seasons backtested", value: "2008–2023" },
              { label: "Games", value: overall.games.toLocaleString() },
              { label: "Straight-up", value: fmtPct(overall.straight_up_pct) },
              { label: "ATS (≥1.5pt edge)", value: `${fmtWlp(overall.ats)} · ${fmtPct(overall.ats_pct)}` },
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
                  <td className="px-4 py-3 font-semibold">Margin RMSE</td>
                  <td className="px-4 py-3 font-mono">{overall.our_margin_rmse.toFixed(2)}</td>
                  <td className="px-4 py-3 font-mono">{overall.line_margin_rmse.toFixed(2)}</td>
                  <td className="px-4 py-3 font-mono font-semibold text-red-400 light:text-red-600">+{(overall.our_margin_rmse - overall.line_margin_rmse).toFixed(2)} worse</td>
                </tr>
                <tr className="border-t border-zinc-800 light:border-zinc-200">
                  <td className="px-4 py-3 font-semibold">Total RMSE</td>
                  <td className="px-4 py-3 font-mono">{overall.our_total_rmse.toFixed(2)}</td>
                  <td className="px-4 py-3 font-mono">{overall.line_total_rmse.toFixed(2)}</td>
                  <td className="px-4 py-3 font-mono font-semibold text-red-400 light:text-red-600">+{(overall.our_total_rmse - overall.line_total_rmse).toFixed(2)} worse</td>
                </tr>
                <tr className="border-t border-zinc-800 light:border-zinc-200">
                  <td className="px-4 py-3 font-semibold">ATS (≥1.5pt disagreement)</td>
                  <td className="px-4 py-3 font-mono">{fmtWlp(overall.ats)} · {fmtPct(overall.ats_pct)}</td>
                  <td className="px-4 py-3 font-mono text-zinc-400 light:text-zinc-600">—</td>
                  <td className="px-4 py-3 font-mono font-semibold text-red-400 light:text-red-600">needs 52.4% at -110</td>
                </tr>
                <tr className="border-t border-zinc-800 light:border-zinc-200">
                  <td className="px-4 py-3 font-semibold">O/U (≥3pt disagreement)</td>
                  <td className="px-4 py-3 font-mono">{fmtWlp(overall.ou)} · {fmtPct(overall.ou_pct)}</td>
                  <td className="px-4 py-3 font-mono text-zinc-400 light:text-zinc-600">—</td>
                  <td className="px-4 py-3 font-mono font-semibold text-red-400 light:text-red-600">negative</td>
                </tr>
              </tbody>
            </table>
          </div>
        </>
      )}

      <LiveSeason log={seasonLog as unknown as SeasonLog} />

      {eras.length > 0 && (
        <>
          <h2 className="mt-12 font-display text-3xl font-semibold uppercase tracking-wide">ATS by era</h2>
          <p className="mt-1 max-w-2xl text-[15px] leading-relaxed text-zinc-400 light:text-zinc-600">
            No era comes close to a betting edge — and the gap to the line widens over time. The
            dashed line is 52.4% — break-even against standard -110 vig.
          </p>
          <div className="mt-4 space-y-3 rounded-2xl border border-zinc-800 bg-zinc-900/40 p-5 light:border-zinc-200 light:bg-zinc-50">
            {eras.map((e) => {
              const pct = e.ats_pct ?? 0;
              const left = Math.max(0, Math.min(100, ((pct - 0.45) / 0.15) * 100));
              const be = ((0.524 - 0.45) / 0.15) * 100;
              const good = pct >= 0.524;
              return (
                <div key={e.label} className="flex items-center gap-3">
                  <div className="w-24 shrink-0 text-sm font-bold">{e.label}</div>
                  <div className="relative h-6 flex-1 rounded bg-zinc-800/70 light:bg-zinc-200">
                    <div className="absolute inset-y-0 left-0 w-px bg-zinc-500 light:bg-zinc-400" style={{ left: `${be}%` }} title="Break-even 52.4%" />
                    <div className={`absolute inset-y-1 rounded ${good ? "bg-emerald-400/80 light:bg-emerald-500" : "bg-red-400/80 light:bg-red-500"}`} style={{ width: `${left}%` }} />
                  </div>
                  <div className={`w-16 shrink-0 text-right font-mono text-sm font-bold ${good ? "text-emerald-400 light:text-emerald-700" : "text-red-400 light:text-red-600"}`}>
                    {e.ats_pct != null ? fmtPct(e.ats_pct) : "—"}
                  </div>
                </div>
              );
            })}
          </div>

          <div className="mt-4 overflow-x-auto rounded-xl border border-zinc-800 light:border-zinc-200">
            <table className="w-full min-w-[560px] text-sm">
              <thead className="sticky-head">
                <tr className="bg-zinc-900 text-left text-xs uppercase tracking-wider text-zinc-400 light:bg-zinc-100 light:text-zinc-600">
                  <th className="px-4 py-3">Era</th>
                  <th className="px-4 py-3">ATS %</th>
                  <th className="px-4 py-3">O/U %</th>
                  <th className="px-4 py-3">Straight-up</th>
                  <th className="px-4 py-3">Our RMSE</th>
                  <th className="px-4 py-3">Line RMSE</th>
                </tr>
              </thead>
              <tbody>
                {eras.map((e) => (
                  <tr key={e.label} className="border-t border-zinc-800 light:border-zinc-200">
                    <td className="px-4 py-3 font-semibold">{e.label}</td>
                    <td className={`px-4 py-3 font-mono font-semibold ${e.ats_pct != null && e.ats_pct >= 0.524 ? "text-emerald-400 light:text-emerald-700" : "text-red-400 light:text-red-600"}`}>
                      {e.ats_pct != null ? fmtPct(e.ats_pct) : "—"}
                    </td>
                    <td className="px-4 py-3 font-mono text-zinc-400 light:text-zinc-600">{e.ou_pct != null ? fmtPct(e.ou_pct) : "—"}</td>
                    <td className="px-4 py-3 font-mono text-zinc-400 light:text-zinc-600">{e.su_pct != null ? fmtPct(e.su_pct) : "—"}</td>
                    <td className="px-4 py-3 font-mono text-zinc-400 light:text-zinc-600">{e.our_rmse.toFixed(2)}</td>
                    <td className="px-4 py-3 font-mono text-zinc-400 light:text-zinc-600">{e.line_rmse.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="mt-2 text-xs text-zinc-500">
            52.4% is break-even against standard -110 vig. Green = profitable, red = not.
          </p>
        </>
      )}

      <h2 className="mt-12 font-display text-3xl font-semibold uppercase tracking-wide">Season by season</h2>
      {seasons.length > 0 ? (
        <>
          <p className="mt-1 max-w-2xl text-[15px] text-zinc-400 light:text-zinc-600">
            Every season the model was tested on. Green ATS seasons beat the vig; the rest didn&rsquo;t.
          </p>
          <div className="mt-4 overflow-x-auto rounded-xl border border-zinc-800 light:border-zinc-200">
            <table className="w-full min-w-[720px] text-sm">
              <thead className="sticky-head">
                <tr className="bg-zinc-900 text-left text-xs uppercase tracking-wider text-zinc-400 light:bg-zinc-100 light:text-zinc-600">
                  <th className="px-4 py-3">Season</th>
                  <th className="px-4 py-3">Games</th>
                  <th className="px-4 py-3">Straight-up</th>
                  <th className="px-4 py-3">Our RMSE</th>
                  <th className="px-4 py-3">Line RMSE</th>
                  <th className="px-4 py-3">ATS record</th>
                  <th className="px-4 py-3">ATS %</th>
                </tr>
              </thead>
              <tbody>
                {[...seasons].reverse().map((s) => (
                  <tr key={s.season} className="border-t border-zinc-800 hover:bg-zinc-900/50 light:border-zinc-200 light:hover:bg-zinc-100">
                    <td className="px-4 py-3 font-semibold">{s.season}</td>
                    <td className="px-4 py-3 font-mono">{s.games}</td>
                    <td className="px-4 py-3 font-mono">{fmtPct(s.straight_up_pct)}</td>
                    <td className="px-4 py-3 font-mono text-zinc-400 light:text-zinc-600">{s.our_rmse.toFixed(2)}</td>
                    <td className="px-4 py-3 font-mono text-zinc-400 light:text-zinc-600">{s.line_rmse.toFixed(2)}</td>
                    <td className="px-4 py-3 font-mono">{s.ats_w}-{s.ats_l}-{s.ats_p}</td>
                    <td className={`px-4 py-3 font-mono ${s.ats_pct != null && s.ats_pct >= 0.524 ? "text-emerald-400 light:text-emerald-700" : "text-zinc-400 light:text-zinc-600"}`}>
                      {s.ats_pct != null ? fmtPct(s.ats_pct) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : (
        <div className="mt-4 rounded-2xl border border-amber-400/25 bg-amber-400/[0.06] p-6 text-center light:bg-amber-50">
          <p className="mx-auto max-w-xl text-[15px] leading-relaxed text-zinc-400 light:text-zinc-600">
            {rec.pending_season_reason ?? "Per-season detail is still being tabulated."}
          </p>
        </div>
      )}
    </div>
  );
}

function fmtDay(dk: string): string {
  const parts = dk.split("-").map(Number);
  if (parts.length < 3 || parts.some(Number.isNaN)) return dk;
  const [, m, d] = parts;
  const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  return `${months[m - 1]} ${d}`;
}

function LiveSeason({ log }: { log: SeasonLog }) {
  const days = Object.entries(log.days).sort(([a], [b]) => (a < b ? -1 : a > b ? 1 : 0));
  if (days.length === 0) return null;

  let aw = 0, al = 0, ap = 0, ow = 0, ol = 0, op = 0;
  let pw = 0, pl = 0, pp = 0;
  for (const [, w] of days) {
    for (const p of w.picks) {
      if (p.result?.ats === "win") aw++; else if (p.result?.ats === "loss") al++; else if (p.result?.ats === "push") ap++;
      if (p.result?.ou === "win") ow++; else if (p.result?.ou === "loss") ol++; else if (p.result?.ou === "push") op++;
    }
    if (w.parlay?.result === "win") pw++;
    else if (w.parlay?.result === "loss") pl++;
    else if (w.parlay?.result === "push") pp++;
  }

  return (
    <div className="mt-8">
      <h2 className="font-display text-3xl font-semibold uppercase tracking-wide">
        {log.season - 1}–{String(log.season).slice(2)} season — live
        <span className="ml-3 rounded bg-amber-400/15 px-2 py-0.5 align-middle font-sans text-xs font-bold uppercase tracking-wider text-amber-300 light:bg-amber-600/15 light:text-amber-700">
          grading in progress
        </span>
      </h2>
      <p className="mt-1 text-sm text-zinc-400 light:text-zinc-600">
        This season&rsquo;s picks, graded as games go final. Nothing hidden, nothing rewritten.
      </p>
      <div className="mt-4 grid grid-cols-3 gap-4">
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4 light:border-zinc-200 light:bg-white">
          <div className="text-2xl font-extrabold">{aw}-{al}-{ap}</div>
          <div className="mt-1 text-xs text-zinc-500">Against the spread</div>
        </div>
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4 light:border-zinc-200 light:bg-white">
          <div className="text-2xl font-extrabold">{ow}-{ol}-{op}</div>
          <div className="mt-1 text-xs text-zinc-500">Over/under</div>
        </div>
        <div className="rounded-xl border border-amber-400/25 bg-amber-400/[0.06] p-4 light:bg-amber-50">
          <div className="text-2xl font-extrabold">{pw}-{pl}-{pp}</div>
          <div className="mt-1 text-xs text-zinc-500">Parlay of the night</div>
        </div>
      </div>
      {days.map(([dk, w]) => (
        <div key={dk} className="mt-6">
          <h3 className="text-sm font-bold uppercase tracking-wider text-zinc-400 light:text-zinc-600">
            {fmtDay(dk)} {w.complete ? "" : "· partial"}
          </h3>
          {w.parlay && w.parlay.legs.length > 0 && (
            <div className="mt-2 flex flex-wrap items-center gap-2 rounded-xl border border-amber-400/25 bg-amber-400/[0.06] px-4 py-2.5 text-sm light:bg-amber-50">
              <span className="font-bold text-amber-200 light:text-amber-700">Parlay:</span>
              <span className="text-zinc-300 light:text-zinc-700">{w.parlay.legs.map((l) => l.label).join(" · ")}</span>
              {resultBadge(w.parlay.result ?? undefined)}
            </div>
          )}
          <div className="mt-2 overflow-x-auto rounded-xl border border-zinc-800 light:border-zinc-200">
            <table className="w-full min-w-[720px] text-sm">
              <thead>
                <tr className="bg-zinc-900 text-left text-xs uppercase tracking-wider text-zinc-400 light:bg-zinc-100 light:text-zinc-600">
                  <th className="px-4 py-3">Game</th>
                  <th className="px-4 py-3">Score</th>
                  <th className="px-4 py-3">Spread pick</th>
                  <th className="px-4 py-3">ATS</th>
                  <th className="px-4 py-3">O/U pick</th>
                  <th className="px-4 py-3">O/U</th>
                </tr>
              </thead>
              <tbody>
                {w.picks.map((p) => (
                  <tr key={`${p.away}-${p.home}`} className="border-t border-zinc-800 light:border-zinc-200">
                    <td className="px-4 py-3 font-semibold">
                      <span className="inline-flex items-center gap-1.5">
                        <NbaTeamLogo abbr={p.away_abbr ?? p.away} name={p.away} size={20} />{p.away}
                      </span>
                      <span className="text-zinc-500"> @ </span>
                      <span className="inline-flex items-center gap-1.5">
                        <NbaTeamLogo abbr={p.home_abbr ?? p.home} name={p.home} size={20} />{p.home}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono">{p.result ? `${p.result.away_score}-${p.result.home_score}` : "—"}</td>
                    <td className="px-4 py-3 text-zinc-400 light:text-zinc-600">
                      {p.pick_spread ? `${p.pick_spread_label ?? p.pick_spread} (${fmtPct(p.cover_prob)})` : "No play"}
                    </td>
                    <td className="px-4 py-3">{resultBadge(p.result?.ats)}</td>
                    <td className="px-4 py-3 text-zinc-400 light:text-zinc-600">
                      {p.pick_total ? `${p.pick_total_label ?? p.pick_total} (${fmtPct(p.ou_prob)})` : "No play"}
                    </td>
                    <td className="px-4 py-3">{resultBadge(p.result?.ou)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </div>
  );
}
