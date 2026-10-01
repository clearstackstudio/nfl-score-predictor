import record from "../../data/track_record.json";
import { fmtPct } from "../lib/format";

type Season = {
  season: number; games: number; straight_up_pct: number;
  our_rmse: number; line_rmse: number;
  ats_w: number; ats_l: number; ats_p: number; ats_pct: number | null;
};

const seasons = record.seasons as Season[];

function decadeOf(s: Season) {
  return Math.floor(s.season / 10) * 10;
}

export default function TrackRecord() {
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
      <h1 className="text-3xl font-extrabold tracking-tight">Track record</h1>
      <p className="mt-2 max-w-2xl text-sm text-zinc-400">{record.model}</p>

      <div className="mt-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
        {[
          { label: "Seasons backtested", value: String(seasons.length) },
          { label: "Games", value: totalGames.toLocaleString() },
          { label: "Straight-up", value: fmtPct(su) },
          { label: "ATS (≥1.5pt edge)", value: `${tw}-${tl}-${tp} · ${fmtPct(tw / (tw + tl))}` },
        ].map((c) => (
          <div key={c.label} className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-4">
            <div className="text-2xl font-extrabold">{c.value}</div>
            <div className="mt-1 text-xs text-zinc-500">{c.label}</div>
          </div>
        ))}
      </div>

      <h2 className="mt-8 text-xl font-bold">ATS by decade — the edge decays</h2>
      <p className="mt-1 text-sm text-zinc-400">
        The model beats bad lines from weak eras. Against the modern market, it does not.
      </p>
      <div className="mt-4 overflow-x-auto rounded-xl border border-zinc-800">
        <table className="w-full min-w-[560px] text-sm">
          <thead>
            <tr className="bg-zinc-900 text-left text-xs uppercase tracking-wider text-zinc-400">
              <th className="px-4 py-3">Decade</th>
              <th className="px-4 py-3">Record</th>
              <th className="px-4 py-3">Win %</th>
              <th className="px-4 py-3">Our RMSE</th>
              <th className="px-4 py-3">Line RMSE</th>
            </tr>
          </thead>
          <tbody>
            {[...decades.entries()].map(([d, ss]) => {
              const w = ss.reduce((a, s) => a + s.ats_w, 0);
              const l = ss.reduce((a, s) => a + s.ats_l, 0);
              const p = ss.reduce((a, s) => a + s.ats_p, 0);
              const g = ss.reduce((a, s) => a + s.games, 0);
              const our = ss.reduce((a, s) => a + s.our_rmse * s.games, 0) / g;
              const line = ss.reduce((a, s) => a + s.line_rmse * s.games, 0) / g;
              const pct = w / (w + l);
              return (
                <tr key={d} className="border-t border-zinc-800">
                  <td className="px-4 py-3 font-semibold">{d}s</td>
                  <td className="px-4 py-3 font-mono">{w}-{l}-{p}</td>
                  <td className={`px-4 py-3 font-mono font-semibold ${pct >= 0.524 ? "text-emerald-400" : "text-red-400"}`}>
                    {fmtPct(pct)}
                  </td>
                  <td className="px-4 py-3 font-mono text-zinc-400">{our.toFixed(2)}</td>
                  <td className="px-4 py-3 font-mono text-zinc-400">{line.toFixed(2)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-xs text-zinc-500">
        52.4% is break-even against standard -110 vig. Green = profitable, red = not.
      </p>

      <h2 className="mt-8 text-xl font-bold">Season by season</h2>
      <div className="mt-4 overflow-x-auto rounded-xl border border-zinc-800">
        <table className="w-full min-w-[720px] text-sm">
          <thead>
            <tr className="bg-zinc-900 text-left text-xs uppercase tracking-wider text-zinc-400">
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
              <tr key={s.season} className="border-t border-zinc-800 hover:bg-zinc-900/50">
                <td className="px-4 py-3 font-semibold">{s.season}</td>
                <td className="px-4 py-3 font-mono">{s.games}</td>
                <td className="px-4 py-3 font-mono">{fmtPct(s.straight_up_pct)}</td>
                <td className="px-4 py-3 font-mono text-zinc-400">{s.our_rmse.toFixed(2)}</td>
                <td className="px-4 py-3 font-mono text-zinc-400">{s.line_rmse.toFixed(2)}</td>
                <td className="px-4 py-3 font-mono">{s.ats_w}-{s.ats_l}-{s.ats_p}</td>
                <td className={`px-4 py-3 font-mono ${s.ats_pct != null && s.ats_pct >= 0.524 ? "text-emerald-400" : "text-zinc-400"}`}>
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
