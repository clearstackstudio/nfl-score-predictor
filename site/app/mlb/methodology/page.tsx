export default function MlbMethodology() {
  const sections = [
    {
      n: "01",
      title: "The model",
      body: (
        <>
          <p>
            Every MLB team gets <span className="font-semibold text-zinc-100 light:text-zinc-900">park-adjusted exponential runs ratings</span> —
            separate offense and defense numbers. Runs are first adjusted for park,
            using expanding park factors with a 100-game shrinkage prior and an
            expanding league scoring average, so a Coors slugfest and a Petco
            pitchers&rsquo; duel aren&rsquo;t judged on raw runs.
          </p>
          <p>
            The walk-forward tuning on 2012–2015 settled on a fitted home edge of{" "}
            <span className="font-semibold text-zinc-100 light:text-zinc-900">0.130 runs</span>, a slow
            learning rate (alpha = 1/40 — baseball&rsquo;s long season rewards slow
            learning), and a{" "}
            <span className="font-semibold text-zinc-100 light:text-zinc-900">0.25 prior-season carryover</span> —
            last season&rsquo;s ratings keep a quarter of their weight into April.
          </p>
          <p>
            From the predicted run differential the model converts to a win probability
            with a <span className="font-semibold text-zinc-100 light:text-zinc-900">Normal CDF, sigma 4.135</span> fitted
            on tuning residuals. Calibration is honest: predicted 0.40 → actual 0.465,
            0.50 → 0.53, 0.60 → 0.60, 0.73 → 0.70 — slightly under-confident on
            underdogs, otherwise well-calibrated.
          </p>
          <p>
            Thirty <span className="font-semibold text-zinc-100 light:text-zinc-900">neutral-site games</span> get
            zero home edge — the Tokyo, London, Sydney, Mexico, and Puerto Rico series,
            the Field of Dreams and Fort Bragg games, Omaha, the Williamsport Classic,
            and six 2017 hurricane-relocation games — in both prediction and rating updates.
          </p>
          <p>
            The betting line is <span className="font-semibold text-zinc-100 light:text-zinc-900">never</span> an
            input to the model. It is only the benchmark we measure against.
          </p>
        </>
      ),
    },
    {
      n: "02",
      title: "What’s different from the other models",
      list: [
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">Moneyline, not spread:</span>, " baseball doesn’t have a meaningful point spread, so picks and the moneyline evaluation are purely on win probability — we bet only where |model probability − implied probability| ≥ 0.05."],
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">No ties:</span>, " every game ends with a winner, so there are no pushes on the moneyline — only on totals (680 over/under pushes in the backtest)."],
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">Park-adjusted, not pace-adjusted:</span>, " where the NBA model adjusts for pace, the MLB model adjusts for park — the same kind of context normalization, fit for baseball."],
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">Pitcher adjustment is designed, not tested:</span>, " the historical data has no pitcher column, so the backtest is team-level only. A design exists (see pitcher.py) for live picks to adjust for probable pitchers from the free MLB Stats API with a league-average fallback — it was never called by the backtest and claims nothing until it’s measured."],
      ],
    },
    {
      n: "03",
      title: "How the backtest stays honest",
      list: [
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">Walk-forward:</span>, " games are processed in chronological order. Each prediction is made from ratings built only on games already played — the model never learns from the game it’s predicting."],
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">No line as input:</span>, " ratings come from game results only."],
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">Vig-removed closing lines as benchmark:</span>, " moneyline bets are graded against actual closing prices, and the Brier score is compared against the vig-removed closing line — the sharpest available probability."],
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">Full history published:</span>, " every season from 2012 through 2021 — 22,765 games, including the shortened 2020 season — not a cherry-picked hot streak. Code is open source."],
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">Tuning is quarantined:</span>, " alpha, carryover, home edge, and sigma were tuned on 2012–2015 only; the 2016–2021 post-tuning slice is reported separately so you can see the model after tuning knew nothing."],
      ],
    },
    {
      n: "04",
      title: "The honest verdict",
      body: (
        <>
          <p>
            The verdict is plain: <span className="font-semibold text-zinc-100 light:text-zinc-900">competent forecaster, no betting edge</span>.
            Walk-forward over 2012–2021 (22,765 games), the model picks the winner{" "}
            <span className="font-semibold text-zinc-100 light:text-zinc-900">55.3%</span> straight up —
            barely above the 53.5% the home team won on its own. The Brier score is{" "}
            <span className="font-semibold text-zinc-100 light:text-zinc-900">0.2456 vs the closing line&rsquo;s 0.2402</span> —
            the line remains the sharper probability.
          </p>
          <p>
            Flat $100 moneyline bets at the 0.05 edge threshold went{" "}
            <span className="font-semibold text-zinc-100 light:text-zinc-900">5,061-6,308 (44.5%)</span> for{" "}
            <span className="font-semibold text-zinc-100 light:text-zinc-900">−$24,959 (−2.2% ROI)</span> over
            11,369 bets; on the post-tuning 2016–2021 slice it was{" "}
            <span className="font-semibold text-zinc-100 light:text-zinc-900">3,018-3,713 (−1.0% ROI)</span>.
            Totals: model RMSE 4.42 vs the line&rsquo;s 4.37, and over/under bets at
            a 0.5-run threshold went{" "}
            <span className="font-semibold text-zinc-100 light:text-zinc-900">6,582-6,472 (50.4%, −$47,939, −3.7% ROI)</span>.
          </p>
          <p>
            This model is a decent forecaster — well-calibrated probabilities that
            track reality — but it is{" "}
            <span className="font-semibold text-zinc-100 light:text-zinc-900">not a betting tool</span>.
            Team strength alone does not beat the closing MLB line. Its honest role is a
            transparent prior for the site: the numbers on the track-record page, not
            marketing. The plausible path to any future edge is the probable-pitcher
            adjustment — and it has to clear the same walk-forward bar before it claims
            anything.
          </p>
        </>
      ),
    },
  ];

  return (
    <div className="max-w-3xl">
      <div className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-amber-400/90 light:text-amber-700">
        <span className="h-px w-8 bg-amber-400/60 light:bg-amber-600/70" aria-hidden="true" />
        MLB · How it works
      </div>
      <h1 className="mt-3 font-display text-5xl font-semibold uppercase leading-[0.95] tracking-wide">
        Method<span className="text-amber-400 light:text-amber-600">ology</span>
      </h1>
      <p className="mt-4 text-[15px] text-zinc-400 light:text-zinc-600">
        How the MLB picks are made — and what we honestly claim about them.
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
