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
            The parlay of the week is the week&rsquo;s three highest-probability
            published picks, spread or total. It is rebuilt every time the
            picks refresh, so it always matches the cards: if a line moves far
            enough that a leg&rsquo;s pick drops to no play — as happened in
            Week 6 of 2026, when Tampa Bay&rsquo;s total moved from 40.5 to
            39.5, onto our number — the leg leaves the parlay and the next-best
            published pick takes its place. Once the first leg kicks off, the
            parlay freezes exactly as published: a live bet is a record, and
            no later update rewrites it.
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
            One more, adopted in October 2026: turnover plays count at half
            weight in the ratings. A defense that feasts on takeaways one year
            rarely repeats it — turnover EPA barely persists season to season
            (correlation ≈ 0.08) — so counting a few fluky interceptions and
            fumble recoveries at full weight was crediting luck as skill. In a
            pre-registered walk-forward test, halving turnover plays (inside
            the quarterback adjustment too) cut the model&apos;s margin error
            from 14.4 to 14.1 points across 2021–24 — and a placebo check,
            damping equally large non-turnover plays instead, recovered only
            about a third of that gain, confirming the improvement is
            specific to turnovers rather than generic shrinkage. The honest
            trade: our against-the-spread record in that window slipped from
            47.5% to 47.3%, well within noise. We took the accuracy anyway.
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
            our own 45-season Elo backtest shows a winning ATS record in the 80s
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
      title: "How the probabilities are calibrated",
      body: (
        <>
          <p>
            The cover probabilities on our picks used to come straight from a
            textbook formula — how far our number sat from the Vegas line, in
            units of typical game noise. On 2026-10-09 we checked that formula
            against our own walk-forward backtest, and it was systematically
            overconfident: a published 77% was hitting about 45%. The gap
            between our number and the line turned out to be mostly our error,
            not our insight.
          </p>
          <p>
            So we replaced it with an empirical calibration: every published
            probability is mapped through the actual hit rates from the
            backtest. A number we publish as 55% is a number that hit about
            55% in testing. Because the honest curve is nearly flat, most
            picks now show probabilities near 50% — that is the data telling
            the truth, not the model being modest. The picks themselves (which
            side, over or under) are unchanged; only the probabilities got
            honest. We re-check the calibration regularly and will refit the
            curve if it drifts.
          </p>
          <p>
            The full evidence — the backtest curves plus this season&rsquo;s live receipts — is on
            the <a href="/calibration" className="font-semibold text-emerald-400 underline decoration-emerald-400/40 underline-offset-4 hover:decoration-emerald-400 light:text-emerald-700">calibration page</a>.
          </p>
        </>
      ),
    },
    {
      n: "04",
      title: "How the backtest stays honest",
      list: [
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">Walk-forward:</span>, " games are processed in chronological order. Each prediction is made from ratings built only on games already played — the model never learns from the game it’s predicting."],
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">No line as input:</span>, " ratings come from final scores and play efficiency only."],
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">Closing lines as benchmark:</span>, " every historical pick is graded against the actual closing spread and total."],
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">Full history published:</span>, " all 45 seasons, not a cherry-picked hot streak. Code is open source."],
      ],
    },
    {
      n: "05",
      title: "Tested and rejected: a quarterback’s last game",
      body: (
        <>
          <p>
            On 2026-10-19 we ran a pre-registered test of an idea that sounds
            obviously true: a quarterback coming off a strong game — or a bad
            one — carries that form into the next week. The model already
            adjusts when the starting quarterback <em>changes</em>; this would
            have added a term for how the starter played in his most recent
            game, relative to his own season baseline. The test was written
            down before it was run, then run walk-forward over 2021–2025. It
            could only apply where both starting quarterbacks also started
            their team&rsquo;s previous game — 305 games, about 22% of the games
            the model predicted in that span.
          </p>
          <p>
            The bars were set in advance, and the term cleared none of them.
            On the held-out 2024–25 seasons, the effect&rsquo;s slope scored{" "}
            <span className="font-semibold text-zinc-100 light:text-zinc-900">z = +0.74 against a required 1.96</span>{" "}
            — indistinguishable from zero. Adding the term made margin error
            worse, not better:{" "}
            <span className="font-semibold text-zinc-100 light:text-zinc-900">13.267 points to 13.366</span>{" "}
            (+0.099; 95% confidence interval [−0.091, +0.277]). It worsened
            both validation seasons — 2024: 13.902 → 14.049; 2025: 12.425 →
            12.455 — which the protocol treats as an automatic rejection. And
            the effect&rsquo;s sign flipped between the seasons used to fit it
            (−2.41) and the seasons used to judge it (+2.54).
          </p>
          <p>
            Verdict:{" "}
            <span className="font-semibold text-zinc-100 light:text-zinc-900">rejected</span>.
            The model is unchanged — its ratings already weight recent games,
            and one game&rsquo;s deviation from a quarterback&rsquo;s own baseline
            adds nothing measurable on top. One process note, because it is
            the point of publishing tests like this: the first attempt stopped
            itself before running, when the protocol&rsquo;s baseline check caught
            that the benchmark it was pinned to predated the turnover change
            described above. The pin was corrected with a dated, approved
            addendum, and the test then ran exactly as pre-registered.
          </p>
        </>
      ),
    },
    {
      n: "06",
      title: "What’s next",
      list: [
        ["QB-specific adjustments (injuries and backup quarterbacks move games)."],
        ["Rest differentials: short weeks, Thursday games, bye weeks."],
        ["Weather and dome effects on totals."],
        ["Live pick tracking for the current season, graded weekly."],
      ],
    },
    {
      n: "07",
      title: "A worked example: from a spread to a probability",
      body: (
        <>
          <p>
            Everything above produces a margin — say, a team by 6. A margin is not a
            probability, so the last step is a formula: the normal cumulative
            distribution, Φ, which asks how often a team favored by that much
            actually wins, given how noisy football margins are:
          </p>
          <p className="rounded-xl border border-white/10 bg-black/30 px-4 py-3 font-mono text-[13px] leading-relaxed text-zinc-100 light:border-zinc-200 light:bg-zinc-50 light:text-zinc-900">
            P(win) = Φ( predicted margin ÷ σ ), σ = 14.5 points
          </p>
          <p>
            The σ is not a guess: it is the backtest RMSE of our predicted margin
            (2021–2024) — how wrong the margin usually is. Worked:{" "}
            <span className="font-semibold text-zinc-100 light:text-zinc-900">Φ(6 ÷ 14.5) = Φ(0.41) ≈ 66%</span>.
            The same formula run against the Vegas line instead of zero gives the
            raw cover probability — our margin sitting 3 points beyond the spread
            is Φ(3 ÷ 14.5) ≈ 58% — and the calibration map described on this page
            then pulls that down toward the low 50s before it is published,
            because that is the rate that edge actually hit in the backtest.
            Totals work identically, with σ = 15.4.
          </p>
        </>
      ),
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
