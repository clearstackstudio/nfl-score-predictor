import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "About Honest Line",
  description:
    "What Honest Line is and why it exists: an honest public record for sports model predictions — every pick published before the game, every result graded in public, nothing sold.",
  alternates: { canonical: "/about" },
};

const rules = [
  {
    n: "01",
    title: "Picks are frozen before the game",
    body: [
      "Every pick is published before its game starts and cannot be changed afterward. If the model looks bad on Sunday, the pick that made it look bad is still right there on Monday.",
    ],
  },
  {
    n: "02",
    title: "Everything gets graded",
    body: [
      "Wins, losses, pushes, and the weeks we'd rather forget — all of it goes on the permanent public track record. Null results and losing seasons are published, not buried.",
    ],
  },
  {
    n: "03",
    title: "No cherry-picking",
    body: [
      "We show the full record or nothing. No \"premium\" subset of picks that mysteriously outperforms, no resetting the clock after a bad month, no deleting the evidence.",
    ],
  },
  {
    n: "04",
    title: "Nothing is for sale",
    body: [
      "Honest Line sells no picks, no subscriptions, and no \"locks.\" It's a research project with a public scoreboard, supported by advertising. If someone ever tries to sell you Honest Line picks, it isn't us.",
    ],
  },
  {
    n: "05",
    title: "Not betting advice",
    body: [
      "Our own backtests show no edge against the closing line, and we say so on the front page. Everything here is entertainment and research for adults 21+. The full details are on the disclaimers page.",
    ],
  },
];

export default function About() {
  return (
    <div className="max-w-3xl">
      <div className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-red-500/90 light:text-red-700">
        <span className="h-px w-8 bg-red-500/60 light:bg-red-600/70" aria-hidden="true" />
        About this site
      </div>
      <h1 className="mt-3 font-display text-5xl font-semibold uppercase leading-[0.95] tracking-wide">
        About Honest <span className="text-red-500 light:text-red-600">Line</span>
      </h1>
      <p className="mt-4 text-[15px] text-zinc-400 light:text-zinc-600">
        Honest Line publishes sports prediction models — for the NFL, NBA,
        college football, and college basketball — and keeps an honest public
        record of how they do.
      </p>

      <section className="mt-8 rounded-2xl border border-white/10 bg-zinc-900/40 p-6 sm:p-8 light:border-zinc-200 light:bg-white">
        <h2 className="font-display text-2xl font-semibold uppercase tracking-wide">
          Why it exists
        </h2>
        <div className="mt-4 space-y-4 text-[15px] leading-relaxed text-zinc-300 light:text-zinc-700">
          <p>
            Sports predictions are easy to sell and hard to check. Anyone can
            advertise a hot week; almost nobody publishes the cold ones, the
            full-season record, or the backtest that shows their model doing
            no better than a coin flip against the spread.
          </p>
          <p>
            Honest Line exists to be the opposite of that: a permanent,
            checkable record of what a set of fundamentals-based models
            predicted, published before the games and graded after them. The
            point was never to promise winners. The point is to find out —
            in public, with the receipts — what a disciplined model actually
            gets right, and how close to the market a fundamentals-only
            approach can honestly get.{" "}
            <Link href="/how-it-works" className="underline hover:text-zinc-300 light:hover:text-zinc-900">
              How it works
            </Link>{" "}
            explains the method.
          </p>
        </div>
      </section>

      <h2 className="mt-10 font-display text-3xl font-semibold uppercase tracking-wide">
        The house <span className="text-red-500 light:text-red-600">rules</span>
      </h2>

      {rules.map((s) => (
        <section
          key={s.n}
          className="mt-6 rounded-2xl border border-white/10 bg-zinc-900/40 p-6 sm:p-8 light:border-zinc-200 light:bg-white"
        >
          <div className="flex items-baseline gap-4">
            <span className="tnum font-display text-lg font-semibold text-red-500/80 light:text-red-700">
              {s.n}
            </span>
            <h3 className="font-display text-2xl font-semibold uppercase tracking-wide">
              {s.title}
            </h3>
          </div>
          <div className="mt-4 space-y-4 text-[15px] leading-relaxed text-zinc-300 light:text-zinc-700">
            {s.body.map((p, i) => (
              <p key={i}>{p}</p>
            ))}
          </div>
        </section>
      ))}

      <section className="mt-8 rounded-2xl border border-white/10 bg-zinc-900/40 p-6 sm:p-8 light:border-zinc-200 light:bg-white">
        <h2 className="font-display text-2xl font-semibold uppercase tracking-wide">
          Who runs it
        </h2>
        <div className="mt-4 space-y-4 text-[15px] leading-relaxed text-zinc-300 light:text-zinc-700">
          <p>
            Honest Line is built and run by Bryant, an independent software
            developer, and published by ClearStack Studio, his independent
            software studio. There is no tout service, no sales team, and no
            sponsor with a say in the numbers — the models publish what they
            publish.
          </p>
          <p>
            Each week&apos;s results are written up in the{" "}
            <Link href="/recaps" className="underline hover:text-zinc-300 light:hover:text-zinc-900">
              weekly recaps
            </Link>
            . Before you rely on anything here, please read the{" "}
            <Link href="/disclaimer" className="underline hover:text-zinc-300 light:hover:text-zinc-900">
              disclaimers
            </Link>{" "}
            — the short version is that this is research and entertainment,
            not betting advice and not a way to make money.
          </p>
        </div>
      </section>
    </div>
  );
}
