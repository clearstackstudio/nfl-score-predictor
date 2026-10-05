"use client";
import { useState } from "react";
import picksData from "../data/picks.json";
import seasonLog from "../data/season_2026.json";
import { fmtSpread, fmtPct, trim } from "./lib/format";
import TeamLogo from "./lib/team-logo";
import EmailSignup from "./lib/email-signup";
import SharePicks from "./lib/share-picks";

type Pick = {
  away: string; home: string; away_abbr: string; home_abbr: string;
  gameday: string; weekday: string;
  line_spread: number; line_total: number;
  our_spread: number; our_total: number;
  spread_edge: number; total_edge: number;
  pick_spread: "home" | "away" | null;
  pick_total: "over" | "under" | null;
  pick_total_note?: string | null;
  wind_mph?: number | null; wind_adj_pts?: number | null;
  pick_spread_label: string | null;
  pick_total_label: string | null;
  cover_prob: number | null; ou_prob: number | null;
  home_qb: string | null; away_qb: string | null;
  result?: { home_score: number; away_score: number; ats?: string; ou?: string } | null;
};


function fmtGameday(p: Pick): string {
  // gameday is YYYY-MM-DD; weekday already provided
  const [, m, d] = p.gameday.split("-").map(Number);
  const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  return `${p.weekday.slice(0, 3)}, ${months[m - 1]} ${d}`;
}

function spreadPickText(p: Pick): string {
  // Labels are computed and validated by the generator (single source of
  // truth); the site renders them verbatim. Fallback only for old data.
  if (p.pick_spread_label) return `${p.pick_spread_label} · ${fmtPct(p.cover_prob)} to cover`;
  const team = p.pick_spread === "home" ? p.home_abbr : p.away_abbr;
  return `${team} · ${fmtPct(p.cover_prob)} to cover`;
}

function ouPickText(p: Pick): string {
  if (p.pick_total_label) return `${p.pick_total_label} · ${fmtPct(p.ou_prob)}`;
  return `${p.pick_total === "over" ? "Over" : "Under"} ${trim(p.line_total)} · ${fmtPct(p.ou_prob)}`;
}

function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-amber-400/90 light:text-amber-700">
      <span className="h-px w-8 bg-amber-400/60 light:bg-amber-600/70" aria-hidden="true" />
      {children}
    </div>
  );
}

function MarketPanel({
  name,
  ourLabel,
  ourCaption,
  vegasLabel,
  vegasCaption,
  edge,
  edgeCaption,
  pick,
}: {
  name: string;
  ourLabel: string;
  ourCaption: string;
  vegasLabel: string;
  vegasCaption: string;
  edge: number;
  edgeCaption: string;
  pick: React.ReactNode;
}) {
  return (
    <div className="mt-4 overflow-hidden rounded-xl border border-white/5 bg-zinc-950/70 light:border-zinc-200 light:bg-zinc-50">
      <div className="grid grid-cols-3 divide-x divide-white/5 light:divide-zinc-200">
        <div className="p-3.5">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">
            {name} · us
          </div>
          <div className="tnum mt-1.5 font-mono text-[15px] font-semibold text-zinc-100 light:text-zinc-900">
            {ourLabel}
          </div>
          <div className="mt-0.5 text-[11px] text-zinc-600 light:text-zinc-500">{ourCaption}</div>
        </div>
        <div className="p-3.5">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">
            {name} · Vegas
          </div>
          <div className="tnum mt-1.5 font-mono text-[15px] text-zinc-400 light:text-zinc-600">
            {vegasLabel}
          </div>
          <div className="mt-0.5 text-[11px] text-zinc-600 light:text-zinc-500">{vegasCaption}</div>
        </div>
        <div className="p-3.5">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">
            Disagreement
          </div>
          <div className="tnum mt-1.5 font-mono text-[15px] text-zinc-400 light:text-zinc-600">
            {trim(Math.abs(edge))} pts
          </div>
          <div className="mt-0.5 text-[11px] text-zinc-600 light:text-zinc-500">{edgeCaption}</div>
        </div>
      </div>
      <div className="border-t border-white/5 light:border-zinc-200">{pick}</div>
    </div>
  );
}

function ResultBadge({ r }: { r: "win" | "loss" | "push" }) {
  const cls =
    r === "win"
      ? "bg-emerald-400/15 text-emerald-300 light:bg-emerald-600/10 light:text-emerald-700"
      : r === "loss"
        ? "bg-rose-400/15 text-rose-300 light:bg-rose-600/10 light:text-rose-700"
        : "bg-zinc-400/15 text-zinc-400 light:bg-zinc-500/10 light:text-zinc-600";
  const text = r === "win" ? "✓ Won" : r === "loss" ? "✗ Lost" : "Push";
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${cls}`}>
      {text}
    </span>
  );
}

function PickStrip({ active, note, result, children }: { active: boolean; note?: string | null; result?: "win" | "loss" | "push" | null; children: React.ReactNode }) {
  if (active) {
    return (
      <div className="border-l-2 border-amber-400 bg-amber-400/[0.07] px-4 py-3">
        <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.16em] text-amber-400/90 light:text-amber-700">
          Model pick
          {result && <ResultBadge r={result} />}
        </div>
        <div className="mt-0.5 text-[15px] font-semibold text-amber-100 light:text-amber-800">{children}</div>
      </div>
    );
  }
  return (
    <div className="px-4 py-2.5 text-[13px] text-zinc-600 light:text-zinc-500">
      {note ?? "No play — we agree with Vegas here."}
    </div>
  );
}

function GameCard({ p }: { p: Pick }) {
  return (
    <article className="rounded-2xl border border-white/10 bg-gradient-to-b from-zinc-900/70 to-zinc-900/30 p-5 transition-colors hover:border-white/20 light:border-zinc-200 light:from-white light:to-zinc-50 light:hover:border-zinc-300">
      {/* Header: matchup + date */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex flex-wrap items-center gap-x-2.5 text-[17px] font-bold tracking-tight">
          <span className="inline-flex items-center gap-2">
            <TeamLogo abbr={p.away_abbr} size={26} />
            {p.away}
          </span>
          <span className="text-sm font-medium text-zinc-600 light:text-zinc-400">@</span>
          <span className="inline-flex items-center gap-2">
            <TeamLogo abbr={p.home_abbr} size={26} />
            {p.home}
          </span>
        </h2>
        <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-xs font-medium text-zinc-400 light:border-zinc-200 light:bg-zinc-100 light:text-zinc-600">
          {fmtGameday(p)}
        </span>
      </div>
      {(p.away_qb || p.home_qb) && (
        <p className="mt-2 text-xs text-zinc-500">
          Probable QBs — {p.away_abbr}: {p.away_qb ?? "—"} · {p.home_abbr}: {p.home_qb ?? "—"}
        </p>
      )}

      <MarketPanel
        name="Spread"
        ourLabel={fmtSpread(p.our_spread, p.home_abbr, p.away_abbr)}
        ourCaption="Our number"
        vegasLabel={fmtSpread(p.line_spread, p.home_abbr, p.away_abbr)}
        vegasCaption="Vegas line"
        edge={p.spread_edge}
        edgeCaption="pts of disagreement"
        pick={
          <PickStrip active={!!p.pick_spread} result={(p.result?.ats as "win" | "loss" | "push") ?? null}>
            {p.pick_spread ? spreadPickText(p) : null}
          </PickStrip>
        }
      />

      <MarketPanel
        name="Total"
        ourLabel={trim(p.our_total)}
        ourCaption={p.wind_mph != null && p.wind_adj_pts
          ? `Our number · wind ${p.wind_mph} mph (${p.wind_adj_pts} pts)`
          : "Our number"}
        vegasLabel={trim(p.line_total)}
        vegasCaption="Vegas line"
        edge={p.total_edge}
        edgeCaption="pts of disagreement"
        pick={
          <PickStrip active={!!p.pick_total} note={p.pick_total_note} result={(p.result?.ou as "win" | "loss" | "push") ?? null}>
            {p.pick_total ? ouPickText(p) : null}
          </PickStrip>
        }
      />
    </article>
  );
}

type ParlayLeg = {
  game: string; market: "spread" | "total"; label: string; prob: number;
};
type Parlay = {
  legs: ParlayLeg[]; combined_prob: number; fair_odds: string; book_pays: string;
  result?: "win" | "loss" | "push" | null;
} | null;

type WeekLog = {
  generated: string; complete: boolean;
  picks: Pick[]; parlay: Parlay;
};
type SeasonLog = { season: number; weeks: Record<string, WeekLog> };

type WeekView = {
  week: number; season: number; generated: string;
  picks: Pick[]; parlay: Parlay; disclaimer: string;
  isCurrent: boolean; complete: boolean;
};

const currentWeek: WeekView = {
  week: (picksData as { week: number }).week,
  season: (picksData as { season: number }).season,
  generated: (picksData as { generated: string }).generated,
  picks: (picksData as { picks: Pick[] }).picks,
  parlay: (picksData as { parlay?: Parlay }).parlay ?? null,
  disclaimer: (picksData as { disclaimer: string }).disclaimer,
  isCurrent: true,
  complete: false,
};

const pastWeeks: WeekView[] = Object.entries((seasonLog as SeasonLog).weeks)
  .map(([wn, w]) => ({
    week: Number(wn),
    season: (seasonLog as SeasonLog).season,
    generated: w.generated,
    picks: w.picks,
    parlay: w.parlay ?? null,
    disclaimer: "",
    isCurrent: false,
    complete: w.complete,
  }))
  .sort((a, b) => b.week - a.week);

const allWeeks: WeekView[] = [currentWeek, ...pastWeeks];

function ParlayCard({ parlay }: { parlay: Parlay }) {
  if (!parlay || parlay.legs.length < 2) return null;
  return (
    <section className="mb-8 overflow-hidden rounded-2xl border border-amber-400/25 bg-gradient-to-b from-amber-400/[0.09] to-amber-400/[0.03]">
      <div className="flex flex-wrap items-baseline justify-between gap-2 px-5 pt-5">
        <div>
          <div className="text-[11px] font-bold uppercase tracking-[0.18em] text-amber-400/90 light:text-amber-700">
            For fun · not a strategy
          </div>
          <h2 className="mt-1 font-display text-3xl font-semibold uppercase tracking-wide">
            Parlay of the week
            {parlay.result && (
              <span className="ml-3 align-middle">
                <ResultBadge r={parlay.result} />
              </span>
            )}
          </h2>
        </div>
        <span className="text-sm text-zinc-500">
          Our {parlay.legs.length} highest-conviction picks, combined
        </span>
      </div>

      <ul className="mt-4 space-y-2 px-5">
        {parlay.legs.map((l) => (
          <li
            key={`${l.game}-${l.market}`}
            className="flex items-center justify-between gap-3 rounded-xl border border-white/5 bg-zinc-950/70 px-4 py-2.5 light:border-zinc-200 light:bg-white"
          >
            <div>
              <span className="font-bold text-amber-200 light:text-amber-700">{l.label}</span>
              <span className="ml-2 text-sm text-zinc-500">{l.game}</span>
            </div>
            <span className="tnum font-mono text-sm font-semibold text-zinc-300 light:text-zinc-700">
              {fmtPct(l.prob)}
            </span>
          </li>
        ))}
      </ul>

      <div className="mt-4 grid grid-cols-2 gap-3 px-5">
        <div className="rounded-xl border border-white/5 bg-zinc-950/70 p-3.5 light:border-zinc-200 light:bg-white">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">
            Model&rsquo;s combined chance
          </div>
          <div className="tnum mt-1 text-xl font-extrabold">
            {fmtPct(parlay.combined_prob)}{" "}
            <span className="text-sm font-semibold text-zinc-400 light:text-zinc-600">
              · fair odds {parlay.fair_odds}
            </span>
          </div>
        </div>
        <div className="rounded-xl border border-white/5 bg-zinc-950/70 p-3.5 light:border-zinc-200 light:bg-white">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">
            Books typically pay
          </div>
          <div className="tnum mt-1 text-xl font-extrabold">
            {parlay.book_pays}{" "}
            <span className="text-sm font-semibold text-zinc-400 light:text-zinc-600">
              on {parlay.legs.length} legs
            </span>
          </div>
        </div>
      </div>

      <p className="px-5 pb-5 pt-4 text-[13px] leading-relaxed text-zinc-400 light:text-zinc-600">
        The honest fine print: parlays multiply the book&rsquo;s edge along with the
        payout — on true coin flips a {parlay.legs.length}-legger&rsquo;s fair price is{" "}
        {parlay.legs.length === 3 ? "+700" : "+300"}, worse than the {parlay.book_pays} books
        pay. And our model&rsquo;s confidence is unproven: its backtest shows no edge
        against the closing line, and early-season ratings swing wildly. This is
        entertainment, not a strategy.
      </p>
    </section>
  );
}

export default function Home() {
  const [sel, setSel] = useState(0);
  const wv = allWeeks[sel] ?? currentWeek;
  const picks = wv.picks;
  const nSpread = picks.filter((p) => p.pick_spread).length;
  const nTotal = picks.filter((p) => p.pick_total).length;

  return (
    <div>
      {/* Hero */}
      <div className="mb-8">
        <Eyebrow>
          Week {wv.week} · {wv.season} season · generated {wv.generated}
          {!wv.isCurrent && !wv.complete && (
            <span className="ml-2 rounded bg-zinc-500/15 px-2 py-0.5 text-zinc-400 light:text-zinc-600">partial</span>
          )}
        </Eyebrow>
        <h1 className="mt-3 font-display text-5xl font-semibold uppercase leading-[0.95] tracking-wide sm:text-6xl">
          {wv.isCurrent ? (
            <>This week&rsquo;s <span className="text-amber-400 light:text-amber-600">picks</span></>
          ) : (
            <>Week {wv.week} <span className="text-amber-400 light:text-amber-600">picks</span></>
          )}
        </h1>
        {allWeeks.length > 1 && (
          <div className="mt-4 flex flex-wrap gap-2" role="tablist" aria-label="Browse weeks">
            {allWeeks.map((w, i) => (
              <button
                key={w.week}
                role="tab"
                aria-selected={i === sel}
                onClick={() => setSel(i)}
                className={`rounded-full border px-3.5 py-1.5 text-sm font-semibold transition ${
                  i === sel
                    ? "border-amber-400 bg-amber-400/15 text-amber-200 light:border-amber-600 light:bg-amber-600/10 light:text-amber-700"
                    : "border-zinc-800 bg-zinc-900 text-zinc-400 hover:border-zinc-600 hover:text-zinc-200 light:border-zinc-200 light:bg-white light:text-zinc-600 light:hover:border-zinc-400"
                }`}
              >
                {w.isCurrent ? `Week ${w.week} · current` : `Week ${w.week}`}
              </button>
            ))}
          </div>
        )}
        <p className="mt-4 max-w-2xl text-[15px] leading-relaxed text-zinc-400 light:text-zinc-600">
          {picks.length} games, {nSpread} spread plays and {nTotal} total plays —
          from opponent-adjusted EPA ratings. The model never sees the betting
          line; the line is only the benchmark we measure against. Lines are a
          snapshot from generation time and don&rsquo;t update mid-week — every
          pick is graded against the line shown here.
        </p>
        <div className="mt-5 flex flex-wrap gap-x-8 gap-y-3">
          {[
            [String(picks.length), "games"],
            [String(nSpread), "spread plays"],
            [String(nTotal), "total plays"],
          ].map(([v, l]) => (
            <div key={l} className="flex items-baseline gap-2">
              <span className="tnum font-display text-3xl font-semibold text-zinc-100 light:text-zinc-900">{v}</span>
              <span className="text-xs font-medium uppercase tracking-wider text-zinc-500">{l}</span>
            </div>
          ))}
        </div>
        <p className="mt-5 max-w-2xl rounded-xl border border-amber-400/25 bg-amber-400/10 px-4 py-3 text-sm leading-relaxed text-amber-200/90 light:text-amber-800">
          {wv.isCurrent ? wv.disclaimer : "Graded results — every pick marked won, lost, or push. Nothing hidden, nothing rewritten."}
        </p>
        <div className="mt-5">
          <SharePicks />
        </div>
      </div>

      <ParlayCard parlay={wv.parlay} />

      <div className="mb-4 flex items-baseline justify-between">
        <h2 className="font-display text-2xl font-semibold uppercase tracking-wide">
          Every game
        </h2>
        <span className="text-sm text-zinc-500">Model vs. Vegas, side by side</span>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        {picks.map((p) => (
          <GameCard key={`${p.away_abbr}-${p.home_abbr}`} p={p} />
        ))}
      </div>

      <p className="mt-6 max-w-2xl text-sm leading-relaxed text-zinc-500 light:text-zinc-600">
        How to read a card: <span className="text-zinc-300 light:text-zinc-800">Our number</span> is what the
        model thinks the spread or total should be; <span className="text-zinc-300 light:text-zinc-800">Vegas line</span> is
        the market. A pick appears only where we disagree by enough to matter —
        the percentage is our estimated chance that side covers or the total lands.
      </p>

      {wv.isCurrent && (
        <div className="mt-10">
          <EmailSignup />
        </div>
      )}
    </div>
  );
}
