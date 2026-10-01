import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Disclaimers — Honest Line",
  description:
    "Entertainment and research only. Our picks are not betting advice, carry no guarantees, and are for adults 21+. Please play responsibly.",
};

const sections = [
  {
    n: "01",
    title: "Not betting advice",
    body: [
      "Everything on Honest Line is published for entertainment and research purposes only. Our picks, probabilities, and model outputs are not financial advice, not betting advice, and not a tipster service. Decisions about whether or how to wager are yours alone.",
    ],
  },
  {
    n: "02",
    title: "No guarantees",
    body: [
      "Our probabilities are estimates, and estimates are wrong sometimes. Our own 45-season backtest shows the model roughly tying the closing line on score error and flipping a coin against the spread in recent seasons. Past performance — ours or anyone's — does not predict future results.",
    ],
  },
  {
    n: "03",
    title: "21+ and responsible play",
    body: [
      "This site is intended for adults 21 and over. Never bet more than you can afford to lose, and never chase losses. If gambling stops being fun, stop — and consider talking to someone.",
      "Free, confidential help is available 24/7 from the National Council on Problem Gambling at 1-800-GAMBLER or ncpgambling.org.",
    ],
  },
  {
    n: "04",
    title: "Lines are snapshots",
    body: [
      "The market lines shown next to our picks were current when the picks were generated. Lines move. A pick that looked interesting at one number may not be at another — always check the current line before drawing any conclusions.",
    ],
  },
  {
    n: "05",
    title: "Limitation of liability",
    body: [
      "To the fullest extent permitted by law, Honest Line and ClearStack Studio are not liable for any decisions you make based on this site's content, or for any losses arising from them. You use this site at your own risk.",
    ],
  },
];

export default function Disclaimer() {
  return (
    <div className="max-w-3xl">
      <div className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-amber-400/90 light:text-amber-700">
        <span className="h-px w-8 bg-amber-400/60 light:bg-amber-600/70" aria-hidden="true" />
        The fine print
      </div>
      <h1 className="mt-3 font-display text-5xl font-semibold uppercase leading-[0.95] tracking-wide">
        Disclaim<span className="text-amber-400 light:text-amber-600">ers</span>
      </h1>
      <p className="mt-4 text-[15px] text-zinc-400 light:text-zinc-600">
        The short version: this is a research project with a public scoreboard,
        not a way to make money. Read the details below.
      </p>

      {sections.map((s) => (
        <section
          key={s.n}
          className="mt-8 rounded-2xl border border-white/10 bg-zinc-900/40 p-6 sm:p-8 light:border-zinc-200 light:bg-white"
        >
          <div className="flex items-baseline gap-4">
            <span className="tnum font-display text-lg font-semibold text-amber-400/80 light:text-amber-700">
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

      <p className="mt-8 text-xs leading-relaxed text-zinc-500 light:text-zinc-500">
        Effective September 30, 2026. This page is general information, not
        legal advice. If you need legal guidance about gambling regulations in
        your jurisdiction, consult a qualified attorney.
      </p>
    </div>
  );
}
