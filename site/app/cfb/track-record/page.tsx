import record from "../../../data/cfb_track_record.json";
import seasonLog from "../../../data/cfb_season_2026.json";
import { fmtPct } from "../../lib/format";

type Season = {
  season: number; games: number; straight_up_pct: number;
  our_rmse: number; line_rmse: number;
  ats_w: number; ats_l: number; ats_p: number; ats_pct: number | null;
};

type GradedPick = {
  away: string; home: string;
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
type SeasonLog = { sport: string; season: number; weeks: Record<string, WeekLog> };

type RecordFile = {
  model: string; overall: null | {
    games: number; straight_up_pct: number;
    our_margin_rmse: number; line_margin_rmse: number;
    ats: [number, number, number]; ats_pct: number;
    our_total_rmse: number; line_total_rmse: number;
    ou: [number, number, number]; ou_pct: number;
  };
  pending?: boolean; pending_reason?: string; seasons: Season[];
};

const rec = record as unknown as RecordFile;
const seasons = rec.seasons;

function decadeOf(s: Season) {
  return Math.floor(s.season / 10) * 10;
}

function resultBadge(r?: "win" | "loss" | "push") {
  if (!r) return <span className="text-zinc-600 light:text-zinc-400">—</span>;
  const cls =
    r === "win" ? "bg-emerald-500/15 text-emerald-400 light:bg-emerald-600/15 light:text-emerald-700"
    : r === "loss" ? "bg-red-500/15 text-red-400 light:bg-red-600/15 light:text-red-600"
    : "bg-zinc-500/15 text-zinc-400 light:bg-zinc-500/15 light:text-zinc-600";
  return <span className={`rounded px-2 py-0.5 text-xs font-bold uppercase ${cls}`}>{r}</span>;
}

export default function CfbTrackRecord() {
  if (rec.pending || seasons.length === 0) {
    return (
      <div>
        <div className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-amber-400/90 light:text-amber-700">
          <span className="h-px w-8 bg-amber-400/60 light:bg-amber-600/70" aria-hidden="true" />
          College football · Full history · nothing hidden
        </div>
        <h1 className="mt-3 font-display text-5xl font-semibold uppercase leading-[0.95] tracking-wide">
          Track <span className="text-amber-400 light:text-amber-600">record</span>
        </h1>
        <div className="mt-8 rounded-2xl border border-amber-400/25 bg-amber-400/[0.06] p-8 text-center light:bg-amber-50">
          <div className="font-display text-2xl font-semibold uppercase tracking-wide">Backtest warming up</div>
          <p className="mx-auto mt-3 max-w-xl text-[15px] leading-relaxed text-zinc-400 light:text-zinc-600">
            {rec.pending_reason} Once it lands, every season from 2014 on — winners, losers, and the
            ATS record against the closing line — appears here, same as the NFL side.
          </p>
        </div>
      </div>
    );
  }

  const totalGames = seasons.reduce((a, s) => a + s.games, 0);
  const tw = seasons.reduce((a, s) => a + s.ats_w, 0);
  const tl = seasons.reduce((a, s) => a + s.ats_l, 0);
  const tp = seasons.reduce((a, s) => a + s.ats_p, 0);
  const su = seasons.reduce((a, s) => a + s.straight_up_pct * s.games, 0) / totalGames;

  const decades = new Map<number, Season[]>();
  for (const s of seasons) {
    const d = decadeOf(s);
    if (!decades.has(d)) decades.set(d, []);
    decades.get(d)!.push(s);
  }

  return (
    <div>
      <div className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-amber-400/90 light:text-amber-700">
        <span className="h-px w-8 bg-amber-400/60 light:bg-amber-600/70" aria-hidden="true" />
        College football · Full history · nothing hidden
      </div>
      <h1 className="mt-3 font-display text-5xl font-semibold uppercase leading-[0.95] tracking-wide">
        Track <span className="text-amber-400 light:text-amber-600">record</span>
      </h1>
      <p className="mt-4 max-w-2xl text-sm text-zinc-400 light:text-zinc-600">{rec.model}</p>

      <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        {[
          { label: "Seasons backtested", value: String(seasons.length) },
          { label: "Games", value: totalGames.toLocaleString() },
          { label: "Straight-up", value: fmtPct(su) },
          { label: "ATS (≥1.5pt edge)", value: `${tw}-${tl}-${tp} · ${fmtPct(tw / (tw + tl))}` },
        ].map((c) => (
          <div key={c.label} className="rounded-xl border border-white/10 bg-zinc-900/50 p-4 light:border-zinc-200 light:bg-white">
            <div className="tnum text-2xl font-extrabold">{c.value}</div>
            <div className="mt-1 text-xs text-zinc-500">{c.label}</div>
          </div>
        ))}
      </div>

      <LiveSeason log={seasonLog as SeasonLog} />

      <h2 className="mt-12 font-display text-3xl font-semibold uppercase tracking-wide">ATS by era</h2>
      <p className="mt-1 max-w-2xl text-[15px] leading-relaxed text-zinc-400 light:text-zinc-600">
        The college market is less efficient than the NFL&rsquo;s — but &ldquo;less efficient&rdquo; is not
        the same as &ldquo;beatable.&rdquo; The dashed line is 52.4% — break-even against standard -110 vig.
      </p>

      <div className="mt-4 space-y-3 rounded-2xl border border-zinc-800 bg-zinc-900/40 p-5 light:border-zinc-200 light:bg-zinc-50">
        {[...decades.entries()].map(([d, ss]) => {
          const w = ss.reduce((a, s) => a + s.ats_w, 0);
          const l = ss.reduce((a, s) => a + s.ats_l, 0);
          const pct = w / (w + l);
          const left = Math.max(0, Math.min(100, ((pct - 0.45) / 0.15) * 100));
          const be = ((0.524 - 0.45) / 0.15) * 100;
          const good = pct >= 0.524;
          return (
            <div key={d} className="flex items-center gap-3">
              <div className="w-12 shrink-0 text-sm font-bold">{d}s</div>
              <div className="relative h-6 flex-1 rounded bg-zinc-800/70 light:bg-zinc-200">
                <div className="absolute inset-y-0 left-0 w-px bg-zinc-500 light:bg-zinc-400" style={{ left: `${be}%` }} title="Break-even 52.4%" />
                <div className={`absolute inset-y-1 rounded ${good ? "bg-emerald-400/80 light:bg-emerald-500" : "bg-red-400/80 light:bg-red-500"}`} style={{ width: `${left}%` }} />
              </div>
              <div className={`w-16 shrink-0 text-right font-mono text-sm font-bold ${good ? "text-emerald-400 light:text-emerald-700" : "text-red-400 light:text-red-600"}`}>
                {fmtPct(pct)}
              </div>
            </div>
          );
        })}
      </div>

      <h2 className="mt-12 font-display text-3xl font-semibold uppercase tracking-wide">Season by season</h2>
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
    </div>
  );
}

function LiveSeason({ log }: { log: SeasonLog }) {
  const weeks = Object.entries(log.weeks).sort(([a], [b]) => Number(a) - Number(b));
  if (weeks.length === 0) return null;

  let aw = 0, al = 0, ap = 0, ow = 0, ol = 0, op = 0;
  let pw = 0, pl = 0, pp = 0;
  for (const [, w] of weeks) {
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
        {log.season} season — live
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
          <div className="mt-1 text-xs text-zinc-500">Against the spread, {log.season}</div>
        </div>
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4 light:border-zinc-200 light:bg-white">
          <div className="text-2xl font-extrabold">{ow}-{ol}-{op}</div>
          <div className="mt-1 text-xs text-zinc-500">Over/under, {log.season}</div>
        </div>
        <div className="rounded-xl border border-amber-400/25 bg-amber-400/[0.06] p-4 light:bg-amber-50">
          <div className="text-2xl font-extrabold">{pw}-{pl}-{pp}</div>
          <div className="mt-1 text-xs text-zinc-500">Parlay of the week, {log.season}</div>
        </div>
      </div>
      {weeks.map(([wn, w]) => (
        <div key={wn} className="mt-6">
          <h3 className="text-sm font-bold uppercase tracking-wider text-zinc-400 light:text-zinc-600">
            Week {wn} {w.complete ? "" : "· partial"}
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
                    <td className="px-4 py-3 font-semibold">{p.away} @ {p.home}</td>
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
