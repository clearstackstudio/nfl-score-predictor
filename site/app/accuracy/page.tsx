import type { Metadata } from "next";
import Link from "next/link";
import nfl from "../../data/track_record.json";
import cfb from "../../data/cfb_track_record.json";

export const metadata: Metadata = {
  title: "Model accuracy",
  description:
    "How accurate are the Honest Line models? Prediction error vs the closing line for NFL, college football, NBA, and NCAAB — the full honest accounting.",
  alternates: { canonical: "/accuracy" },
};
import nba from "../../data/nba_track_record.json";
import ncaab from "../../data/ncaab_track_record.json";
import { fmtPct } from "../lib/format";

type SportCard = {
  name: string;
  span: string;
  games: number;
  suPct: number;
  atsW: number;
  atsL: number;
  atsP: number;
  ouPct: number | null;
  ourRmse: number;
  lineRmse: number;
  href: string;
  note: string;
};

function nflCard(): SportCard {
  const seasons = nfl.seasons as any[];
  const games = seasons.reduce((a, s) => a + s.games, 0);
  const su = seasons.reduce((a, s) => a + s.straight_up_pct * s.games, 0) / games;
  const w = seasons.reduce((a, s) => a + s.ats_w, 0);
  const l = seasons.reduce((a, s) => a + s.ats_l, 0);
  const p = seasons.reduce((a, s) => a + s.ats_p, 0);
  const our = seasons.reduce((a, s) => a + s.our_rmse * s.games, 0) / games;
  const line = seasons.reduce((a, s) => a + s.line_rmse * s.games, 0) / games;
  const first = seasons[0].season;
  const last = seasons[seasons.length - 1].season;
  return {
    name: "NFL",
    span: `${first}–${last} · ${seasons.length} seasons`,
    games, suPct: su, atsW: w, atsL: l, atsP: p, ouPct: null,
    ourRmse: our, lineRmse: line, href: "/track-record",
    note: "Early edge faded — about 50.8% ATS in the 2020s.",
  };
}

function cfbCard(): SportCard {
  const o = (cfb as any).overall;
  const seasons = (cfb as any).seasons as any[];
  const first = seasons[0].season ?? seasons[0].year;
  const last = seasons[seasons.length - 1].season ?? seasons[seasons.length - 1].year;
  return {
    name: "College football",
    span: `${first}–${last} · ${seasons.length} seasons`,
    games: o.games, suPct: o.straight_up_pct,
    atsW: o.ats[0], atsL: o.ats[1], atsP: o.ats[2], ouPct: o.ou_pct,
    ourRmse: o.our_margin_rmse, lineRmse: o.line_margin_rmse,
    href: "/cfb/track-record",
    note: "Never beat the closing line on margin error.",
  };
}

function nbaCard(): SportCard {
  const o = (nba as any).overall;
  const eras = (nba as any).eras as { label: string }[];
  const first = eras[0]?.label.split("–")[0] ?? "";
  const last = eras[eras.length - 1]?.label.split("–")[1] ?? "";
  return {
    name: "NBA",
    span: `${first}–${last} · ${eras.length} eras`,
    games: o.games, suPct: o.straight_up_pct,
    atsW: o.ats[0], atsL: o.ats[1], atsP: o.ats[2], ouPct: o.ou_pct,
    ourRmse: o.our_margin_rmse, lineRmse: o.line_margin_rmse,
    href: "/nba/track-record",
    note: "Edge decayed by era: 51.0% → 50.3% → 50.1% ATS.",
  };
}

function AtsBar({ pct }: { pct: number }) {
  // scale 45%..60% across the bar; break-even marker at 52.4%
  const left = Math.max(0, Math.min(100, ((pct - 0.45) / 0.15) * 100));
  const be = ((0.524 - 0.45) / 0.15) * 100;
  const good = pct >= 0.524;
  return (
    <div>
      <div className="relative h-6 flex-1 rounded bg-zinc-800/70 light:bg-zinc-200">
        <div
          className="absolute inset-y-0 w-px bg-zinc-500 light:bg-zinc-400"
          style={{ left: `${be}%` }}
          title="Break-even 52.4%"
        />
        <div
          className={`absolute inset-y-1 rounded ${good ? "bg-emerald-400/80 light:bg-emerald-500" : "bg-red-400/80 light:bg-red-500"}`}
          style={{ width: `${left}%` }}
        />
      </div>
      <div className="mt-1 flex justify-between text-[10px] text-zinc-500">
        <span>45%</span>
        <span>break-even 52.4%</span>
        <span>60%</span>
      </div>
    </div>
  );
}

function ncaabCard(): SportCard {
  const o = (ncaab as any).overall;
  const eras = (ncaab as any).eras as { label: string }[];
  const first = eras[0]?.label.split("–")[0] ?? "";
  const last = eras[eras.length - 1]?.label.split("–")[1] ?? "";
  return {
    name: "NCAAB",
    span: `${first}–${last} · ${eras.length} eras`,
    games: o.games, suPct: o.straight_up_pct,
    atsW: o.ats[0], atsL: o.ats[1], atsP: o.ats[2], ouPct: o.ou_pct,
    ourRmse: o.our_margin_rmse, lineRmse: o.line_margin_rmse,
    href: "/ncaab/track-record",
    note: "No era beat the vig: 48.9% → 49.8% → 50.2% ATS.",
  };
}

export default function Accuracy() {
  const cards = [nflCard(), cfbCard(), nbaCard(), ncaabCard()];
  return (
    <div>
      <div className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-amber-400/90 light:text-amber-700">
        <span className="h-px w-8 bg-amber-400/60 light:bg-amber-600/70" aria-hidden="true" />
        All sports · one honest page
      </div>
      <h1 className="mt-3 font-display text-5xl font-semibold uppercase leading-[0.95] tracking-wide">
        Model <span className="text-amber-400 light:text-amber-600">accuracy</span>
      </h1>
      <p className="mt-4 max-w-2xl text-sm text-zinc-400 light:text-zinc-600">
        Walk-forward backtests: every prediction was made before the result was known.
        The dashed marker on each bar is 52.4% — break-even against standard -110 vig.
      </p>

      <div className="mt-8 grid gap-5 md:grid-cols-3">
        {cards.map((c) => {
          const atsPct = c.atsW / (c.atsW + c.atsL);
          const good = atsPct >= 0.524;
          return (
            <div
              key={c.name}
              className="flex flex-col rounded-2xl border border-zinc-800 bg-zinc-900/40 p-5 light:border-zinc-200 light:bg-white"
            >
              <div className="flex items-baseline justify-between">
                <h2 className="font-display text-2xl font-semibold uppercase tracking-wide">{c.name}</h2>
              </div>
              <p className="mt-1 text-xs text-zinc-500">{c.span} · {c.games.toLocaleString()} games</p>

              <div className="mt-4 grid grid-cols-2 gap-3">
                <div className="rounded-xl bg-zinc-800/50 p-3 light:bg-zinc-100">
                  <div className="tnum text-xl font-extrabold">{fmtPct(c.suPct)}</div>
                  <div className="mt-0.5 text-[11px] text-zinc-500">Straight-up</div>
                </div>
                <div className="rounded-xl bg-zinc-800/50 p-3 light:bg-zinc-100">
                  <div className="tnum text-xl font-extrabold">
                    {c.ourRmse.toFixed(2)}
                    <span className="ml-1 text-xs font-medium text-zinc-500">vs {c.lineRmse.toFixed(2)}</span>
                  </div>
                  <div className="mt-0.5 text-[11px] text-zinc-500">Margin err · us vs line</div>
                </div>
              </div>

              <div className="mt-4">
                <div className="mb-1 flex items-baseline justify-between text-sm">
                  <span className="text-zinc-400 light:text-zinc-600">Against the spread</span>
                  <span className={`font-mono font-bold ${good ? "text-emerald-400 light:text-emerald-700" : "text-red-400 light:text-red-600"}`}>
                    {fmtPct(atsPct)}
                  </span>
                </div>
                <div className="mb-1 text-xs text-zinc-500">
                  {c.atsW.toLocaleString()}-{c.atsL.toLocaleString()}-{c.atsP.toLocaleString()}
                  {c.ouPct != null && <> · Totals {fmtPct(c.ouPct)}</>}
                </div>
                <AtsBar pct={atsPct} />
              </div>

              <p className="mt-3 text-[13px] leading-relaxed text-zinc-400 light:text-zinc-600">{c.note}</p>

              <Link
                href={c.href}
                className="mt-4 inline-flex items-center gap-1.5 text-sm font-semibold text-amber-400 hover:text-amber-300 light:text-amber-700 light:hover:text-amber-800"
              >
                Full {c.name} track record
                <span aria-hidden="true">→</span>
              </Link>
            </div>
          );
        })}
      </div>

      <div className="mt-8 rounded-2xl border border-amber-400/20 bg-amber-400/5 p-5 light:border-amber-600/20 light:bg-amber-50">
        <h2 className="font-display text-xl font-semibold uppercase tracking-wide">The honest verdict</h2>
        <p className="mt-2 max-w-3xl text-[15px] leading-relaxed text-zinc-300 light:text-zinc-700">
          A competent forecaster that roughly matches the Vegas line on prediction error —
          but with no demonstrated betting edge. None of the four models clears the 52.4%
          needed to beat the spread long-term, and the edges that existed in older eras
          have decayed as markets got sharper. Good enough to follow for fun; not a way
          to make money.
        </p>
      </div>
    </div>
  );
}
