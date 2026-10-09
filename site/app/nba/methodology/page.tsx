export default function NbaMethodology() {
  const sections = [
    {
      n: "01",
      title: "The model",
      body: (
        <>
          <p>
            Every NBA team gets a <span className="font-semibold text-zinc-100 light:text-zinc-900">margin-adjusted Elo</span> rating:
            a fitted home edge of 2.75 points, a k-factor of 26, and a 0.5 prior-season
            carryover — last season&rsquo;s rating carries half its weight into October, with the
            rest regressed toward average. Recent games count more than old ones, and a
            team that wins big against bad teams gets less credit than one that does it
            against good ones.
          </p>
          <p>
            Totals come from a separate <span className="font-semibold text-zinc-100 light:text-zinc-900">offensive/defensive efficiency</span> model —
            points scored and allowed per 100 possessions, pace-aware, so a track meet and
            a half-court grinder aren&rsquo;t judged on raw points.
          </p>
          <p>
            One adjustment survived the walk-forward test: <span className="font-semibold text-zinc-100 light:text-zinc-900">rest days</span>.
            A team on a back-to-back facing a rested opponent gets +0.58 points of
            adjustment per rest-day difference. It&rsquo;s small, but both margin and total
            RMSE improved on 18,552 games, so it stays.
          </p>
          <p>
            From those ratings the model generates its own spread and total for each
            game, then compares them against the market line. Where our number disagrees
            with Vegas by at least 1.5 points on the spread (3 points on the total),
            we publish a pick with an estimated cover probability — and the track record
            grades exactly that same set of picks, nothing more selective.
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
      title: "What’s different from the NFL model",
      list: [
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">Efficiency, not EPA:</span>, " possessions and per-100 numbers instead of per-play expected points."],
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">Rest is real:</span>, " an 82-game grind with back-to-backs and 3-in-4 nights — the rest-day adjustment is the one term the NFL model doesn’t have."],
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">Neutral courts:</span>, " the 88 games from the 2020 bubble (2020-07-30 through 2020-08-14) get zero home edge — in both prediction and rating updates."],
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">Carryover between seasons:</span>, " 0.5 of last season’s Elo survives October, since NBA rosters turn over less violently than college ones."],
      ],
    },
    {
      n: "03",
      title: "The honest part",
      body: (
        <>
          <p>
            The verdict is plain: <span className="font-semibold text-zinc-100 light:text-zinc-900">no betting edge</span>.
            Walk-forward over 2008–2023 (18,552 regular-season games; 2023 is a partial
            season), the model&rsquo;s margin RMSE is <span className="font-semibold text-zinc-100 light:text-zinc-900">12.50 vs the closing line&rsquo;s 12.18</span> —
            0.32 points worse. Totals are 18.26 vs 17.69 — 0.57 points worse.
          </p>
          <p>
            Against the spread, at the 1.5-point disagreement threshold:{" "}
            <span className="font-semibold text-zinc-100 light:text-zinc-900">5,466-5,370-179 — 50.4%</span>.
            Breaking even at standard -110 vig requires 52.4%. Totals are worse:
            3,930-4,207-103, <span className="font-semibold text-zinc-100 light:text-zinc-900">48.3%</span> — negative.
          </p>
          <p>
            And it&rsquo;s decaying. Era by era: ATS 51.0% (2008–12) → 50.3% (2013–17) → 50.1% (2018–23),
            with the RMSE gap to the line widening from +0.25 to +0.44. Straight-up accuracy
            fell from 68.8% to 64.4% as pace-and-three offenses made games more volatile.
            No era comes close to an edge.
          </p>
          <p>
            This model is a decent forecaster — 66.8% straight-up, predictions correlate
            with reality — but it is <span className="font-semibold text-zinc-100 light:text-zinc-900">not a betting tool</span>.
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
            The cover probabilities on our picks used to come straight from a
            textbook formula — how far our number sat from the Vegas line, in
            units of typical game noise. On 2026-10-09 we checked that formula
            against our own walk-forward backtest, and it was systematically
            overconfident: a published 74% was hitting about 51%. The gap
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
        </>
      ),
    },
    {
      n: "05",
      title: "How the backtest stays honest",
      list: [
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">Walk-forward:</span>, " games are processed in chronological order. Each prediction is made from ratings built only on games already played — the model never learns from the game it’s predicting."],
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">No line as input:</span>, " ratings come from game results and efficiency only."],
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">Closing lines as benchmark:</span>, " every historical pick is graded against the actual closing spread and total (median across providers)."],
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">Full history published:</span>, " every season from 2008 through 2023 — including the partial 2023 season and a 2020 season with zero home court — not a cherry-picked hot streak. Code is open source."],
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">Known gap:</span>, " there is no free source of historical closing lines after January 2023, so the backtest ends there; nightly logging of fresh lines starts the record going forward."],
      ],
    },
  ];

  return (
    <div className="max-w-3xl">
      <div className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-amber-400/90 light:text-amber-700">
        <span className="h-px w-8 bg-amber-400/60 light:bg-amber-600/70" aria-hidden="true" />
        NBA · How it works
      </div>
      <h1 className="mt-3 font-display text-5xl font-semibold uppercase leading-[0.95] tracking-wide">
        Method<span className="text-amber-400 light:text-amber-600">ology</span>
      </h1>
      <p className="mt-4 text-[15px] text-zinc-400 light:text-zinc-600">
        How the NBA picks are made — and what we honestly claim about them.
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
