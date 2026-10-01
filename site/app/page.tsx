import picksData from "../data/picks.json";
import { fmtSpread, fmtPct, trim } from "./lib/format";
import TeamLogo from "./lib/team-logo";

type Pick = {
  away: string; home: string; away_abbr: string; home_abbr: string;
  gameday: string; weekday: string;
  line_spread: number; line_total: number;
  our_spread: number; our_total: number;
  spread_edge: number; total_edge: number;
  pick_spread: "home" | "away" | null;
  pick_total: "over" | "under" | null;
  pick_spread_label: string | null;
  pick_total_label: string | null;
  cover_prob: number | null; ou_prob: number | null;
  home_qb: string | null; away_qb: string | null;
};

const picks = picksData.picks as Pick[];

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
function edgeLabel(edge: number): string {
  // Absolute: direction is already conveyed by the pick pill.
  return `${trim(Math.abs(edge))}`;
}

function PickPill({ children, active }: { children: React.ReactNode; active: boolean }) {
  return (
    <span
      className={
        active
          ? "inline-block rounded-full bg-amber-400/15 px-3 py-1 text-sm font-bold text-amber-300"
          : "inline-block rounded-full bg-zinc-800/60 px-3 py-1 text-sm font-medium text-zinc-500"
      }
    >
      {children}
    </span>
  );
}

function GameCard({ p }: { p: Pick }) {
  return (
    <article className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-5">
      {/* Header: matchup + date */}
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="flex flex-wrap items-center gap-x-2 text-lg font-bold tracking-tight">
          <span className="inline-flex items-center gap-1.5">
            <TeamLogo abbr={p.away_abbr} />
            {p.away}
          </span>
          <span className="font-medium text-zinc-500">@</span>
          <span className="inline-flex items-center gap-1.5">
            <TeamLogo abbr={p.home_abbr} />
            {p.home}
          </span>
        </h2>
        <span className="text-sm text-zinc-500">{fmtGameday(p)}</span>
      </div>
      {(p.away_qb || p.home_qb) && (
        <p className="mt-1 text-xs text-zinc-500">
          {p.away_abbr}: {p.away_qb ?? "—"} · {p.home_abbr}: {p.home_qb ?? "—"}
        </p>
      )}

      {/* Spread row */}
      <div className="mt-4 grid grid-cols-3 gap-2 rounded-xl bg-zinc-950/60 p-3">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">Spread</div>
          <div className="mt-1 font-mono text-sm font-semibold">
            {fmtSpread(p.our_spread, p.home_abbr, p.away_abbr)}
          </div>
          <div className="text-[11px] text-zinc-500">Our number</div>
        </div>
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">&nbsp;</div>
          <div className="mt-1 font-mono text-sm text-zinc-400">
            {fmtSpread(p.line_spread, p.home_abbr, p.away_abbr)}
          </div>
          <div className="text-[11px] text-zinc-500">Vegas line</div>
        </div>
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">&nbsp;</div>
          <div className="mt-1 font-mono text-sm text-zinc-400">
            edge {edgeLabel(p.spread_edge)}
          </div>
          <div className="text-[11px] text-zinc-500">pts of disagreement</div>
        </div>
      </div>
      <div className="mt-2">
        <PickPill active={!!p.pick_spread}>
          {p.pick_spread ? `Pick: ${spreadPickText(p)}` : "No spread play — we agree with Vegas"}
        </PickPill>
      </div>

      {/* Total row */}
      <div className="mt-3 grid grid-cols-3 gap-2 rounded-xl bg-zinc-950/60 p-3">
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">Total</div>
          <div className="mt-1 font-mono text-sm font-semibold">{trim(p.our_total)}</div>
          <div className="text-[11px] text-zinc-500">Our number</div>
        </div>
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">&nbsp;</div>
          <div className="mt-1 font-mono text-sm text-zinc-400">{trim(p.line_total)}</div>
          <div className="text-[11px] text-zinc-500">Vegas line</div>
        </div>
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">&nbsp;</div>
          <div className="mt-1 font-mono text-sm text-zinc-400">
            edge {edgeLabel(p.total_edge)}
          </div>
          <div className="text-[11px] text-zinc-500">pts of disagreement</div>
        </div>
      </div>
      <div className="mt-2">
        <PickPill active={!!p.pick_total}>
          {p.pick_total ? `Pick: ${ouPickText(p)}` : "No total play — we agree with Vegas"}
        </PickPill>
      </div>
    </article>
  );
}

type ParlayLeg = {
  game: string; market: "spread" | "total"; label: string; prob: number;
};
type Parlay = {
  legs: ParlayLeg[]; combined_prob: number; fair_odds: string; book_pays: string;
} | null;

function ParlayCard({ parlay }: { parlay: Parlay }) {
  if (!parlay || parlay.legs.length < 2) return null;
  return (
    <section className="mb-6 rounded-2xl border border-amber-400/30 bg-amber-400/[0.06] p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-xl font-extrabold tracking-tight">
          Parlay of the week{" "}
          <span className="ml-1 rounded bg-zinc-800 px-2 py-0.5 align-middle text-[11px] font-bold uppercase tracking-wider text-zinc-400">
            for fun
          </span>
        </h2>
        <span className="text-sm text-zinc-500">
          Our {parlay.legs.length} highest-conviction picks, combined
        </span>
      </div>

      <ul className="mt-4 space-y-2">
        {parlay.legs.map((l) => (
          <li
            key={`${l.game}-${l.market}`}
            className="flex items-center justify-between gap-3 rounded-xl bg-zinc-950/60 px-4 py-2.5"
          >
            <div>
              <span className="font-bold text-amber-200">{l.label}</span>
              <span className="ml-2 text-sm text-zinc-500">{l.game}</span>
            </div>
            <span className="font-mono text-sm font-semibold text-zinc-300">
              {fmtPct(l.prob)}
            </span>
          </li>
        ))}
      </ul>

      <div className="mt-4 grid grid-cols-2 gap-3">
        <div className="rounded-xl bg-zinc-950/60 p-3">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">
            Model&rsquo;s combined chance
          </div>
          <div className="mt-1 text-lg font-extrabold">
            {fmtPct(parlay.combined_prob)}{" "}
            <span className="text-sm font-semibold text-zinc-400">
              · fair odds {parlay.fair_odds}
            </span>
          </div>
        </div>
        <div className="rounded-xl bg-zinc-950/60 p-3">
          <div className="text-[11px] font-semibold uppercase tracking-wider text-zinc-500">
            Books typically pay
          </div>
          <div className="mt-1 text-lg font-extrabold">
            {parlay.book_pays}{" "}
            <span className="text-sm font-semibold text-zinc-400">
              on {parlay.legs.length} legs
            </span>
          </div>
        </div>
      </div>

      <p className="mt-4 text-[13px] leading-relaxed text-zinc-400">
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
  const nSpread = picks.filter((p) => p.pick_spread).length;
  const nTotal = picks.filter((p) => p.pick_total).length;

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-3xl font-extrabold tracking-tight">
          Week {picksData.week} picks{" "}
          <span className="font-medium text-zinc-500">· {picksData.season} season</span>
        </h1>
        <p className="mt-2 max-w-2xl text-[15px] leading-relaxed text-zinc-400">
          {picks.length} games, {nSpread} spread plays and {nTotal} total plays.
          Generated {picksData.generated} from opponent-adjusted EPA ratings —
          the model never sees the betting line; the line is only the benchmark
          we measure against. Lines are a snapshot from generation time and
          don’t update mid-week — every pick is graded against the line shown here.
        </p>
        <p className="mt-3 max-w-2xl rounded-xl border border-amber-400/25 bg-amber-400/10 px-4 py-3 text-sm leading-relaxed text-amber-200/90">
          {picksData.disclaimer}
        </p>
      </div>

      <ParlayCard parlay={(picksData as { parlay?: Parlay }).parlay ?? null} />

      <div className="grid gap-4 md:grid-cols-2">
        {picks.map((p) => (
          <GameCard key={`${p.away_abbr}-${p.home_abbr}`} p={p} />
        ))}
      </div>

      <p className="mt-6 max-w-2xl text-sm leading-relaxed text-zinc-500">
        How to read a card: <span className="text-zinc-300">Our number</span> is what the
        model thinks the spread or total should be; <span className="text-zinc-300">Vegas line</span> is
        the market. A pick appears only where we disagree by enough to matter —
        the percentage is our estimated chance that side covers or the total lands.
      </p>
    </div>
  );
}
