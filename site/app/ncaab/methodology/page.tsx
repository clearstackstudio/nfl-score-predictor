export default function NcaabMethodology() {
  const sections = [
    {
      n: "01",
      title: "The model",
      body: (
        <>
          <p>
            Every NCAAB team gets an <span className="font-semibold text-zinc-100 light:text-zinc-900">adjusted-efficiency rating</span>:
            offensive and defensive points per possession, plus tempo, all
            opponent-adjusted at prediction time. Ratings are
            exponentially-weighted moving averages — each game gets a weight of
            0.10, league-average priors drift slowly underneath (weight 0.005),
            and last season&rsquo;s rating carries 60% of its weight into
            November with the rest regressed toward average. Recent games count
            more than old ones, and a blowout against a bad team counts less
            than the same blowout against a good one.
          </p>
          <p>
            The <span className="font-semibold text-zinc-100 light:text-zinc-900">home edge is a fitted 5.04 points</span> —
            roughly twice the NBA&rsquo;s — and it drops to zero on neutral
            courts, which early-season multi-team events and holiday
            tournaments are full of.
          </p>
          <p>
            The transfer portal makes November uniquely noisy: rosters turn over
            almost completely every offseason. We <span className="font-semibold text-zinc-100 light:text-zinc-900">used to down-weight
            November updates by half</span> (0.5) and December by a quarter
            (0.75) — but a 2026 walk-forward test showed that was wrong. In the
            portal era the preseason prior is weak, so slow learning just
            anchored the model to bad ratings longer. Since October 2026 the
            model learns at full weight from game one, and early-season
            accuracy improved.
          </p>
          <p>
            From those ratings the model generates its own spread and total for
            each game, then compares them against the market line. Where our
            number disagrees with Vegas by at least 0.5 points on the spread
            (1 point on the total), we publish a pick with an estimated cover
            probability — and the track record grades exactly that same set of
            picks, nothing more selective.
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
      title: "What’s different from the NBA model",
      list: [
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">Efficiency is the whole model:</span>, " in the NBA, efficiency feeds totals while Elo drives the spread. In college basketball, adjusted per-possession efficiency drives everything."],
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">A real home-court edge:</span>, " 5.04 fitted points vs the NBA's 2.75 — college crowds, student sections, and young teams far from home move numbers. Neutral courts get zero."],
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">Full-weight learning from game one:</span>, " the portal-era roster churn has no NBA equivalent, so the model learns fast from real games instead of anchoring to a weak preseason prior — a 2026 test showed down-weighting early updates made ratings worse."],
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">D1 only:</span>, " games count only when both teams are Division I — mirroring the CFB FBS-only rule. Exhibition games are excluded entirely."],
      ],
    },
    {
      n: "03",
      title: "The honest part",
      body: (
        <>
          <p>
            The verdict is plain: <span className="font-semibold text-zinc-100 light:text-zinc-900">no betting edge</span>.
            Walk-forward over 2013–2026 (47,794 regular and postseason games),
            the model&rsquo;s margin RMSE is <span className="font-semibold text-zinc-100 light:text-zinc-900">12.17 vs the closing line&rsquo;s 11.04</span> —
            1.13 points worse. Totals are 18.05 vs 16.90 — 1.15 points worse.
            The line is simply better at this than we are.
          </p>
          <p>
            Against the spread, at the 0.5-point disagreement threshold:{" "}
            <span className="font-semibold text-zinc-100 light:text-zinc-900">16,868-17,093-488 — 49.7%</span>.
            Breaking even at standard -110 vig requires 52.4%. Totals are
            15,366-14,817-200, <span className="font-semibold text-zinc-100 light:text-zinc-900">50.9%</span> — also
            below break-even.
          </p>
          <p>
            It&rsquo;s stable rather than decaying: ATS 48.9% (2013–16) →
            49.8% (2017–20) → 50.2% (2021–26) — improving, but no era comes
            close to an edge. The model is a competent forecaster (70.4%
            straight-up), but competence isn&rsquo;t profit.
          </p>
          <p>
            This model is <span className="font-semibold text-zinc-100 light:text-zinc-900">not a betting tool</span>.
            Its honest role is a transparent prior for the site: the numbers on the track-record
            page, not marketing. Any future claim of edge has to clear the same walk-forward
            bar, with the line as benchmark.
          </p>
        </>
      ),
    },
    {
      n: "04",
      title: "How the probabilities are calibrated",
      body: (
        <>
          <p>
            Like every sport on this site, the cover probabilities used to come
            from a textbook formula — how far our number sat from the Vegas
            line, in units of typical game noise. The 2026-10-09 recalibration
            project showed that formula was systematically overconfident: the
            gap between our number and the line is mostly our error, not our
            insight.
          </p>
          <p>
            So every published probability is mapped through the actual hit
            rates from this model&rsquo;s walk-forward backtest. A number we
            publish as 55% is a number that hit about 55% in testing. For
            NCAAB, the empirical curves are <span className="font-semibold text-zinc-100 light:text-zinc-900">nearly
            flat at 0.50 from day one</span> — most picks show probabilities
            near a coin flip, and that is the data telling the truth, not the
            model being modest. The picks themselves (which side, over or
            under) are unchanged; only the probabilities got honest. We
            re-check the calibration regularly and will refit the curve if it
            drifts.
          </p>
          <p>
            The full evidence — the backtest curves plus this season&rsquo;s live receipts — is on
            the <a href="/calibration" className="font-semibold text-emerald-400 underline decoration-emerald-400/40 underline-offset-4 hover:decoration-emerald-400 light:text-emerald-700">calibration page</a>.
          </p>
        </>
      ),
    },
    {
      n: "05",
      title: "How the backtest stays honest",
      list: [
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">Walk-forward:</span>, " games are processed in chronological order. Each prediction is made from ratings built only on games already played — the model never learns from the game it’s predicting. Hyperparameters were tuned on a held-out split, not the test games."],
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">No line as input:</span>, " ratings come from game results and efficiency only."],
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">Closing lines as benchmark:</span>, " every historical pick is graded against the actual closing spread and total from CollegeBasketballData (median across books)."],
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">Full history published:</span>, " every D1 season from 2013 through 2026 — regular season, conference tournaments, NCAA and NIT — not a cherry-picked hot streak. Code is open source."],
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">Exhibitions excluded:</span>, " exhibition and preseason games are excluded from training and from the backtest — the model was validated on regular and postseason games only. Any exhibition that lands on a card is flagged experimental."],
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">Data-quality guard:</span>, " the raw box-score pace field has known garbage values (the 2013 season's pace is on an inflated scale); the model sanitizes possessions before they touch a rating."],
      ],
    },
  ];

  return (
    <div className="max-w-3xl">
      <div className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-amber-400/90 light:text-amber-700">
        <span className="h-px w-8 bg-amber-400/60 light:bg-amber-600/70" aria-hidden="true" />
        NCAAB · How it works
      </div>
      <h1 className="mt-3 font-display text-5xl font-semibold uppercase leading-[0.95] tracking-wide">
        Method<span className="text-amber-400 light:text-amber-600">ology</span>
      </h1>
      <p className="mt-4 text-[15px] text-zinc-400 light:text-zinc-600">
        How the NCAAB picks are made — and what we honestly claim about them.
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
