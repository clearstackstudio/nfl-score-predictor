import type { Metadata } from "next";
import TrackerPage from "./tracker-page";

export const metadata: Metadata = {
  title: "Bet Tracker",
  description:
    "Log your own bets and get the Honest Line treatment: real record, honest ROI, and a calibration plot of your odds against your actual hit rate. Your receipt, not your memory.",
  alternates: { canonical: "/tracker" },
};

function TrackerExplainer() {
  return (
    <section className="mt-12 max-w-3xl">
      <h2 className="font-display text-3xl font-semibold uppercase tracking-wide">
        How the tracker works
      </h2>
      <div className="mt-4 space-y-4 text-[15px] leading-relaxed text-zinc-300 light:text-zinc-700">
        <p>
          The bet tracker is the Honest Line grading system pointed at your own bets
          instead of our models. Add a bet — sport, market, the selection, the odds you
          got, and your stake — and when the game ends, mark it a win, a loss, or a
          push. The tracker keeps the full history and does the math most bettors never
          do: your real record, your profit or loss after the vig, and your return on
          investment across every dollar staked, broken down by sport, by market, and
          by month. Everything is stored only in this browser — there is no account and
          nothing is sent anywhere — and you can export the whole log as JSON at any
          time.
        </p>
        <p>
          The number that decides whether a bettor is actually good is not the win
          rate — it is the win rate compared to what the odds demanded. Every price
          implies a breakeven rate: a standard −110 bet has to win 52.4% of the time
          just to break even, because the bookmaker&rsquo;s cut — the vig — is baked
          into the price. The tracker computes the breakeven rate your own odds
          demanded across your bets and sets it next to your actual hit rate, so the
          comparison is the honest one. Beating your own memory is easy; beating the
          price is the whole game.
        </p>
        <p>
          The calibration plot borrows the same test we publish for our own models.
          Your bets are grouped by the odds you took; for each group, the plot compares
          the breakeven rate those odds implied with how often you actually won.
          Groups above the dashed line beat the price they were given; groups below it
          paid the vig. Small samples swing wildly — a handful of bets can sit far from
          the line on luck alone — so the plot means more as the log grows. That is
          exactly why it exists: to replace a feeling about your betting with a
          receipt. If you recorded a confidence number when you logged a bet, the same
          mirror applies to your judgment: what you thought your chance was, against
          what actually happened.
        </p>
        <p>
          This is deliberately the same treatment Honest Line gives itself. Every
          model pick on this site is published before the game, graded against the
          final score, and kept on a public track record — the bad weeks included —
          and the calibration page checks whether our published probabilities matched
          reality. We do not claim the models beat the closing line; our own backtests
          say they don&rsquo;t. The tracker exists so you can hold your own picks to
          the same standard: a complete record, honest math, and no selective memory.
        </p>
      </div>
    </section>
  );
}

export default function Tracker() {
  return (
    <>
      <TrackerPage />
      <TrackerExplainer />
    </>
  );
}
