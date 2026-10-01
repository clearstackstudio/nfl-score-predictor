import picksData from "../data/picks.json";
import { fmtSpread, fmtPct, trim } from "./lib/format";

type Pick = {
  away: string; home: string; away_abbr: string; home_abbr: string;
  gameday: string; weekday: string;
  line_spread: number; line_total: number;
  our_spread: number; our_total: number;
  spread_edge: number; total_edge: number;
  pick_spread: "home" | "away" | null;
  pick_total: "over" | "under" | null;
  cover_prob: number | null; ou_prob: number | null;
  home_qb: string | null; away_qb: string | null;
};

const picks = picksData.picks as Pick[];

function pickLabel(p: Pick): string {
  if (!p.pick_spread) return "No play";
  const team = p.pick_spread === "home" ? p.home_abbr : p.away_abbr;
  return `${team} ${fmtPct(p.cover_prob)}`;
}

function ouLabel(p: Pick): string {
  if (!p.pick_total) return "No play";
  return `${p.pick_total === "over" ? "Over" : "Under"} ${trim(p.line_total)} (${fmtPct(p.ou_prob)})`;
}

export default function Home() {
  return (
    <div>
      <div className="mb-6">
        <h1 className="text-3xl font-extrabold tracking-tight">
          Week {picksData.week} picks <span className="text-zinc-500">· {picksData.season} season</span>
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-zinc-400">
          Generated {picksData.generated} from opponent-adjusted EPA ratings.
          The model never sees the betting line — the line is only the benchmark
          we measure against.{" "}
          <span className="text-amber-400/90">{picksData.disclaimer}</span>
        </p>
      </div>

      <div className="overflow-x-auto rounded-xl border border-zinc-800">
        <table className="w-full min-w-[720px] text-sm">
          <thead>
            <tr className="bg-zinc-900 text-left text-xs uppercase tracking-wider text-zinc-400">
              <th className="px-4 py-3">Game</th>
              <th className="px-4 py-3">Our spread</th>
              <th className="px-4 py-3">Vegas line</th>
              <th className="px-4 py-3">Spread pick</th>
              <th className="px-4 py-3">Our total</th>
              <th className="px-4 py-3">Vegas total</th>
              <th className="px-4 py-3">O/U pick</th>
            </tr>
          </thead>
          <tbody>
            {picks.map((p) => (
              <tr key={`${p.away_abbr}-${p.home_abbr}`} className="border-t border-zinc-800 hover:bg-zinc-900/50">
                <td className="px-4 py-3">
                  <div className="font-semibold">
                    {p.away_abbr} <span className="text-zinc-500">@</span> {p.home_abbr}
                  </div>
                  <div className="text-xs text-zinc-500">
                    {p.weekday} {p.gameday}
                  </div>
                </td>
                <td className="px-4 py-3 font-mono">{fmtSpread(p.our_spread, p.home_abbr, p.away_abbr)}</td>
                <td className="px-4 py-3 font-mono text-zinc-400">{fmtSpread(p.line_spread, p.home_abbr, p.away_abbr)}</td>
                <td className="px-4 py-3">
                  <span className={p.pick_spread ? "font-semibold text-amber-300" : "text-zinc-600"}>
                    {pickLabel(p)}
                  </span>
                </td>
                <td className="px-4 py-3 font-mono">{trim(p.our_total)}</td>
                <td className="px-4 py-3 font-mono text-zinc-400">{trim(p.line_total)}</td>
                <td className="px-4 py-3">
                  <span className={p.pick_total ? "font-semibold text-amber-300" : "text-zinc-600"}>
                    {ouLabel(p)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="mt-4 text-xs text-zinc-500">
        Spread pick = the side our number favors by at least half a point; probability
        is our estimated chance that side covers. Totals work the same way against
        the over/under. Spreads shown favorite-first, standard sportsbook style.
      </p>
    </div>
  );
}
