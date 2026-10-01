export default function Methodology() {
  return (
    <div className="max-w-3xl">
      <h1 className="text-3xl font-extrabold tracking-tight">Methodology</h1>
      <p className="mt-2 text-[15px] text-zinc-400">
        How the picks are made — and what we honestly claim about them.
      </p>

      <section className="mt-10 rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6">
        <h2 className="text-xl font-bold">The model</h2>
        <div className="mt-3 space-y-4 text-[15px] leading-relaxed text-zinc-300">
          <p>
            Every team gets two ratings — offensive and defensive efficiency —
            built from play-by-play EPA (expected points added per play) over a
            trailing window of games, adjusted for schedule strength. A team
            that piles up EPA against bad defenses gets less credit than one
            that does it against good ones.
          </p>
          <p>
            From those ratings the model generates its own spread and total for
            each game, then compares them against the market line. Where our
            number disagrees with Vegas by enough, we publish a pick with an
            estimated cover probability.
          </p>
          <p>
            The betting line is <span className="font-semibold text-zinc-100">never</span> an
            input to the model. It is only the benchmark we measure against.
            Most “prediction” apps quietly feed the line in and echo it back —
            that is circular, and it can never beat the market by construction.
          </p>
        </div>
      </section>

      <section className="mt-10 rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6">
        <h2 className="text-xl font-bold">The honest part</h2>
        <div className="mt-3 space-y-4 text-[15px] leading-relaxed text-zinc-300">
          <p>
            Nobody beats the Vegas line by much. It is one of the most
            efficient markets in the world, and it has only gotten sharper —
            our own 45-season backtest shows a winning ATS record in the 80s
            through 2000s decaying to a coin flip in the 2020s.
          </p>
          <p>
            So we don’t claim magic accuracy. The win we’re chasing is{" "}
            <span className="font-semibold text-zinc-100">calibration and transparency</span>:
            honest probabilities, every pick published before kickoff, and a
            complete public record — winners and losers — that anyone can audit.
            If the model develops a real edge, the track record will show it.
            If it doesn’t, the track record will show that too.
          </p>
        </div>
      </section>

      <section className="mt-10 rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6">
        <h2 className="text-xl font-bold">How the backtest stays honest</h2>
        <ul className="mt-3 list-disc space-y-3 pl-5 text-[15px] leading-relaxed text-zinc-300">
          <li>
            <span className="font-semibold text-zinc-100">Walk-forward:</span> games are
            processed in chronological order. Each prediction is made from
            ratings built only on games already played — the model never learns
            from the game it’s predicting.
          </li>
          <li>
            <span className="font-semibold text-zinc-100">No line as input:</span> ratings
            come from final scores and play efficiency only.
          </li>
          <li>
            <span className="font-semibold text-zinc-100">Closing lines as benchmark:</span> every
            historical pick is graded against the actual closing spread and total.
          </li>
          <li>
            <span className="font-semibold text-zinc-100">Full history published:</span> all
            45 seasons, not a cherry-picked hot streak. Code is open source.
          </li>
        </ul>
      </section>

      <section className="mt-10 rounded-2xl border border-zinc-800 bg-zinc-900/40 p-6">
        <h2 className="text-xl font-bold">What’s next</h2>
        <ul className="mt-3 list-disc space-y-3 pl-5 text-[15px] leading-relaxed text-zinc-300">
          <li>QB-specific adjustments (injuries and backup quarterbacks move games).</li>
          <li>Rest differentials: short weeks, Thursday games, bye weeks.</li>
          <li>Weather and dome effects on totals.</li>
          <li>Live pick tracking for the current season, graded weekly.</li>
        </ul>
      </section>
    </div>
  );
}
