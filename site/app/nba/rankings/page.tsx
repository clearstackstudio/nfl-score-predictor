import type { Metadata } from "next";
import rankings from "../../../data/nba_power_rankings.json";
import NbaTeamLogo from "../../lib/nba-team-logo";

export const metadata: Metadata = {
  title: "NBA power rankings",
  description:
    "Honest Line NBA power rankings: the model's own Elo ratings, converted at the model's fitted rate to expected margin vs an average team on a neutral court. Predictive, not a resume ranking.",
  alternates: { canonical: "/nba/rankings" },
};

type Team = {
  rank: number;
  team: string;
  abbr: string;
  rating: number;
  prev_rank: number | null;
};

const doc = rankings as {
  season: number;
  updated: string;
  note: string;
  teams: Team[];
};

function movement(t: Team) {
  if (t.prev_rank == null) return { arrow: "–", cls: "text-zinc-500", label: "new" };
  const d = t.prev_rank - t.rank;
  if (d > 0) return { arrow: `▲ ${d}`, cls: "text-emerald-400 light:text-emerald-600", label: `up ${d}` };
  if (d < 0) return { arrow: `▼ ${-d}`, cls: "text-red-400 light:text-red-600", label: `down ${-d}` };
  return { arrow: "–", cls: "text-zinc-500", label: "unchanged" };
}

export default function NbaRankings() {
  const teams = doc.teams;
  return (
    <div>
      <div className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-amber-400/90 light:text-amber-700">
        <span className="h-px w-8 bg-amber-400/60 light:bg-amber-600/70" aria-hidden="true" />
        The model&apos;s own ratings · updated {doc.updated}
      </div>
      <h1 className="mt-3 font-display text-5xl font-semibold uppercase leading-[0.95] tracking-wide">
        Power <span className="text-amber-400 light:text-amber-600">rankings</span>
      </h1>
      <p className="mt-4 max-w-2xl text-[15px] leading-relaxed text-zinc-400 light:text-zinc-600">
        These are the Honest Line model&apos;s internal predictive ratings —
        the same numbers behind every nightly pick. The model rates teams with
        margin-adjusted Elo; the rating shown here converts Elo to points at
        the model&apos;s own fitted rate (30 Elo points = 1 point of margin),
        so it reads as a team&apos;s expected margin against an average team
        on a neutral court, before the nightly rest and star-availability
        adjustments. This is not a resume ranking: it doesn&apos;t care about
        win-loss records or headlines, and it moves only when games are
        played. Like everything here, it&apos;s published to be checked, not
        believed.
      </p>

      <div className="mt-8 overflow-hidden rounded-2xl border border-zinc-800 light:border-zinc-200">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-800 bg-zinc-900/60 text-left text-xs uppercase tracking-wider text-zinc-500 light:border-zinc-200 light:bg-zinc-100">
              <th className="px-4 py-3 font-semibold">#</th>
              <th className="px-4 py-3 font-semibold">Team</th>
              <th className="px-4 py-3 text-right font-semibold">Rating</th>
              <th className="px-4 py-3 text-right font-semibold">Trend</th>
            </tr>
          </thead>
          <tbody>
            {teams.map((t) => {
              const m = movement(t);
              const top = t.rank <= 3;
              return (
                <tr
                  key={t.abbr}
                  className="border-b border-zinc-800/60 last:border-0 hover:bg-white/[0.03] light:border-zinc-100 light:hover:bg-zinc-50"
                >
                  <td className="px-4 py-2.5">
                    <span
                      className={`inline-flex h-7 w-7 items-center justify-center rounded-md text-xs font-extrabold ${
                        top
                          ? "bg-amber-400/15 text-amber-300 light:bg-amber-100 light:text-amber-800"
                          : "bg-zinc-800/60 text-zinc-300 light:bg-zinc-100 light:text-zinc-600"
                      }`}
                    >
                      {t.rank}
                    </span>
                  </td>
                  <td className="px-4 py-2.5">
                    <span className="flex items-center gap-2.5">
                      <NbaTeamLogo abbr={t.abbr} name={t.team} size={26} />
                      <span className="font-semibold text-zinc-100 light:text-zinc-900">{t.team}</span>
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-right font-mono font-bold text-zinc-100 light:text-zinc-900">
                    {t.rating > 0 ? "+" : ""}
                    {t.rating.toFixed(1)}
                  </td>
                  <td className={`px-4 py-2.5 text-right font-mono text-xs font-bold ${m.cls}`} title={m.label}>
                    {m.arrow}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <p className="mt-6 max-w-2xl text-sm leading-relaxed text-zinc-500 light:text-zinc-600">
        Ratings refresh with each nightly model run. A positive rating means the model
        would favor the team on a neutral court; negative means it would be an underdog.
        For how the ratings are built, see the methodology page. For whether they beat
        Vegas, see the track record — nothing hidden.
      </p>
    </div>
  );
}
