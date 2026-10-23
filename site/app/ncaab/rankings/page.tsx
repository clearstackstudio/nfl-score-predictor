import type { Metadata } from "next";
import rankings from "../../../data/ncaab_power_rankings.json";

export const metadata: Metadata = {
  title: "NCAAB power rankings",
  description:
    "Honest Line college basketball power rankings: the model's own efficiency ratings — net points per 100 possessions vs a league-average opponent. Predictive, not a resume ranking.",
  alternates: { canonical: "/ncaab/rankings" },
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

export default function NcaabRankings() {
  const teams = doc.teams;
  return (
    <div>
      <div className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-red-500/90 light:text-red-700">
        <span className="h-px w-8 bg-red-500/60 light:bg-red-600/70" aria-hidden="true" />
        The model&apos;s own ratings · updated {doc.updated}
      </div>
      <h1 className="mt-3 font-display text-5xl font-semibold uppercase leading-[0.95] tracking-wide">
        Power <span className="text-red-500 light:text-red-600">rankings</span>
      </h1>
      <p className="mt-4 max-w-2xl text-[15px] leading-relaxed text-zinc-400 light:text-zinc-600">
        These are the Honest Line model&apos;s internal predictive ratings —
        the same numbers behind every nightly pick. A team&apos;s rating is
        its net efficiency: expected points scored minus points allowed per
        100 possessions against a league-average opponent, from the
        model&apos;s per-possession efficiency ratings. Because it&apos;s
        measured per possession, pace can&apos;t inflate it — a fast team
        gets no credit just for playing more possessions. This is not a
        resume ranking: it doesn&apos;t care about win-loss records or
        polls, and it moves only when games are played. Like everything
        here, it&apos;s published to be checked, not believed.
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
                          ? "bg-red-500/15 text-red-300 light:bg-red-100 light:text-red-800"
                          : "bg-zinc-800/60 text-zinc-300 light:bg-zinc-100 light:text-zinc-600"
                      }`}
                    >
                      {t.rank}
                    </span>
                  </td>
                  <td className="px-4 py-2.5">
                    <span className="font-semibold text-zinc-100 light:text-zinc-900">{t.team}</span>
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
        expects the team to outscore a league-average opponent over 100 possessions;
        negative means the opposite. For how the ratings are built, see the methodology
        page. For whether they beat Vegas, see the track record — nothing hidden.
      </p>
    </div>
  );
}
