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
            that does it against good ones. Recent games count more than older
            ones: a game&apos;s weight halves roughly every eight games, so a
            Week 4 rating reflects this season far more than last.
          </p>
          <p>
            From those ratings the model generates its own spread and total for
            each game, then compares them against the market line. Totals also
            account for pace — how many plays each team typically runs — because
            points come from efficiency times opportunity. Where our number
            disagrees with Vegas by enough, we publish a pick with an
            estimated cover probability.
          </p>
          <p>
            Two guardrails keep the model honest with itself. Quarterback
            changes are adjusted for explicitly: when the announced starter
            differs from the passers who produced a team&apos;s trailing
            numbers, the offensive rating shifts by a regressed measure of the
            gap — no adjustment when the same quarterback keeps playing.
            Wind is adjusted for too: in outdoor stadiums, our total drops
            about a point for every mph of forecast wind above 10 (capped at
            8), because the 2021–24 backtest showed our totals running ~7
            points hot in 15–20 mph wind. Domes and retractable roofs get no
            wind adjustment (there&apos;s no wind inside). Total probabilities use their own calibrated noise
            model, not the spread&apos;s. Indoor games get +3 points on our
            total: the 2021–24 backtest showed domes and retractable roofs
            scoring about 3 points higher than the model expected, consistently
            across all four seasons — perfect conditions and a fast track.
            And when our number sits more than a touchdown off
            the market, we publish no pick at all: extreme disagreement with
            one of the sharpest markets in the world is more likely our error
            than our edge.
          </p>
          <p>
            The betting line is <span className="font-semibold text-zinc-100 light:text-zinc-900">never</span> an
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
            <span className="font-semibold text-zinc-100 light:text-zinc-900">calibration and transparency</span>:
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
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">Walk-forward:</span>, " games are processed in chronological order. Each prediction is made from ratings built only on games already played — the model never learns from the game it’s predicting."],
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">No line as input:</span>, " ratings come from final scores and play efficiency only."],
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">Closing lines as benchmark:</span>, " every historical pick is graded against the actual closing spread and total."],
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">Full history published:</span>, " all 45 seasons, not a cherry-picked hot streak. Code is open source."],
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
      <div className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-amber-400/90 light:text-amber-700">
        <span className="h-px w-8 bg-amber-400/60 light:bg-amber-600/70" aria-hidden="true" />
        How it works
      </div>
      <h1 className="mt-3 font-display text-5xl font-semibold uppercase leading-[0.95] tracking-wide">
        Method<span className="text-amber-400 light:text-amber-600">ology</span>
      </h1>
      <p className="mt-4 text-[15px] text-zinc-400 light:text-zinc-600">
        How the picks are made — and what we honestly claim about them.
      </p>

      {sections.map((s) => (
        <section key={s.n} className="mt-8 rounded-2xl border border-white/10 bg-zinc-900/40 p-6 sm:p-8 light:border-zinc-200 light:bg-white">
          <div className="flex items-baseline gap-4">
            <span className="tnum font-display text-lg font-semibold text-amber-400/80 light:text-amber-700">{s.n}</span>
            <h2 className="font-display text-2xl font-semibold uppercase tracking-wide">{s.title}</h2>
          </div>
          {s.body && (
            <div className="mt-4 space-y-4 text-[15px] leading-relaxed text-zinc-300 light:text-zinc-700">{s.body}</div>
          )}
          {s.list && (
            <ul className="mt-4 space-y-3 text-[15px] leading-relaxed text-zinc-300 light:text-zinc-700">
              {s.list.map((item, i) => (
                <li key={i} className="flex gap-3">
                  <span className="mt-[9px] h-1.5 w-1.5 shrink-0 rounded-full bg-amber-400/70 light:bg-amber-600" aria-hidden="true" />
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
