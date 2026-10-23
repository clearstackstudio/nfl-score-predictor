import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "MLB pick'em game",
  description:
    "Free MLB pick'em game: pick every winner straight up. Returns for the 2027 season.",
  alternates: { canonical: "/mlb/pick-em" },
};

export default function MlbPickEm() {
  return (
    <div>
      <div className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-red-500/90 light:text-red-700">
        <span className="h-px w-8 bg-red-500/60 light:bg-red-600/70" aria-hidden="true" />
        MLB · Beat the model, not the book
      </div>
      <h1 className="mt-3 font-display text-5xl font-semibold uppercase leading-[0.95] tracking-wide">
        Pick<span className="text-red-500 light:text-red-600">&rsquo;em</span>
      </h1>
      <p className="mt-4 max-w-2xl text-[15px] leading-relaxed text-zinc-400 light:text-zinc-600">
        Baseball pick&rsquo;em is simple: pick the winner of every game, straight up —
        no spreads in baseball. Lock your card before first pitch, and we grade it
        against the final scores. Your picks live in your browser (no account needed);
        saved cards persist under the key{" "}
        <span className="font-mono text-[13px] text-zinc-300 light:text-zinc-700">hl-mlb-pickem-2027</span>.
      </p>

      <div className="mt-8 rounded-2xl border border-red-500/25 bg-red-500/[0.06] p-8 text-center light:bg-red-50">
        <div className="font-display text-2xl font-semibold uppercase tracking-wide">
          Pick&rsquo;em opens on Opening Day 2027
        </div>
        <p className="mx-auto mt-3 max-w-xl text-[15px] leading-relaxed text-zinc-400 light:text-zinc-600">
          No MLB games until late March 2027, so there&rsquo;s no card to fill in yet.
          Check back when the season starts — and meanwhile, the model&rsquo;s full
          walk-forward backtest is on the track-record page.
        </p>
        <a
          href="/mlb/track-record"
          className="mt-5 inline-block rounded-xl bg-red-500 px-6 py-3 text-sm font-bold uppercase tracking-wider text-white transition hover:bg-red-600"
        >
          Full track record →
        </a>
      </div>
    </div>
  );
}
