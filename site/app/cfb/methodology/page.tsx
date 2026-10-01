export default function CfbMethodology() {
  const sections = [
    {
      n: "01",
      title: "The model",
      body: (
        <>
          <p>
            Every FBS team gets two ratings — offensive and defensive efficiency —
            built from per-play PPA (predicted points added), garbage time excluded,
            over a trailing window of about one season&rsquo;s worth of games, adjusted
            for schedule strength. A team that piles up PPA against bad defenses gets
            less credit than one that does it against good ones.
          </p>
          <p>
            Per-play matters more in college than anywhere: pace ranges from 60 to 90
            plays a game, so raw totals would reward fast teams for being fast. Ratings
            are efficiency, then re-scaled by a typical game&rsquo;s play count to produce
            our spread and total.
          </p>
          <p>
            From those ratings the model generates its own spread and total for each
            game, then compares them against the market line. Where our number disagrees
            with Vegas by at least half a point on the spread (a full point on the total),
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
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">FBS vs. FBS only:</span>, " games against FCS opponents are excluded — 70-point blowouts of overmatched teams add noise, not signal."],
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">Garbage time excluded:</span>, " at the data source. College backups play entire fourth quarters of blowouts; counting those plays would poison the ratings."],
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">Less prior-season weight:</span>, " the transfer portal era turns over rosters fast, so last season&rsquo;s rating carries less into September than in the NFL model."],
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">Bigger home edge:</span>, " campus home fields are worth more than NFL stadiums — the model starts from a larger home-field value, calibrated in the backtest."],
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">Neutral sites:</span>, " bowl games and kickoff classics get no home edge at all."],
      ],
    },
    {
      n: "03",
      title: "The honest part",
      body: (
        <>
          <p>
            The college market is less efficient than the NFL&rsquo;s — fewer sharp dollars,
            130+ teams, wild talent gaps. That means a real edge is <span className="font-semibold text-zinc-100 light:text-zinc-900">more
            plausible</span> here than on Sundays. But &ldquo;plausible&rdquo; is not a result.
          </p>
          <p>
            So we claim nothing until the backtest does. The win we&rsquo;re chasing is{" "}
            <span className="font-semibold text-zinc-100 light:text-zinc-900">calibration and transparency</span>:
            honest probabilities, every pick published before kickoff, and a complete public
            record — winners and losers — that anyone can audit. If the model develops a real
            edge against college lines, the track record will show it. If it doesn&rsquo;t, the
            track record will show that too.
          </p>
        </>
      ),
    },
    {
      n: "04",
      title: "How the backtest stays honest",
      list: [
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">Walk-forward:</span>, " games are processed in chronological order. Each prediction is made from ratings built only on games already played — the model never learns from the game it’s predicting."],
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">No line as input:</span>, " ratings come from play efficiency only."],
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">Closing lines as benchmark:</span>, " every historical pick is graded against the actual closing spread and total (median across providers)."],
        [<span key="k" className="font-semibold text-zinc-100 light:text-zinc-900">Full history published:</span>, " every season from 2014 on, not a cherry-picked hot streak. Code is open source."],
      ],
    },
  ];

  return (
    <div className="max-w-3xl">
      <div className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-amber-400/90 light:text-amber-700">
        <span className="h-px w-8 bg-amber-400/60 light:bg-amber-600/70" aria-hidden="true" />
        College football · How it works
      </div>
      <h1 className="mt-3 font-display text-5xl font-semibold uppercase leading-[0.95] tracking-wide">
        Method<span className="text-amber-400 light:text-amber-600">ology</span>
      </h1>
      <p className="mt-4 text-[15px] text-zinc-400 light:text-zinc-600">
        How the college picks are made — and what we honestly claim about them.
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
