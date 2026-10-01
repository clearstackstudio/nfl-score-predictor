export default function Methodology() {
  const sections = [
    {
      n: "01",
      title: "The model",
      body: (
        <>
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
        </>
      ),
    },
    {
      n: "02",
      title: "The honest part",
      body: (
        <>
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
        </>
      ),
    },
    {
      n: "03",
      title: "How the backtest stays honest",
      list: [
        [<span key="k" className="font-semibold text-zinc-100">Walk-forward:</span>, " games are processed in chronological order. Each prediction is made from ratings built only on games already played — the model never learns from the game it’s predicting."],
        [<span key="k" className="font-semibold text-zinc-100">No line as input:</span>, " ratings come from final scores and play efficiency only."],
        [<span key="k" className="font-semibold text-zinc-100">Closing lines as benchmark:</span>, " every historical pick is graded against the actual closing spread and total."],
        [<span key="k" className="font-semibold text-zinc-100">Full history published:</span>, " all 45 seasons, not a cherry-picked hot streak. Code is open source."],
      ],
    },
    {
      n: "04",
      title: "What’s next",
      list: [
        ["QB-specific adjustments (injuries and backup quarterbacks move games)."],
        ["Rest differentials: short weeks, Thursday games, bye weeks."],
        ["Weather and dome effects on totals."],
        ["Live pick tracking for the current season, graded weekly."],
      ],
    },
  ];

  return (
    <div className="max-w-3xl">
      <div className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-amber-400/90">
        <span className="h-px w-8 bg-amber-400/60" aria-hidden="true" />
        How it works
      </div>
      <h1 className="mt-3 font-display text-5xl font-semibold uppercase leading-[0.95] tracking-wide">
        Method<span className="text-amber-400">ology</span>
      </h1>
      <p className="mt-4 text-[15px] text-zinc-400">
        How the picks are made — and what we honestly claim about them.
      </p>

      {sections.map((s) => (
        <section key={s.n} className="mt-8 rounded-2xl border border-white/10 bg-zinc-900/40 p-6 sm:p-8">
          <div className="flex items-baseline gap-4">
            <span className="tnum font-display text-lg font-semibold text-amber-400/80">{s.n}</span>
            <h2 className="font-display text-2xl font-semibold uppercase tracking-wide">{s.title}</h2>
          </div>
          {s.body && (
            <div className="mt-4 space-y-4 text-[15px] leading-relaxed text-zinc-300">{s.body}</div>
          )}
          {s.list && (
            <ul className="mt-4 space-y-3 text-[15px] leading-relaxed text-zinc-300">
              {s.list.map((item, i) => (
                <li key={i} className="flex gap-3">
                  <span className="mt-[9px] h-1.5 w-1.5 shrink-0 rounded-full bg-amber-400/70" aria-hidden="true" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      ))}
    </div>
  );
}
