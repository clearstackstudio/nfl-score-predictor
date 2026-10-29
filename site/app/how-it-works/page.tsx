import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "How Honest Line works",
  description:
    "How the Honest Line models make their picks: fundamentals-only inputs, honest walk-forward backtests, and every pick published before game time and graded in public.",
  alternates: { canonical: "/how-it-works" },
};

const sections = [
  {
    n: "01",
    title: "What we publish",
    body: [
      "Honest Line publishes model-generated lines and picks — spreads, totals, and win probabilities — for the NFL, NBA, college football (NCAAF), and college basketball (NCAAB). Models for MLB and the NHL are in development and will join the site under the same rules once they pass the same testing described below.",
      "Every league page shows the model's numbers next to the current market line, so you can see exactly where the model agrees with the market and where it doesn't.",
    ],
  },
  {
    n: "02",
    title: "Fundamentals in, market out",
    body: [
      "The models are built from team-strength and fundamentals data only: how teams actually perform — scoring, efficiency, pace, schedule strength, rest, and similar inputs. The betting market is never an input to any model.",
      "That separation is deliberate. A model that copies the market can never tell you anything the market hasn't already said. Our models form their own opinion first; the market line only appears afterward, as the benchmark the opinion is graded against.",
    ],
  },
  {
    n: "03",
    title: "Tested before trusted",
    body: [
      "Before any model publishes a live pick, it is validated with a walk-forward backtest: the model is re-run through history using only the information that would have been available at the time, and its picks are graded against the historical closing lines. No peeking, no hindsight-tuned parameters.",
      "The results are published whether they flatter us or not. Our college football backtest covers 8,947 games and grades 49.3% against the spread and 50.8% on totals. The NBA backtest covers 18,552 games at 50.4% against the spread. College basketball: 47,794 games at 49.5% against the spread. The MLB model picked the correct winner in 55.6% of 22,765 games. The NFL model's multi-decade backtest is published on the track record page.",
      "Read those numbers honestly: at standard -110 odds, a bettor needs about 52.4% against the spread to break even. Our backtests do not clear that bar, and we do not claim a betting edge. What they show is a model that is roughly as accurate as the market itself — which is exactly why we think the honest public record, not a sales pitch, is the interesting product here.",
    ],
  },
  {
    n: "04",
    title: "Published before, graded after",
    body: [
      "Every pick is published before its game starts. Once a game tips off, the pick is frozen — it cannot be edited, moved, or quietly deleted. After the game, every pick is graded in public and added to a permanent track record for its league.",
      "Losing weeks stay on the record with the same prominence as winning ones, and each Monday we publish a weekly recap of what the picks got right and wrong. Nothing is cherry-picked, and the record is never reset to make a bad stretch disappear.",
    ],
  },
  {
    n: "05",
    title: "What we're not claiming",
    body: [
      "Honest Line's standard is calibration and transparency, not beating Vegas. If a model says 60%, we want events to happen about 60% of the time — and we publish the calibration data so you can check. We don't sell picks, we don't offer guarantees, and nothing here is betting advice.",
      "Detailed methodology documentation is maintained for each model. This page is the plain-language summary; the track record and calibration pages are where the receipts live.",
    ],
  },
];

export default function HowItWorks() {
  return (
    <div className="max-w-3xl">
      <div className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-red-500/90 light:text-red-700">
        <span className="h-px w-8 bg-red-500/60 light:bg-red-600/70" aria-hidden="true" />
        The short version
      </div>
      <h1 className="mt-3 font-display text-5xl font-semibold uppercase leading-[0.95] tracking-wide">
        How it <span className="text-red-500 light:text-red-600">works</span>
      </h1>
      <p className="mt-4 text-[15px] text-zinc-400 light:text-zinc-600">
        Honest Line is a set of sports prediction models with a public
        scoreboard. The models use fundamentals only, they were tested against
        history before they were trusted with a single live pick, and every
        pick they make is published before the game and graded after it —
        winners and losers alike.
      </p>

      {sections.map((s) => (
        <section
          key={s.n}
          className="mt-8 rounded-2xl border border-white/10 bg-zinc-900/40 p-6 sm:p-8 light:border-zinc-200 light:bg-white"
        >
          <div className="flex items-baseline gap-4">
            <span className="tnum font-display text-lg font-semibold text-red-500/80 light:text-red-700">
              {s.n}
            </span>
            <h2 className="font-display text-2xl font-semibold uppercase tracking-wide">
              {s.title}
            </h2>
          </div>
          <div className="mt-4 space-y-4 text-[15px] leading-relaxed text-zinc-300 light:text-zinc-700">
            {s.body.map((p, i) => (
              <p key={i}>{p}</p>
            ))}
          </div>
        </section>
      ))}

      <p className="mt-8 text-[15px] leading-relaxed text-zinc-400 light:text-zinc-600">
        See the receipts: the{" "}
        <Link href="/track-record" className="underline hover:text-zinc-300 light:hover:text-zinc-900">
          NFL track record
        </Link>{" "}
        and the{" "}
        <Link href="/recaps" className="underline hover:text-zinc-300 light:hover:text-zinc-900">
          weekly recaps
        </Link>{" "}
        show the live record, and{" "}
        <Link href="/about" className="underline hover:text-zinc-300 light:hover:text-zinc-900">
          About
        </Link>{" "}
        explains why this site exists. Please also read the{" "}
        <Link href="/disclaimer" className="underline hover:text-zinc-300 light:hover:text-zinc-900">
          disclaimers
        </Link>{" "}
        — this is research and entertainment, not a way to make money.
      </p>
    </div>
  );
}
