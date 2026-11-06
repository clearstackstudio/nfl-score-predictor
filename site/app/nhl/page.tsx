"use client";
import { useState } from "react";
import picksData from "../../data/nhl_picks.json";
import seasonLog from "../../data/nhl_season_2027.json";
import { fmtPct, trim } from "../lib/format";
import NhlTeamLogo from "../lib/nhl-team-logo";
import Expandable from "../lib/expandable";
import AdSlot from "../lib/ad-slot";

type PickResult = {
  home_score: number; away_score: number;
  su?: "win" | "loss" | null;
} | null;

type Pick = {
  away: string; home: string; away_abbr: string; home_abbr: string;
  game_id: number; gameday: string; weekday: string; start_time_pt?: string;
  home_ml: number | null; away_ml: number | null;
  market_p_home: number | null; market_p_away: number | null;
  p_home_raw: number; p_home_cal: number; p_away_cal: number;
  model_total: number; total_line: number | null;
  pick_side: "home" | "away" | null;
  pick_label: string | null; pick_prob: number | null;
  edge_pp: number | null;
  result?: PickResult;
};

type PicksFile = {
  sport: string; season: number | null; date?: string | null;
  generated: string | null; disclaimer: string;
  preseason?: boolean; experimental_note?: string | null;
  pending_reason?: string;
  parlay?: null; picks: Pick[];
};

const data = picksData as unknown as PicksFile;

type DayLog = {
  date: string; generated: string | null;
  preseason?: boolean; experimental_note?: string | null;
  graded: boolean; complete: boolean;
  picks: Pick[]; parlay: null;
};
type SeasonLog = { sport: string; season: number; days: Record<string, DayLog> };

type DayView = {
  date: string | null; season: number | null; generated: string | null;
  picks: Pick[]; disclaimer: string;
  preseason?: boolean; experimental_note?: string | null;
  pending_reason?: string;
  isCurrent: boolean; complete: boolean;
};

const season = (seasonLog as unknown as SeasonLog).season;

const currentDay: DayView = {
  date: data.date ?? null,
  season: data.season ?? season,
  generated: data.generated,
  picks: data.picks,
  disclaimer: data.disclaimer,
  preseason: data.preseason,
  experimental_note: data.experimental_note,
  pending_reason: data.pending_reason,
  isCurrent: true,
  complete: false,
};

const pastDays: DayView[] = Object.entries((seasonLog as unknown as SeasonLog).days)
  .filter(([dk]) => dk !== data.date) // season log also holds the current day
  .map(([, d]) => ({
    date: d.date,
    season,
    generated: d.generated,
    picks: d.picks,
    disclaimer: "",
    preseason: d.preseason,
    experimental_note: d.experimental_note,
    isCurrent: false,
    complete: d.complete,
  }))
  .sort((a, b) => (b.date ?? "").localeCompare(a.date ?? ""));

const allDays: DayView[] = [currentDay, ...pastDays];

function fmtGameday(p: Pick): string {
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

function fmtMl(ml: number | null | undefined): string {
  if (ml == null) return "—";
  const v = Number(ml);
  const s = Number.isInteger(v) ? String(v) : String(Math.round(v * 100) / 100);
  return v > 0 ? `+${s}` : s;
}

function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3 text-xs font-semibold uppercase tracking-[0.18em] text-red-500/90 light:text-red-700">
      <span className="h-px w-8 bg-red-500/60 light:bg-red-600/70" aria-hidden="true" />
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
          <div className="tnum mt-1.5 font-mono text-[15px] font-semibold text-zinc-400 light:text-zinc-600">{vegasLabel}</div>
          <div className="mt-0.5 text-[11px] text-zinc-600 light:text-zinc-500">{vegasCaption}</div>
        </div>
        <div className="p-3.5">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">Disagreement</div>
          <div className="tnum mt-1.5 font-mono text-[15px] font-semibold text-zinc-400 light:text-zinc-600">{trim(Math.abs(edge))} pts</div>
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
      <div className="border-l-2 border-red-500 bg-red-500/[0.07] px-4 py-3">
        <div className="text-[10px] font-bold uppercase tracking-[0.16em] text-red-500/90 light:text-red-700">Model pick</div>
        <div className="mt-0.5 text-[15px] font-semibold text-red-100 light:text-red-800">{children}</div>
      </div>
    );
  }
  if (note) {
    return <div className="px-4 py-2.5 text-[13px] text-zinc-500 light:text-zinc-500">{note}</div>;
  }
  return <div className="px-4 py-2.5 text-[13px] text-zinc-600 light:text-zinc-500">No play — we agree with Vegas here.</div>;
}

function GameCard({ p }: { p: Pick }) {
  const totalEdge = p.total_line != null ? p.model_total - p.total_line : null;
  return (
    <article className="rounded-2xl border border-white/10 bg-gradient-to-b from-zinc-900/70 to-zinc-900/30 p-5 transition-colors hover:border-white/20 light:border-zinc-200 light:from-white light:to-zinc-50 light:hover:border-zinc-300">
      <Expandable>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="flex flex-wrap items-center gap-x-2.5 text-[17px] font-bold tracking-tight">
          <span className="inline-flex items-center gap-2">
            <NhlTeamLogo abbr={p.away_abbr} name={p.away} size={26} />{p.away}
          </span>
          <span className="text-sm font-medium text-zinc-600 light:text-zinc-400">@</span>
          <span className="inline-flex items-center gap-2">
            <NhlTeamLogo abbr={p.home_abbr} name={p.home} size={26} />{p.home}
          </span>
        </h2>
        <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-xs font-medium text-zinc-400 light:border-zinc-200 light:bg-zinc-100 light:text-zinc-600">
          {fmtGameday(p)}
        </span>
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-xs font-medium text-zinc-400 light:text-zinc-600">
        <span className="tnum rounded-full border border-white/10 bg-white/5 px-2.5 py-1 font-mono light:border-zinc-200 light:bg-zinc-100">
          {p.away_abbr} {fmtMl(p.away_ml)}
        </span>
        <span className="tnum rounded-full border border-white/10 bg-white/5 px-2.5 py-1 font-mono light:border-zinc-200 light:bg-zinc-100">
          {p.home_abbr} {fmtMl(p.home_ml)}
        </span>
        <span className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 light:border-zinc-200 light:bg-zinc-100">
          Moneyline · median across books
        </span>
      </div>
      <MarketPanel
        name="Moneyline"
        ourLabel={fmtPct(p.p_home_cal)}
        ourCaption={`Our win probability — ${p.home}`}
        vegasLabel={p.market_p_home != null ? fmtPct(p.market_p_home) : "—"}
        vegasCaption="Vegas implied, vig removed"
        edge={p.edge_pp ?? 0}
        edgeCaption="pts of disagreement"
        pick={
          <PickStrip active={!!p.pick_side}>
            {p.pick_side ? `${p.pick_label} · ${fmtPct(p.pick_prob)} to win` : null}
          </PickStrip>
        }
      />
      <MarketPanel
        name="Total"
        ourLabel={trim(Math.round(p.model_total * 100) / 100)}
        ourCaption="Our expected goals"
        vegasLabel={p.total_line != null ? trim(p.total_line) : "—"}
        vegasCaption="Vegas total"
        edge={totalEdge ?? 0}
        edgeCaption="goals of disagreement"
        pick={
          <PickStrip
            active={false}
            note="Context only — we don't publish NHL totals picks, and no totals record is kept. The model's total is shown so the disagreement is visible, nothing more."
          >
            {null}
          </PickStrip>
        }
      />
      </Expandable>
    </article>
  );
}

function PendingNotice({ reason }: { reason?: string }) {
  return (
    <div className="rounded-2xl border border-red-500/25 bg-red-500/[0.06] p-8 text-center light:bg-red-50">
      <div className="font-display text-2xl font-semibold uppercase tracking-wide">No card yet</div>
      <p className="mx-auto mt-3 max-w-xl text-[15px] leading-relaxed text-zinc-400 light:text-zinc-600">
        {reason ?? "No games on today's slate."} Check back soon — boards publish the
        night before, and every result lands on the track record.
      </p>
    </div>
  );
}

function winPct(w: number, l: number): number | null {
  return w + l === 0 ? null : w / (w + l);
}

function SeasonRecord({ days, href }: { days: DayView[]; href: string }) {
  let w = 0, l = 0;
  for (const d of days)
    for (const p of d.picks) {
      const r = p.result;
      if (r?.su === "win") w++; else if (r?.su === "loss") l++;
    }
  if (w + l === 0) return null;
  const card = "rounded-xl border border-white/10 bg-zinc-900/50 p-4 transition-colors hover:border-red-500/40 light:border-zinc-200 light:bg-white";
  return (
    <a href={href} className="mb-8 grid max-w-2xl grid-cols-1 gap-3 sm:grid-cols-2" aria-label="Season record — full track record">
      <div className={card}>
        <div className="tnum text-xl font-extrabold">
          {w}-{l}
          <span className="ml-2 text-sm font-semibold text-zinc-400 light:text-zinc-600">{fmtPct(winPct(w, l))}</span>
        </div>
        <div className="mt-1 text-xs text-zinc-500">Moneyline picks this season →</div>
      </div>
      <div className="rounded-xl border border-white/10 bg-zinc-900/50 p-4 light:border-zinc-200 light:bg-white">
        <div className="text-xl font-extrabold text-zinc-400 light:text-zinc-600">Totals: context only</div>
        <div className="mt-1 text-xs leading-relaxed text-zinc-500">
          Model totals are shown for context — no totals picks, no totals record. <span className="underline">Why →</span>
        </div>
      </div>
    </a>
  );
}

export default function NhlHome() {
  const [sel, setSel] = useState(0);
  const dv = allDays[sel] ?? currentDay;
  const picks = dv.picks;
  const isPending = picks.length === 0;
  const nPlays = picks.filter((p) => p.pick_side).length;
  const seasonLabel = dv.season ? `${dv.season - 1}–${String(dv.season).slice(2)}` : "";

  return (
    <div>
      <AdSlot format="leaderboard" league="nhl" />
      <div className="mb-8">
        <Eyebrow>
          NHL · {seasonLabel} season
          {dv.date ? ` · ${fmtSlateDate(dv.date)}` : ""}
          {dv.generated ? ` · generated ${dv.generated}` : ""}
          {!dv.isCurrent && !dv.complete && (
            <span className="ml-2 rounded bg-zinc-500/15 px-2 py-0.5 text-zinc-400 light:text-zinc-600">partial</span>
          )}
        </Eyebrow>
        <h1 className="mt-3 font-display text-5xl font-semibold uppercase leading-[0.95] tracking-wide sm:text-6xl">
          {dv.isCurrent ? (
            <>NHL <span className="text-red-500 light:text-red-600">picks</span></>
          ) : (
            <><span className="text-red-500 light:text-red-600">{fmtSlateDate(dv.date)}</span> slate</>
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
                    ? "border-red-500 bg-red-500/15 text-red-200 light:border-red-600 light:bg-red-600/10 light:text-red-700"
                    : "border-zinc-800 bg-zinc-900 text-zinc-400 hover:border-zinc-600 hover:text-zinc-200 light:border-zinc-200 light:bg-white light:text-zinc-600 light:hover:border-zinc-400"
                }`}
              >
                {d.isCurrent ? `${fmtSlateDate(d.date)} · today` : fmtSlateDate(d.date)}
              </button>
            ))}
          </div>
        )}
        <p className="mt-4 max-w-2xl text-[15px] leading-relaxed text-zinc-400 light:text-zinc-600">
          Tonight&rsquo;s slate from an expected-goals ratings model — team offense and
          defense ratings fitted on MoneyPuck expected goals, a 0.20-goal home-ice term,
          a rest-day term, and a calibration map fitted on 4,573 games. The model never
          sees the betting line; the line is only the benchmark we measure against. A
          moneyline pick publishes when model and market disagree by 2 points or more.
          Same honesty rules as every sport here: every pick published before puck drop,
          every result graded in public.
        </p>
        <div className="mt-5 max-w-2xl rounded-xl border border-zinc-700/60 bg-zinc-900/60 px-4 py-3 light:border-zinc-300 light:bg-zinc-100">
          <div className="text-xs font-bold uppercase tracking-[0.16em] text-zinc-300 light:text-zinc-700">Totals are context only</div>
          <p className="mt-1 text-sm leading-relaxed text-zinc-400 light:text-zinc-600">
            Each card shows the model&rsquo;s expected total next to the market total, but
            we publish no totals picks and keep no totals record. Before launch the model
            ran 16 nights in shadow — 110 games frozen and graded — and finished in an
            effective tie with the market. The full record, including the one game
            excluded from market comparisons and why, is on the{" "}
            <a href="/nhl/track-record" className="underline">track record</a>.
          </p>
        </div>
        {isPending ? (
          <div className="mt-6"><PendingNotice reason={dv.pending_reason} /></div>
        ) : (
          <>
            <div className="mt-5 flex flex-wrap gap-x-8 gap-y-3">
              {[[String(picks.length), "games"], [String(nPlays), "moneyline plays"]].map(([v, l]) => (
                <div key={l} className="flex items-baseline gap-2">
                  <span className="tnum font-display text-3xl font-semibold text-zinc-100 light:text-zinc-900">{v}</span>
                  <span className="text-xs font-medium uppercase tracking-wider text-zinc-500">{l}</span>
                </div>
              ))}
            </div>
            <p className="mt-5 max-w-2xl rounded-xl border border-red-500/25 bg-red-500/10 px-4 py-3 text-sm leading-relaxed text-red-200/90 light:text-red-800">
              {dv.isCurrent ? dv.disclaimer : "Graded results — every pick marked won or lost. Nothing hidden, nothing rewritten."}
            </p>
          </>
        )}
      </div>

      {!isPending && <SeasonRecord days={allDays} href="/nhl/track-record" />}

      <AdSlot format="rectangle" league="nhl" />

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
