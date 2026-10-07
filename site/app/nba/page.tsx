"use client";
import { useState } from "react";
import picksData from "../../data/nba_picks.json";
import seasonLog from "../../data/nba_season_2027.json";
import { fmtSpread, fmtPct, trim } from "../lib/format";
import NbaTeamLogo from "../lib/nba-team-logo";

type Pick = {
  away: string; home: string; away_abbr: string; home_abbr: string;
  gameday: string; weekday: string; neutral?: boolean;
  line_spread: number; line_total: number;
  our_spread: number; our_total: number;
  spread_edge: number; total_edge: number;
  pick_spread: "home" | "away" | null;
  pick_total: "over" | "under" | null;
  pick_spread_label: string | null;
  pick_total_label: string | null;
  pick_total_note?: string | null;
  spread_labels?: { home: string; away: string };
  cover_prob: number | null; ou_prob: number | null;
  result?: { home_score: number; away_score: number; ats?: string; ou?: string } | null;
};

type PicksFile = {
  sport: string; season: number; week?: number | null; date?: string | null;
  generated: string | null; disclaimer: string;
  preseason?: boolean; experimental?: boolean; experimental_note?: string | null;
  pending?: boolean; pending_reason?: string;
  parlay?: Parlay | null; picks: Pick[];
};

const data = picksData as PicksFile;

type DayLog = {
  date: string; generated: string | null;
  preseason?: boolean; experimental_note?: string | null;
  graded: boolean; complete: boolean;
  picks: Pick[]; parlay: Parlay;
};
type SeasonLog = { sport: string; season: number; days: Record<string, DayLog> };

type DayView = {
  date: string | null; season: number; generated: string | null;
  picks: Pick[]; parlay: Parlay; disclaimer: string;
  preseason?: boolean; experimental_note?: string | null;
  pending?: boolean; pending_reason?: string;
  isCurrent: boolean; complete: boolean;
};

const currentDay: DayView = {
  date: data.date ?? null,
  season: data.season,
  generated: data.generated,
  picks: data.picks,
  parlay: data.parlay ?? null,
  disclaimer: data.disclaimer,
  preseason: data.preseason ?? data.experimental,
  experimental_note: data.experimental_note,
  pending: data.pending,
  pending_reason: data.pending_reason,
  isCurrent: true,
  complete: false,
};

const pastDays: DayView[] = Object.entries((seasonLog as unknown as SeasonLog).days)
  .filter(([dk]) => dk !== data.date) // season log also holds the current day
  .map(([dk, d]) => ({
    date: d.date,
    season: (seasonLog as unknown as SeasonLog).season,
    generated: d.generated,
    picks: d.picks,
    parlay: d.parlay ?? null,
    disclaimer: "",
    preseason: d.preseason,
    experimental_note: d.experimental_note,
    isCurrent: false,
    complete: d.complete,
  }))
  .sort((a, b) => (b.date ?? "").localeCompare(a.date ?? ""));

const allDays: DayView[] = [currentDay, ...pastDays];

function fmtGameday(p: Pick): string {
  if (p.neutral) return "Neutral site";
  if (!p.gameday) return "";
  const parts = p.gameday.split("-").map(Number);
  if (parts.length < 3) return p.gameday;
  const [, m, d] = parts;
  const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  const wd = p.weekday ? p.weekday.slice(0, 3) + ", " : "";
  return `${wd}${months[m - 1]} ${d}`;
}

function fmtSlateDate(iso: string | null | undefined): string {
  if (!iso) return "";
  const parts = iso.split("-").map(Number);
  if (parts.length < 3) return iso;
  const [y, m, d] = parts;
  const months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
  const wd = new Date(Date.UTC(y, m - 1, d)).toLocaleDateString("en-US", { weekday: "short", timeZone: "UTC" });
  return `${wd}, ${months[m - 1]} ${d}`;
}

function spreadPickText(p: Pick): string {
  if (p.pick_spread_label) return `${p.pick_spread_label} · ${fmtPct(p.cover_prob)} to cover`;
  const team = p.pick_spread === "home" ? p.home : p.away;
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
  name, ourLabel, ourCaption, vegasLabel, vegasCaption, edge, edgeCaption, pick,
}: {
  name: string; ourLabel: string; ourCaption: string;
  vegasLabel: string; vegasCaption: string;
  edge: number; edgeCaption: string; pick: React.ReactNode;
}) {
  return (
    <div className="mt-4 overflow-hidden rounded-xl border border-white/5 bg-zinc-950/70 light:border-zinc-200 light:bg-zinc-50">
      <div className="grid grid-cols-3 divide-x divide-white/5 light:divide-zinc-200">
        <div className="p-3.5">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">{name} · us</div>
          <div className="tnum mt-1.5 font-mono text-[15px] font-semibold text-zinc-100 light:text-zinc-900">{ourLabel}</div>
          <div className="mt-0.5 text-[11px] text-zinc-600 light:text-zinc-500">{ourCaption}</div>
        </div>
        <div className="p-3.5">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">{name} · Vegas</div>
          <div className="tnum mt-1.5 font-mono text-[15px] text-zinc-400 light:text-zinc-600">{vegasLabel}</div>
          <div className="mt-0.5 text-[11px] text-zinc-600 light:text-zinc-500">{vegasCaption}</div>
        </div>
        <div className="p-3.5">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">Disagreement</div>
          <div className="tnum mt-1.5 font-mono text-[15px] text-zinc-400 light:text-zinc-600">{trim(Math.abs(edge))} pts</div>
          <div className="mt-0.5 text-[11px] text-zinc-600 light:text-zinc-500">{edgeCaption}</div>
        </div>
      </div>
      <div className="border-t border-white/5 light:border-zinc-200">{pick}</div>
    </div>
  );
}

function PickStrip({ active, note, children }: { active: boolean; note?: string | null; children: React.ReactNode }) {
  if (active) {
    return (
      <div className="border-l-2 border-amber-400 bg-amber-400/[0.07] px-4 py-3">
        <div className="text-[10px] font-bold uppercase tracking-[0.16em] text-amber-400/90 light:text-amber-700">Model pick</div>
        <div className="mt-0.5 text-[15px] font-semibold text-amber-100 light:text-amber-800">{children}</div>
      </div>
    );
  }
  if (note) {
    return <div className="px-4 py-2.5 text-[13px] text-zinc-500 light:text-zinc-500">{note}</div>;
  }
  return <div className="px-4 py-2.5 text-[13px] text-zinc-600 light:text-zinc-500">No play — we agree with Vegas here.</div>;
}

function GameCard({ p }: { p: Pick }) {
  return (
    <article className="rounded-2xl border border-white/10 bg-gradient-to-b from-zinc-900/70 to-zinc-900/30 p-5 transition-colors hover:border-white/20 light:border-zinc-200 light:from-white light:to-zinc-50 light:hover:border-zinc-300">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex flex-wrap items-center gap-x-2.5 text-[17px] font-bold tracking-tight">
          <span className="inline-flex items-center gap-2">
            <NbaTeamLogo abbr={p.away_abbr} name={p.away} size={26} />{p.away}
          </span>
          <span className="text-sm font-medium text-zinc-600 light:text-zinc-400">@</span>
          <span className="inline-flex items-center gap-2">
            <NbaTeamLogo abbr={p.home_abbr} name={p.home} size={26} />{p.home}
          </span>
        </h2>
        <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-xs font-medium text-zinc-400 light:border-zinc-200 light:bg-zinc-100 light:text-zinc-600">
          {fmtGameday(p)}
        </span>
      </div>
      <MarketPanel
        name="Spread"
        ourLabel={fmtSpread(p.our_spread, p.home_abbr, p.away_abbr)}
        ourCaption="Our number"
        vegasLabel={fmtSpread(p.line_spread, p.home_abbr, p.away_abbr)}
        vegasCaption="Vegas line"
        edge={p.spread_edge}
        edgeCaption="pts of disagreement"
        pick={<PickStrip active={!!p.pick_spread}>{p.pick_spread ? spreadPickText(p) : null}</PickStrip>}
      />
      <MarketPanel
        name="Total"
        ourLabel={trim(p.our_total)}
        ourCaption="Our number"
        vegasLabel={trim(p.line_total)}
        vegasCaption="Vegas line"
        edge={p.total_edge}
        edgeCaption="pts of disagreement"
        pick={<PickStrip active={!!p.pick_total} note={p.pick_total_note}>{p.pick_total ? ouPickText(p) : null}</PickStrip>}
      />
    </article>
  );
}

type ParlayLeg = { game: string; market: "spread" | "total"; label: string; prob: number };
type Parlay = { legs: ParlayLeg[]; combined_prob: number; fair_odds: string; book_pays: string } | null;

function ParlayCard({ parlay, title }: { parlay: Parlay; title: string }) {
  if (!parlay || parlay.legs.length < 2) return null;
  return (
    <section className="mb-8 overflow-hidden rounded-2xl border border-amber-400/25 bg-gradient-to-b from-amber-400/[0.09] to-amber-400/[0.03]">
      <div className="flex flex-wrap items-baseline justify-between gap-2 px-5 pt-5">
        <div>
          <div className="text-[11px] font-bold uppercase tracking-[0.18em] text-amber-400/90 light:text-amber-700">For fun · not a strategy</div>
          <h2 className="mt-1 font-display text-3xl font-semibold uppercase tracking-wide">{title}</h2>
        </div>
        <span className="text-sm text-zinc-500">Our {parlay.legs.length} highest-conviction picks, combined</span>
      </div>
      <ul className="mt-4 space-y-2 px-5">
        {parlay.legs.map((l) => (
          <li key={`${l.game}-${l.market}`} className="flex items-center justify-between gap-3 rounded-xl border border-white/5 bg-zinc-950/70 px-4 py-2.5 light:border-zinc-200 light:bg-white">
            <div>
              <span className="font-bold text-amber-200 light:text-amber-700">{l.label}</span>
              <span className="ml-2 text-sm text-zinc-500">{l.game}</span>
            </div>
            <span className="tnum font-mono text-sm font-semibold text-zinc-300 light:text-zinc-700">{fmtPct(l.prob)}</span>
          </li>
        ))}
      </ul>
      <div className="mt-4 grid grid-cols-2 gap-3 px-5">
        <div className="rounded-xl border border-white/5 bg-zinc-950/70 p-3.5 light:border-zinc-200 light:bg-white">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">Model&rsquo;s combined chance</div>
          <div className="tnum mt-1 text-xl font-extrabold">{fmtPct(parlay.combined_prob)} <span className="text-sm font-semibold text-zinc-400 light:text-zinc-600">· fair odds {parlay.fair_odds}</span></div>
        </div>
        <div className="rounded-xl border border-white/5 bg-zinc-950/70 p-3.5 light:border-zinc-200 light:bg-white">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">Books typically pay</div>
          <div className="tnum mt-1 text-xl font-extrabold">{parlay.book_pays} <span className="text-sm font-semibold text-zinc-400 light:text-zinc-600">on {parlay.legs.length} legs</span></div>
        </div>
      </div>
      <p className="px-5 pb-5 pt-4 text-[13px] leading-relaxed text-zinc-400 light:text-zinc-600">
        The honest fine print: parlays multiply the book&rsquo;s edge along with the payout. And our model&rsquo;s
        confidence is unproven until the backtest says otherwise. Entertainment, not a strategy.
      </p>
    </section>
  );
}

function PendingNotice({ reason }: { reason?: string }) {
  return (
    <div className="rounded-2xl border border-amber-400/25 bg-amber-400/[0.06] p-8 text-center light:bg-amber-50">
      <div className="font-display text-2xl font-semibold uppercase tracking-wide">No card yet</div>
      <p className="mx-auto mt-3 max-w-xl text-[15px] leading-relaxed text-zinc-400 light:text-zinc-600">
        {reason ?? "No games on today's slate yet."} Check back soon — the pipeline, the model, and the backtest are all built.
        Only the data connection is missing.
      </p>
    </div>
  );
}

function winPct(w: number, l: number): number | null {
  return w + l === 0 ? null : w / (w + l);
}

function SeasonRecord({ days, href }: { days: DayView[]; href: string }) {
  let aw = 0, al = 0, ap = 0, ow = 0, ol = 0, op = 0;
  for (const d of days)
    for (const p of d.picks) {
      const r = p.result;
      if (r?.ats === "win") aw++; else if (r?.ats === "loss") al++; else if (r?.ats === "push") ap++;
      if (r?.ou === "win") ow++; else if (r?.ou === "loss") ol++; else if (r?.ou === "push") op++;
    }
  if (aw + al + ow + ol === 0) return null;
  const card = "rounded-xl border border-white/10 bg-zinc-900/50 p-4 transition-colors hover:border-amber-400/40 light:border-zinc-200 light:bg-white";
  return (
    <a href={href} className="mb-8 grid max-w-2xl grid-cols-2 gap-3" aria-label="Season record — full track record">
      <div className={card}>
        <div className="tnum text-xl font-extrabold">
          {aw}-{al}-{ap}
          <span className="ml-2 text-sm font-semibold text-zinc-400 light:text-zinc-600">{fmtPct(winPct(aw, al))}</span>
        </div>
        <div className="mt-1 text-xs text-zinc-500">ATS this season →</div>
      </div>
      <div className={card}>
        <div className="tnum text-xl font-extrabold">
          {ow}-{ol}-{op}
          <span className="ml-2 text-sm font-semibold text-zinc-400 light:text-zinc-600">{fmtPct(winPct(ow, ol))}</span>
        </div>
        <div className="mt-1 text-xs text-zinc-500">O/U this season →</div>
      </div>
    </a>
  );
}

export default function NbaHome() {
  const [sel, setSel] = useState(0);
  const dv = allDays[sel] ?? currentDay;
  const picks = dv.picks;
  const isPending = !!dv.pending || picks.length === 0;
  const nSpread = picks.filter((p) => p.pick_spread).length;
  const nTotal = picks.filter((p) => p.pick_total).length;
  const seasonLabel = `${dv.season - 1}–${String(dv.season).slice(2)}`;
  const showPreseason = dv.preseason === true || !!dv.experimental_note;

  return (
    <div>
      <div className="mb-8">
        <Eyebrow>
          NBA · {seasonLabel} season
          {dv.date ? ` · ${fmtSlateDate(dv.date)}` : ""}
          {dv.generated ? ` · generated ${dv.generated}` : ""}
          {!dv.isCurrent && !dv.complete && (
            <span className="ml-2 rounded bg-zinc-500/15 px-2 py-0.5 text-zinc-400 light:text-zinc-600">partial</span>
          )}
        </Eyebrow>
        <h1 className="mt-3 font-display text-5xl font-semibold uppercase leading-[0.95] tracking-wide sm:text-6xl">
          {dv.isCurrent ? (
            <>NBA <span className="text-amber-400 light:text-amber-600">picks</span></>
          ) : (
            <><span className="text-amber-400 light:text-amber-600">{fmtSlateDate(dv.date)}</span> slate</>
          )}
        </h1>
        {allDays.length > 1 && (
          <div className="mt-4 flex flex-wrap gap-2" role="tablist" aria-label="Browse days">
            {allDays.map((d, i) => (
              <button
                key={d.date ?? "current"}
                role="tab"
                aria-selected={i === sel}
                onClick={() => setSel(i)}
                className={`rounded-full border px-3.5 py-1.5 text-sm font-semibold transition ${
                  i === sel
                    ? "border-amber-400 bg-amber-400/15 text-amber-200 light:border-amber-600 light:bg-amber-600/10 light:text-amber-700"
                    : "border-zinc-800 bg-zinc-900 text-zinc-400 hover:border-zinc-600 hover:text-zinc-200 light:border-zinc-200 light:bg-white light:text-zinc-600 light:hover:border-zinc-400"
                }`}
              >
                {d.isCurrent ? `${fmtSlateDate(d.date)} · today` : fmtSlateDate(d.date)}
              </button>
            ))}
          </div>
        )}
        <p className="mt-4 max-w-2xl text-[15px] leading-relaxed text-zinc-400 light:text-zinc-600">
          Tonight&rsquo;s slate from a margin-adjusted Elo — home edge 2.75, k=26, prior-season
          carryover — with an offensive/defensive efficiency totals model and a rest-day
          adjustment. The model never sees the betting line; the line is only the
          benchmark we measure against. Same honesty rules as every sport here: every pick published
          before tip-off, every result graded in public.
        </p>
        {showPreseason && (
          <div className="mt-5 max-w-2xl rounded-xl border border-sky-400/30 bg-sky-400/10 px-4 py-3 light:bg-sky-50">
            <div className="text-xs font-bold uppercase tracking-[0.16em] text-sky-300 light:text-sky-700">Preseason — experimental</div>
            <p className="mt-1 text-sm leading-relaxed text-sky-200/90 light:text-sky-800">
              {dv.experimental_note ?? "The model is running before it has seen a real regular-season game. Treat these numbers as a calibration exercise, not as picks."}
            </p>
          </div>
        )}
        {isPending ? (
          <div className="mt-6"><PendingNotice reason={dv.pending_reason} /></div>
        ) : (
          <>
            <div className="mt-5 flex flex-wrap gap-x-8 gap-y-3">
              {[[String(picks.length), "games"], [String(nSpread), "spread plays"], [String(nTotal), "total plays"]].map(([v, l]) => (
                <div key={l} className="flex items-baseline gap-2">
                  <span className="tnum font-display text-3xl font-semibold text-zinc-100 light:text-zinc-900">{v}</span>
                  <span className="text-xs font-medium uppercase tracking-wider text-zinc-500">{l}</span>
                </div>
              ))}
            </div>
            <p className="mt-5 max-w-2xl rounded-xl border border-amber-400/25 bg-amber-400/10 px-4 py-3 text-sm leading-relaxed text-amber-200/90 light:text-amber-800">
              {dv.isCurrent ? dv.disclaimer : "Graded results — every pick marked won, lost, or push. Nothing hidden, nothing rewritten."}
            </p>
          </>
        )}
      </div>

      {!isPending && <SeasonRecord days={allDays} href="/nba/track-record" />}

      {!isPending && <ParlayCard parlay={dv.parlay ?? null} title="Parlay of the night" />}

      {!isPending && picks.length > 0 && (
        <>
          <div className="mb-4 flex items-baseline justify-between">
            <h2 className="font-display text-2xl font-semibold uppercase tracking-wide">Every game</h2>
            <span className="text-sm text-zinc-500">Model vs. Vegas, side by side</span>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {picks.map((p) => <GameCard key={`${p.away}-${p.home}`} p={p} />)}
          </div>
        </>
      )}
    </div>
  );
}
